from app import app
from database import db
from sqlalchemy import inspect, text

def update_schema():
    with app.app_context():
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('training_log')]

        if 'warmup_notes' not in columns:
            try:
                db.session.execute(text("ALTER TABLE training_log ADD COLUMN warmup_notes TEXT"))
                db.session.commit()
                print("Added warmup_notes column.")
            except Exception as e:
                print(f"warmup_notes column error: {e}")
        else:
            print("warmup_notes column already exists.")

        if 'main_set_details' not in columns:
            try:
                db.session.execute(text("ALTER TABLE training_log ADD COLUMN main_set_details TEXT"))
                db.session.commit()
                print("Added main_set_details column.")
            except Exception as e:
                print(f"main_set_details column error: {e}")
        else:
            print("main_set_details column already exists.")

if __name__ == "__main__":
    update_schema()
