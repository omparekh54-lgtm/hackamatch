# Verification — 21 October 2026

## Results actually obtained

| Check | Result |
|---|---|
| Backend automated suite | **35 passed, 1 skipped**, no failures/errors; about 24 seconds |
| Exact supplied CSV through the real import pipeline | 96 accepted, 90 approved, 6 declined, 33 unknown availability, no ambiguous emails |
| Header coverage | All 52 actual column names inspected; exact-header synthetic fixtures provided |
| Signup/email/session flow | Passed, including single-use/expired links, unverified eligibility and logout |
| Actual SMTP delivery test | Passed against a loopback SMTP inbox with synthetic addresses |
| Actual elapsed registration window | Passed: 10-second window, nine verified participants, independent worker process, three teams, organizer publication, member visibility |
| Matching pools | Passed for 0, 1, 2, 9, 10, 20 and 96 people, plus unknown/unbalanced skills |
| Determinism and constraints | Fixed seed reproduces allocation; complete accounting, no duplicates, exact team size and explicit waitlist |
| Job idempotency/recovery | Repeated execution, worker restart and injected failure rollback/retry passed |
| Import reconciliation | Idempotency, duplicate emails, conflicting IDs, blank/malformed values, historical originals and override preservation passed |
| Administration | Authorization, audited overrides, configuration, swaps, regeneration, reopening and publication checks passed |
| Exports | CSV/XLSX passed; formula-prefix neutralization passed |
| PostgreSQL migrations | Alembic compiled PostgreSQL DDL successfully; SQLite upgrade ran successfully |
| Frontend | Production Next.js build and TypeScript check passed |
| Browser | Landing layout inspected; signup review encountered preview/runtime limitations; authenticated browser flows are **not verified** |
| Compose | YAML structure, service dependencies and persistent volumes parsed/checked; containers **not run** in this environment |

The skipped test is **concurrent matching on PostgreSQL**. SQLite does not provide equivalent row-lock semantics. `compose.test.yaml` and the GitHub workflow include a disposable PostgreSQL test setup that runs this check; neither Docker nor that GitHub workflow was run here. Runtime PostgreSQL migration execution and production concurrency remain acceptance checks before real registrations.

A separate synthetic 96-person allocation produced 32 teams with no leftovers in roughly **2.2 seconds** in one measured run. This is a local benchmark, not a production latency guarantee. The test suite enforces a 10-second upper bound for its expected synthetic pools.

The suite emits one upstream deprecation warning about FastAPI/Starlette's httpx TestClient integration; it does not affect the passing assertions. Real participant information is absent from tests, source, demo data and this report.

## Remaining deployment/acceptance work

- Run `docker compose -f compose.test.yaml up --build --abort-on-container-exit --exit-code-from tests` to validate runtime PostgreSQL migrations/locking and the packaged container build on a Docker host.
- Configure real SMTP, HTTPS, production secrets, PostgreSQL persistence/backups and an always-running worker on the chosen host.
- Verify authenticated organizer and participant browser flows on that deployment, including responsive layouts and cookie forwarding through the proxy.
- Privately import the current full Luma export, resolve review records and rehearse with synthetic accounts before opening the real two-hour window.

No production service was deployed, no real participant emails were sent, and no live matching window or allocation was activated. The real-data inspection used an isolated private local database; it was excluded from the source package.
