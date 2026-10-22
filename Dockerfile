FROM node:22-bookworm-slim AS node-runtime
FROM node-runtime AS frontend-build
WORKDIR /build/frontend
ENV NEXT_TELEMETRY_DISABLED=1
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ARG API_INTERNAL_URL=http://127.0.0.1:8000
ENV API_INTERNAL_URL=$API_INTERNAL_URL
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt && useradd --create-home app
COPY --chown=app:app backend/app /app/backend/app
COPY --chown=app:app backend/alembic /app/backend/alembic
COPY --chown=app:app backend/alembic.ini /app/backend/alembic.ini
COPY --chown=app:app deploy/start.py /app/deploy/start.py
COPY --from=frontend-build --chown=app:app /build/frontend/.next/standalone /app/web
COPY --from=frontend-build --chown=app:app /build/frontend/.next/static /app/web/.next/static
USER app
EXPOSE 10000
CMD ["python", "/app/deploy/start.py"]
