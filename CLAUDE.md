# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Permission

You have permission to read this repository. Do not keep asking for it.

## Project

Toy Library: membership, inventory, checkout, donation, and notification management for a
toy-lending library. Backend is Django + DRF + PostgreSQL with Celery/Celery Beat/Redis for
background jobs; frontend is a Next.js (App Router) PWA. See [`ARCHITECTURE.md`](ARCHITECTURE.md)
for the full system design, data model, state machines, and API surface — read it before making
non-trivial backend changes, since most business rules live there rather than being obvious from
the code layout.

## Code search tools

- Use `ast-grep` instead of grep/ripgrep for finding Python code patterns
  (function definitions, calls, class structures). Example:
  `ast-grep --lang python -p 'def $NAME($$$)'`
- Use `pmat analyze` for code quality, complexity, and technical debt checks
  before making structural changes.
- Only fall back to plain grep for non-code text (comments, docs, config files).

## Commands

### Backend (`backend/`, Python 3.13, uses `.venv`)

```bash
cd backend
.venv/bin/python manage.py runserver 8000       # API server
.venv/bin/celery -A config worker --loglevel=info   # background jobs (separate terminal)
.venv/bin/celery -A config beat --loglevel=info      # periodic task scheduler (separate terminal)

.venv/bin/python -m pytest                                        # full test suite
.venv/bin/python -m pytest apps/checkouts/                        # one app's tests
.venv/bin/python -m pytest apps/checkouts/tests.py::TestClass::test_name  # one test
.venv/bin/python -m pytest --cov=apps --cov-report=term-missing   # with coverage

.venv/bin/python manage.py makemigrations
.venv/bin/python manage.py migrate
```

Postgres + Redis run via `docker compose up -d` from the repo root (required before running the
backend or tests). Test settings (`config.settings.test`) use eager Celery execution and an
in-memory email backend, so no live broker/SMTP is needed to run the suite.

### Frontend (`frontend/`, Next.js 16 App Router)

```bash
cd frontend
npm run dev      # dev server, http://localhost:3000
npm run build
npm run lint
```

No frontend test runner is configured.

### Full local stack

`docker compose up -d` (Postgres + Redis) → backend `runserver` → Celery worker → Celery beat →
frontend `npm run dev`, each in its own terminal. Details, first-time setup, and env var
reference are in [`README.md`](README.md).

## Architecture

Ten Django apps under `backend/apps/`, split by bounded domain (not model-per-app): `common`,
`accounts`, `memberships`, `billing`, `inventory`, `donations`, `checkouts`, `waitlist`,
`reservations`, `notifications`. Full ownership table and data model are in `ARCHITECTURE.md`.

Load-bearing conventions that aren't obvious from file layout alone:

- **Business logic lives in `services.py`**, not in serializers or views. Views call service
  functions and translate `ValueError` into a 400. When changing behavior, look for the app's
  `services.py` first.
- **`inventory.Toy.status` is never set directly.** All transitions go through
  `inventory.services.transition_toy_status(toy, new_status, actor, reason)`, which validates
  against an explicit `ALLOWED_TRANSITIONS` map and logs every change. This is also the hook
  point for the waitlist auto-claim (see below).
- **`billing.LedgerEntry` is the single money-movement table** for the whole system (fees,
  deposits, renewals, late fees, paid extensions, refunds, tier changes). Entries are immutable
  once `PAID`; corrections are new offsetting entries, not edits. There is no live payment
  gateway — staff mark charges paid via the admin console after collecting payment in person.
- **Paid extensions and tier upgrades are two-phase**: creating them only produces a PENDING
  `LedgerEntry`; the actual state change (due date moving, tier changing) happens only when
  `billing.services.mark_paid` confirms payment, matching in-person cash/card collection.
  Downgrades and complimentary extensions apply immediately instead.
- **Waitlist → reservation auto-claim**: when a toy transitions to `AVAILABLE`,
  `inventory.services.transition_toy_status` calls `waitlist.services.claim_next_waitlist_entry`,
  which takes the oldest `WAITING` entry, auto-creates a `Reservation`, and moves the toy straight
  to `RESERVED` — it's never left generally available while a waitlist exists.
  `CheckoutRecord.status == OVERDUE` and toy `status == OVERDUE` are both derived, flipped only by
  the hourly Celery sweep — never set via the API.
- **Cross-app references** use Django string `ForeignKey("app.Model")`, and cross-app service
  calls are imported lazily inside functions where a top-level import would create a cycle (e.g.
  `inventory.services` importing `waitlist.services`).
- **Access control is enforced at the queryset level**: `get_queryset()` scopes non-staff users to
  their own rows before any object-permission check runs, so requesting another member's resource
  returns 404, not 403.
- **Periodic tasks are DB-scheduled** via `django-celery-beat`, seeded once with
  `manage.py seed_periodic_tasks` (`apps/common/management/commands/seed_periodic_tasks.py`).
  Adding a new scheduled job means adding it there, not just writing the Celery task.

### Frontend structure (`frontend/`)

- `app/(auth)/`, `app/(member)/`, `app/(staff)/` are separate route groups, each gating access in
  its own layout via `useAuth()` + a redirect effect — there is no middleware-based auth.
- `lib/api-client.ts` is the typed fetch wrapper (token auth header, typed `ApiError`);
  `lib/types.ts` mirrors the DRF serializers by hand, so backend serializer field changes need a
  matching manual update here.
- Data fetching is React Query; every mutation invalidates the relevant query key.
- Web push (`lib/push.ts`, `public/sw.js`) uses VAPID keys — public key in
  `frontend/.env.local`, private key in `backend/.env`. Works on `localhost` without HTTPS in
  Chrome only.
- This project pins a pre-release/unfamiliar Next.js version (16) with breaking API changes vs.
  training-data Next.js — check `node_modules/next/dist/docs/` for current APIs before writing
  Next.js-specific code (routing, PWA/`serwist` config, etc.), per `frontend/AGENTS.md`.

## Testing conventions

- `backend/apps/*/tests.py`: service-layer unit tests (business rules, state machine transitions)
  using `factory_boy` factories from `apps/common/factories.py`.
- `backend/apps/*/test_api.py`: DRF `APIClient` endpoint tests (auth, permissions, validation,
  status codes) using shared fixtures in `backend/conftest.py` (`api_client`, `member_client`,
  `staff_client`, `active_membership`, `toy`, `silver_tier`).

 ## Test Coverage Minimums
* **Global Target:** Minimum **80%** line coverage.
* **Core Business Logic / Services:** Minimum **90%** coverage.

##  Celery Task Testing Rules
* **Never use `task.delay()` or `.apply()` in unit tests.** This introduces race conditions and relies on a live broker.
* **Testing Execution:** Use `task.apply(args=(), kwargs=())` to test the task logic synchronously and in-process without needing a live Celery worker.
* **Mocking Tasks:** If the task involves complex external API calls, use `unittest.mock` to patch the third-party network requests.
* **No Database State Leaks:** Ensure tasks retrieve database models fresh via IDs rather than passing model instances directly as serialized arguments.

## Django Component Requirements
Every new Django feature must have corresponding test coverage targeting the following:
* **Models:** Custom property methods, signals, and custom model managers.
* **Views/API Endpoints:** Authenticated (200/401/403 states), malformed payloads (400), and nonexistent resources (404).
* **Forms & Serializers:** Validation logic for valid and invalid states.

## Testing Anti-Patterns (Strictly Forbidden)
* Never use hard-coded live timestamps; use `django.utils.timezone.now` combined with `freezegun`.
* Do not use JSON fixture files for application tests. Use **FactoryBoy** to prevent brittle tests.

# Architecture & Patterns
- Follow Django's strict MVT (Model-View-Template) pattern.
- Use Class-Based Views (CBVs) for complex logic and reusable components.
- Use Function-Based Views (FBVs) only for simple, straightforward endpoints.
- Leverage the Django ORM natively. Avoid raw SQL unless explicitly instructed for specific performance reasons.
- Use `select_related()` and `prefetch_related()` when querying foreign keys or many-to-many fields to prevent $N+1$ query issues.

# Do NOT Do This
- Do NOT use `import *` in Python files.
- Do NOT hardcode secrets. Always refer to `django.conf.settings` or environment variables.
- Do NOT put complex business logic in views. Extract logic into services or model methods to keep views "skinny."
- Do NOT write raw queries if a built-in ORM method (`filter`, `annotate`, `aggregate`) exists.
