import argparse, getpass
from sqlalchemy import select, delete
from .db import Session
from .models import *
from .auth import hash_password
from .service import audit
from .importer import import_data


def main():
    p = argparse.ArgumentParser(description="HackAMatch trusted operator commands")
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("organizer")
    s.add_argument("email")
    s = sub.add_parser("import")
    s.add_argument("path")
    s = sub.add_parser("purge-event")
    s.add_argument("--confirm", required=True)
    args = p.parse_args()
    with Session.begin() as db:
        if args.command == "organizer":
            from .importer import email

            em = email(args.email)
            u = db.scalar(select(User).where(User.email == em))
            if not u:
                password = getpass.getpass("New organizer password (10+ characters): ")
                if len(password) < 10:
                    raise SystemExit("Password too short")
                u = User(email=em, password=hash_password(password))
                db.add(u)
                db.flush()
                db.add(Profile(user_id=u.id))
            u.role = "organizer"
            u.verified = True
            audit(
                db,
                u.id,
                "organizer.bootstrapped",
                u.id,
                "Trusted host operator command",
            )
            print("Organizer ready. Log in with this account.")
        elif args.command == "import":
            with open(args.path, "rb") as f:
                result = import_data(db, f.read(), args.path, None)
            audit(
                db,
                None,
                "luma.imported",
                result["id"],
                details={"accepted": result["accepted"]},
            )
            print(
                {
                    k: result[k]
                    for k in [
                        "id",
                        "accepted",
                        "approved",
                        "declined",
                        "unknown_availability",
                    ]
                }
            )
        elif args.command == "purge-event":
            if args.confirm != "DELETE EVENT DATA":
                raise SystemExit("Confirmation must be DELETE EVENT DATA")
            for table in [
                Member,
                Team,
                Snapshot,
                Registration,
                Job,
                Window,
                Attendee,
                ImportRecord,
                Import,
                Mail,
            ]:
                db.execute(delete(table))
            audit(db, None, "event.purged", "event", "Retention period ended")
            print("Event data removed. Accounts retained.")


if __name__ == "__main__":
    main()
