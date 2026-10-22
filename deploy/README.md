# Render deployment

The root Dockerfile builds the Next frontend and runs it with the private Python API and durable matching worker in one supervised service. The public URL routes all `/api/*` traffic internally to the API. A failure in any required process exits the container so Render can restart it. Schema migrations run before HTTP traffic starts. Database contents must be in external PostgreSQL, never ephemeral SQLite.

Use the `render.yaml` Blueprint or create a Docker web service from the repository root. Set `DATABASE_URL` to the pooled application connection and `DATABASE_URL_UNPOOLED` to the direct migration connection. Standard `postgresql://` URLs are accepted. The start process derives `PUBLIC_URL` from Render's actual `RENDER_EXTERNAL_URL`, so a guessed hostname is not required.

The default plan is **free for preview**. Render's free service sleeps after 15 minutes without inbound traffic; it can take about a minute to wake. The matching worker runs while the service is awake and recovers due windows after wake/restart. This preview plan does **not** guarantee an unattended match at the exact deadline. Use always-on compute for a live event that requires matching without visitors. No paid upgrade is applied automatically.

Email delivery starts disabled. Real participants cannot verify ownership until a real delivery method is configured. Render blocks standard outbound SMTP ports on free services; use an approved HTTP email delivery integration or an appropriate compute plan before real registrations. Never use a shared development inbox to verify real email ownership.

All participant data stays in the private database. Do not upload the real Luma CSV to GitHub. Import it from the authenticated organizer dashboard only after deployment and organizer account setup.

The CI workflow checks real PostgreSQL concurrency and builds/runs the complete Docker image with a disposable database. Do not call a service live until its deploy is `live` and the landing page and `/api/health` have been verified.

References:
- https://render.com/docs/docker
- https://render.com/docs/free
- https://render.com/docs/health-checks
