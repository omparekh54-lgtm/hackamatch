import os, io, csv, zipfile
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Request,
    Response,
    UploadFile,
    File,
    Query,
)
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func, delete
from sqlalchemy.exc import IntegrityError
from openpyxl import Workbook
from .db import now
from .models import *
from .auth import *
from .importer import import_data, FIELDS, MAPPINGS, normalize
from .service import *
from .matching import WEIGHTS, allocate

app = FastAPI(title="HackAMatch API", version="1.0.0")


@app.middleware("http")
async def guard(request, call_next):
    if request.method not in ["GET", "HEAD", "OPTIONS"]:
        # UI uses same-origin Next proxy. Origin protects cookie-auth writes.
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") != os.getenv(
            "PUBLIC_URL", "http://localhost:3000"
        ).rstrip("/"):
            return JSONResponse({"detail": "Origin rejected"}, status_code=403)
        length = request.headers.get("content-length")
        if length and (not length.isdigit() or int(length) > 6 * 1024 * 1024):
            return JSONResponse({"detail": "Upload too large"}, status_code=413)
    try:
        response = await call_next(request)
    except Exception:
        # Do not leak SQL parameters, questionnaire rows or session tokens.
        return JSONResponse(
            {"detail": "Operation failed safely; retry or contact the organizer"},
            status_code=500,
        )
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(ValueError)
async def bad_value(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=400)


@app.exception_handler(IntegrityError)
async def conflict(request, exc):
    return JSONResponse(
        {"detail": "Concurrent change or duplicate record. Refresh and retry."},
        status_code=409,
    )


class Credentials(BaseModel):
    email: str
    password: str = Field(min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def em(cls, v):
        return email(v)


class Verify(BaseModel):
    token: str = Field(min_length=30, max_length=100)


class EmailInput(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def em(cls, v):
        return email(v)


class Reason(BaseModel):
    reason: str = Field(min_length=5, max_length=500)


class Policy(BaseModel):
    require_offline: bool = False
    required_fields: list[str] = Field(
        default_factory=lambda: ["skills", "goals", "schedule"]
    )

    @field_validator("required_fields")
    @classmethod
    def required(cls, v):
        if not set(v) <= set(FIELDS):
            raise ValueError("Unknown questionnaire field")
        return v


class Config(BaseModel):
    seed: int = Field(default=42, ge=0, le=2147483647)
    weights: dict[str, float] = Field(default_factory=lambda: dict(WEIGHTS))

    @field_validator("weights")
    @classmethod
    def weights_valid(cls, v):
        if (
            set(v) != set(WEIGHTS)
            or any(not 0 <= n <= 100 for n in v.values())
            or abs(sum(v.values()) - 100) > 0.01
        ):
            raise ValueError("Seven scoring weights must be nonnegative and total 100")
        return v


class WindowInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    opens: datetime | None = None
    duration_seconds: int = Field(default=7200, ge=10, le=86400)
    policy: Policy = Field(default_factory=Policy)
    config: Config = Field(default_factory=Config)


class WindowUpdate(Reason):
    policy: Policy
    config: Config


class ParticipantUpdate(Reason):
    excluded: bool | None = None
    availability: str | None = None

    @field_validator("availability")
    @classmethod
    def available(cls, v):
        if v not in [None, "yes", "no", "unknown"]:
            raise ValueError("Availability must be yes, no or unknown")
        return v


class Reassign(Reason):
    outgoing_user_id: int
    incoming_user_id: int


class MappingInput(Reason):
    mappings: dict[str, list[str]]


def locked_window(db, wid):
    w = db.scalar(select(Window).where(Window.id == wid).with_for_update())
    if not w:
        raise HTTPException(404, "Window not found")
    return w


def page(query, db, offset, limit):
    return list(db.scalars(query.offset(offset).limit(limit)))


def imports_json(i):
    return {
        "id": i.id,
        "filename": i.filename,
        "active": i.active,
        "created_at": i.created_at.isoformat() + "Z",
        **i.summary,
    }


def safe_csv(v):
    s = str(v or "")
    return "'" + s if s.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else s


@app.get("/api/health")
def health(db=Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok"}


@app.get("/api/public/status")
def public_status(db=Depends(get_db)):
    w = latest_window(db)
    return {
        "event": "HackAMatch",
        "hosts": "Data Mavericks × NSDC",
        "team_size": 3,
        "email_enabled": bool(os.getenv("SMTP_HOST")),
        "window": window_json(w) if w else None,
    }


@app.post("/api/auth/signup")
def signup(body: Credentials, request: Request, db=Depends(get_db)):
    rate_limit(db, "signup:" + str(request.client.host), 1000)
    rate_limit(db, "signup-email:" + body.email, 3)
    if not db.scalar(select(User).where(User.email == body.email)):
        u = User(email=body.email, password=hash_password(body.password))
        db.add(u)
        db.flush()
        db.add(Profile(user_id=u.id))
        queue_verification(db, u)
    return {
        "message": "If this address can register, a verification email will be queued.",
        "email_enabled": bool(os.getenv("SMTP_HOST")),
    }


@app.post("/api/auth/resend")
def resend(body: EmailInput, request: Request, db=Depends(get_db)):
    rate_limit(db, "resend:" + body.email, 3)
    u = db.scalar(select(User).where(User.email == body.email))
    if u and not u.verified:
        queue_verification(db, u)
    return {
        "message": "If needed, a verification email has been queued.",
        "email_enabled": bool(os.getenv("SMTP_HOST")),
    }


@app.post("/api/auth/verify")
def verify(body: Verify, request: Request, db=Depends(get_db)):
    rate_limit(db, "verify:" + str(request.client.host), 1000)
    tok = db.scalar(
        select(Token).where(Token.digest == digest(body.token)).with_for_update()
    )
    if not tok or tok.kind != "verify" or tok.expires < now():
        raise HTTPException(400, "Verification link is invalid or expired")
    u = db.get(User, tok.user_id)
    u.verified = True
    db.execute(delete(Token).where(Token.user_id == u.id, Token.kind == "verify"))
    audit(db, u.id, "email.verified", u.id)
    return {"message": "Email verified. You can now log in."}


@app.post("/api/auth/login")
def login(body: Credentials, request: Request, response: Response, db=Depends(get_db)):
    rate_limit(db, "login-ip:" + str(request.client.host), 3000)
    rate_limit(db, "login:" + body.email, 10)
    u = db.scalar(select(User).where(User.email == body.email))
    dummy = "invalid-salt:" + ("0" * 64)
    ok = check_password(body.password, u.password if u else dummy)
    if not u or not ok:
        raise HTTPException(401, "Email or password is incorrect")
    raw = issue(db, u, "session", 24)
    response.set_cookie(
        "hm_session",
        raw,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "true") == "true",
        samesite="lax",
        max_age=86400,
        path="/",
    )
    return {"id": u.id, "email": u.email, "verified": u.verified, "role": u.role}


@app.get("/api/auth/me")
def me(user=Depends(current)):
    return {
        "id": user.id,
        "email": user.email,
        "verified": user.verified,
        "role": user.role,
    }


@app.post("/api/auth/logout")
def logout(
    request: Request, response: Response, user=Depends(current), db=Depends(get_db)
):
    db.execute(
        delete(Token).where(
            Token.digest == digest(request.cookies.get("hm_session", ""))
        )
    )
    response.delete_cookie("hm_session", path="/")
    return {"ok": True}


@app.get("/api/participant/profile")
def profile(user=Depends(current), db=Depends(get_db)):
    w = latest_window(db)
    e = eligibility(db, user, w.policy if w else Policy().model_dump())
    raw = None
    if user.verified and e.get("attendee_id"):
        a = db.get(Attendee, e["attendee_id"])
        raw = {k: a.raw.get(col, "") for k, col in FIELDS.items()}
    return {**e, "responses": raw, "email_verified": user.verified}


@app.get("/api/participant/matching-window")
def participant_window(user=Depends(current), db=Depends(get_db)):
    w = latest_window(db)
    return window_json(w) if w else None


@app.get("/api/participant/registration")
def registration(user=Depends(current), db=Depends(get_db)):
    w = latest_window(db)
    r = (
        db.scalar(
            select(Registration).where(
                Registration.user_id == user.id, Registration.window_id == w.id
            )
        )
        if w
        else None
    )
    return {
        "window": window_json(w) if w else None,
        "joined": bool(r),
        "state": r.state if r else "not_joined",
    }


@app.post("/api/participant/join")
def join(user=Depends(current), db=Depends(get_db)):
    w = latest_window(db)
    if not w:
        raise HTTPException(400, "No matching window has been opened")
    w = locked_window(db, w.id)
    if w.status not in ["open", "scheduled"] or not w.opens <= now() < w.closes:
        raise HTTPException(409, "This registration window is closed")
    e = eligibility(db, user, w.policy)
    if not e["eligible"]:
        raise HTTPException(403, "; ".join(e["reasons"]))
    r = db.scalar(
        select(Registration).where(
            Registration.user_id == user.id, Registration.window_id == w.id
        )
    )
    if not r:
        db.add(
            Registration(
                user_id=user.id,
                window_id=w.id,
                eligibility={
                    k: v for k, v in e.items() if k not in ["name", "profile"]
                },
            )
        )
        audit(db, user.id, "pool.joined", w.id)
    return {"joined": True, "window_id": w.id}


@app.get("/api/participant/team")
def participant_team(user=Depends(current), db=Depends(get_db)):
    w = latest_window(db)
    if not w or w.status != "published":
        return {"status": "unpublished", "team": None}
    member = db.scalar(
        select(Member).where(Member.user_id == user.id, Member.window_id == w.id)
    )
    r = db.scalar(
        select(Registration).where(
            Registration.user_id == user.id, Registration.window_id == w.id
        )
    )
    return {
        "status": "assigned" if member else (r.state if r else "not_joined"),
        "team": team_json(db, db.get(Team, member.team_id)) if member else None,
    }


@app.get("/api/admin/overview")
def overview(user=Depends(admin), db=Depends(get_db)):
    w = latest_window(db)
    attendees = list(db.scalars(select(Attendee).where(Attendee.active == True)))
    users = list(db.scalars(select(User)))
    prof = [a.normalized for a in attendees]
    job = db.scalar(select(Job).where(Job.window_id == w.id)) if w else None
    return {
        "total": len(attendees),
        "approved": sum(a.approval == "approved" for a in attendees),
        "declined": sum(a.approval == "declined" for a in attendees),
        "verified": sum(u.verified for u in users),
        "eligible": sum(
            eligibility(db, u, w.policy if w else Policy().model_dump())["eligible"]
            for u in users
        ),
        "completeness": round(sum(p["completeness"] for p in prof) / len(prof), 1)
        if prof
        else 0,
        "unknown_availability": sum(p["availability"] == "unknown" for p in prof),
        "window": window_json(w) if w else None,
        "proposed_teams": db.scalar(
            select(func.count()).select_from(Team).where(Team.status == "proposed")
        ),
        "published_teams": db.scalar(
            select(func.count()).select_from(Team).where(Team.status == "published")
        ),
        "waitlisted": db.scalar(
            select(func.count())
            .select_from(Registration)
            .where(Registration.state == "waitlisted")
        ),
        "job": {"status": job.status, "attempts": job.attempts, "error": job.error}
        if job
        else None,
        "email_enabled": bool(os.getenv("SMTP_HOST")),
    }


@app.post("/api/admin/luma/import")
async def upload(
    file: UploadFile = File(...),
    preview: bool = False,
    user=Depends(admin),
    db=Depends(get_db),
):
    data = await file.read(5 * 1024 * 1024 + 1)
    result = import_data(db, data, file.filename or "", user.id, preview)
    if not preview:
        audit(
            db,
            user.id,
            "luma.imported",
            result["id"],
            details={
                "accepted": result["accepted"],
                "duplicate": result["duplicate_import"],
            },
        )
    return result


@app.get("/api/admin/luma/imports")
def imports(
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    user=Depends(admin),
    db=Depends(get_db),
):
    return [
        imports_json(i)
        for i in page(select(Import).order_by(Import.id.desc()), db, offset, limit)
    ]


@app.get("/api/admin/luma/imports/{iid}")
def one_import(iid: int, user=Depends(admin), db=Depends(get_db)):
    i = db.get(Import, iid)
    if not i:
        raise HTTPException(404, "Import not found")
    return imports_json(i)


@app.post("/api/admin/luma/verify")
def luma_verify(body: EmailInput, user=Depends(admin), db=Depends(get_db)):
    u = db.scalar(select(User).where(User.email == body.email))
    w = latest_window(db)
    if not u:
        return {"state": "not_found", "eligible": False, "reasons": ["No account yet"]}
    return eligibility(db, u, w.policy if w else Policy().model_dump())


@app.get("/api/admin/skill-mappings")
def mappings(user=Depends(admin), db=Depends(get_db)):
    s = db.get(Setting, "skill_mappings")
    return s.value if s else MAPPINGS


@app.put("/api/admin/skill-mappings")
def update_mappings(body: MappingInput, user=Depends(admin), db=Depends(get_db)):
    if set(body.mappings) != set(MAPPINGS) or any(
        not v or len(v) > 30 or any(not x.strip() or len(x) > 80 for x in v)
        for v in body.mappings.values()
    ):
        raise ValueError(
            "Supply the existing categories and 1–30 nonempty keywords each"
        )
    s = db.get(Setting, "skill_mappings")
    if not s:
        s = Setting(key="skill_mappings", value=body.mappings)
        db.add(s)
    else:
        s.value = body.mappings
    for a in db.scalars(select(Attendee)):
        a.normalized = normalize(a.raw, body.mappings)
    audit(db, user.id, "mappings.updated", "skills", body.reason)
    return {"ok": True}


@app.get("/api/admin/participants")
def participants(
    q: str = "",
    status: str = "",
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    user=Depends(admin),
    db=Depends(get_db),
):
    # Search is organizer-only, including records with no account yet.
    query = select(Attendee).where(Attendee.active == True)
    if q:
        query = query.where(Attendee.email.ilike("%" + q[:100] + "%"))
    if status:
        query = query.where(Attendee.approval == status)
    result = []
    w = latest_window(db)
    for a in page(query.order_by(Attendee.id), db, offset, limit):
        u = db.scalar(select(User).where(User.email == a.email))
        e = (
            eligibility(db, u, w.policy if w else Policy().model_dump())
            if u
            else {
                "state": "no_account",
                "eligible": False,
                "reasons": ["Participant has not signed up"],
            }
        )
        result.append(
            {
                "id": a.id,
                "user_id": u.id if u else None,
                "name": a.raw.get("name"),
                "email": a.email,
                "approval": a.approval,
                "profile": a.normalized,
                "eligibility": e,
                "responses": {k: a.raw.get(col, "") for k, col in FIELDS.items()},
            }
        )
    return result


@app.patch("/api/admin/participants/{uid}")
def change_participant(
    uid: int, body: ParticipantUpdate, user=Depends(admin), db=Depends(get_db)
):
    if not db.get(User, uid):
        raise HTTPException(404, "Account not found")
    p = db.get(Profile, uid)
    if not p:
        p = Profile(user_id=uid)
        db.add(p)
    if body.excluded is not None:
        p.excluded = body.excluded
    if body.availability is not None:
        p.availability_override = body.availability
    p.updated_at = now()
    audit(
        db,
        user.id,
        "participant.updated",
        uid,
        body.reason,
        {"excluded": body.excluded, "availability": body.availability},
    )
    return {"ok": True}


@app.post("/api/admin/matching-windows")
def create_window(body: WindowInput, user=Depends(admin), db=Depends(get_db)):
    # Serialize window creation across organizers, even when no window exists.
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    if db.scalar(
        select(Window).where(Window.status.not_in(["published", "cancelled"]))
    ):
        raise ValueError("Finish or cancel the current window first")
    if (
        os.getenv("APP_ENV", "production") == "production"
        and body.duration_seconds != 7200
    ):
        raise ValueError("Production windows last two hours")
    opens = (
        body.opens.astimezone(timezone.utc).replace(tzinfo=None)
        if body.opens and body.opens.tzinfo
        else body.opens or now()
    )
    w = Window(
        name=body.name,
        opens=opens,
        closes=opens + timedelta(seconds=body.duration_seconds),
        policy=body.policy.model_dump(),
        config=body.config.model_dump(),
        status="open" if opens <= now() else "scheduled",
    )
    db.add(w)
    db.flush()
    db.add(Job(window_id=w.id, key=f"match:{w.id}"))
    audit(db, user.id, "window.created", w.id)
    return window_json(w)


@app.get("/api/admin/matching-windows")
def windows(
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    user=Depends(admin),
    db=Depends(get_db),
):
    return [
        window_json(w)
        for w in page(select(Window).order_by(Window.id.desc()), db, offset, limit)
    ]


@app.get("/api/admin/matching-windows/{wid}")
def one_window(wid: int, user=Depends(admin), db=Depends(get_db)):
    return window_json(locked_window(db, wid))


@app.patch("/api/admin/matching-windows/{wid}")
def configure(wid: int, body: WindowUpdate, user=Depends(admin), db=Depends(get_db)):
    w = locked_window(db, wid)
    if w.status not in ["scheduled", "open"] or w.closes <= now():
        raise ValueError("Configuration freezes at the deadline")
    w.policy = body.policy.model_dump()
    w.config = body.config.model_dump()
    audit(db, user.id, "window.configured", wid, body.reason)
    return window_json(w)


@app.post("/api/admin/matching-windows/{wid}/preview")
def preview(wid: int, user=Depends(admin), db=Depends(get_db)):
    w = locked_window(db, wid)
    pool = pool_for(db, w)
    return {
        "eligible": len(pool),
        "result": allocate(pool, w.config["seed"], w.config["weights"]),
    }


@app.post("/api/admin/matching-windows/{wid}/start")
def start(wid: int, user=Depends(admin), db=Depends(get_db)):
    w = run_matching(db, wid, user.id)
    return window_json(w)


@app.post("/api/admin/matching-windows/{wid}/publish")
def publish_window(wid: int, user=Depends(admin), db=Depends(get_db)):
    w = locked_window(db, wid)
    publish(db, w, user.id)
    return window_json(w)


@app.post("/api/admin/matching-windows/{wid}/regenerate")
def regenerate(wid: int, body: Reason, user=Depends(admin), db=Depends(get_db)):
    w = locked_window(db, wid)
    if w.status != "review":
        raise ValueError("Only unpublished proposals may be regenerated")
    db.execute(delete(Member).where(Member.window_id == wid))
    db.execute(delete(Team).where(Team.window_id == wid))
    # Frozen pool is preserved; a new seed explores another valid proposal.
    w.config = {**w.config, "seed": w.config["seed"] + 1}
    w.status = "failed"
    for r in db.scalars(
        select(Registration).where(
            Registration.window_id == wid,
            Registration.state.in_(["assigned", "waitlisted"]),
        )
    ):
        r.state = "frozen"
    snap = db.scalar(select(Snapshot).where(Snapshot.window_id == wid))
    snap.config = w.config
    audit(db, user.id, "teams.regenerated", wid, body.reason)
    return window_json(run_matching(db, wid, user.id))


@app.post("/api/admin/matching-windows/{wid}/reopen")
def reopen(wid: int, body: Reason, user=Depends(admin), db=Depends(get_db)):
    w = locked_window(db, wid)
    if w.status not in ["review", "failed"]:
        raise ValueError("Only review or failed windows can reopen")
    db.execute(delete(Member).where(Member.window_id == wid))
    db.execute(delete(Team).where(Team.window_id == wid))
    db.execute(delete(Snapshot).where(Snapshot.window_id == wid))
    for r in db.scalars(select(Registration).where(Registration.window_id == wid)):
        r.state = "joined"
    w.frozen_at = None
    w.opens = now()
    w.closes = now() + timedelta(hours=2)
    w.status = "open"
    j = db.scalar(select(Job).where(Job.window_id == wid))
    j.status = "queued"
    audit(db, user.id, "window.reopened", wid, body.reason)
    return window_json(w)


@app.post("/api/admin/matching-windows/{wid}/cancel")
def cancel(wid: int, body: Reason, user=Depends(admin), db=Depends(get_db)):
    w = locked_window(db, wid)
    if w.status == "published":
        raise ValueError("Published windows cannot be cancelled")
    w.status = "cancelled"
    audit(db, user.id, "window.cancelled", wid, body.reason)
    return window_json(w)


@app.get("/api/admin/teams")
def teams(
    window_id: int | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    user=Depends(admin),
    db=Depends(get_db),
):
    w = db.get(Window, window_id) if window_id else latest_window(db)
    return (
        [
            team_json(db, t)
            for t in page(
                select(Team).where(Team.window_id == w.id).order_by(Team.number),
                db,
                offset,
                limit,
            )
        ]
        if w
        else []
    )


@app.get("/api/admin/unassigned")
def unassigned(
    window_id: int | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    user=Depends(admin),
    db=Depends(get_db),
):
    w = db.get(Window, window_id) if window_id else latest_window(db)
    if not w:
        return []
    return [
        {"user_id": r.user_id, "state": r.state, "eligibility": r.eligibility}
        for r in page(
            select(Registration)
            .where(
                Registration.window_id == w.id, Registration.state.not_in(["assigned"])
            )
            .order_by(Registration.id),
            db,
            offset,
            limit,
        )
    ]


@app.post("/api/admin/teams/{tid}/reassign")
def reassign(tid: int, body: Reassign, user=Depends(admin), db=Depends(get_db)):
    t = db.get(Team, tid)
    if not t:
        raise HTTPException(404, "Team not found")
    w = locked_window(db, t.window_id)
    if w.status != "review":
        raise ValueError("Reassignment is available before publication")
    snap = db.scalar(select(Snapshot).where(Snapshot.window_id == w.id))
    pool = {p["id"]: p for p in snap.pool}
    if (
        body.incoming_user_id not in pool
        or body.outgoing_user_id not in pool
        or body.incoming_user_id == body.outgoing_user_id
    ):
        raise ValueError("Both people must be distinct members of the frozen pool")
    incoming = db.get(User, body.incoming_user_id)
    if not eligibility(db, incoming, w.policy)["eligible"]:
        raise ValueError("Incoming participant is not eligible")
    outgoing = db.scalar(
        select(Member).where(
            Member.team_id == tid, Member.user_id == body.outgoing_user_id
        )
    )
    if not outgoing:
        raise ValueError("Outgoing participant is not in this team")
    other = db.scalar(
        select(Member).where(
            Member.window_id == w.id, Member.user_id == body.incoming_user_id
        )
    )
    other_tid = other.team_id if other else None
    db.delete(outgoing)
    if other:
        db.delete(other)
    db.flush()
    db.add(Member(team_id=tid, window_id=w.id, user_id=body.incoming_user_id))
    if other_tid:
        db.add(Member(team_id=other_tid, window_id=w.id, user_id=body.outgoing_user_id))
    for uid, state in [
        (body.incoming_user_id, "assigned"),
        (body.outgoing_user_id, "assigned" if other_tid else "waitlisted"),
    ]:
        db.scalar(
            select(Registration).where(
                Registration.window_id == w.id, Registration.user_id == uid
            )
        ).state = state
    db.flush()
    for team_id in {tid, other_tid} - {None}:
        team = db.get(Team, team_id)
        ps = [
            pool[m]
            for m in db.scalars(select(Member.user_id).where(Member.team_id == team_id))
        ]
        known_experience = [
            p["experience"] for p in snap.pool if p.get("experience") is not None
        ]
        pool_mean = (
            sum(known_experience) / len(known_experience) if known_experience else 1
        )
        breakdown = score_team(ps, w.config["weights"], pool_mean)
        team.score = breakdown["total"]
        team.breakdown = breakdown
    audit(
        db,
        user.id,
        "team.reassigned",
        tid,
        body.reason,
        {"outgoing": body.outgoing_user_id, "incoming": body.incoming_user_id},
    )
    return {"ok": True}


@app.get("/api/admin/audit")
def logs(
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    user=Depends(admin),
    db=Depends(get_db),
):
    return [
        {
            "id": a.id,
            "actor": a.actor,
            "action": a.action,
            "target": a.target,
            "reason": a.reason,
            "details": a.details,
            "created_at": a.created_at.isoformat() + "Z",
        }
        for a in page(select(Audit).order_by(Audit.id.desc()), db, offset, limit)
    ]


@app.get("/api/admin/export")
def export(
    format: str = "csv",
    window_id: int | None = None,
    user=Depends(admin),
    db=Depends(get_db),
):
    w = db.get(Window, window_id) if window_id else latest_window(db)
    if not w or w.status != "published":
        raise ValueError("Publish teams before exporting")
    rows = [["team", "participant", "skills", "status"]]
    for t in db.scalars(
        select(Team).where(Team.window_id == w.id).order_by(Team.number)
    ):
        for m in team_json(db, t)["members"]:
            rows.append([t.number, m["name"], ", ".join(m["skills"]), "assigned"])
    for r in db.scalars(
        select(Registration).where(
            Registration.window_id == w.id, Registration.state == "waitlisted"
        )
    ):
        e = eligibility(db, db.get(User, r.user_id), w.policy)
        rows.append(["", e.get("name", "Participant"), "", "waitlisted"])
    rows = [[safe_csv(v) for v in r] for r in rows]
    audit(db, user.id, "teams.exported", w.id, details={"format": format})
    if format == "xlsx":
        book = Workbook()
        ws = book.active
        ws.title = "HackAMatch teams"
        for row in rows:
            ws.append(row)
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for col, width in [("A", 12), ("B", 32), ("C", 60), ("D", 18)]:
            ws.column_dimensions[col].width = width
        buf = io.BytesIO()
        book.save(buf)
        content = buf.getvalue()
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif format == "csv":
        buf = io.StringIO()
        csv.writer(buf).writerows(rows)
        content = buf.getvalue().encode("utf-8-sig")
        mime = "text/csv"
    else:
        raise ValueError("Export format must be csv or xlsx")
    return Response(
        content,
        media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="hackamatch-teams.{format}"'
        },
    )
