"""
migrate_to_postgres.py — One-time data transfer from SQLite → PostgreSQL.

Usage:
  1. Set DATABASE_URL in .env to your PostgreSQL connection string
  2. Run:  python migrate_to_postgres.py
  3. The script reads from the local sports_science.db and bulk-inserts
     all records into the PostgreSQL database.

This is safe to re-run — it will skip if the PostgreSQL database already
contains data (to prevent duplicates).
"""
import os
import sqlite3
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get('DATABASE_URL', '')

def main():
    if not DB_URL.startswith('postgresql'):
        print("[ERROR] DATABASE_URL in .env is not a PostgreSQL connection string.")
        print("        Set it to something like: postgresql://user:pass@localhost:5432/jru_athletics")
        print("        Then re-run this script.")
        return

    # ── Step 1: Read all data from local SQLite ───────────────────────────────
    sqlite_path = os.path.join(os.path.dirname(__file__), 'sports_science.db')
    if not os.path.exists(sqlite_path):
        print(f"[ERROR] SQLite file not found: {sqlite_path}")
        return

    print(f"[INFO] Reading data from {sqlite_path}...")
    src = sqlite3.connect(sqlite_path)
    src.row_factory = sqlite3.Row

    athletes     = [dict(r) for r in src.execute("SELECT * FROM athlete").fetchall()]
    training     = [dict(r) for r in src.execute("SELECT * FROM training_log").fetchall()]
    performances = [dict(r) for r in src.execute("SELECT * FROM performance_result").fetchall()]
    recovery     = [dict(r) for r in src.execute("SELECT * FROM recovery_metric").fetchall()]
    src.close()

    print(f"    Athletes:     {len(athletes)}")
    print(f"    Training:     {len(training)}")
    print(f"    Performance:  {len(performances)}")
    print(f"    Recovery:     {len(recovery)}")

    # ── Step 2: Connect to PostgreSQL via the Flask app ───────────────────────
    from app import app, db
    from models import Athlete, TrainingLog, PerformanceResult, RecoveryMetric

    with app.app_context():
        # Safety check: skip if data already exists
        existing = Athlete.query.count()
        if existing > 0:
            print(f"[WARN] PostgreSQL already contains {existing} athletes. Aborting to prevent duplicates.")
            print("       To force, drop all tables first: db.drop_all() then db.create_all().")
            return

        # Create tables
        db.create_all()
        print("[OK] PostgreSQL schema created.")

        # ── Step 3: Insert athletes ───────────────────────────────────────────
        id_map = {}  # old_id → new_id (in case PostgreSQL assigns different IDs)
        for row in athletes:
            a = Athlete(
                name=row['name'],
                category=row.get('category', 'Sprinter'),
                event=row['event'],
                age=row.get('age'),
                height=row.get('height'),
                weight=row.get('weight'),
                password_hash=row.get('password_hash'),
            )
            db.session.add(a)
            db.session.flush()
            id_map[row['id']] = a.id

        print(f"[OK] Inserted {len(athletes)} athletes.")

        # ── Step 4: Insert training logs ──────────────────────────────────────
        for row in training:
            new_athlete_id = id_map.get(row['athlete_id'])
            if not new_athlete_id:
                continue
            log = TrainingLog(
                athlete_id=new_athlete_id,
                date=_parse_date(row['date']),
                training_type=row.get('training_type'),
                training_phase=row.get('training_phase'),
                distance=row.get('distance'),
                tonnage=row.get('tonnage'),
                duration=row.get('duration'),
                intensity=row.get('intensity'),
                fatigue_post_workout=row.get('fatigue_post_workout'),
                warmup_notes=row.get('warmup_notes'),
                main_set_details=row.get('main_set_details'),
                event_trained=row.get('event_trained'),
                created_at=_parse_datetime(row.get('created_at')),
            )
            db.session.add(log)

        print(f"[OK] Inserted {len(training)} training logs.")

        # ── Step 5: Insert performance results ────────────────────────────────
        for row in performances:
            new_athlete_id = id_map.get(row['athlete_id'])
            if not new_athlete_id:
                continue
            perf = PerformanceResult(
                athlete_id=new_athlete_id,
                date=_parse_date(row['date']),
                event=row['event'],
                time_seconds=row.get('time_seconds'),
                distance_meters=row.get('distance_meters'),
                rank=row.get('rank'),
                competition_name=row.get('competition_name'),
                created_at=_parse_datetime(row.get('created_at')),
            )
            db.session.add(perf)

        print(f"[OK] Inserted {len(performances)} performance results.")

        # ── Step 6: Insert recovery metrics ───────────────────────────────────
        for row in recovery:
            new_athlete_id = id_map.get(row['athlete_id'])
            if not new_athlete_id:
                continue
            rec = RecoveryMetric(
                athlete_id=new_athlete_id,
                date=_parse_date(row['date']),
                sleep_hours=row.get('sleep_hours'),
                sleep_quality=row.get('sleep_quality'),
                morning_fatigue=row.get('morning_fatigue'),
                soreness=row.get('soreness'),
                stress_level=row.get('stress_level'),
                motivation=row.get('motivation'),
                created_at=_parse_datetime(row.get('created_at')),
            )
            db.session.add(rec)

        print(f"[OK] Inserted {len(recovery)} recovery metrics.")

        db.session.commit()
        print("\n[DONE] All data migrated to PostgreSQL successfully!")


def _parse_date(val):
    """Parse a date string from SQLite into a Python date object."""
    if val is None:
        return date.today()
    if isinstance(val, date):
        return val
    try:
        return datetime.strptime(str(val)[:10], '%Y-%m-%d').date()
    except Exception:
        return date.today()


def _parse_datetime(val):
    """Parse a datetime string from SQLite into a Python datetime object."""
    if val is None:
        return datetime.utcnow()
    if isinstance(val, datetime):
        return val
    try:
        return datetime.strptime(str(val)[:19], '%Y-%m-%d %H:%M:%S')
    except Exception:
        return datetime.utcnow()


if __name__ == '__main__':
    main()
