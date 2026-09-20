# Deployment guide

## Environment

Set at least:

```bash
export DJANGO_SECRET_KEY='a-long-random-production-secret-at-least-50-characters'
export DJANGO_DEBUG=0
export DJANGO_ALLOWED_HOSTS='exam.example.com'
export DJANGO_TIME_ZONE='UTC'
export DJANGO_CSRF_TRUSTED_ORIGINS='https://exam.example.com'
```

The production defaults enable HTTPS redirects, secure cookies, and one-year HSTS. If TLS terminates at a proxy, forward the original scheme correctly. Test HTTPS before exposing the service; changing HSTS settings carelessly can lock clients into HTTPS.

## Install and prepare

```bash
uv sync --frozen
uv run python manage.py migrate
uv run python manage.py collectstatic --noinput
uv run python manage.py createsuperuser
DJANGO_DEBUG=0 uv run python manage.py check --deploy
```

Run Django behind a production WSGI/ASGI server and a TLS reverse proxy. Do not use `runserver` in production. Add rate limiting for `/accounts/login/` at the proxy (or install a maintained Django throttling package) before public exposure.

## Expiry reconciliation

The app checks deadlines on answer, submit, result, attempt, and dashboard requests. Also schedule this idempotent command once per minute so abandoned browser sessions are finalized:

```bash
uv run python manage.py finalize_expired_attempts --limit 500
```

## Backups

Stop application writes or use SQLite's online backup API, then copy `db.sqlite3` to protected storage. Keep several dated copies and test restoration. Example during maintenance:

```bash
cp db.sqlite3 "backups/db-$(date +%Y%m%d-%H%M%S).sqlite3"
```

Restore by stopping the application, replacing `db.sqlite3`, applying any pending migrations, and checking the site. For substantial concurrent exam traffic, move to PostgreSQL; SQLite write contention is acceptable only for small deployments and prototypes.

## Release checks

```bash
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py migrate
uv run python manage.py check
uv run ruff check .
uv run pytest -v
uv run coverage run -m pytest
uv run coverage report --fail-under=90
```
