# PersonalPortfolio

A Flask and SQLite website for Prajwal Ram Gowda. The public site contains a portfolio, web résumé with a downloadable PDF, writing, and a contact form. The private studio handles Markdown publishing, topics, the contact inbox, and profile and résumé editing.

## Static portfolio

The root `index.html` is the static portfolio, split from the approved `reference/prajwal-portfolio.html`. It uses plain HTML, CSS, JavaScript and self-hosted fonts.

Run a local preview from the repository root.

```sh
python3 -m http.server --bind 127.0.0.1 41873
```

Open `http://127.0.0.1:41873/`. The approved reference is available at `/reference/prajwal-portfolio.html`.

To publish through GitHub Pages, first merge the static portfolio into the default branch. In **Settings → Pages → Build and deployment**, select **Deploy from a branch**, then choose the default branch and **/(root)**. Save the settings and use the published URL shown by GitHub. The Flask application has its own development and VPS workflow below.

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

The portfolio runs on the Hostinger Ubuntu VPS as a dedicated Gunicorn service. Its own Nginx gateway listens on `127.0.0.1:8080` and forwards to a private Unix socket. The existing Cloudflare Tunnel sends the public hostname to this gateway and provides HTTPS. GitHub pushes run CI. Only a deploy from the VPS switches the running release.

### Prepare the portfolio service once

Confirm `8080` is free on the VPS with `sudo ss -ltnp 'sport = :8080'`. Check the existing connector and available disk space before changes. The portfolio uses Python 3.12 and the Ubuntu Nginx binary with the HTTP Real IP module. If Nginx is absent, have the VPS administrator arrange installation without enabling default public listeners. Use a dedicated, non-root `portfolio` account outside other apps' groups. Clone the repository as that user.

```sh
git clone --branch portfolio-redesign https://github.com/prajwalram8/PersonalPortfolio.git personalportfolio
cd personalportfolio
```

After approval for the VPS changes, the administrator can install the two dedicated systemd units, gateway configuration, and two-command sudo rule. Run these commands from the clone.

```sh
sudo install -d -o portfolio -g portfolio -m 700 /srv/personal-portfolio /srv/personal-portfolio/data
sudo install -d -m 755 /etc/personal-portfolio
sudo install -m 644 deploy/nginx-portfolio.conf /etc/personal-portfolio/gateway.conf
sudo install -m 644 deploy/personal-portfolio.service deploy/personal-portfolio-gateway.service /etc/systemd/system/
sudo visudo -cf deploy/personal-portfolio.sudoers
sudo install -m 440 deploy/personal-portfolio.sudoers /etc/sudoers.d/personal-portfolio
sudo systemctl daemon-reload
sudo systemctl enable personal-portfolio.service
sudo systemctl enable --now personal-portfolio-gateway.service
```

As `portfolio`, save the following unquoted settings in `/srv/personal-portfolio/production.env` and set permissions to `600`. Generate the session secret with `openssl rand -hex 32` and keep it stable between releases.

```ini
PORTFOLIO_ENV=production
PORTFOLIO_SECRET_KEY=your_generated_secret
PORTFOLIO_TRUSTED_HOSTS=prajwalramgowda.xyz
PORTFOLIO_TRUST_PROXY=1
```

### First launch and Cloudflare

Stage the first release before routing public traffic. This checks the local gateway and private app socket, so the apex DNS record can still be absent.

```sh
./scripts/deploy.py deploy origin/portfolio-redesign --local-only
./scripts/deploy.py check --local
```

Add `--import-db /absolute/path/to/portfolio.sqlite` to import the original portfolio database on that first launch. Stop any app or job writing to the source before importing. Also pass `--legacy-init-db` for the original unversioned `manage.py --init-db` schema. The script stamps only the copy. Without an import, first launch starts with an empty database. Create or reset the studio login with `./scripts/deploy.py owner YOUR_USERNAME`.

After local validation and approval for the public route, inspect Cloudflare DNS for existing records and preserve email and unrelated records. In the existing tunnel, add only the public **Published application** route for `prajwalramgowda.xyz` to **HTTP** `http://127.0.0.1:8080`, with no Access application for the public site. Set the route’s HTTP Host Header to `prajwalramgowda.xyz`. Cloudflare can manage the apex CNAME via flattening. The gateway redirects public HTTP to HTTPS and uses Cloudflare's client IP header for app rate limits. Keep origin headers intact and bypass edge caching for the portfolio's HTML, forms, and studio so the deployment gate reaches visitors.

For `www`, use a hostname-scoped Cloudflare redirect to `https://prajwalramgowda.xyz` that preserves the path and query string. Give `www` a proxied DNS record for the redirect. The domain can use the same tunnel CNAME target as the apex. On Cloudflare, keep all private routes and Access policies scoped as they are.

Check the public site after the DNS change.

```sh
./scripts/deploy.py check
```

The check covers the public homepage, writing, résumé PDF, contact form, studio sign-in redirect, and HTTPS headers. Finish by signing in and submitting a test contact message in a browser. Verify the existing private preview still requires Access, check that the private production app still works, and confirm the portfolio listens only on loopback.

### Updates and recovery

Use the following from the VPS after launch. Prefer the exact commit SHA from passing CI over a moving branch.

```sh
./scripts/deploy.py deploy origin/portfolio-redesign
```

The script stages the release before downtime and checks the maintenance gate locally and through Cloudflare before stopping Gunicorn. It backs up production SQLite, migrates a copy, and switches the code and database together. If private checks fail, it reactivates the previous release with its original database. After reopening traffic, it preserves the active database so any new edits or messages survive a public-check failure. `--local-only` is limited to first launch.

The database copies and backups live in `/srv/personal-portfolio/data` and `/srv/personal-portfolio/backups`. Allow disk space for a new release, database copy, and backup. For an interrupted deployment, run `./scripts/deploy.py recover` as the deployment user. View application and gateway logs with `journalctl -u personal-portfolio.service -u personal-portfolio-gateway.service`. For a full launch withdrawal, remove only the new portfolio routes and DNS/redirect entries, then stop the portfolio's two units. The shared connector stays in service.

### Backups

Schedule private off-host backups in addition to the deployment snapshots. Backups contain inbox messages and password hashes. Use a new destination file every time and test restores separately. Run these commands as the deployment user, with backup destinations writable only by that user.

```sh
cd /srv/personal-portfolio/current
PORTFOLIO_DATABASE="$PWD/database.sqlite" .venv/bin/python -m flask --app wsgi backup-db /private/backups/portfolio.sqlite
.venv/bin/python -m flask --app wsgi restore-db /private/backups/portfolio.sqlite /private/restores/portfolio.sqlite
```
