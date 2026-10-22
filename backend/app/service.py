from datetime import timedelta
from sqlalchemy import select, delete
from .db import now
from .models import *
from .matching import allocate, WEIGHTS, score_team


def audit(db, actor, action, target, reason=None, details=None):
    db.add(
        Audit(
            actor=actor,
            action=action,
            target=str(target),
            reason=reason,
            details=details or {},
        )
    )


def eligibility(db, user, policy):
    if not user.verified:
        return {
            "state": "pending_verification",
            "eligible": False,
            "reasons": ["Verify email ownership"],
            "profile": None,
        }
    entries = list(
        db.scalars(
            select(Attendee).where(
                Attendee.email == user.email, Attendee.active == True
            )
        )
    )
    if len(entries) != 1:
        return {
            "state": "not_found" if not entries else "manual_review",
            "eligible": False,
            "reasons": [
                "No active Luma registration"
                if not entries
                else "Duplicate Luma email requires review"
            ],
            "profile": None,
        }
    a = entries[0]
    p = dict(a.normalized)
    override = db.get(Profile, user.id)
    if override and override.availability_override:
        p["availability"] = override.availability_override
    reasons = []
    if a.approval != "approved":
        reasons.append(
            "Registration declined"
            if a.approval == "declined"
            else "Approval requires review"
        )
    if override and override.excluded:
        reasons.append("Excluded by organizer")
    for key in policy.get("required_fields", ["skills", "goals", "schedule"]):
        if not p.get(key) or key == "skills" and p[key] == ["other"]:
            reasons.append("Missing or unresolved " + key)
    if policy.get("require_offline", False) and p["availability"] != "yes":
        reasons.append("Offline availability " + p["availability"])
    return {
        "state": "verified"
        if a.approval == "approved"
        else "declined"
        if a.approval == "declined"
        else "manual_review",
        "eligible": not reasons,
        "reasons": reasons,
        "profile": p,
        "name": a.raw.get("name", "Participant"),
        "attendee_id": a.id,
    }


def window_json(w):
    return {
        "id": w.id,
        "name": w.name,
        "opens": w.opens.isoformat() + "Z",
        "closes": w.closes.isoformat() + "Z",
        "status": (
            "open"
            if w.opens <= now() < w.closes
            else "closing"
            if now() >= w.closes
            else "scheduled"
        )
        if w.status in ["open", "scheduled"]
        else w.status,
        "policy": w.policy,
        "config": w.config,
        "frozen_at": w.frozen_at.isoformat() + "Z" if w.frozen_at else None,
        "published_at": w.published_at.isoformat() + "Z" if w.published_at else None,
        "server_time": now().isoformat() + "Z",
    }


def latest_window(db):
    return db.scalar(
        select(Window).where(Window.status != "cancelled").order_by(Window.id.desc())
    )


def pool_for(db, w, freeze=False):
    pool = []
    regs = list(db.scalars(select(Registration).where(Registration.window_id == w.id)))
    for r in regs:
        e = eligibility(db, db.get(User, r.user_id), w.policy)
        if freeze:
            r.eligibility = {k: v for k, v in e.items() if k not in ["profile", "name"]}
            r.state = "frozen" if e["eligible"] else "ineligible"
        if e["eligible"]:
            pool.append({"id": r.user_id, **e["profile"]})
    return pool


def run_matching(db, window_id, actor=None):
    # Transaction-scoped row lock serializes competing API / worker executions.
    # Work and status commit atomically; a crash rolls back, leaving a retryable job.
    w = db.scalar(select(Window).where(Window.id == window_id).with_for_update())
    if not w:
        raise ValueError("Window not found")
    if w.status in ["review", "published"]:
        return w
    if w.status == "cancelled":
        raise ValueError("Window cancelled")
    if now() < w.closes:
        raise ValueError("Matching starts only after the backend deadline")
    job = db.scalar(select(Job).where(Job.window_id == w.id))
    if not job:
        job = Job(window_id=w.id, key=f"match:{w.id}", status="queued")
        db.add(job)
    job.attempts = (job.attempts or 0) + 1
    job.status = "running"
    job.error = None
    job.updated_at = now()
    snap = db.scalar(select(Snapshot).where(Snapshot.window_id == w.id))
    if snap:
        pool = snap.pool
    else:
        pool = pool_for(db, w, True)
        current = db.scalar(select(Import).where(Import.active == True))
        snap = Snapshot(
            window_id=w.id,
            import_id=current.id if current else None,
            pool=pool,
            policy=w.policy,
            config=w.config,
        )
        db.add(snap)
        w.frozen_at = now()
    w.status = "matching"
    db.flush()
    result = allocate(
        pool, seed=w.config.get("seed", 42), weights=w.config.get("weights", WEIGHTS)
    )
    for number, t in enumerate(result["teams"], 1):
        team = Team(
            window_id=w.id,
            number=number,
            score=t["score"]["total"],
            breakdown=t["score"],
        )
        db.add(team)
        db.flush()
        for uid in t["members"]:
            db.add(Member(team_id=team.id, user_id=uid, window_id=w.id))
            db.scalar(
                select(Registration).where(
                    Registration.window_id == w.id, Registration.user_id == uid
                )
            ).state = "assigned"
    for uid in result["unassigned"]:
        db.scalar(
            select(Registration).where(
                Registration.window_id == w.id, Registration.user_id == uid
            )
        ).state = "waitlisted"
    job.status = "complete"
    w.status = "review"
    audit(
        db,
        actor,
        "matching.completed",
        w.id,
        details={k: v for k, v in result.items() if k not in ["teams", "unassigned"]},
    )
    return w


def team_json(db, t):
    snap = db.scalar(select(Snapshot).where(Snapshot.window_id == t.window_id))
    profiles = {p["id"]: p for p in snap.pool} if snap else {}
    members = []
    for uid in db.scalars(
        select(Member.user_id).where(Member.team_id == t.id).order_by(Member.user_id)
    ):
        u = db.get(User, uid)
        a = db.scalar(
            select(Attendee).where(Attendee.email == u.email, Attendee.active == True)
        )
        p = profiles.get(uid, {})
        # Only relevant teammate fields, no contacts, raw responses, IDs or gender.
        members.append(
            {
                "id": uid,
                "name": a.raw.get("name", "Participant") if a else "Participant",
                "skills": p.get("skills", []),
                "goals": p.get("goals", []),
                "schedule": p.get("schedule", []),
                "hobbies": p.get("hobbies", []),
            }
        )
    return {
        "id": t.id,
        "window_id": t.window_id,
        "number": t.number,
        "name": f"Team {t.number:02}",
        "status": t.status,
        "score": t.score,
        "breakdown": t.breakdown,
        "members": members,
    }


def publish(db, w, actor):
    if w.status == "published":
        return
    if w.status != "review":
        raise ValueError("Run matching and review proposals first")
    teams = list(db.scalars(select(Team).where(Team.window_id == w.id)))
    members = list(db.scalars(select(Member).where(Member.window_id == w.id)))
    for t in teams:
        ms = [m for m in members if m.team_id == t.id]
        if len(ms) != 3 or len({m.user_id for m in ms}) != 3:
            raise ValueError("Each team needs three distinct participants")
        for m in ms:
            if not eligibility(db, db.get(User, m.user_id), w.policy)["eligible"]:
                raise ValueError(
                    "A proposed participant is no longer eligible; review allocation"
                )
        t.status = "published"
    expected = {
        p["id"]
        for p in db.scalar(select(Snapshot).where(Snapshot.window_id == w.id)).pool
    }
    tracked = {
        r.user_id
        for r in db.scalars(
            select(Registration).where(
                Registration.window_id == w.id,
                Registration.state.in_(["assigned", "waitlisted"]),
            )
        )
    }
    if expected != tracked:
        raise ValueError("Every frozen participant must be assigned or waitlisted")
    w.status = "published"
    w.published_at = now()
    audit(db, actor, "teams.published", w.id)
