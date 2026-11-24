import io
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest

from sqlalchemy import text
from werkzeug.security import generate_password_hash

from PortfolioApp import create_app, db
from PortfolioApp.models import Category, ContactSubmission, MarkdownFile, User, utc_now


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
        for path in ("/admin", "/admin/inbox", "/admin/posts/new", "/admin/topics"):
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
        source = "    indented code\n\n## Example section\n\n<div>Raw markup</div>\n\n$x^2$\n"
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
