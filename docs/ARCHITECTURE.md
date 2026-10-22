# Architecture and implementation decisions

## Trust and eligibility

Email is trimmed/lowercased; Luma `guest_id` identifies source registrations. A name never grants eligibility. Accounts store PBKDF2-SHA256 password hashes with per-user salts and 600,000 iterations. Verification links and session tokens use 32 bytes of cryptographic randomness; only token hashes are stored in the token table. Verification messages temporarily contain their delivery link in a private durable outbox. Tokens expire after 24 hours; verification links are single-use. Session cookies are HttpOnly, SameSite=Lax and Secure in production.

Signups cannot choose their role. Only the trusted host bootstrap command creates/promotes organizers. Both role and verified status are required for organizer endpoints. Unverified participants cannot load imported responses or join. Duplicate normalized emails in the current dataset require manual review. Approval must be exactly `approved`; declined records are ineligible and other statuses require review.

Eligibility is evaluated when joining, again when the pool freezes, and again for assigned participants at publication. Default required fields are recognized skills, goals and schedule. Offline availability is optional by default and can be made mandatory per window. Unknown is separate from no. A confirmed override survives imports; self-editing is not enabled.

The frontend proxies API calls to keep cookie auth on one origin. Mutations reject unexpected Origin headers. The API/database are intended to be private services. Account/IP rate-limit buckets persist in the database with atomic upserts; client IP should be supplied by trusted network topology, not blindly accepted from caller-controlled forwarded headers. Configure edge rate limits when exposing the frontend publicly. Uploads are limited to 5 MB; XLSX decompression is limited to 30 MB. CSV headers, rows, identity fields and input schemas are validated. Errors do not expose SQL parameters or raw participant records. Exports neutralize spreadsheet-formula prefixes.

## Import model

Every source column is preserved privately in versioned import records. The current attendee table keeps the active version for efficient lookups. Import summaries track accepted, rejected, duplicate, ambiguous-email and approval counts. Each import has a SHA-256 file fingerprint. The same file cannot create another dataset version. Import writes and the audit entry are transactional. A malformed/empty import with no accepted rows cannot deactivate the current dataset.

The exact questionnaire columns map into normalized features. Goals, schedule and music are sets; hobbies/feed/self-description use transparent token normalization. Year recognizes ordinal years and known shorthand; malformed years stay unknown. A full-stack label remains its own category. Administrator keyword mappings are editable and version changes are audited. Phone, gender, SAP ID, email domain and payment metadata never enter the scoring function.

A partial export must not be used as if it were a full replacement. The import preview explicitly explains replacement semantics. Conflicting repeated guest IDs are quarantined; ambiguous repeated emails remain in source but cannot establish eligibility. Historical original responses remain separate from current normalization.

## Matching

Each component is a 0–1 score; the UI presents 0–100. Available component weights are renormalized when data is missing. Entirely unknown profiles receive a neutral score, not a negative judgment. Default weights:

| Component | Weight | Definition |
|---|---:|---|
| Skills | 35% | 60% category breadth, 40% pairwise marginal diversity; `other` is omitted |
| Roles | 20% | Best distinct-person assignment to building, design and communication responsibilities |
| Goals | 15% | Average pairwise Jaccard overlap of stated hackathon goals |
| Experience | 10% | Team mean proximity to the known pool mean, balancing experience across teams |
| Schedule | 10% | Pairwise overlap of productivity periods |
| Working style | 5% | Leadership balance, conflict-style distribution and stretch-learning support |
| Interests | 5% | Low-weight token/set overlap across hobbies, self-description, feed and soundtrack |

Skills measure diversity rather than individual ability. Role scoring measures whether *different people* can cover responsibilities. Full-stack contributes 0.8 to build coverage and 0.35 to design coverage, rather than being treated as specialist coverage everywhere. Only the best assignment of the three roles is counted. The skill and role components still correlate; their deliberate different definitions and heuristic weights are documented rather than claimed to be statistically independent.

Conflict categories are the actual source choices: debate, vote and deferring to the owner. Variety is a small soft preference; no style is ranked as intrinsically better. Leadership answers distribute strong leaders/avoiders without appointing a formal leader. A stretch preference receives a small support signal when another teammate shares a skill and is not exclusively stretching. Interests do not infer intelligence, reliability or personality traits. College/year are normalized for profile context but are not included in the MVP score.

The allocation sorts stable participant IDs, seeds a local RNG, uses 16 restarts, caches candidate triple scores and performs global improving swaps across teams and the waitlist. It chooses the highest **sum of team scores**, with a fixed complete-team count. Waitlist members can participate in swaps, so the earliest rows are not automatically favored. At least floor(n/3) teams are created; n mod 3 people are explicitly waitlisted. A deterministic final validation requires exactly three distinct people per team, no duplicate assignments and full accounting for the input pool.

This is a heuristic optimization, not a proof of a globally optimal partition or a validated measure of human compatibility. Candidate generation is sampled, not exhaustive. Supported allocation size is capped at 500 verified participants per window to bound worker cost; the expected event pool is much smaller. Scores are explainable suggestions for organizer review.

## Persistence, deadline and concurrency

Window rows persist opening/closing times, policy, scoring settings, freeze and publication timestamps. A generated unique active-slot column prevents two active windows, including concurrent creations. A job key `match:<window_id>` and unique window constraints prevent duplicate jobs. The worker polls every two seconds; it never depends on browser state.

On the deadline, a PostgreSQL transaction locks the window row with `FOR UPDATE`. Workers use `SKIP LOCKED` when selecting due windows. The transaction re-evaluates joined registrations, captures the active import reference and normalized eligible pool, computes the allocation, saves teams/members, and transitions to review. A process crash rolls back that transaction; the persisted open/failed window remains recoverable. Publication is a separate locked transaction. Other matching requests wait, then see review/published status and return without duplicating teams. Member uniqueness is enforced by `(window_id, user_id)`.

The externally observable successful transition is open/scheduled → review; the intermediate matching status is written within the atomic transaction. The UI derives closing from the backend deadline before the worker finishes. Failure rolls back partial work; the worker stores a sanitized failure status in a savepoint-aware transaction and retries up to five times with a 30-second cooldown. Organizers can retry after resolving the cause.

The deadline is strict for joining. Freeze happens when the worker detects it, normally within two seconds, and uses eligibility at that transaction. Changes to the current dataset before that detection can affect eligibility; the stored freeze timestamp identifies the actual cutoff used. Once frozen, regeneration uses the snapshot. Reopening explicitly discards unpublished proposals/snapshot and rechecks eligibility for the new deadline.

The mail outbox is persistent, locked during delivery and retried up to five times. Delivery is at least once: a process crash after SMTP acceptance but before commit can send a duplicate verification email. Tokens remain single-use. Matching does not require SMTP delivery to be enabled; new email ownership verification does.

## Data exposure and retention

Imported records, current profiles and snapshots are accessible only on the backend. Participants retrieve their own questionnaire after verification. Before publication, teammate information is withheld. After publication, each authenticated participant can retrieve only their own team and a restricted teammate profile (name, skills, goals, schedule, hobbies). Teammate contact details and raw exports remain private.

Audit events contain administrative IDs, actions, reasons and safe counts/algorithm metadata. An explicit event purge command deletes event data in foreign-key order after the organizer's retention period. Accounts and safe administrative audit history remain. Backups, encryption at rest and account retention are deployment responsibilities.
