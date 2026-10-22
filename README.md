# HackAMatch

**Live application:** https://hackamatch.onrender.com/

Hosted on Render with a separate persistent PostgreSQL database. Deployment verified on 22 October 2026: homepage/login/signup and database health respond; private API routes reject anonymous requests. PostgreSQL integration (36 tests), production frontend build and full Docker smoke test pass in GitHub Actions.

This is a free preview deployment. It sleeps when idle. Email delivery and organizer account setup are required before real registrations.

A questionnaire-based team formation app for **Data Mavericks × NSDC**. Participants verify the email used on Luma, see their imported responses, and join a server-timed registration window. A persistent worker proposes teams of exactly three; an organizer reviews and publishes them. Participants only see their own team after publication.

This repository contains the application source, local setup, and Render deployment configuration. Real participant data is not included. See [verification](docs/VERIFICATION.md) for prior local checks and [Render deployment](deploy/README.md) for the hosted runtime and free-preview limitations. GitHub Actions runs PostgreSQL integration, frontend production build, and a complete Docker smoke test on pushes.

## Included

- Next.js 16, TypeScript, Tailwind CSS 4 and a shadcn-style Radix Button component.
- FastAPI/Pydantic, SQLAlchemy, PostgreSQL, two Alembic migrations.
- Password hashing, email ownership verification, hashed opaque sessions, organizer authorization, origin checks, persistent rate limits, safe errors.
- Private CSV/XLSX import preview, exact Luma field mapping, normalization, full-export reconciliation, versioned originals and import history.
- Configurable eligibility, required fields, offline availability and scoring weights; audited exclusions and overrides.
- Seeded multistart allocation with candidate scoring and global swap improvement, component breakdowns and explicit waitlists.
- Database-driven background scheduling with row locking, durable jobs, frozen snapshots, retries and restart recovery.
- Organizer review, regeneration, swaps/reassignments, publication, CSV/XLSX export and administrative audit log.
- All requested participant and organizer routes, loading/error/empty states and responsive dark styling.
- Synthetic demo CSV, automated tests, a PostgreSQL integration workflow, Dockerfiles and Docker Compose.

## Start locally with Docker Desktop

Install Docker Desktop and enable its Compose support. No cloud account is required for local use.

1. Extract this folder and open a terminal inside it.
2. Copy `.env.example` to `.env`:
   - PowerShell: `Copy-Item .env.example .env`
   - macOS/Linux: `cp .env.example .env`
3. Set `POSTGRES_PASSWORD` in `.env` to a random URL-safe value. For example, generate one locally with `python -c "import secrets; print(secrets.token_urlsafe(32))"`. Keep it private.
4. Start the application:

```sh
docker compose up --build -d
```

5. Open **http://localhost:3000**. Use `localhost` consistently because the backend validates the configured origin.
6. Create your organizer account from the trusted server terminal:

```sh
docker compose exec api python -m app.cli organizer organizer@example.test
```

Replace the example address with your organizer email. The command prompts privately for a password if the account is new. There is no default administrator password. This operator command grants organizer status; ordinary participants must use email verification.

7. Log in on the website, then choose **Switch to organizer view**.
8. Open **Luma imports**, choose the original Luma CSV, review the mapping and counts, then **Confirm import**. Use `demo/synthetic-attendees.csv` for a demonstration instead.

PostgreSQL, migrations, API, scheduler, frontend and a development email inbox start as separate services. Database volumes survive restarts. The API and database are not exposed as public host ports.

### Email verification during development

Open **http://localhost:8025** to view Mailpit's local development inbox. Messages are captured locally; they are not delivered to real recipients. A participant signs up on the website, opens their verification link from that inbox, confirms ownership, then logs in.

Only use synthetic participants with this shared development inbox. For a real event, configure a real SMTP service so each participant receives their own verification link. Do not expose Mailpit or use it as proof of ownership for real attendees.

To disable email entirely, set `SMTP_HOST=` in `.env` and recreate the API/worker. The app remains usable by existing verified accounts, displays delivery-disabled notices, and queues verification requests. New participants cannot become eligible without proving email ownership.

### Run a short matching window

1. Import the synthetic CSV and verify a few synthetic accounts first.
2. In **Matching window**, select **1 minute — development only** (or the 10-second automated-test duration).
3. Choose required profile fields, optional mandatory offline availability and scoring weights. Open the window.
4. Have verified participants select **Join the pool** before the deadline.
5. The worker notices the deadline within roughly two seconds, freezes eligibility and creates proposals. No browser needs to remain open.
6. Review **Team proposals**, including any waitlisted or ineligible registrations, and publish. Participants can now view their team.

Exactly three distinct participants are required per complete team. Leftovers stay visible. Reassignment can swap two frozen-pool participants or exchange a team member with someone waitlisted. Regeneration preserves the frozen pool and changes the seed. Reopening discards unpublished proposals and opens another two-hour window. Opening a new window after publication creates a separate matching round.

## Testing

The automated elapsed-time integration test uses a loopback SMTP server and an independent scheduler process. It verifies signup → delivered email → ownership verification → login → joining → actual 10-second expiry → proposals → publication → member visibility.

Run the full suite against a disposable PostgreSQL database, including concurrent matching:

```sh
docker compose -f compose.test.yaml up --build --abort-on-container-exit --exit-code-from tests
```

This uses a separate Compose project, a temporary PostgreSQL data directory and synthetic credentials/data. It does not connect to your event database. Stop its services afterward:

```sh
docker compose -f compose.test.yaml down
```

Without Docker, use Python 3.12 and a virtual environment:

```sh
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Tests use a new temporary SQLite database by default; PostgreSQL row-lock concurrency is skipped there. To exercise that test, explicitly set `TEST_DATABASE_URL` to an isolated PostgreSQL database whose name contains `test`. The suite drops/recreates its test tables; it deliberately ignores a normal `DATABASE_URL` for test selection.

Build the frontend separately with Node.js 22:

```sh
cd frontend
npm ci
npm run build
```

`.github/workflows/verify.yml` provides PostgreSQL integration and frontend-build jobs when this source is put in a GitHub repository. It has not been run on GitHub in this session.

## Run without Docker

For local exploration, SQLite can be used with one API and one scheduler. PostgreSQL is required for production concurrency guarantees.

```sh
cd backend
python -m pip install -r requirements-dev.txt
python -m alembic upgrade head
```

Then, from `frontend`, run:

```sh
npm ci
npm run dev -- --with-backend
```

The combined development launcher runs migrations, API and worker with an isolated SQLite preview database at `/tmp/hackamatch-preview.db`. On Windows, use Docker or set `DATABASE_URL` to an appropriate SQLite absolute path before invoking the combined launcher. Standard `npm run dev` launches the frontend only; run the API and worker yourself with the same database URL if preferred.

For separate processes, set `APP_ENV=development`, `COOKIE_SECURE=false`, `PUBLIC_URL=http://localhost:3000` and your `DATABASE_URL` in the API/worker environment, then use `python -m uvicorn app.main:app --port 8000 --no-access-log` and `python -m app.worker`. Frontend requests proxy to `http://127.0.0.1:8000` by default. `API_INTERNAL_URL` changes that destination at frontend build time.

## Deploy the full application

Deploy the provided Docker Compose stack to a host with Docker, or deploy the frontend, API, worker and PostgreSQL separately. Sites hosting alone does not run this Python/PostgreSQL stack; this package preserves the requested architecture.

1. Provide persistent PostgreSQL storage and backups, then run `python -m alembic upgrade head` once before starting API/worker processes.
2. Set `APP_ENV=production`, the exact HTTPS `PUBLIC_URL`, and `COOKIE_SECURE=true` in API and worker environments. Production windows enforce a two-hour duration.
3. Configure real SMTP credentials, TLS and a verified sender domain. Keep credentials in the hosting provider's secret store.
4. Build the frontend with `API_INTERNAL_URL` pointing to the internal API service. Place the frontend behind an HTTPS reverse proxy at `PUBLIC_URL`; keep the API/database private. The supplied Compose web port is bound to loopback for a host reverse proxy.
5. Keep at least one worker running continuously. Multiple workers are supported with PostgreSQL row locks. Do not replace the worker with a browser timer.
6. Bootstrap an organizer from the trusted host, sign in, and import the real export privately.
7. Run the isolated PostgreSQL tests and a short synthetic rehearsal in a development environment before opening real registrations.

The root Dockerfile and `render.yaml` provide a single-service Render deployment with an external PostgreSQL database. Read [the hosting guide](deploy/README.md) before opening real registrations. Production email credentials and organizer account setup are separate from publishing the source.

## API and architecture

- Interactive API docs: `/docs` on the internal FastAPI service; OpenAPI is also in `docs/openapi.json`.
- Relational schema: `backend/app/models.py`; PostgreSQL DDL in `docs/schema-postgresql.sql`.
- Import mapping/normalization: `backend/app/importer.py`.
- Scoring/optimization: `backend/app/matching.py`; detailed decisions in `docs/ARCHITECTURE.md`.
- Registration and publication rules: `backend/app/service.py`.
- Durable scheduler/outbox: `backend/app/worker.py`.
- Exact field names and dataset observations: `docs/DATASET-AUDIT.md`.

The UI includes `/`, `/login`, `/signup`, `/dashboard`, `/waiting-room`, `/team`, `/admin`, `/admin/luma`, `/admin/participants`, `/admin/matching`, `/admin/teams`, `/admin/audit`. All administrative data endpoints require a verified organizer session. Teammate contacts, phone numbers, SAP IDs and raw source rows are not returned to participants.

## Imports, retention and operational decisions

Each accepted import is a **full replacement of the active attendee set**, not an incremental batch. Missing rows become inactive. Identical bytes are a no-op, including when that version has since been archived. Re-importing a historical identical file does not silently reactivate it. Changed exports reconcile by `guest_id`; duplicate normalized emails require review. Conflicting rows sharing a guest ID are quarantined; exact duplicate rows are deduplicated.

Participant self-editing is disabled. Organizer availability/exclusion overrides require a reason and survive later imports. Historical import originals and frozen matching inputs remain available for audit. Skill mapping changes re-normalize current profiles but do not change frozen snapshots.

Operational recommendation: retain event imports and snapshots only for the agreed audit period (for example, 90 days after the event), then use the trusted operator command below. It deletes event imports, teams, registrations, windows and email outbox contents while retaining account identities and administrative audit records:

```sh
docker compose exec api python -m app.cli purge-event --confirm "DELETE EVENT DATA"
```

This is destructive; run it only when the event's retention period has ended and any required export is secured. Account retention and removal must follow the organizer's privacy policy. Never commit real CSV exports, databases, `.env` files or participant screenshots.
