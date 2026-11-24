# PersonalPortfolio

A Flask and SQLite website for Prajwal Ram Gowda. The public site contains a portfolio, web résumé with a downloadable PDF, writing, and a contact form. The private studio handles Markdown publishing, topics, the contact inbox, and profile and résumé editing.

## Local development

From the repository root:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m flask --app wsgi db upgrade
.venv/bin/python -m flask --app wsgi run
```

The default database is the ignored `sqlite3.db` in the repository root. Set `PORTFOLIO_DATABASE` to a different file to use a separate database. Back up an existing database before upgrading. The publishing migration keeps existing posts public and redirects their old article links to the new URLs.

If an older database was created with the original `manage.py --init-db` and has no Alembic revision, back it up and baseline it at the original final revision before running the upgrade. Use this only for that original model schema.

```sh
.venv/bin/python -m flask --app wsgi db stamp 10b29f2a3de3
.venv/bin/python -m flask --app wsgi db upgrade
```

Create or reset an owner account with a hidden password prompt:

```sh
.venv/bin/python -m flask --app wsgi create-owner YOUR_USERNAME
```

Sign in at `/admin`. Choose **New post**, then import a UTF-8 `.md` file or write in the editor. Use **Preview**, **Save draft**, and **Publish** as needed. Drafts stay in the studio. You can download the original Markdown from the editor. Articles support code blocks, tables, and equations using `$...$` or `$$` block delimiters. Contact messages go to the studio inbox.

## Edit the profile and résumé

Use **Studio → Profile** to change the homepage headline, introduction, location, and About biography. Use **Studio → Résumé** to add, edit, reorder, or remove experience, education, skills, and publications. Designate an experience as **Selected work** to show it on the homepage. Saving updates the public site.

The web résumé has a print layout. Choose Print or Save as PDF in your browser, then use the editor’s **Downloadable PDF** section to upload the updated file. The public download uses the uploaded PDF when present and the bundled PDF by default.

## Checks

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m flask --app wsgi db check
```

## Deployment configuration

Configure these variables on the host:

- `PORTFOLIO_ENV=production`.
- `PORTFOLIO_SECRET_KEY` with a new random secret of at least 32 characters from your host’s secret store.
- `PORTFOLIO_TRUSTED_HOSTS` with comma-separated public hostnames, for example `portfolio.example.com,www.portfolio.example.com`.
- `PORTFOLIO_DATABASE` with an absolute file path on a persistent, writable volume outside the checkout.
- `PORTFOLIO_TRUST_PROXY=1` only when a single trusted reverse proxy sits in front of the server, replaces forwarded headers, and blocks direct access to the backend. Leave it unset when the WSGI server already receives the correct client address and HTTPS scheme.

Configure the proxy to redirect HTTP to HTTPS and to pass the public host and HTTPS scheme. For example, a single Nginx proxy can pass `Host $host`, `X-Forwarded-For $remote_addr`, and `X-Forwarded-Proto $scheme`. Bind Gunicorn to a private address, run migrations, then start the app.

```sh
.venv/bin/python -m flask --app wsgi db upgrade
.venv/bin/gunicorn --bind 127.0.0.1:5000 wsgi:app
```

Check the deployed HTTPS URL for a successful response and the `Strict-Transport-Security` and `Content-Security-Policy` headers. Verify in a browser that you can sign in and submit the contact form through the proxy. The app shares request limits between workers in SQLite. Each client address gets 10 sign-in attempts in 15 minutes and 5 contact submissions per hour.

If you ran the legacy app, replace its old session secret and reset the owner password with `create-owner` before using this version. The original login printed submitted passwords to application logs. Review access to those logs.

## Backup and restore

Schedule backups with the host’s job runner and keep copies outside the volume. Backups contain the inbox and password hashes, so store them privately. The commands verify SQLite integrity and require a new destination file.

```sh
.venv/bin/python -m flask --app wsgi backup-db /path/to/backups/portfolio.sqlite
.venv/bin/python -m flask --app wsgi restore-db /path/to/backups/portfolio.sqlite /path/to/restore/portfolio.sqlite
```

To test recovery, point `PORTFOLIO_DATABASE` at the restored file in a separate instance, apply migrations, and check the résumé, posts, and inbox. To switch production to a restored file, stop the app first, update its database path, and restart it after validation.
