# Grownica Django Deployment (Ubuntu 22.04)

This guide walks you through deploying the project on a fresh Ubuntu VPS with a domain.
Adjust paths and names as needed.

## 0) Assumptions
- Project path: /srv/grownica/project
- Virtualenv: /srv/grownica/venv
- User: ubuntu (replace with yours)
- Domain: example.com (replace with your domain)

## 1) System prep (run as root or via sudo)
```bash
apt update && apt -y upgrade
apt -y install git python3-venv python3-pip nginx
# If PostgreSQL is on the same VPS:
apt -y install postgresql postgresql-contrib libpq-dev
```

Create folders and user permissions:
```bash
mkdir -p /srv/grownica
chown -R $USER:$USER /srv/grownica
```

## 2) Clone project and create virtualenv
```bash
cd /srv/grownica
git clone <YOUR_REPO_URL> project
python3 -m venv /srv/grownica/venv
source /srv/grownica/venv/bin/activate
pip install --upgrade pip
pip install -r /srv/grownica/project/project/requirements.txt
```

## 3) Configure environment (.env)
Copy template and edit:
```bash
cp /srv/grownica/project/project/.env.example /srv/grownica/project/project/.env
nano /srv/grownica/project/project/.env
```
Set the following (examples):
```
DEBUG=False
SECRET_KEY=<generate a long random string>
ALLOWED_HOSTS=example.com,www.example.com
CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com

# HTTPS & security
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=<your@gmail.com>
EMAIL_HOST_PASSWORD=<app_password>

# Nova Poshta
NOVA_POSHTA_API_KEY=<your_api_key>

# Logging
LOG_LEVEL=INFO
LOG_TO_FILE=True
LOG_FILE=/var/log/grownica/app.log

# DB (if local postgres)
DB_NAME=<db_name>
DB_USER=<db_user>
DB_PASSWORD=<db_password>
DB_HOST=localhost
DB_PORT=5432

# Optional: hashed static files
# STATICFILES_STORAGE=django.contrib.staticfiles.storage.ManifestStaticFilesStorage
```

Create logs directory and allow writing:
```bash
mkdir -p /var/log/grownica
chown -R $USER:www-data /var/log/grownica
chmod 775 /var/log/grownica
```

## 4) Database (PostgreSQL local example)
```bash
sudo -u postgres psql -c "CREATE DATABASE <db_name> ENCODING 'UTF8';"
sudo -u postgres psql -c "CREATE USER <db_user> WITH PASSWORD '<db_password>';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE <db_name> TO <db_user>;"
```

## 5) Django setup
```bash
cd /srv/grownica/project
source /srv/grownica/venv/bin/activate
python project/manage.py migrate
python project/manage.py collectstatic --noinput
# Optional: create admin
python project/manage.py createsuperuser
```

## 6) Gunicorn as a systemd service
Create service file from template:
```bash
sudo cp /srv/grownica/project/project/deploy/gunicorn.service /etc/systemd/system/grownica.service
sudo nano /etc/systemd/system/grownica.service
# update paths and user if needed
sudo systemctl daemon-reload
sudo systemctl enable grownica
sudo systemctl start grownica
sudo systemctl status grownica --no-pager
```

## 7) Nginx reverse proxy
Create site config from template:
```bash
sudo cp /srv/grownica/project/project/deploy/nginx.conf.example /etc/nginx/sites-available/grownica
sudo nano /etc/nginx/sites-available/grownica
sudo ln -s /etc/nginx/sites-available/grownica /etc/nginx/sites-enabled/grownica
sudo nginx -t
sudo systemctl reload nginx
```

Ensure static/media paths exist with correct perms:
```bash
mkdir -p /srv/grownica/project/staticfiles /srv/grownica/project/media
chown -R $USER:www-data /srv/grownica/project/staticfiles /srv/grownica/project/media
chmod -R 755 /srv/grownica/project/staticfiles
chmod -R 775 /srv/grownica/project/media
```

## 8) HTTPS with Certbot (after DNS points to your VPS)
```bash
apt -y install certbot python3-certbot-nginx
sudo certbot --nginx -d example.com -d www.example.com
# follow the prompts to obtain certificates and auto-configure HTTPS
```

## 9) Post-deploy checks
```bash
source /srv/grownica/venv/bin/activate
cd /srv/grownica/project
python project/manage.py check --deploy
```
Test in browser:
- Static files load from /static/
- Media upload works (admin)
- Cart → order → emails OK
- Nova Poshta search/warehouses OK

## 10) Operations
- Restart app: `sudo systemctl restart grownica`
- View app logs: `tail -f /var/log/grownica/app.log`
- Nginx logs: `/var/log/nginx/access.log`, `/var/log/nginx/error.log`

## Templates location
- systemd unit: `project/deploy/gunicorn.service`
- Nginx config: `project/deploy/nginx.conf.example`

## Notes
- For Redis cache replace default FILE cache in settings and install redis server/client.
- For Sentry monitoring add DSN to .env and integrate SDK later if desired.
