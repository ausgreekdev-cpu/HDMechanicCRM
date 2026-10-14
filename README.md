# HD Mechanic CRM

Full-stack CRM for auto repair shops: customers, vehicles, work orders, parts/inventory, invoicing & payments (Square), quotes-to-work-orders, scheduling, SMS/email notifications, a customer-facing portal, a workflow template marketplace, and analytics. Ships with a React-free Jinja UI, Android companion app (`android/`), and Docker/Render deployment configs.

## Stack

- **Backend:** Flask 3 + SQLAlchemy 2 (SQLite by default, `CRM_DATABASE_URL` for Postgres), Flask-WTF CSRF, Flask-Limiter, Flask-Caching (Redis optional)
- **Payments:** Square (payment links + webhook-verified grants); opt-in demo mode via `CRM_ALLOW_DEMO_PAYMENTS=1` when Square is not configured
- **Frontend:** Jinja2 templates + Bootstrap
- **Android:** native app under `android/` posting telemetry to `/api/analytics/*`
- **Tooling:** pytest, ruff (`.ruff.toml`), GitHub Actions CI

## Quick start

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env   # set CRM_SECRET_KEY
python main.py         # http://localhost:8000 (make dev)
```

The marketplace catalog seeds automatically on startup. Demo customers/vehicles are **not** seeded by default — opt in with `CRM_SEED_DEMO=1` (local/demo environments only).

## Configuration (env / `.env`)

| Variable | Purpose |
|---|---|
| `CRM_SECRET_KEY` | Flask session/CSRF signing key (**required in production**) |
| `CRM_DATABASE_URL` | SQLAlchemy URL (default: SQLite `data/crm.db`) |
| `CRM_REDIS_URL` | Redis for cache/rate limits (falls back to in-memory) |
| `CRM_SQUARE_ACCESS_TOKEN`, `CRM_SQUARE_APPLICATION_ID`, `CRM_SQUARE_LOCATION_ID`, `CRM_SQUARE_ENVIRONMENT` | Square payments |
| `CRM_SQUARE_WEBHOOK_SIGNATURE_KEY` | HMAC key for `/payments/webhook` verification |
| `CRM_SQUARE_CURRENCY` | Payment currency (default `AUD`) |
| `CRM_ALLOW_DEMO_PAYMENTS` | `1` = inline fake purchases when Square is unset (**local dev only**) |
| `CRM_SEED_DEMO` | `1` = seed demo customers/vehicles at startup |
| `CRM_ADMIN_USER` / `CRM_ADMIN_PASSWORD` | Bootstrap admin login |
| `CRM_TWILIO_SID` / `CRM_TWILIO_AUTH` / `CRM_TWILIO_PHONE` | SMS |
| `CRM_SMTP_*` / `CRM_SENDGRID_API_KEY` / `CRM_FROM_EMAIL` | Email |
| `CRM_LOG_LEVEL` / `CRM_LOG_FILE` | Logging |

See `.env.example` for the full list.

## Testing

```bash
python -m pytest tests/ -v   # make test
ruff check .                 # lint (gate rules in .ruff.toml)
```

CI (`.github/workflows/ci.yml`) runs install → ruff → pytest → boot smoke test on `master`/`main`/`develop`.

## Deployment

- `Dockerfile` + `docker-compose.yml` (`make deploy`), or `gunicorn -c gunicorn.conf.py main:app` (`make prod`)
- `render.yaml`, `Procfile`, `nginx.conf` for platform deploys
- Database migrations: Alembic (`alembic/`, `alembic.ini`)

## Project layout

```
main.py            # entrypoint, startup seeding + logging
app/
  __init__.py      # app factory, CSRF, cache, rate limits
  routes/          # feature blueprints (core, finance, marketplace, …)
  models/          # SQLAlchemy models
  templates/       # Jinja templates
  seed.py          # catalog + optional demo data
tests/             # pytest suite
android/           # companion Android app
```
