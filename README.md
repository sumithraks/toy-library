# Toy Library

Membership, inventory, checkout, donation, and notification management for a toy-lending library.

- **Backend**: Django + Django REST Framework + PostgreSQL, Celery + Celery Beat + Redis for background jobs, TOTP 2FA, email + Web Push notifications.
- **Frontend**: Next.js (App Router) + TypeScript + Tailwind, React Query, installable as a PWA.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full system design, data model, and business rules.

## Prerequisites

- Docker (for Postgres + Redis)
- Python 3.13
- Node.js 20+

## Running it

### 1. Database + Redis

```bash
cd /path/to/toy-library
docker compose up -d
```

Postgres on `localhost:5432`, Redis on `localhost:6379` (credentials in `docker-compose.yml` / `backend/.env`).

### 2. Backend API (terminal 1)

First time only:

```bash
cd backend
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate          # also seeds the 3 membership tiers
.venv/bin/python manage.py seed_periodic_tasks
.venv/bin/python manage.py createsuperuser
```

Then, every time:

```bash
cd backend
.venv/bin/python manage.py runserver 8000
```

- API base: `http://localhost:8000/api/`
- Admin: `http://localhost:8000/admin/`
- Swagger docs: `http://localhost:8000/api/docs/`

### 3. Celery worker (terminal 2)

Background jobs — late fee assessment, due-date/reservation reminders, waitlist expiry, etc.

```bash
cd backend
.venv/bin/celery -A config worker --loglevel=info
```

### 4. Celery beat (terminal 3)

Schedules the periodic tasks registered by `seed_periodic_tasks` (hourly late-fee sweep, 15-min reservation/push sweeps, daily reminders — see `ARCHITECTURE.md` for the full table).

```bash
cd backend
.venv/bin/celery -A config beat --loglevel=info
```

### 5. Frontend (terminal 4)

```bash
cd frontend
npm install
npm run dev
```

Runs on `http://localhost:3000` (or the next free port). `frontend/.env.local` points it at the backend API and holds the public VAPID key for web push.

## Testing

```bash
cd backend
.venv/bin/python -m pytest                                    # run the suite
.venv/bin/python -m pytest --cov=apps --cov-report=term-missing  # with coverage
```

## Configuration

- `backend/.env` (gitignored): `DATABASE_URL`, `CELERY_BROKER_URL`, `EMAIL_BACKEND`, `VAPID_*`, `CORS_ALLOWED_ORIGINS`, `FRONTEND_BASE_URL`. Email defaults to the console backend, so verification/reset/notification emails print to the `runserver` terminal instead of sending for real.
- `frontend/.env.local` (gitignored): `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_VAPID_PUBLIC_KEY`.

## Resetting the database schema

Full reset (drops all data, regenerates migrations) — dev only:

```bash
docker compose down -v          # drops the Postgres volume
docker compose up -d
cd backend
find apps -path "*/migrations/*.py" -not -name "__init__.py" -delete
.venv/bin/python manage.py makemigrations
.venv/bin/python manage.py migrate
```

Reset a single app's schema without touching the others:

```bash
cd backend
.venv/bin/python manage.py migrate <app_name> zero   # unapply that app's migrations
.venv/bin/python manage.py migrate <app_name>         # re-apply
```

Squash an app's migration history into one file instead of deleting it:

```bash
.venv/bin/python manage.py squashmigrations <app_name> <last_migration_number>
```

## Notes

- Payments are ledger-only (no live payment gateway) — staff mark charges as paid via the admin billing console after collecting cash/card in person.
- Web push works on `localhost` without HTTPS in Chrome; production deployment will need a real domain + HTTPS.
