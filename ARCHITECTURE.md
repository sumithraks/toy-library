# Architecture

## Overview

A toy-lending library management system: member signups across three paid tiers, toy
inventory tracking, a tiered checkout/extension/late-fee system, a donation-intake pipeline,
waitlists/reservations with soft-hold auto-claiming, and a notification system (email + web
push) that drives the due-date/extension/reservation UX.

```
┌─────────────────────┐        REST/JSON        ┌──────────────────────────┐
│  Next.js PWA         │ ───────────────────────▶│  Django + DRF API         │
│  (React Query)        │◀─────────────────────── │  (Token + Session auth)   │
└─────────────────────┘                          └────────────┬─────────────┘
                                                                │
                                          ┌─────────────────────┼─────────────────────┐
                                          │                     │                     │
                                   ┌──────▼──────┐      ┌───────▼───────┐    ┌────────▼────────┐
                                   │  PostgreSQL  │      │ Celery worker │    │  Celery beat     │
                                   │              │      │  + Redis      │    │  (schedules)     │
                                   └──────────────┘      └───────┬───────┘    └──────────────────┘
                                                                  │
                                                        ┌─────────▼─────────┐
                                                        │ Email (console/    │
                                                        │ SMTP) + Web Push   │
                                                        │ (pywebpush/VAPID)  │
                                                        └────────────────────┘
```

## Backend: Django apps

Ten apps, split by bounded domain rather than model-per-app (`backend/apps/`):

| App | Owns |
|---|---|
| `common` | `TimeStampedModel` base, DRF permissions (`IsStaff`, `IsStaffOrReadOnly`, `IsOwnerOrStaff`), pagination |
| `accounts` | Custom `User` (email login), email verification, TOTP 2FA, password reset |
| `memberships` | `MembershipTier`, `Membership`, tier-change and sign-off business rules |
| `billing` | `LedgerEntry` — the single ledger every other app writes to |
| `inventory` | `Toy` and its status state machine (single source of truth) |
| `donations` | Donor/Donation/DonationItem intake pipeline, receipts |
| `checkouts` | `CheckoutRecord`, `Extension`, `LateFeeAssessment` — checkout/extension/late-fee logic |
| `waitlist` | `WaitlistEntry`, FIFO waitlist and soft-hold claiming |
| `reservations` | `Reservation` — pickup-window flow (user-initiated and waitlist-auto-created) |
| `notifications` | `NotificationPreference`, `PushSubscription`, `NotificationLog`, email/push dispatch |

**Cross-app rules enforced by design:**
- `inventory.Toy.status` is never written directly (`toy.status = X; toy.save()` is banned by
  convention). Every transition goes through `inventory.services.transition_toy_status(toy,
  new_status, actor, reason)`, which validates against an explicit `ALLOWED_TRANSITIONS` map,
  writes a `ToyStatusLog` row, and does it all inside `transaction.atomic()`. The API exposes
  `status` as read-only; the only way to change it is `POST /api/toys/{id}/transition/` or an
  internal service call.
- `billing.LedgerEntry` is the only money-movement table (joining fees, deposits, renewals,
  late fees, paid extensions, refunds, tier-change adjustments). Entries are immutable once
  `PAID` — corrections are new offsetting entries, never edits.
- Apps reference each other's models via Django's string `ForeignKey("app.Model")` and import
  each other's `services` modules lazily (inside functions) where it would otherwise create an
  import cycle — e.g. `inventory.services` calls into `waitlist.services` only at the point a
  toy becomes `AVAILABLE`; `billing.services.mark_paid` calls into `checkouts.services` and
  `memberships.services` only for the entry types that need a post-payment side effect.

## Data model (by app)

**accounts**
- `User` (UUID pk, email as `USERNAME_FIELD`, `is_email_verified`, `is_staff`)
- `SingleUseToken` (`purpose`: `EMAIL_VERIFICATION` / `PASSWORD_RESET`)
- `TwoFactorRecoveryCode`, `PreAuthToken` (short-lived, issued after password check for
  2FA-enrolled users; exchanged for a full token via a TOTP code)
- TOTP devices are `django_otp.plugins.otp_totp.models.TOTPDevice` (third-party, not
  reimplemented)

**memberships**
- `MembershipTier`: `code` (SILVER/PLATINUM/DIAMOND), `joining_fee`, `deposit_amount`,
  `renewal_fee` (stored explicitly = 50% of joining_fee at seed time, not derived live so
  historical renewals stay correct if pricing changes), `max_concurrent_checkouts`,
  `loan_period_days`, `complimentary_extension_days`
- `Membership`: `user`, `tier`, `status` (`PENDING_PAYMENT` / `ACTIVE` / `DISCONTINUED`),
  `renewed_through`, `deposit_ledger_entry`. `UniqueConstraint` enforces one `ACTIVE`
  membership per user.
- `MembershipTierChange`: audit trail for upgrade/downgrade, links the deposit-adjustment
  `LedgerEntry`
- `MembershipSignOff`: discontinuation record — deposit due (snapshotted from the original
  charge, not current tier config), amount actually returned, required deduction reason if
  less than the deposit

**billing**
- `LedgerEntry`: `entry_type` (JOINING_FEE / DEPOSIT / RENEWAL_FEE / LATE_FEE /
  PAID_EXTENSION_FEE / DEPOSIT_REFUND / TIER_CHANGE_ADJUSTMENT / OTHER), `amount` (always
  positive), `direction` (CHARGE / CREDIT), `status` (PENDING / PAID / WAIVED / CANCELLED),
  optional FKs back to the checkout/membership/donation that generated it

**inventory**
- `Toy`: `status` (INTAKE / AVAILABLE / RESERVED / CHECKED_OUT / OVERDUE / BROKEN /
  UNDER_REPAIR / RETIRED), `condition`, `source` (PURCHASED / DONATED)
- `ToyStatusLog`: every transition, who triggered it (nullable = system/Celery), why
- `IntakeRecord`: assessment at donation intake, post-repair, or initial purchase

**donations**
- `Donor` (may be a non-member), `Donation` (SUBMITTED → ACCEPTED/REJECTED → IN_INTAKE →
  COMPLETED), `DonationItem` (`item_type` enum explicitly includes `SOFT_TOY`/`DOLL` so
  rejecting them is a clean validation error, not fragile keyword matching on free text),
  `DonationReceipt` (frozen itemized snapshot, sequential `DON-YYYY-NNNNNN` numbers)

**checkouts**
- `CheckoutRecord`: `membership` is snapshotted at checkout time (a later tier change doesn't
  retroactively alter an in-progress loan), `original_due_date` vs `current_due_date`
  (mutated by extensions), `complimentary_extension_used`, `status` (ACTIVE / RETURNED /
  OVERDUE — OVERDUE is derived, only ever set by the Celery sweep, never via the API)
- `Extension`: `extension_type` (COMPLIMENTARY / PAID), `days_added`, linked `LedgerEntry` for
  paid ones, `applied` flag (paid extensions are two-phase — see below)
- `LateFeeAssessment`: one row per daily assessment run, backing a single growing
  `LedgerEntry` per overdue episode

**waitlist**
- `WaitlistEntry`: `status` (WAITING / CONVERTED_TO_RESERVATION / EXPIRED / CANCELLED),
  `UniqueConstraint` prevents duplicate active entries per (toy, user)

**reservations**
- `Reservation`: `pickup_by_date` (≤ 2 days out), `pickup_deadline` (precise `DateTimeField` —
  needed for the "10 hours before" reminder to have an unambiguous instant), `status` (ACTIVE
  / PICKED_UP / EXPIRED / CANCELLED), optional `waitlist_entry` FK (set when
  system-auto-created rather than user-initiated)

**notifications**
- `NotificationPreference` (per-category toggles: due-date, waitlist, reservation, billing),
  `PushSubscription` (soft-deactivated on HTTP 404/410 instead of hard-deleted),
  `NotificationLog` (every send, every channel, powers the in-app notification center)

## Key business logic

### Toy status state machine

```
INTAKE ──▶ AVAILABLE | BROKEN
AVAILABLE ──▶ RESERVED | CHECKED_OUT | BROKEN | UNDER_REPAIR | RETIRED
RESERVED ──▶ CHECKED_OUT | AVAILABLE
CHECKED_OUT ──▶ AVAILABLE | RESERVED | UNDER_REPAIR | BROKEN | OVERDUE
OVERDUE ──▶ AVAILABLE | RESERVED | CHECKED_OUT | UNDER_REPAIR | BROKEN
BROKEN ──▶ UNDER_REPAIR | RETIRED
UNDER_REPAIR ──▶ AVAILABLE | RETIRED | BROKEN
```

Enforced by `inventory.services.transition_toy_status` against an explicit
`ALLOWED_TRANSITIONS` dict (`apps/inventory/services.py`). `OVERDUE` is flipped only by the
hourly Celery sweep, keyed off `CheckoutRecord.current_due_date`.

### Checkout / extension / late fee (tiered, per confirmed business rules)

| Tier | Concurrent checkouts | Loan period | Complimentary extension |
|---|---|---|---|
| Silver | 1 | 14 days | 2 days |
| Platinum | 2 | 14 days | 3 days |
| Diamond | 5 | 21 days | 5 days |

- **`create_checkout`**: validates `membership.status == ACTIVE`, `renewed_through >= today`
  (lapsed membership blocks new checkouts), and under the tier's concurrent-checkout limit.
- **Complimentary extension**: only while `status == ACTIVE` (blocked once `OVERDUE`), one-time
  per checkout, extends from `current_due_date` (not from today).
- **Paid extension (5¢/day)**: two-phase. `apply_paid_extension` creates a PENDING
  `LedgerEntry` and an `Extension(applied=False)` row but does **not** move the due date.
  Only `billing.services.mark_paid` → `checkouts.services.confirm_paid_extension` actually
  advances `current_due_date` (and reverses `OVERDUE` status if applicable) — matching the
  cash-collection reality that staff confirm payment in person.
- **Late fees (15¢/day)**: hourly Celery sweep (`checkouts.tasks.assess_late_fees`) flips
  ACTIVE → OVERDUE past the due date and upserts a single growing PENDING `LedgerEntry` per
  overdue episode, **capped at the member's deposit amount** to bound liability.
- **Sign-off**: blocked while any ACTIVE/OVERDUE checkout or PENDING charge exists for the
  member — staff must resolve everything before the deposit refund can be processed.

### Waitlist → soft-hold reservation

When a toy transitions to `AVAILABLE` (return, repair completion, intake completion) and a
`WaitlistEntry` exists:
1. Take the oldest `WAITING` entry (FIFO).
2. **Auto-create a `Reservation`** for that user (2-day pickup window) and transition the toy
   straight to `RESERVED` — never leaving it in a plain `AVAILABLE` state another member could
   grab. This reuses the same `Reservation`/expiry machinery as a user-initiated reservation.
3. Mark the entry `CONVERTED_TO_RESERVATION`, send a `WAITLIST_AVAILABLE` notification.
4. If the reservation expires unpicked, the toy reverts to `AVAILABLE` and the same claim logic
   runs again for the next entry in line.

Implemented in `waitlist.services.claim_next_waitlist_entry`, invoked from
`inventory.services.transition_toy_status` whenever the new status is `AVAILABLE`.

### Membership tier change

`memberships.services.change_tier` computes the deposit difference between tiers:
- **Upgrade** (higher deposit): creates a PENDING charge; the tier does **not** change until
  the charge is marked paid (`confirm_tier_change_charge`, mirroring the paid-extension
  pay-gate pattern).
- **Downgrade** (lower deposit): credits the difference immediately and applies the tier
  change immediately.

In-progress checkouts are never affected by a tier change — `CheckoutRecord.membership` is
snapshotted at checkout time.

## Background jobs — Celery + Celery Beat + Redis

Chosen over cron (no retry/observability/ad-hoc-trigger support) and APScheduler (in-process,
doesn't survive restarts or scale past one worker). `django-celery-beat` gives DB-editable
schedules; seeded once via `manage.py seed_periodic_tasks`
(`apps/common/management/commands/seed_periodic_tasks.py`):

| Task | Cadence | Purpose |
|---|---|---|
| `checkouts.tasks.assess_late_fees` | hourly | Flip ACTIVE→OVERDUE, accrue capped late fee |
| `checkouts.tasks.send_due_date_reminders` | daily | Reminders 3 and 1 day before due, with extension CTA |
| `reservations.tasks.expire_reservations` | every 15 min | Expire past pickup deadline, revert toy to AVAILABLE, re-trigger waitlist claim |
| `reservations.tasks.send_reservation_reminders` | every 15 min | Reminder ~10h before pickup deadline |
| `memberships.tasks.send_renewal_reminders` | daily | Renewal-due notifications |
| `notifications.tasks.retry_failed_push` | every 15 min | Deactivate stale push subscriptions |

Immediate (non-scheduled) triggers fire synchronously from service-layer code — e.g. the
waitlist auto-claim and the `notifications.services.notify()` fan-out on checkout creation,
extension, donation acceptance, and reservation creation.

## API surface (DRF)

Auth: `TokenAuthentication` for the PWA + `SessionAuthentication` for the Django admin. 2FA is
a two-step login — password grants a short-lived `pre_auth_token`, then a TOTP code exchanges
it for a full token.

```
# Auth  (api/auth/)
POST /signup/  /verify-email/  /login/  /2fa/verify/  /2fa/enroll/  /2fa/confirm/  /2fa/disable/
POST /password-reset/request/  /password-reset/confirm/
GET/PATCH /me/

# Memberships  (api/memberships/)
GET  /tiers/                              (public)
GET  /me/                                 current user's membership
POST /signup/                             {tier_code}
GET  /                                    list (own, or all if staff)
POST /{id}/activate/                      staff-only
POST /{id}/change-tier/                   {new_tier_code}
POST /{id}/signoff/                       staff-only {amount_returned, reason}

# Billing  (api/ledger-entries/)
GET  /?status=&entry_type=&user=
POST /{id}/mark-paid/                     staff-only

# Inventory  (api/toys/)
GET/POST /            (write = staff-only, status read-only)
PATCH/GET /{id}/
POST /{id}/transition/                    staff-only {new_status, reason}
GET  /{id}/status-log/

# Checkouts  (api/checkouts/)
GET/POST /             (create = staff-only)
POST /{id}/return/                        staff-only {condition, damaged_status?}
POST /{id}/extend/complimentary/
POST /{id}/extend/paid/                   {days}
GET  /{id}/extensions/

# Waitlist  (api/waitlist/)
GET/POST/DELETE /

# Reservations  (api/reservations/)
GET/POST /   POST /{id}/cancel/   POST /{id}/confirm-pickup/  (staff-only)

# Donations  (api/donations/)
POST /                                    public (donor may be non-member)
GET  /                                    staff-only
POST /{id}/accept/  /{id}/reject/         staff-only
POST /{id}/items/{item_id}/complete-intake/   staff-only -> creates a Toy
GET  /{id}/receipt/

# Notifications  (api/)
GET  /notifications/    POST /notifications/{id}/mark-read/
GET/PATCH /notification-preferences/me/
POST/DELETE /push-subscriptions/
```

Business-rule validation lives in the `services.py` module of the owning app, not in
serializer `.save()` overrides — views call services and translate `ValueError` into a 400.
Object-level access control mostly happens at the **queryset** level (`get_queryset()` scopes
non-staff users to their own rows before any object permission check runs), so a non-owner
requesting another member's resource gets a 404, not a 403.

## Frontend (Next.js 16, App Router)

```
app/
  (auth)/       login, signup, verify-email, 2fa/verify
  (member)/     dashboard, browse, browse/[toyId], checkouts, reservations,
                membership, notifications, settings
  (staff)/      admin/inventory, admin/donations, admin/checkouts,
                admin/reservations, admin/billing, admin/members
  layout.tsx    PWA manifest link
  manifest.ts   PWA manifest
lib/
  api-client.ts   fetch wrapper, token auth header, typed ApiError
  auth.tsx        React context wrapping /api/auth/me/
  push.ts         service worker registration + push subscription flow
  types.ts        shared TS types mirroring the DRF serializers
public/sw.js      service worker: push + notificationclick handlers
```

- `(member)` and `(staff)` are separate route groups, each with its own layout that redirects
  unauthenticated/unauthorized users (`useAuth()` + `useEffect` redirect, not middleware).
- Data fetching via React Query; every mutation invalidates the relevant query key.
- The checkout resource serializer exposes computed `complimentary_extension_available` and
  `paid_extension_rate` fields so the frontend renders the correct CTA without re-deriving
  business rules client-side.
- Web push: VAPID keys generated once, public key in `frontend/.env.local`, private key in
  `backend/.env`. Subscribe flow registers `public/sw.js`, calls
  `pushManager.subscribe()`, and POSTs the subscription to `/api/push-subscriptions/`
  (`update_or_create` on `endpoint` so re-subscribing doesn't duplicate rows).

## Testing

`backend/apps/*/tests.py` — service-layer unit tests (business rules, state machine
transitions) using `factory_boy` factories (`apps/common/factories.py`).

`backend/apps/*/test_api.py` — DRF `APIClient`-based endpoint tests (auth, permissions,
validation, status codes) using the shared fixtures in `backend/conftest.py`
(`api_client`, `member_client`, `staff_client`, `active_membership`, `toy`, `silver_tier`).

Run with `pytest --cov=apps --cov-report=term-missing` from `backend/`. As of the last run:
140 tests, 94% statement coverage — the uncovered remainder is Celery task wrappers (thin
pass-throughs to already-tested service functions) and the network-I/O internals of email/push
sending.

## Known simplifications / not yet built

- No live payment gateway — all fees/deposits are ledger entries; staff mark them paid after
  collecting cash/card in person.
- No production deployment config (Dockerfiles for Django/Celery/Next, CI, hosting) — local
  dev only, per the original scope.
- Web push is verified to work on `localhost`; production will need a real HTTPS domain.
- No native mobile app — the frontend is a responsive, installable PWA instead.
