"""Run the Next frontend, private FastAPI API and durable scheduler on Render."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def environment():
    env = os.environ.copy()
    if not env.get("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL must be configured; production does not use local SQLite")
    if env["DATABASE_URL"].startswith("sqlite"):
        raise RuntimeError("Configure persistent PostgreSQL for hosted deployments")
    env.setdefault("APP_ENV", "production")
    env.setdefault("COOKIE_SECURE", "true")
    if not env.get("PUBLIC_URL"):
        if env.get("RENDER_EXTERNAL_URL"):
            env["PUBLIC_URL"] = env["RENDER_EXTERNAL_URL"].rstrip("/")
        else:
            raise RuntimeError("PUBLIC_URL or RENDER_EXTERNAL_URL must be configured")
    env.setdefault("PORT", "10000")
    env["HOSTNAME"] = "0.0.0.0"
    return env


def main():
    try:
        env = environment()
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1
    migrations = env.copy()
    if env.get("DATABASE_URL_UNPOOLED"):
        migrations["DATABASE_URL"] = env["DATABASE_URL_UNPOOLED"]
    result = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env=migrations)
    if result.returncode:
        return result.returncode
    children = []
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True
        for child in children:
            if child.poll() is None:
                child.terminate()

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, stop)
    try:
        api = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--no-access-log"], cwd=BACKEND, env=env)
        children.append(api)
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline and not stopping:
            if api.poll() is not None:
                return 1
            try:
                with urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=3) as response:
                    if response.status == 200 and json.load(response).get("status") == "ok":
                        break
            except Exception:
                time.sleep(1)
        else:
            print("API readiness timed out", file=sys.stderr)
            return 1
        if stopping:
            return 0
        children.append(subprocess.Popen([sys.executable, "-m", "app.worker"], cwd=BACKEND, env=env))
        children.append(subprocess.Popen(["node", "server.js"], cwd=ROOT / "web", env=env))
        print("HackAMatch frontend, API and scheduler started", flush=True)
        while not stopping:
            if any(child.poll() is not None for child in children):
                print("A required process stopped; restarting the service is necessary", file=sys.stderr)
                return 1
            time.sleep(0.5)
        return 0
    finally:
        stop()
        for child in children:
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == "__main__":
    sys.exit(main())
