import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


URL = os.getenv("DATABASE_URL", "sqlite:///./hackamatch.db")
# Hosting providers usually return a standard PostgreSQL URL; retain psycopg 3.
if URL.startswith("postgresql://"):
    URL = URL.replace("postgresql://", "postgresql+psycopg://", 1)
elif URL.startswith("postgres://"):
    URL = URL.replace("postgres://", "postgresql+psycopg://", 1)
engine = create_engine(
    URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False, "timeout": 30}
    if URL.startswith("sqlite")
    else {},
)
if URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def sqlite_config(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")


Session = sessionmaker(engine, expire_on_commit=False)
