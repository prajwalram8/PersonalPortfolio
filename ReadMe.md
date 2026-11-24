# PersonalPortfolio

A Flask and SQLite website for Prajwal Ram Gowda. The public site contains a portfolio, web résumé with a downloadable PDF, writing, and a contact form. The private studio handles Markdown publishing, topics, and the contact inbox.

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

## Checks

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m flask --app wsgi db check
```

## Deployment configuration

Set `PORTFOLIO_ENV=production` and provide a stable, random `PORTFOLIO_SECRET_KEY` of at least 32 characters through your hosting provider. Use an HTTPS reverse proxy and a persistent, backed-up SQLite file. Apply migrations before starting the WSGI server with `gunicorn wsgi:app`.
