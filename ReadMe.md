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

## Production deployment

The deploy script targets one Linux server running systemd, Nginx, and Python 3.12. GitHub pushes run CI. A release goes live when you run the deploy command on the server.

### Set up the server once

1. Use a dedicated non-root account called `portfolio`. Clone this repo as that user with `git clone --branch portfolio-redesign https://github.com/prajwalram8/PersonalPortfolio.git personalportfolio`, then enter the clone. Enable its user services at boot with `sudo loginctl enable-linger portfolio`.
2. As that user, create the private runtime directory and install the user unit.

   ```sh
   install -d -m 700 "$HOME/portfolio" "$HOME/.config/systemd/user"
   install -m 644 deploy/personalportfolio.service "$HOME/.config/systemd/user/"
   systemctl --user daemon-reload
   systemctl --user enable personalportfolio.service
   ```

3. Save the following unquoted settings in `~/portfolio/production.env` with permissions `600`. Use the real public hostname and generate a fresh secret, for example with `openssl rand -hex 32`. Keep that secret stable between releases.

   ```ini
   PORTFOLIO_ENV=production
   PORTFOLIO_SECRET_KEY=your_generated_secret
   PORTFOLIO_TRUSTED_HOSTS=portfolio.example.com
   PORTFOLIO_TRUST_PROXY=1
   ```

4. Ask the server administrator to create the deployment gate directory and install the Nginx snippet. Include it inside the site's HTTPS server block, after setting up DNS and a TLS certificate. Redirect HTTP and any aliases to the canonical HTTPS origin. Point all traffic to the app through this gate and keep port 5000 private. Check Nginx with `sudo nginx -t` and reload it. If a CDN fronts Nginx, let maintenance requests reach the origin, bypass caching for the app's forms and studio, and configure Nginx to use the provider's real client IP headers.

   ```sh
   sudo install -d -o portfolio -g portfolio -m 755 /var/lib/personalportfolio-gate
   sudo install -m 644 deploy/nginx-portfolio.conf /etc/nginx/snippets/personalportfolio.conf
   ```

### Deploy a release

Run the same command for each update. Prefer the exact commit SHA from a passing CI run when deploying to production.

```sh
./scripts/deploy.py deploy origin/portfolio-redesign --url https://portfolio.example.com
```

For the first launch, add `--import-db /absolute/path/to/portfolio.sqlite` if you have an existing database. Stop any app or job writing to that file before importing, and keep it stopped after switching over. For a database created by the original `manage.py --init-db` that has no Alembic revision, also pass `--legacy-init-db`. The script checks that schema before stamping a copy. A first launch without an import starts with an empty database.

After the first launch, create or reset your studio login with `./scripts/deploy.py owner YOUR_USERNAME`. That prompts for your password. Reset it if you used the legacy app, which wrote submitted passwords to its logs.

### What happens to production data during updates

- The script checks out the selected Git revision and installs its pinned dependencies in a new release while the current site keeps serving traffic.
- It activates and verifies maintenance mode at the public HTTPS URL, then stops the app. It verifies a SQLite backup, restores that backup to a new database file, and applies migrations **to the copy**. Posts, drafts, inbox messages, profile changes, and uploaded PDFs come from the current production database.
- It switches the code and database together, starts Gunicorn, and checks the app while public traffic is still gated. If a step fails, it switches back to the previous release with its untouched database. After opening the gate, it checks the public site. If that final check fails, the active database stays in place so any new writes are preserved.

The site returns a short maintenance response during backup, migration, and cutover. The script keeps previous releases and backups on disk. Allow space for an extra database copy, a backup, and the new release. If a deployment is interrupted and leaves the gate closed, run `./scripts/deploy.py recover` as the deployment user. Recovery only rolls back while maintenance is active. Inspect the service with `journalctl --user -u personalportfolio.service`.

### Launch checks and backups

Use `./scripts/deploy.py check https://portfolio.example.com` any time. It checks the homepage, writing, résumé and PDF, contact form, protected studio redirect, and relevant HTTPS headers. Sign in and submit one test contact message in a browser to verify your actual credentials and inbox.

Schedule off-host backups with the hosting provider or use the SQLite backup command below and copy the result to private off-host storage. Backups contain inbox messages and password hashes. Use a new destination file for every backup and restore.

```sh
cd "$HOME/portfolio/current"
PORTFOLIO_DATABASE="$PWD/database.sqlite" .venv/bin/python -m flask --app wsgi backup-db /private/backups/portfolio.sqlite
.venv/bin/python -m flask --app wsgi restore-db /private/backups/portfolio.sqlite /private/restores/portfolio.sqlite
```

Test restores in a separate instance. After a release has accepted public traffic, preserve the current database when diagnosing a problem. Reopening an older snapshot can discard posts, résumé edits, and messages received since that snapshot.
