import os
from dotenv import load_dotenv
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from database import db

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'jru-athletics-secret-2024')

# ─── Database Configuration ──────────────────────────────────────────────────
# Reads DATABASE_URL from .env. Falls back to local SQLite for development.
basedir = os.path.abspath(os.path.dirname(__file__))
default_db = 'sqlite:///' + os.path.join(basedir, 'sports_science.db')
db_url = os.environ.get('DATABASE_URL', default_db)

# Fix for Heroku/Railway: SQLAlchemy 2.0 requires 'postgresql://' instead of 'postgres://'
if db_url and db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Security check: Ensure a real SECRET_KEY is provided in production
is_prod = os.environ.get('FLASK_ENV') == 'production'
if is_prod and app.secret_key == 'jru-athletics-secret-2024':
    print("WARNING: Using default SECRET_KEY in production! Please set a secure key.")

# Connection pool settings (used by PostgreSQL; SQLite ignores these)
if db_url.startswith('postgresql'):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,
        'max_overflow': 20,
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }

db.init_app(app)

# Import models after db initialization to avoid circular imports
import models

# Import and register API blueprint
from api import api
app.register_blueprint(api, url_prefix='/api')

# ─── Credential Helpers ───────────────────────────────────────────────────────
COACH_USERNAME      = 'jru_coach'
COACH_PASSWORD_HASH = generate_password_hash('athletics2024')

def make_username(name):
    """
    Generate a username slug from an athlete's full name.
    e.g. "John Dave Puno" → "johndavepuno"
    """
    return name.strip().lower().replace(' ', '')

def verify_login(username, password):
    """
    Verify credentials against the database (athletes) or hashed constant (coach).
    Returns a user dict on success, or None on failure.
    """
    # Coach check
    if username == COACH_USERNAME:
        if check_password_hash(COACH_PASSWORD_HASH, password):
            return {'role': 'coach', 'athlete_id': None, 'display': 'Coach'}
        return None
    # Athlete check — look up by derived username
    try:
        athletes = models.Athlete.query.all()
        for a in athletes:
            if make_username(a.name) == username:
                if a.password_hash and check_password_hash(a.password_hash, password):
                    return {'role': 'athlete', 'athlete_id': a.id, 'display': a.name}
                return None  # username matched but wrong password
    except Exception:
        pass
    return None

def login_required(role=None):
    """Decorator factory for role-based route protection."""
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user' not in session:
                return redirect(url_for('login'))
            if role == 'coach' and session.get('role') != 'coach':
                return redirect(url_for('athlete_portal'))
            if role == 'athlete' and session.get('role') != 'athlete':
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator

# ─── Auth Routes ─────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '').strip()
        user = verify_login(username, password)
        if user:
            session['user'] = username
            session['role'] = user['role']
            session['display'] = user['display']
            session['athlete_id'] = user['athlete_id']
            if user['role'] == 'coach':
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('athlete_portal'))
        else:
            error = 'Invalid username or password. Please try again.'

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─── Routes ──────────────────────────────────────────────────────────────────
@app.route('/')
@login_required(role='coach')
def dashboard():
    return render_template('dashboard.html', display_name=session.get('display', 'Coach'))

@app.route('/athletes')
@login_required(role='coach')
def athletes_roster():
    return render_template('athletes.html', display_name=session.get('display', 'Coach'))

@app.route('/training-logs')
@login_required(role='coach')
def training_logs():
    return render_template('training_logs.html', display_name=session.get('display', 'Coach'))

@app.route('/approvals')
@login_required(role='coach')
def approvals():
    return render_template('approvals.html', display_name=session.get('display', 'Coach'))

@app.route('/athlete/<int:athlete_id>')
@login_required(role='coach')
def athlete_profile(athlete_id):
    athlete = models.Athlete.query.get_or_404(athlete_id)
    return render_template('athlete.html', athlete=athlete, display_name=session.get('display', 'Coach'))

@app.route('/my-portal')
@login_required(role='athlete')
def athlete_portal():
    athlete_id = session.get('athlete_id')
    athlete = models.Athlete.query.get_or_404(athlete_id)
    return render_template('athlete_portal.html', athlete=athlete, display_name=session.get('display'))

@app.route('/api/status')
def status():
    return jsonify({"status": "Sports Science API is running", "theme": "JRU Blue & Gold"})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    # Run config
    env = os.environ.get('FLASK_ENV', 'development')
    is_debug = (env == 'development')
    port = int(os.environ.get('PORT', 5000))
    
    print(f"Starting JRU Athletics Portal in {env} mode...")
    app.run(debug=is_debug, host='0.0.0.0', port=port)
