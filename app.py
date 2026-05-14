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

# ─── Auto-create tables on startup (works with Gunicorn in production) ────────
with app.app_context():
    db.create_all()
    print("[OK] Database tables verified/created.")

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
                # If no password hash set, auto-assign default 'athlete123'
                if not a.password_hash:
                    if password == 'athlete123':
                        a.password_hash = generate_password_hash('athlete123')
                        db.session.commit()
                        return {'role': 'athlete', 'athlete_id': a.id, 'display': a.name}
                    return None  # No hash set and wrong default password
                if check_password_hash(a.password_hash, password):
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

@app.route('/admin/seed', methods=['GET', 'POST'])
def admin_seed():
    """Protected admin route to seed the live database with demo data."""
    SECRET = os.environ.get('SEED_SECRET', 'jru-seed-2024')
    
    # Simple password protection
    if request.method == 'GET':
        return '''
        <html><body style="font-family:Arial;max-width:500px;margin:80px auto;text-align:center;background:#f8f9fe;">
        <h2 style="color:#003087;">JRU Athletics — Database Seeder</h2>
        <p style="color:#666;">Enter the seed password to populate the live database with demo data.</p>
        <form method="POST">
            <input name="secret" type="password" placeholder="Enter seed password"
                style="padding:10px;width:80%;border:1px solid #003087;border-radius:6px;margin:10px 0;font-size:1rem;">
            <br>
            <button type="submit"
                style="background:#003087;color:white;padding:12px 30px;border:none;border-radius:6px;font-size:1rem;cursor:pointer;margin-top:10px;">
                🚀 Seed Database
            </button>
        </form>
        </body></html>
        '''
    
    if request.form.get('secret') != SECRET:
        return '<h3 style="color:red;text-align:center;margin-top:100px;">❌ Wrong password.</h3>', 403
    
    try:
        import random, json
        from datetime import datetime, timedelta
        from werkzeug.security import generate_password_hash
        from models import Athlete, TrainingLog, PerformanceResult, RecoveryMetric

        # --- Clear existing data safely ---
        RecoveryMetric.query.delete()
        TrainingLog.query.delete()
        PerformanceResult.query.delete()
        Athlete.query.delete()
        db.session.commit()

        DEFAULT_HASH = generate_password_hash('athlete123')

        EVENT_BENCHMARKS = {
            '100m Sprint':   {'type': 'time',  'range': (10.4, 11.8)},
            '200m Sprint':   {'type': 'time',  'range': (21.2, 24.5)},
            '400m Sprint':   {'type': 'time',  'range': (47.5, 53.0)},
            '800m Run':      {'type': 'time',  'range': (110.0, 135.0)},
            '1500m Run':     {'type': 'time',  'range': (235.0, 280.0)},
            'Long Jump':     {'type': 'dist',  'range': (6.50, 7.80)},
            'High Jump':     {'type': 'dist',  'range': (1.90, 2.20)},
            'Javelin Throw': {'type': 'dist',  'range': (58.0, 75.0)},
            'Shot Put':      {'type': 'dist',  'range': (13.5, 18.0)},
        }

        ATHLETE_DATA = [
            {'name': 'John Dave Puno',   'event': '100m Sprint',  'category': 'Sprinter',       'age': 21, 'height': 179.6, 'weight': 69.6},
            {'name': 'Miguel Rivera',    'event': 'Long Jump',    'category': 'Jumper',         'age': 20, 'height': 176.0, 'weight': 72.0},
            {'name': 'Gabriel Santos',   'event': '800m Run',     'category': 'Middle Distance','age': 22, 'height': 172.0, 'weight': 63.5},
            {'name': 'Carlo Reyes',      'event': '200m Sprint',  'category': 'Sprinter',       'age': 19, 'height': 175.0, 'weight': 70.0},
            {'name': 'Angelo Bautista',  'event': '400m Sprint',  'category': 'Sprinter',       'age': 21, 'height': 177.0, 'weight': 73.0},
            {'name': 'Kevin Torres',     'event': 'Javelin Throw','category': 'Thrower',        'age': 23, 'height': 183.0, 'weight': 85.0},
            {'name': 'Luis Mendoza',     'event': '1500m Run',    'category': 'Middle Distance','age': 20, 'height': 170.0, 'weight': 60.0},
            {'name': 'Mark Garcia',      'event': '100m Sprint',  'category': 'Sprinter',       'age': 18, 'height': 174.0, 'weight': 68.0},
            {'name': 'Paul Villanueva',  'event': 'High Jump',    'category': 'Jumper',         'age': 22, 'height': 180.0, 'weight': 71.0},
            {'name': 'Rafael Ocampo',    'event': 'Shot Put',     'category': 'Thrower',        'age': 24, 'height': 182.0, 'weight': 92.0},
        ]

        WARMUPS = [
            'Jog 800m, dynamic drills, leg swings, arm circles',
            'Standard Track Warmup: A-Skips, B-Skips, High Knees 3x30m',
            'Mobility circuit: 10 min foam roll + mobility flow',
            'JRU Team Protocol: Dynamic stretching + technical prep',
            'Road run, zigzag stairs, sledge 60m x 3',
        ]
        COMPETITIONS = [
            'NCAA Season 99 Track & Field Meet',
            'UAAP Season 86 Athletics',
            'JRU Internal Time Trial',
            'Recto Cup Invitational',
            'PRISAA National Finals',
            'PSC-NSA Assessment Meet',
        ]
        SESSION_TYPES = ['Track', 'Track', 'Track', 'Weight Room', 'Active Recovery']

        athletes = []
        for d in ATHLETE_DATA:
            a = Athlete(
                name=d['name'], category=d['category'], event=d['event'],
                age=d['age'], height=d['height'], weight=d['weight'],
                password_hash=DEFAULT_HASH
            )
            db.session.add(a)
            athletes.append((a, d['event']))
        db.session.commit()

        start_date = datetime.now().date() - timedelta(days=180)
        logs_n = perf_n = rec_n = 0

        for athlete, ev in athletes:
            bench = EVENT_BENCHMARKS.get(ev, {'type': 'time', 'range': (10.5, 12.0)})
            base_val = random.uniform(*bench['range'])

            for day in range(181):
                cur_date = start_date + timedelta(days=day)
                weekday = cur_date.weekday()

                # Wellness (daily)
                fatigue = min(7, random.randint(1, 4) + (1 if day % 4 == 0 else 0))
                rec = RecoveryMetric(
                    athlete_id=athlete.id, date=cur_date,
                    sleep_hours=round(random.uniform(7.0, 9.0), 1),
                    sleep_quality=random.randint(4, 7),
                    morning_fatigue=fatigue,
                    soreness=min(7, random.randint(1, 3) + (1 if day % 3 == 0 else 0)),
                    stress_level=random.randint(1, 5),
                    motivation=random.randint(4, 7),
                    created_at=datetime.combine(cur_date, datetime.min.time()).replace(hour=random.randint(6,7), minute=random.randint(0,59))
                )
                db.session.add(rec)
                rec_n += 1

                # Training (Mon–Sat)
                if weekday < 6:
                    stype = random.choice(SESSION_TYPES)
                    intensity = random.randint(5, 9) if day > 90 else random.randint(3, 6)
                    duration = random.randint(60, 120)
                    log = TrainingLog(
                        athlete_id=athlete.id, date=cur_date,
                        training_type=stype, training_phase='Specific Preparation' if day > 90 else 'General Preparation',
                        distance=round(random.uniform(600, 2000)) if stype == 'Track' else 0,
                        tonnage=float(random.randint(3,5) * random.randint(4,8) * random.randint(40,100)) if stype == 'Weight Room' else 0.0,
                        duration=duration, intensity=intensity,
                        fatigue_post_workout=min(10, intensity + random.randint(0, 2)),
                        warmup_notes=random.choice(WARMUPS),
                        main_set_details=json.dumps({'dist': 100, 'effort': random.randint(85,100), 'time': round(random.uniform(9.8, 11.5), 2)}) if stype == 'Track' else 'Weight room compound movements',
                        event_trained=ev,
                        status='confirmed',
                        created_at=datetime.combine(cur_date, datetime.min.time()).replace(hour=random.randint(9,11), minute=random.randint(0,59))
                    )
                    db.session.add(log)
                    logs_n += 1

                # Performance (every 28 days)
                if day > 0 and day % 28 == 0:
                    improvement = (day / 180) * random.uniform(0.02, 0.05)
                    if bench['type'] == 'time':
                        val = round(base_val * (1 - improvement) + random.uniform(-0.05, 0.05), 2)
                        val = max(bench['range'][0], min(bench['range'][1], val))
                        perf = PerformanceResult(
                            athlete_id=athlete.id, date=cur_date, event=ev,
                            time_seconds=val, distance_meters=0.0,
                            rank=random.randint(1, 5),
                            competition_name=random.choice(COMPETITIONS),
                            status='confirmed',
                            created_at=datetime.combine(cur_date, datetime.min.time()).replace(hour=14)
                        )
                    else:
                        val = round(base_val * (1 + improvement) + random.uniform(-0.05, 0.05), 2)
                        val = max(bench['range'][0], min(bench['range'][1], val))
                        perf = PerformanceResult(
                            athlete_id=athlete.id, date=cur_date, event=ev,
                            distance_meters=val, time_seconds=0.0,
                            rank=random.randint(1, 4),
                            competition_name=random.choice(COMPETITIONS),
                            status='confirmed',
                            created_at=datetime.combine(cur_date, datetime.min.time()).replace(hour=14)
                        )
                    db.session.add(perf)
                    perf_n += 1

            if logs_n % 500 == 0:
                db.session.flush()

        db.session.commit()
        return f'''
        <html><body style="font-family:Arial;max-width:600px;margin:80px auto;text-align:center;background:#f8f9fe;">
        <h2 style="color:#003087;">✅ Database Seeded Successfully!</h2>
        <p><strong>{len(ATHLETE_DATA)}</strong> Athletes created</p>
        <p><strong>{logs_n}</strong> Training logs</p>
        <p><strong>{rec_n}</strong> Wellness entries</p>
        <p><strong>{perf_n}</strong> Competition results</p>
        <br>
        <a href="/" style="background:#003087;color:white;padding:12px 30px;border-radius:6px;text-decoration:none;font-size:1rem;">
            🏠 Go to Dashboard
        </a>
        </body></html>
        '''
    except Exception as e:
        db.session.rollback()
        return f'<h3 style="color:red;text-align:center;margin-top:100px;">❌ Error: {str(e)}</h3>', 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    # Run config
    env = os.environ.get('FLASK_ENV', 'development')
    is_debug = (env == 'development')
    port = int(os.environ.get('PORT', 5000))
    
    print(f"Starting JRU Athletics Portal in {env} mode...")
    app.run(debug=is_debug, host='0.0.0.0', port=port)
