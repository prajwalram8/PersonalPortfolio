from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from PortfolioApp import create_app, db
from PortfolioApp.models import ContactSubmission, MarkdownFile, ResumeDocument, SiteProfile, utc_now
from PortfolioApp.profile import DEFAULT_PROFILE
from scripts import deploy


HTTP_ORIGIN = "https://portfolio.example.com"
OLD_REVISION = "8b63ee91fd42"


class TestDeploymentHost(deploy.Deployment):
    def __init__(self, root, gate):
        super().__init__(root, gate)
        self.running = False
        self.calls = []
        self.revision = 0

    def stage(self, ref):
        self.revision += 1
        release = self.releases / f"release-{self.revision}"
        release.mkdir()
        return release

    def unit(self, action, *, check=True):
        self.calls.append(action)
        if action == "is-active":
            return SimpleNamespace(returncode=0 if self.running else 3)
        if not self.gate.exists():
            raise AssertionError(f"Service changed before maintenance: {action}")
        self.running = action == "start"

    def verify_running_release(self, release):
        if not self.running or self.active_release() != release:
            raise AssertionError("Wrong release running")

    def flask(self, release, database, *args):
        app = app_for(database)
        result = app.test_cli_runner().invoke(args=list(args))
        if result.exit_code != 0:
            raise AssertionError(result.output)


def app_for(database):
    return create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database.resolve()}"})


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory())
        root = Path(directory) / "portfolio"
        root.mkdir()
        gate = Path(directory) / "maintenance"
        self.host = TestDeploymentHost(root, gate)

        env = root / "production.env"
        env.write_text(
            "PORTFOLIO_ENV=production\n"
            "PORTFOLIO_SECRET_KEY=example-only-0123456789abcdef-abcdef\n"
            "PORTFOLIO_TRUSTED_HOSTS=portfolio.example.com\n"
            "PORTFOLIO_TRUST_PROXY=1\n"
        )
        env.chmod(0o600)

        self.enterContext(patch("scripts.deploy.subprocess.check_output", return_value="loaded\n"))
        self.enterContext(patch("scripts.deploy.wait_for_home"))
        self.enterContext(patch("scripts.deploy.check_gate", side_effect=self.check_gate))
        self.checks = self.enterContext(patch("scripts.deploy.site_check", side_effect=self.check_site))
        self.source = Path(directory) / "existing.sqlite"
        app = app_for(self.source)
        result = app.test_cli_runner().invoke(args=["db", "upgrade", OLD_REVISION])
        self.assertEqual(result.exit_code, 0, result.output)
        with app.app_context():
            db.session.add(MarkdownFile(name="Existing post", slug="existing", content="Still here", published_at=utc_now()))
            db.session.add(ContactSubmission(message="Original inbox message"))
            db.session.commit()

    def check_gate(self, origin):
        self.assertEqual(origin, HTTP_ORIGIN)
        self.assertTrue(self.host.gate.is_file())

    def check_site(self, origin, host=None):
        self.assertTrue(self.host.running)
        # The private checks must run while the gate is closed to public traffic.
        self.assertEqual(self.host.gate.is_file(), origin == deploy.LOOPBACK)

    def first_release(self):
        with self.host.lock():
            self.host.deploy("origin/portfolio-redesign", HTTP_ORIGIN, self.source, legacy=False)
        return self.host.active_release()

    def test_populated_import_and_update_keep_latest_production_content(self):
        first = self.first_release()
        source = app_for(self.source)
        with source.app_context():
            self.assertEqual(db.session.execute(db.text("SELECT version_num FROM alembic_version")).scalar_one(), OLD_REVISION)

        active = app_for(first / "database.sqlite")
        with active.app_context():
            db.session.add(SiteProfile(id=1, revision=1, content={
                **DEFAULT_PROFILE, "resume_headline": "Production résumé",
            }))
            db.session.add(ResumeDocument(id=1, payload=b"%PDF-test"))
            db.session.add(MarkdownFile(name="Private draft", slug="private", content="Keep draft"))
            db.session.add(ContactSubmission(message="New production inbox message"))
            db.session.commit()

        with self.host.lock():
            self.host.deploy("origin/portfolio-redesign", HTTP_ORIGIN, None, legacy=False)
        latest = self.host.active_release()
        self.assertNotEqual(latest, first)
        self.assertFalse(self.host.gate.exists())
        self.assertFalse(self.host.journal.exists())
        self.assertEqual(len(list((self.host.root / "backups").glob("*.sqlite"))), 2)

        client = app_for(latest / "database.sqlite").test_client()
        self.assertIn(b"Still here", client.get("/writing/existing").data)
        self.assertEqual(client.get("/writing/private").status_code, 404)
        self.assertIn("Production résumé", client.get("/resume").get_data(as_text=True))
        self.assertEqual(client.get("/resume.pdf").data, b"%PDF-test")
        for path in (latest / "database.sqlite", first / "database.sqlite"):
            with app_for(path).app_context():
                self.assertEqual(db.session.scalar(db.select(MarkdownFile).where(MarkdownFile.slug == "private")).content,
                                 "Keep draft")
                self.assertEqual(db.session.scalar(db.select(db.func.count(ContactSubmission.id))), 2)

    def test_failed_private_health_check_reopens_previous_database(self):
        first = self.first_release()
        original_data = (first / "database.sqlite").read_bytes()
        self.checks.side_effect = deploy.DeploymentError("Candidate health check failed.")
        with self.host.lock(), self.assertRaisesRegex(deploy.DeploymentError, "Candidate health check failed"):
            self.host.deploy("origin/portfolio-redesign", HTTP_ORIGIN, None, legacy=False)

        self.assertEqual(self.host.active_release(), first)
        self.assertEqual((first / "database.sqlite").read_bytes(), original_data)
        self.assertTrue(self.host.running)
        self.assertFalse(self.host.gate.exists())
        self.assertFalse(self.host.journal.exists())

    def test_public_failure_preserves_writes_after_reopening(self):
        first = self.first_release()

        def fail_after_first_write(origin, host=None):
            self.check_site(origin, host)
            if origin == HTTP_ORIGIN:
                with app_for(self.host.active_release() / "database.sqlite").app_context():
                    db.session.add(ContactSubmission(message="Arrived after going live"))
                    db.session.commit()
                raise deploy.DeploymentError("Public check failed")

        self.checks.side_effect = fail_after_first_write
        with self.host.lock(), self.assertRaisesRegex(deploy.DeploymentError, "database remains active"):
            self.host.deploy("origin/portfolio-redesign", HTTP_ORIGIN, None, legacy=False)
        latest = self.host.active_release()
        self.assertNotEqual(latest, first)
        self.assertFalse(self.host.gate.exists())
        with app_for(latest / "database.sqlite").app_context():
            self.assertIsNotNone(db.session.scalar(db.select(ContactSubmission.id).where(
                ContactSubmission.message == "Arrived after going live"
            )))

    def test_unverified_gate_keeps_service_running(self):
        first = self.first_release()
        self.host.calls.clear()
        with patch("scripts.deploy.check_gate", side_effect=deploy.DeploymentError("Proxy gate unavailable")):
            with self.host.lock(), self.assertRaisesRegex(deploy.DeploymentError, "Proxy gate unavailable"):
                self.host.deploy("origin/portfolio-redesign", HTTP_ORIGIN, None, legacy=False)
        self.assertEqual(self.host.calls, ["is-active"])
        self.assertEqual(self.host.active_release(), first)
        self.assertFalse(self.host.journal.exists())
        self.assertFalse(self.host.gate.exists())

    def test_recovers_after_an_interrupted_switch(self):
        first = self.first_release()
        with self.host.lock():
            self.host.record(first, True, HTTP_ORIGIN)
            self.host.gate.touch()
            self.host.switch(self.host.stage("interrupted"))
            self.host.recover()
        self.assertEqual(self.host.active_release(), first)
        self.assertTrue(self.host.running)
        self.assertFalse(self.host.gate.exists())
        self.assertFalse(self.host.journal.exists())

    def test_imports_original_unversioned_schema(self):
        legacy = Path(self.source.parent, "original.sqlite")
        app = app_for(legacy)
        runner = app.test_cli_runner()
        result = runner.invoke(args=["db", "upgrade", "10b29f2a3de3"])
        self.assertEqual(result.exit_code, 0, result.output)
        with app.app_context(), db.engine.begin() as connection:
            connection.exec_driver_sql("DROP TABLE alembic_version")
            ContactSubmission.__table__.create(connection)
            connection.execute(ContactSubmission.__table__.insert().values(message="Imported message"))
        with self.host.lock():
            self.host.deploy("origin/portfolio-redesign", HTTP_ORIGIN, legacy, legacy=True)
        with app_for(self.host.active_release() / "database.sqlite").app_context():
            self.assertEqual(db.session.scalar(db.select(ContactSubmission)).message, "Imported message")
