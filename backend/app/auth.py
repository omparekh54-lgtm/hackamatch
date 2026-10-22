import hashlib, hmac, secrets, os
from datetime import timedelta
from sqlalchemy import select, delete
from fastapi import HTTPException, Request, Depends
from .db import Session, now
from .models import User, Token, RateBucket, Mail
from .importer import email


def hash_password(password):
    salt = secrets.token_hex(16)
    return (
        salt
        + ":"
        + hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600000).hex()
    )


def check_password(password, hashed):
    salt, digest = hashed.split(":")
    return hmac.compare_digest(
        hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600000).hex(),
        digest,
    )


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def issue(db, user, kind, hours):
    raw = secrets.token_urlsafe(32)
    db.add(
        Token(
            digest=digest(raw),
            user_id=user.id,
            kind=kind,
            expires=now() + timedelta(hours=hours),
        )
    )
    return raw


def get_db():
    with Session() as db:
        try:
            yield db
            db.commit()
        except:
            db.rollback()
            raise


def current(request: Request, db=Depends(get_db)):
    raw = request.cookies.get("hm_session", "")
    token = db.get(Token, digest(raw))
    if not token or token.kind != "session" or token.expires < now():
        raise HTTPException(401, "Please log in")
    user = db.get(User, token.user_id)
    if not user:
        raise HTTPException(401, "Please log in")
    return user


def admin(user=Depends(current)):
    if user.role != "organizer" or not user.verified:
        raise HTTPException(403, "Organizer access required")
    return user


def rate_limit(db, key, limit=12):
    # Persist fixed-window counters with atomic SQL upsert. Hash identifiers/IPs.
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sq_insert

    key = digest(key)
    n = now()
    expires = n + timedelta(minutes=15)
    insert = pg_insert if db.bind.dialect.name == "postgresql" else sq_insert
    stmt = insert(RateBucket).values(key=key, count=1, expires=expires)
    from sqlalchemy import case

    stmt = stmt.on_conflict_do_update(
        index_elements=["key"],
        set_={
            "count": case((RateBucket.expires < n, 1), else_=RateBucket.count + 1),
            "expires": case(
                (RateBucket.expires < n, expires), else_=RateBucket.expires
            ),
        },
    ).returning(RateBucket.count)
    count = db.scalar(stmt)
    # Commit counters even for rejected auth requests.
    db.commit()
    if count > limit:
        raise HTTPException(429, "Too many attempts. Try again in 15 minutes.")


def queue_verification(db, user):
    raw = issue(db, user, "verify", 24)
    url = os.getenv("PUBLIC_URL", "http://localhost:3000") + "/login?verify=" + raw
    db.add(
        Mail(
            user_id=user.id,
            body="Verify your HackAMatch email (valid for 24 hours):\n" + url,
        )
    )
