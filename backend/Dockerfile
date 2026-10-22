FROM python:3.12-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home app
COPY --chown=app:app . .
USER app
CMD ["python","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--no-access-log"]

FROM base AS tests
USER root
RUN pip install --no-cache-dir -r requirements-dev.txt
USER app
CMD ["python","-m","pytest","-q"]

FROM base AS runtime
