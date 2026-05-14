from app import app
from database import db
from sqlalchemy import inspect, text

def migrate():
    with app.app_context():
        try:
            # Use SQLAlchemy inspect() — works on both SQLite and PostgreSQL
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('athlete')]
            if 'category' not in columns:
                db.session.execute(text("ALTER TABLE athlete ADD COLUMN category VARCHAR(50) DEFAULT 'Sprinter'"))
                db.session.commit()
                print("Migration successful: added category column to athlete table.")
            else:
                print("Category column already exists.")
            
            # Ensure event column can hold more characters
            # PostgreSQL: VARCHAR(200) is enforced; SQLite: dynamic length (no-op).
        except Exception as e:
            print(f"Migration error: {e}")

if __name__ == "__main__":
    migrate()
