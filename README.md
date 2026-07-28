# Toy Library

Membership, inventory, checkout, donation, and notification management for a toy-lending library.

- **Backend**: Django + Django REST Framework + PostgreSQL (with `pgvector`), Celery + Celery Beat + Redis for background jobs, TOTP 2FA, email + Web Push notifications.
- **Frontend**: Next.js (App Router) + TypeScript + Tailwind, React Query, installable as a PWA.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full system design, data model, and business rules.

## Features

- **Membership signup with tier selection** — members pick a tier at signup; the membership starts `PENDING_PAYMENT` until staff activate it in person. Members can nudge staff for approval from their membership page.
- **Toy intake (purchased or donated)** — a shared intake path creates the inventory record, logs the intake assessment, and auto-transitions the toy to `AVAILABLE` (or `BROKEN` if received damaged).
- **AI photo identification** — staff can upload a photo of a toy (on the Inventory "Add toy" form, or during donation intake) and have Claude (via LangChain, `claude-sonnet-5`) suggest the model name, make, condition, and age rating for review before saving. Requires `ANTHROPIC_API_KEY`; the rest of the app works fine without it, the button just shows a "not configured" error.
- **Semantic search over toy descriptions** — members can search the catalog with a free-form description (e.g. "wooden toy that helps with counting") instead of exact keywords. Descriptions are embedded via Voyage AI and matched with `pgvector` cosine similarity. Requires `VOYAGE_API_KEY`; without it the search box shows a "not configured" error, but the separate Model/Make/Age filters keep working. Run `manage.py backfill_toy_embeddings` to (re)embed existing toys.
- **Reservations → checkout** — staff can check a toy out directly from the pending-reservations screen; the button disappears and the row updates in place once picked up.

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

Postgres on `localhost:5432`, Redis on `localhost:6379` (credentials in `docker-compose.yml` / `backend/.env`). Postgres runs the `pgvector/pgvector:pg16` image (plain `postgres:16` plus the `vector` extension, used for semantic search) — if you have an older local volume from before this, `docker compose up -d` will recreate the container but keep your data; the extension is enabled automatically by the `inventory` app's migrations.

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

- `backend/.env` (gitignored): `DATABASE_URL`, `CELERY_BROKER_URL`, `EMAIL_BACKEND`, `VAPID_*`, `CORS_ALLOWED_ORIGINS`, `FRONTEND_BASE_URL`, `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`. Email defaults to the console backend, so verification/reset/notification emails print to the `runserver` terminal instead of sending for real. `ANTHROPIC_API_KEY` powers the staff "Identify from photo" toy-intake helper and `VOYAGE_API_KEY` powers semantic search — both are optional; each feature just shows a "not configured" error when its key is blank, and the rest of the app (including the regular keyword-based toy filters) works fine without them. Django only reads `.env` at process startup, so restart `runserver` after changing a key.
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
