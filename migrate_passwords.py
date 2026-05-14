"""
migrate_passwords.py — Adds password_hash column to existing athletes.
Run this ONCE on your existing sports_science.db to upgrade it.
After running this, you do NOT need to re-seed the database.
"""
from app import app, db
from models import Athlete
from werkzeug.security import generate_password_hash
from sqlalchemy import inspect, text

DEFAULT_HASH = generate_password_hash('athlete123')

def migrate():
    with app.app_context():
        # Step 1: Add the column if it doesn't exist yet (works on SQLite & PostgreSQL)
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('athlete')]

        if 'password_hash' not in columns:
            db.session.execute(text("ALTER TABLE athlete ADD COLUMN password_hash VARCHAR(256)"))
            db.session.commit()
            print("[OK] Added 'password_hash' column to athlete table.")
        else:
            print("[INFO] 'password_hash' column already exists. Skipping ALTER TABLE.")

        # Step 2: Set default hashed password for all athletes that don't have one yet
        athletes = Athlete.query.all()
        updated = 0
        for a in athletes:
            if not a.password_hash:
                a.password_hash = DEFAULT_HASH
                updated += 1

        db.session.commit()
        print(f"[OK] Set hashed password for {updated} athletes.")
        print("[DONE] Migration complete. All athletes can now log in with: athlete123")

if __name__ == '__main__':
    migrate()
