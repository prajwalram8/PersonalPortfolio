#!/usr/bin/env python3.12
"""Deploy a Git revision on a single-host Gunicorn and Nginx installation."""

import argparse
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import signal
import sqlite3
import subprocess
import sys
from time import monotonic, sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import uuid4


REPO = Path(__file__).resolve().parents[1]
UNIT = "personalportfolio.service"
LOOPBACK = "http://127.0.0.1:5000"
SETTING_NAMES = {"PORTFOLIO_ENV", "PORTFOLIO_SECRET_KEY", "PORTFOLIO_TRUSTED_HOSTS", "PORTFOLIO_TRUST_PROXY"}
LEGACY_TABLES = {
    "user": {"id", "username", "password"},
    "category": {"id", "category", "subcategory"},
    "markdown_file": {"id", "name", "category_id", "content", "upload_date", "modification_date", "author_name"},
    "contact_submissions": {"id", "name", "email", "subject", "message"},
}


class DeploymentError(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def https_origin(value):
    address = urlsplit(value)
    if (address.scheme != "https" or not address.hostname or address.username or address.password
            or address.path not in {"", "/"} or address.query or address.fragment):
        raise argparse.ArgumentTypeError("Use a public HTTPS origin such as https://portfolio.example.com.")
    return value.rstrip("/")


def fetch(origin, path, host=None, size=0):
    headers = {"Cache-Control": "no-cache"}
    handlers = [NoRedirect()]
    if host:
        headers.update(Host=host, **{"X-Forwarded-Proto": "https"})
        handlers.append(ProxyHandler({}))
    request = Request(origin + path, headers=headers, method="GET" if size else "HEAD")
    try:
        with build_opener(*handlers).open(request, timeout=5) as response:
            return response.status, response.headers, response.read(size)
    except HTTPError as response:
        with response:
            return response.code, response.headers, b""
    except (URLError, TimeoutError, OSError) as error:
        raise DeploymentError(f"{origin}{path}: {error}") from error


def require(condition, message):
    if not condition:
        raise DeploymentError(message)


def site_check(origin, host=None):
    for path in ("/", "/writing", "/resume", "/resume.pdf", "/contact", "/admin"):
        size = 64 * 1024 if path == "/contact" else (5 if path == "/resume.pdf" else 0)
        status, headers, body = fetch(origin, path, host, size)
        expected = 302 if path == "/admin" else 200
        require(status == expected, f"{origin}{path} returned HTTP {status}; expected {expected}.")
        require(headers.get("Strict-Transport-Security")
                and "frame-ancestors 'none'" in headers.get("Content-Security-Policy", "")
                and headers.get("X-Content-Type-Options") == "nosniff",
                f"{origin}{path} is missing HTTPS or browser security headers.")
        if path == "/admin":
            destination = urlsplit(headers.get("Location", "")).path
            require(destination == "/admin/login" and "no-store" in headers.get("Cache-Control", ""),
                    "The studio did not redirect to the private login page.")
        elif path == "/resume.pdf":
            require(headers.get_content_type() == "application/pdf" and body == b"%PDF-",
                    "The résumé download did not return a PDF.")
        elif path == "/contact":
            cookie = headers.get("Set-Cookie", "").lower()
            require(b'name="csrf_token"' in body and all(flag in cookie for flag in ("; secure", "; httponly", "; samesite=lax")),
                    "The contact form did not set a protected session and CSRF token.")
    print(f"Launch checks passed for {host or origin}.", flush=True)


def wait_for_home(host):
    deadline = monotonic() + 25
    while True:
        try:
            status, _, _ = fetch(LOOPBACK, "/", host)
            if status == 200:
                return
            failure = DeploymentError(f"The app returned HTTP {status} on loopback.")
        except DeploymentError as error:
            failure = error
        if monotonic() >= deadline:
            raise failure
        sleep(.5)


def check_gate(origin):
    status, headers, _ = fetch(origin, f"/?portfolio-maintenance={uuid4().hex}")
    require(status == 503 and headers.get("X-Portfolio-Maintenance") == "1",
            "The public URL did not report this deployment's maintenance gate. Check the Nginx configuration.")


def read_settings(path, origin=None):
    require(path.stat().st_mode & 0o077 == 0, f"Restrict {path} to the deployment user with chmod 600.")
    settings = {}
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, separator, value = line.partition("=")
        require(separator and name in SETTING_NAMES and name not in settings and value and
                not any(char.isspace() or char in "'\"\\`$${}" for char in value),
                f"Use the documented unquoted KEY=value format in {path}.")
        settings[name] = value
    require(settings.get("PORTFOLIO_ENV") == "production" and settings.get("PORTFOLIO_TRUST_PROXY") == "1"
            and len(settings.get("PORTFOLIO_SECRET_KEY", "")) >= 32 and settings.get("PORTFOLIO_TRUSTED_HOSTS"),
            f"Set all four production settings in {path}.")
    if origin:
        require(urlsplit(origin).hostname in settings["PORTFOLIO_TRUSTED_HOSTS"].split(","),
                "The public origin must be a hostname in PORTFOLIO_TRUSTED_HOSTS.")
    return settings


def verify_legacy(database):
    """Accept only the application schema made by the original init-db command."""
    with closing(sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)) as connection:
        tables = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )}
        if "alembic_version" in tables:
            require(not connection.execute("SELECT 1 FROM alembic_version").fetchone(),
                    "This database already has a migration revision. Remove --legacy-init-db.")
            tables.remove("alembic_version")
        require(tables == LEGACY_TABLES.keys(), "The imported database does not match the original init-db schema.")
        for table, columns in LEGACY_TABLES.items():
            actual = {row[1]: row[2] for row in connection.execute(f"PRAGMA table_info({table})")}
            expected_id_type = "INTEGER" if table == "contact_submissions" else "VARCHAR(36)"
            require(actual.keys() == columns and actual["id"].upper() == expected_id_type,
                    "The imported database does not match the original init-db schema.")


class Deployment:
    def __init__(self, root, gate):
        self.root = root
        self.gate = gate
        self.releases = root / "releases"
        self.current = root / "current"
        self.journal = root / "deployment.json"

    @contextmanager
    def lock(self):
        self.root.mkdir(mode=0o700, exist_ok=True)
        self.root.chmod(0o700)
        with (self.root / "deploy.lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise DeploymentError("Another deployment command is running.") from error
            yield

    def active_release(self):
        if not self.current.is_symlink():
            require(not self.current.exists(), f"{self.current} must be a release symlink.")
            return None
        release = self.current.resolve()
        require(release.parent == self.releases and release.is_dir() and
                (release / "database.sqlite").is_file(),
                f"{self.current} does not point to a valid release and database.")
        return release

    def switch(self, release):
        if release is None:
            self.current.unlink(missing_ok=True)
            return
        temporary = self.root / f".current-{uuid4().hex}"
        try:
            temporary.symlink_to(release)
            temporary.replace(self.current)
        finally:
            temporary.unlink(missing_ok=True)

    def unit(self, action, *, check=True):
        return subprocess.run(["systemctl", "--user", action, UNIT], check=check,
                              stdout=None if check else subprocess.DEVNULL)

    def verify_running_release(self, release):
        pid = subprocess.check_output(
            ["systemctl", "--user", "show", "--property=MainPID", "--value", UNIT], text=True,
        ).strip()
        require(pid.isdigit() and int(pid) > 0, f"{UNIT} is not running.")
        require(Path(f"/proc/{pid}/cwd").resolve(strict=True) == release,
                f"{UNIT} is serving from a different directory than the selected release.")

    def flask(self, release, database, *args):
        env = os.environ | self.settings | {"PORTFOLIO_DATABASE": str(database)}
        subprocess.run([str(release / ".venv/bin/python"), "-m", "flask", "--app", "wsgi", *args],
                       cwd=release, env=env, check=True)

    def stage(self, ref):
        if ref.startswith("origin/"):
            remote_ref = "refs/heads/" + ref.removeprefix("origin/")
            subprocess.run(["git", "check-ref-format", remote_ref], cwd=REPO, check=True)
        else:
            require(re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", ref),
                    "Use origin/<branch> or a full commit SHA.")
            remote_ref = ref
        subprocess.run(["git", "fetch", "--no-tags", "origin", remote_ref], cwd=REPO, check=True)
        revision = subprocess.check_output(
            ["git", "rev-parse", "--verify", "FETCH_HEAD^{commit}"], text=True, cwd=REPO,
        ).strip()
        name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + revision[:12] + "-" + uuid4().hex[:6]
        release = self.releases / name
        release.mkdir()
        # Git's archive excludes the checkout's untracked files and secrets.
        archive = self.root / f".{name}.tar"
        try:
            subprocess.run(["git", "archive", "--format=tar", "-o", str(archive), revision], cwd=REPO, check=True)
            subprocess.run(["tar", "-xf", str(archive), "-C", str(release)], check=True)
        finally:
            archive.unlink(missing_ok=True)
        subprocess.run([sys.executable, "-m", "venv", str(release / ".venv")], check=True)
        subprocess.run([str(release / ".venv/bin/python"), "-m", "pip", "install",
                        "--disable-pip-version-check", "--no-input", "-r", "requirements.txt"],
                       cwd=release, check=True)
        subprocess.run([str(release / ".venv/bin/python"), "-m", "pip", "check"], check=True)
        print(f"Staged {revision}.", flush=True)
        return release

    def record(self, previous, was_active, origin):
        with self.journal.open("x") as file:
            json.dump({"previous": previous.name if previous else None, "was_active": was_active, "url": origin}, file)
            file.flush()
            os.fsync(file.fileno())

    def reopen(self):
        # The first public write can arrive as soon as the gate is removed.
        self.gate.unlink()
        self.journal.unlink()

    def rollback(self, state):
        check_gate(state["url"])
        self.unit("stop")
        previous = self.releases / state["previous"] if state["previous"] else None
        require(previous is None or (previous.parent == self.releases and (previous / "database.sqlite").is_file()),
                "The previous release or its database is missing. The maintenance gate was kept closed.")
        self.switch(previous)
        if state["was_active"]:
            self.unit("start")
            wait_for_home(urlsplit(state["url"]).hostname)
            self.verify_running_release(previous)
        self.reopen()
        if previous:
            print("Restored the previous release and its original database.", flush=True)
        else:
            print("Reverted the first deployment. Any imported database was preserved.", flush=True)

    def recover(self):
        require(self.journal.is_file(), "There is no interrupted deployment journal.")
        if not self.gate.exists():
            self.journal.unlink()
            print("The gate is open. Cleared the journal and kept the active release and database.", flush=True)
            return
        self.rollback(json.loads(self.journal.read_text()))

    def deploy(self, ref, origin, import_db, legacy):
        require(not self.journal.exists() and not self.gate.exists(),
                "A maintenance gate or deployment journal already exists. Check it before deploying; use recover for an interrupted deploy.")
        require(self.gate.parent.is_dir(), f"Create the Nginx maintenance directory {self.gate.parent} first.")
        self.settings = read_settings(self.root / "production.env", origin)
        loaded = subprocess.check_output(
            ["systemctl", "--user", "show", "--property=LoadState", "--value", UNIT], text=True,
        ).strip()
        require(loaded == "loaded", f"Install and load the {UNIT} user service first.")
        previous = self.active_release()
        was_active = self.unit("is-active", check=False).returncode == 0
        require(previous or not was_active, "The service is active without a managed release.")
        require(not import_db or (not previous and import_db.is_file()), "--import-db requires an existing file and no active release.")
        require(not legacy or import_db, "--legacy-init-db requires --import-db.")
        if not previous and not import_db:
            for conventional_database in (self.root / "sqlite3.db", self.root / "data/portfolio.sqlite"):
                require(not conventional_database.is_file(),
                        f"Found an existing database at {conventional_database}. Use --import-db to preserve it.")
        source = previous / "database.sqlite" if previous else import_db
        if legacy:
            verify_legacy(source)

        for directory in (self.releases, self.root / "data", self.root / "backups"):
            directory.mkdir(exist_ok=True)
        release = self.stage(ref)
        candidate = self.root / "data" / f"{release.name}.sqlite"
        self.flask(release, candidate, "db", "heads")
        self.record(previous, was_active, origin)
        gated = False
        changed_service = False
        try:
            self.gate.touch(exist_ok=False)
            gated = True
            check_gate(origin)
            changed_service = True
            self.unit("stop")
            if source:
                backup = self.root / "backups" / f"{release.name}.sqlite"
                self.flask(release, source, "backup-db", str(backup))
                self.flask(release, candidate, "restore-db", str(backup), str(candidate))
            if legacy:
                self.flask(release, candidate, "db", "stamp", "10b29f2a3de3")
            self.flask(release, candidate, "db", "upgrade")
            self.flask(release, candidate, "db", "check")
            (release / "database.sqlite").symlink_to(candidate)
            self.switch(release)
            self.unit("start")
            host = urlsplit(origin).hostname
            wait_for_home(host)
            self.verify_running_release(release)
            site_check(LOOPBACK, host)
            check_gate(origin)
            self.reopen()
        except (Exception, KeyboardInterrupt):
            if changed_service and self.gate.exists():
                try:
                    self.recover()
                except (Exception, KeyboardInterrupt) as rollback_error:
                    raise DeploymentError(f"Rollback could not finish: {rollback_error}. The gate and journal were kept for recover.") from rollback_error
            elif not changed_service:
                if gated:
                    self.gate.unlink(missing_ok=True)
                self.journal.unlink(missing_ok=True)
            raise

        print(f"Release {release.name} is live. Database: {candidate}", flush=True)
        try:
            site_check(origin)
        except DeploymentError as error:
            raise DeploymentError(f"The release is live and its database remains active, but the public check failed: {error}") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    deploy = commands.add_parser("deploy", help="Stage, migrate, check, and activate a Git revision.")
    deploy.add_argument("ref")
    deploy.add_argument("--url", required=True, type=https_origin)
    deploy.add_argument("--import-db", type=Path, help="Copy an existing SQLite database on the first deployment.")
    deploy.add_argument("--legacy-init-db", action="store_true", help="Import the original unversioned init-db schema.")
    check = commands.add_parser("check", help="Check the live HTTPS site without writing to it.")
    check.add_argument("url", type=https_origin)
    commands.add_parser("recover", help="Recover an interrupted deployment while maintenance is active.")
    owner = commands.add_parser("owner", help="Create or reset the owner on the active release.")
    owner.add_argument("username")
    args = parser.parse_args()

    os.umask(0o077)
    if args.command == "check":
        site_check(args.url)
        return
    root = (Path.home() / "portfolio").resolve()
    deployment = Deployment(root, Path("/var/lib/personalportfolio-gate/maintenance"))
    with deployment.lock():
        if args.command == "deploy":
            deployment.deploy(args.ref, args.url, args.import_db.resolve() if args.import_db else None, args.legacy_init_db)
        elif args.command == "recover":
            deployment.recover()
        else:
            require(not deployment.journal.exists() and not deployment.gate.exists(),
                    "Finish the deployment before changing the owner.")
            release = deployment.active_release()
            require(release, "Deploy a release before creating its owner.")
            deployment.settings = read_settings(root / "production.env")
            deployment.flask(release, release / "database.sqlite", "create-owner", "--", args.username)


def handle_termination(signum, frame):
    raise KeyboardInterrupt()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_termination)
    try:
        main()
    except (DeploymentError, OSError, ValueError, sqlite3.Error, subprocess.CalledProcessError) as error:
        sys.exit(f"Deployment error: {error}")
    except KeyboardInterrupt:
        sys.exit("Deployment interrupted.")
