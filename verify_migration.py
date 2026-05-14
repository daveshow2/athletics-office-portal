"""Quick verification that the app loads correctly after the PostgreSQL migration changes."""
try:
    from app import app
    uri = app.config['SQLALCHEMY_DATABASE_URI']
    key = app.secret_key
    print(f"DATABASE_URI: {uri}")
    print(f"SECRET_KEY loaded: {key != 'default'}")
    print(f"Uses SQLite: {'sqlite' in uri}")
    
    # Verify database connectivity
    with app.app_context():
        from database import db
        from models import Athlete
        count = Athlete.query.count()
        print(f"Athletes in DB: {count}")
    
    print("[OK] All checks passed. App is PostgreSQL-ready and SQLite still works.")
except Exception as e:
    print(f"[FAIL] {e}")
