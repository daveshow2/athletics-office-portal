from database import db
from datetime import datetime

class Athlete(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False, default='Sprinter') # e.g., 'Sprinter', 'Hurdler'
    event = db.Column(db.String(200), nullable=False) # e.g., '100m, 200m'
    age = db.Column(db.Integer)
    height = db.Column(db.Float) # in cm
    weight = db.Column(db.Float) # in kg
    password_hash = db.Column(db.String(256), nullable=True)  # Werkzeug hashed password

    # Relationships
    training_logs = db.relationship('TrainingLog', backref='athlete', lazy=True, cascade="all, delete-orphan")
    performances = db.relationship('PerformanceResult', backref='athlete', lazy=True, cascade="all, delete-orphan")
    recoveries = db.relationship('RecoveryMetric', backref='athlete', lazy=True, cascade="all, delete-orphan")

class TrainingLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey('athlete.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    training_type = db.Column(db.String(50))  # 'Track', 'Weight Room', 'Recovery'
    training_phase = db.Column(db.String(50)) # Periodization phase name
    distance = db.Column(db.Float)    # Total metres for track; null for weight room
    tonnage = db.Column(db.Float)     # Sets × Reps × Weight (kg) — for weight room only
    duration = db.Column(db.Integer)  # Active session time in minutes
    intensity = db.Column(db.Integer) # Borg CR10 RPE 0-10
    fatigue_post_workout = db.Column(db.Integer) # 1-10
    warmup_notes = db.Column(db.Text)
    main_set_details = db.Column(db.Text) # JSON: dist, effort, time for sprinters
    event_trained = db.Column(db.String(100)) # e.g. '100m Sprint'
    status = db.Column(db.String(20), default='pending') # 'pending', 'confirmed'
    # Temporal integrity: when the entry was actually submitted
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class PerformanceResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey('athlete.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    event = db.Column(db.String(50), nullable=False)
    time_seconds = db.Column(db.Float)    # Track events
    distance_meters = db.Column(db.Float) # Field events
    rank = db.Column(db.Integer)
    competition_name = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending') # 'pending', 'confirmed'
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class RecoveryMetric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey('athlete.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    sleep_hours = db.Column(db.Float)
    sleep_quality = db.Column(db.Integer)    # 1-7 Hooper Index
    soreness = db.Column(db.Integer)         # 1-7 Hooper Index
    morning_fatigue = db.Column(db.Integer)  # 1-7 Hooper Index
    stress_level = db.Column(db.Integer)     # 1-7 Hooper Index
    motivation = db.Column(db.Integer)       # 1-7 Hooper Index
    # Temporal integrity: should be logged every morning
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

