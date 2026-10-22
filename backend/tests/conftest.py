import os, tempfile

test_url = os.getenv("TEST_DATABASE_URL")
if test_url and "test" not in test_url.rsplit("/", 1)[-1]:
    raise RuntimeError(
        "TEST_DATABASE_URL must name an isolated database containing test"
    )
os.environ["DATABASE_URL"] = test_url or "sqlite:///" + tempfile.mktemp(
    prefix="hackamatch-test-", suffix=".db"
)
os.environ["APP_ENV"] = "development"
os.environ["COOKIE_SECURE"] = "false"
import pytest
from fastapi.testclient import TestClient
from app.db import Base, engine, Session, now
from app.main import app
from app.models import *
from app.auth import hash_password, issue


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def organizer(client):
    with Session.begin() as db:
        u = User(
            email="organizer@example.test",
            password=hash_password("Synthetic-pass-938!"),
            verified=True,
            role="organizer",
        )
        db.add(u)
        db.flush()
        raw = issue(db, u, "session", 24)
    client.cookies.set("hm_session", raw)
    return client
