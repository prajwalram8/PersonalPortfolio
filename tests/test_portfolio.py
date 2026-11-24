import io
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from sqlalchemy import text
from werkzeug.datastructures import MultiDict
from werkzeug.security import generate_password_hash

from PortfolioApp import create_app, db
from PortfolioApp.models import Category, ContactSubmission, MarkdownFile, ResumeDocument, SiteProfile, User, utc_now
from PortfolioApp.profile import DEFAULT_PROFILE
from PortfolioApp.studio import PROFILE_FIELDS, RESUME_SECTIONS

BUNDLED_RESUME = Path(__file__).resolve().parents[1] / "PortfolioApp/static/pdf/Prajwal Ram Gowda.pdf"


class PortfolioTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        })
        self.client = self.app.test_client()
        self.password = "test-only-password"
        with self.app.app_context():
            db.create_all()
            owner = User(username="owner", password=generate_password_hash(self.password))
            db.session.add(owner)
            db.session.commit()

    def csrf_token(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        match = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True))
        self.assertIsNotNone(match)
        return match.group(1)

    def sign_in(self):
        response = self.client.post("/admin/login", data={
            "username": "owner", "password": self.password,
            "csrf_token": self.csrf_token("/admin/login"),
        })
        self.assertEqual(response.status_code, 303)
        self.assertTrue(response.location.endswith("/admin"))

    def test_admin_pages_and_actions_require_authentication(self):
        for path in ("/admin", "/admin/inbox", "/admin/posts/new", "/admin/topics", "/admin/profile", "/admin/resume"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertIn("/admin/login", response.location)
                self.assertEqual(response.headers["Cache-Control"], "no-store")

        response = self.client.post("/admin/posts/new", data={
            "csrf_token": self.csrf_token("/contact"), "action": "save",
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login", response.location)

    def test_markdown_preview_draft_and_publish(self):
        self.sign_in()
        path = "/admin/posts/new"
        token = self.csrf_token(path)
        source = "    indented code\n\n## Example section\n\n| Metric |\n| ---: |\n| 1 |\n\n<div>Raw markup</div>\n\n$x^2$\n"
        response = self.client.post(path, data={
            "csrf_token": token, "action": "import", "markdown": (io.BytesIO(source.encode()), "notes.md"),
        })
        self.assertIn(b"Markdown imported.", response.data)
        self.assertIn(b"Example section", response.data)

        form = {"csrf_token": token, "name": "Notes", "content": source, "summary": "A test article"}
        response = self.client.post(path, data={**form, "action": "preview"})
        self.assertIn(b"<h2>Example section</h2>", response.data)
        self.assertNotIn(b"<div>Raw markup</div>", response.data)
        self.assertIn(b"<math ", response.data)
        with self.app.app_context():
            self.assertEqual(db.session.scalar(db.select(db.func.count(MarkdownFile.id))), 0)

        response = self.client.post(path, data={**form, "action": "save"})
        self.assertEqual(response.status_code, 303)
        edit_path = response.location
        self.assertEqual(self.client.get("/writing/notes").status_code, 404)
        self.assertNotIn(b"A test article", self.client.get("/writing").data)

        response = self.client.post(edit_path, data={**form, "action": "publish"})
        self.assertEqual(response.status_code, 303)
        public = self.client.get("/writing/notes")
        self.assertEqual(public.status_code, 200)
        self.assertIn(b"<h2>Example section</h2>", public.data)
        self.assertIn(b"<pre><code>indented code", public.data)
        self.assertIn(b"&lt;div&gt;Raw markup&lt;/div&gt;", public.data)
        self.assertIn(b'<td class="align-right">1</td>', public.data)
        self.assertNotIn(b'style="text-align', public.data)
        self.assertIn(b"<math ", public.data)

        post_id = edit_path.split("/")[-2]
        legacy = self.client.get(f"/blog-post/{post_id}")
        self.assertEqual(legacy.status_code, 301)
        self.assertTrue(legacy.location.endswith("/writing/notes"))
        self.assertEqual(self.client.get(f"/admin/posts/{post_id}/markdown").data.decode(), source)

        response = self.client.post(edit_path, data={**form, "action": "save", "name": "Revised notes"})
        self.assertEqual(response.status_code, 303)
        self.assertIn(b"Revised notes", self.client.get("/writing/notes").data)
        response = self.client.post(f"/admin/posts/{post_id}/unpublish", data={"csrf_token": token})
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.client.get("/writing/notes").status_code, 404)

    def test_topic_filter_includes_all_published_subtopics(self):
        with self.app.app_context():
            analysis = Category(category="Data", subcategory="Analysis")
            engineering = Category(category="Data", subcategory="Engineering")
            db.session.add_all([
                MarkdownFile(name="Analysis notes", slug="analysis", category=analysis, published_at=utc_now()),
                MarkdownFile(name="Engineering notes", slug="engineering", category=engineering, published_at=utc_now()),
                MarkdownFile(name="A private draft", slug="draft", category=analysis),
                MarkdownFile(name="No topic", slug="no-topic", published_at=utc_now()),
            ])
            db.session.commit()

        index = self.client.get("/writing?topic=Data").data
        self.assertIn(b"Analysis notes", index)
        self.assertIn(b"Engineering notes", index)
        self.assertNotIn(b"No topic", index)
        self.assertNotIn(b"A private draft", index)
        self.assertEqual(len(self.client.get("/filter-posts/Data").json["posts"]), 2)
        self.assertEqual(self.client.get("/writing/no-topic").status_code, 200)

    def test_contact_requires_csrf_and_stores_message(self):
        form = {
            "name": "A reader", "email": "reader@example.invalid",
            "subject": "Article", "message": "Thanks for the post.",
        }
        self.assertEqual(self.client.post("/contact", data=form).status_code, 400)
        token = self.csrf_token("/contact")
        response = self.client.post("/contact", data={**form, "email": "invalid", "csrf_token": token})
        self.assertEqual(response.status_code, 422)
        response = self.client.post("/submit_contact", data={**form, "csrf_token": token})
        self.assertEqual(response.status_code, 303)
        self.assertTrue(response.location.endswith("/contact"))
        with self.app.app_context():
            self.assertEqual(db.session.scalar(db.select(ContactSubmission)).message, form["message"])


    def test_profile_and_resume_share_content_and_reject_stale_edits(self):
        self.sign_in()
        profile_path = "/admin/profile"
        profile = {field.name: DEFAULT_PROFILE[field.name] for field in PROFILE_FIELDS}
        profile.update(headline="New portfolio headline", about_text="First paragraph.\n\nSecond paragraph.")
        token = self.csrf_token(profile_path)
        form = {**profile, "revision": "0", "csrf_token": token}
        self.assertEqual(self.client.post(profile_path, data=form).status_code, 303)
        self.assertEqual(self.client.post(profile_path, data=form).status_code, 409)
        self.assertIn(b"New portfolio headline", self.client.get("/").data)
        self.assertIn(b"<p>Second paragraph.</p>", self.client.get("/about").data)

        content = {section[0]: [entry.copy() for entry in DEFAULT_PROFILE[section[0]]] for section in RESUME_SECTIONS}
        first = content["work"][0]
        first.update(company="Revised Company", title="A new case study")
        new = {**first, "slug": "", "company": "Another Company", "role": "Engineer", "featured": "no"}
        content["work"] = [new, first]
        content["publications"] = [{"title": "A new publication", "url": "ftp://example.com/paper"}]

        def resume_form():
            data = MultiDict({"resume_headline": "Editing test", "revision": "1", "csrf_token": token})
            for name, _, _, fields in RESUME_SECTIONS:
                data.add("resume-section", name)
                keys = [field.name for field in fields] + (["slug"] if name == "work" else [])
                for row in content[name]:
                    for key in keys:
                        data.add(f"{name}-{key}", row[key])
            return data

        invalid = self.client.post("/admin/resume", data=resume_form())
        self.assertEqual(invalid.status_code, 422)
        self.assertIn(b"must be an http or https URL", invalid.data)
        content["publications"][0]["url"] = "https://example.com/paper"
        self.assertEqual(self.client.post("/admin/resume", data=resume_form()).status_code, 303)

        home = self.client.get("/").data
        self.assertIn(b"New portfolio headline", home)
        self.assertIn(b"A new case study", home)
        self.assertNotIn(b"Another Company", home)
        resume = self.client.get("/resume").data
        self.assertIn(b'id="business-intelligence"', resume)
        self.assertIn(b'id="another-company"', resume)
        self.assertLess(resume.index(b"Another Company"), resume.index(b"Revised Company"))
        self.assertIn(b"https://example.com/paper", resume)

    def test_pdf_replacement_is_authenticated_and_size_limited(self):
        self.app.config["MAX_CONTENT_LENGTH"] = 128 * 1024
        original = self.client.get("/resume.pdf")
        self.assertIn("attachment", original.headers["Content-Disposition"])
        self.assertEqual(original.mimetype, "application/pdf")
        bundled = original.get_data()
        original.close()

        path = "/admin/resume/pdf"
        token = self.csrf_token("/contact")
        self.assertEqual(self.client.post(path, data={"csrf_token": token}).status_code, 302)
        self.sign_in()
        self.assertEqual(self.client.post(path, data={"pdf": (io.BytesIO(b"plain text"), "sample.pdf")}).status_code, 400)
        token = self.csrf_token("/admin/resume")
        response = self.client.post(path, data={
            "csrf_token": token, "pdf": (io.BytesIO(b"plain text"), "sample.pdf"),
        }, follow_redirects=True)
        self.assertIn(b"Choose a valid PDF file", response.data)
        self.assertGreater(len(bundled), self.app.config["MAX_CONTENT_LENGTH"])
        revised = bundled + b"\n"
        response = self.client.post(path, data={"csrf_token": token, "pdf": (io.BytesIO(revised), "resume.pdf")})
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.client.get("/resume.pdf").data, revised)
        oversized = b"x" * (4 * 1024 * 1024 + 128 * 1024)
        with io.BytesIO(oversized) as stream:
            oversized_request = self.client.post(
                path, input_stream=stream, content_type="multipart/form-data; boundary=test",
            )
        self.assertEqual(oversized_request.status_code, 413)
        self.assertEqual(self.client.post(path, data={"csrf_token": token, "action": "reset"}).status_code, 303)
        response = self.client.get("/resume.pdf")
        self.assertEqual(response.get_data(), bundled)
        response.close()

    def test_rate_and_security_headers(self):
        self.app.config["RATE_LIMITS"] = {"login": (2, 60), "contact": (1, 120)}
        login_token = self.csrf_token("/admin/login")
        invalid = {"csrf_token": login_token, "username": "owner", "password": "a wrong value"}
        with patch("PortfolioApp.security.time", return_value=1000):
            self.assertEqual(self.client.post("/login", data=invalid).status_code, 200)
            self.assertEqual(self.client.post("/admin/login", data=invalid).status_code, 200)
            blocked = self.client.post("/admin/login", data=invalid, headers={"X-Forwarded-For": "192.0.2.12"})
            self.assertEqual(blocked.status_code, 429)
            self.assertEqual(blocked.headers["Retry-After"], "60")
            self.assertEqual(blocked.headers["Cache-Control"], "no-store")

            contact = {"csrf_token": self.csrf_token("/contact"), "name": "A reader",
                       "email": "reader@example.invalid", "subject": "Hello", "message": "Test."}
            self.assertEqual(self.client.post("/contact", data=contact).status_code, 303)
            self.assertEqual(self.client.post("/submit_contact", data=contact).status_code, 429)
        with patch("PortfolioApp.security.time", return_value=1060):
            self.assertEqual(self.client.post("/admin/login", data=invalid).status_code, 200)
        headers = self.client.get("/contact").headers
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertNotIn("Strict-Transport-Security", headers)

    def test_https_through_trusted_proxy_and_host_validation(self):
        app = create_app({
            "TESTING": True, "TRUSTED_HOSTS": ["portfolio.example"], "TRUST_PROXY": True,
            "SESSION_COOKIE_SECURE": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        })
        with app.app_context():
            db.create_all()
        client = app.test_client()
        direct = client.get("/contact", base_url="http://portfolio.example")
        self.assertNotIn("Strict-Transport-Security", direct.headers)
        via_proxy = client.get(
            "/contact", base_url="http://portfolio.example", headers={"X-Forwarded-Proto": "https"},
        )
        self.assertEqual(via_proxy.headers["Strict-Transport-Security"], "max-age=31536000")
        self.assertEqual(client.get("/contact", base_url="http://unused.example").status_code, 400)
        token = re.search(r'name="csrf_token" value="([^"]+)"', via_proxy.get_data(as_text=True)).group(1)
        response = client.post(
            "/contact", base_url="http://portfolio.example",
            headers={"X-Forwarded-Proto": "https", "Referer": "https://portfolio.example/contact"},
            data={"csrf_token": token, "name": "A reader", "email": "reader@example.invalid",
                  "subject": "Hello", "message": "Submitted through HTTPS."},
        )
        self.assertEqual(response.status_code, 303)


class BackupTests(unittest.TestCase):
    def test_backup_and_restore_preserve_content(self):
        with TemporaryDirectory() as directory:
            live = Path(directory, "live.sqlite")
            backup = Path(directory, "backup.sqlite")
            restored = Path(directory, "restored.sqlite")
            app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{live}"})
            with app.app_context():
                db.create_all()
                db.session.add(SiteProfile(id=1, revision=1, content={
                    **DEFAULT_PROFILE, "resume_headline": "Restored résumé",
                }))
                db.session.add(ResumeDocument(id=1, payload=BUNDLED_RESUME.read_bytes()))
                db.session.add(ContactSubmission(message="Keep this inbox message."))
                db.session.commit()

            runner = app.test_cli_runner()
            result = runner.invoke(args=["backup-db", str(backup)])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
            self.assertNotEqual(runner.invoke(args=["backup-db", str(backup)]).exit_code, 0)
            self.assertNotEqual(runner.invoke(args=["restore-db", str(backup), str(live)]).exit_code, 0)
            result = runner.invoke(args=["restore-db", str(backup), str(restored)])
            self.assertEqual(result.exit_code, 0, result.output)

            restored_app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{restored}"})
            client = restored_app.test_client()
            self.assertIn("Restored résumé", client.get("/resume").get_data(as_text=True))
            self.assertEqual(client.get("/resume.pdf").data, BUNDLED_RESUME.read_bytes())
            with restored_app.app_context():
                self.assertEqual(db.session.scalar(db.select(ContactSubmission)).message, "Keep this inbox message.")

    def test_workers_share_rate_limit_budget(self):
        with TemporaryDirectory() as directory:
            path = Path(directory, "shared.sqlite")
            config = {
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{path}",
                "RATE_LIMITS": {"login": (1, 60), "contact": (1, 60)},
                "SECRET_KEY": "test-key-for-both-workers", "TESTING": True, "WTF_CSRF_ENABLED": False,
            }
            first = create_app(config)
            second = create_app(config)
            with first.app_context():
                db.create_all()

            with patch("PortfolioApp.security.time", return_value=1000):
                self.assertEqual(first.test_client().post("/admin/login").status_code, 200)
                self.assertEqual(second.test_client().post("/admin/login").status_code, 429)


class MigrationTests(unittest.TestCase):
    def test_upgrade_preserves_posts_and_the_preexisting_contact_table(self):
        with TemporaryDirectory() as directory:
            database = Path(directory, "upgrade.sqlite")
            app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database}"})
            runner = app.test_cli_runner()
            result = runner.invoke(args=["db", "upgrade", "10b29f2a3de3"])
            self.assertEqual(result.exit_code, 0, result.output)
            with app.app_context(), db.engine.begin() as connection:
                ContactSubmission.__table__.create(connection)
                connection.execute(ContactSubmission.__table__.insert().values(message="Existing message"))
                connection.execute(text("""
                    INSERT INTO markdown_file (id, name, content, upload_date)
                    VALUES ('old-1', 'A post', 'First post', '2024-01-06 11:12:13.000000'),
                           ('old-2', 'A post', 'Second post', '2024-01-07 11:12:13.000000')
                """))

            result = runner.invoke(args=["db", "upgrade"])
            self.assertEqual(result.exit_code, 0, result.output)
            result = runner.invoke(args=["db", "check"])
            self.assertEqual(result.exit_code, 0, result.output)
            first = app.test_client().get("/writing/a-post")
            self.assertIn(b"First post", first.data)
            self.assertIn(b"06 January 2024", first.data)
            self.assertIn(b"Second post", app.test_client().get("/writing/a-post-2").data)
            with app.app_context():
                self.assertEqual(db.session.scalar(db.select(ContactSubmission)).message, "Existing message")


if __name__ == "__main__":
    unittest.main()
