"""Durable database-driven scheduler, independent of HTTP processes."""

import os, time, smtplib, logging
from email.message import EmailMessage
from datetime import timedelta
from sqlalchemy import select, delete
from .db import Session, now
from .models import Window, Job, Mail, User, Token, RateBucket
from .service import run_matching


def tick():
    with Session.begin() as db:
        windows = list(
            db.scalars(
                select(Window)
                .where(
                    Window.closes <= now(),
                    Window.status.in_(["open", "scheduled", "failed"]),
                )
                .with_for_update(skip_locked=True)
            )
        )
        for w in windows:
            job = db.scalar(select(Job).where(Job.window_id == w.id))
            if (
                job
                and job.status == "failed"
                and (
                    job.attempts >= 5 or job.updated_at > now() - timedelta(seconds=30)
                )
            ):
                continue
            try:
                with db.begin_nested():
                    run_matching(db, w.id)
            except Exception:
                job = db.scalar(select(Job).where(Job.window_id == w.id))
                if job:
                    job.status = "failed"
                    job.attempts += 1
                    job.error = "Matching failed; organizer can retry"
                    job.updated_at = now()
                w.status = "failed"
        db.execute(delete(Token).where(Token.expires < now()))
        db.execute(delete(RateBucket).where(RateBucket.expires < now()))
    if not os.getenv("SMTP_HOST"):
        return
    with Session.begin() as db:
        mails = list(
            db.scalars(
                select(Mail)
                .where(Mail.status == "queued", Mail.attempts < 5)
                .limit(20)
                .with_for_update(skip_locked=True)
            )
        )
        for mail in mails:
            mail.attempts += 1
            try:
                msg = EmailMessage()
                msg["From"] = os.getenv("SMTP_FROM", "hackamatch@localhost")
                msg["To"] = db.get(User, mail.user_id).email
                msg["Subject"] = "Verify your HackAMatch email"
                msg.set_content(mail.body)
                with smtplib.SMTP(
                    os.environ["SMTP_HOST"],
                    int(os.getenv("SMTP_PORT", "587")),
                    timeout=10,
                ) as smtp:
                    if os.getenv("SMTP_TLS", "true") == "true":
                        smtp.starttls()
                    if os.getenv("SMTP_USER"):
                        smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
                    smtp.send_message(msg)
                mail.status = "sent"
                mail.body = "[delivered]"
            except Exception:
                if mail.attempts >= 5:
                    mail.status = "failed"
        db.execute(delete(Mail).where(Mail.created_at < now() - timedelta(days=2)))


def main():
    while True:
        try:
            tick()
        except Exception:
            logging.error(
                "Scheduler iteration failed; retrying without logging private parameters"
            )
        time.sleep(2)


if __name__ == "__main__":
    main()
