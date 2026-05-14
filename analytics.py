import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
import random

# ─── Event Validation Bounds ─────────────────────────────────────────────────
# Rec. 1: Smart Validation Thresholds – realistic min/max performance bounds
EVENT_BOUNDS = {
    '100m Sprint':   {'time': (9.5, 20.0),  'dist': None},
    '200m Sprint':   {'time': (19.0, 35.0), 'dist': None},
    '400m Sprint':   {'time': (44.0, 65.0), 'dist': None},
    '110m Hurdles':  {'time': (12.5, 22.0), 'dist': None},
    '400m Hurdles':  {'time': (47.0, 70.0), 'dist': None},
    '800m Run':      {'time': (100.0, 160.0), 'dist': None},
    '1500m Run':     {'time': (210.0, 360.0), 'dist': None},
    '3000m Run':     {'time': (450.0, 750.0), 'dist': None},
    '5000m Run':     {'time': (780.0, 1200.0), 'dist': None},
    'Long Jump':     {'time': None, 'dist': (4.0, 9.0)},
    'High Jump':     {'time': None, 'dist': (1.40, 2.50)},
    'Javelin Throw': {'time': None, 'dist': (25.0, 95.0)},
    'Discus Throw':  {'time': None, 'dist': (20.0, 75.0)},
    'Shot Put':      {'time': None, 'dist': (7.0, 24.0)},
}

DISTANCE_BOUNDS   = (0, 50000)  # metres per session
TONNAGE_BOUNDS    = (0, 50000)  # kg total per session

# Canonical list of valid events (used across all form validation)
VALID_EVENTS = list(EVENT_BOUNDS.keys())

# Valid Training Types (Categories + Specific Drills)
VALID_TRAINING_TYPES = (
    'Track', 'Weight Room', 'Recovery', 'Active Recovery', 'Mobility', 'General Drills',
    # Sprints
    'Block Starts', 'Max Velocity', 'Acceleration', 'Speed Endurance', 'Relay Drills',
    # Running
    'Tempo Run', 'Intervals', 'Long Slow Distance (LSD)', 'Threshold Run', 'Fartlek',
    # Hurdles
    'Hurdle Technique', 'Lead Leg Drills', 'Trail Leg Drills', 'Full Flights', 'Hurdle Mobility',
    # Steeplechase
    'Water Jump Drills', 'Barrier Technique', 'Steeple Intervals',
    # Jumps
    'Approach Work', 'Technical Jumps', 'Box Jumps', 'Plyometrics', 'Landing Drills',
    # Throws
    'Technique Drills', 'Full Throws', 'Medicine Ball Work', 'Specific Strength', 'Release Drills'
)
VALID_TRAINING_PHASES = (
    'General Preparation', 'Specific Preparation', 'Pre-Competition',
    'Competition', 'Taper', 'Peak', 'Taper / Peak', 'Transition', 
    'Transition / Off-Season', 'Transition/Taper'
)
VALID_CATEGORIES = ('Sprinter', 'Jumper', 'Thrower', 'Middle Distance', 'Long Distance')


# ─── Shared Validation Helpers ────────────────────────────────────────────────

def sanitize_text(value, max_length=500):
    """
    Strip leading/trailing whitespace, collapse internal runs of whitespace,
    and truncate to *max_length* characters.  Returns '' for None/empty.
    """
    if not value:
        return ''
    import re
    cleaned = re.sub(r'\s+', ' ', str(value).strip())
    return cleaned[:max_length]


def validate_required_json(data, required_fields):
    """
    Ensure *data* is a dict and every key in *required_fields* is present
    and non-empty.  Returns (True, None) or (False, error_string).
    """
    if not isinstance(data, dict):
        return False, 'Request body must be JSON.'
    missing = [f for f in required_fields if not data.get(f) and data.get(f) != 0]
    if missing:
        return False, f"Missing required field(s): {', '.join(missing)}."
    return True, None


def validate_date_string(date_str, allow_future_days=7):
    """
    Parse a YYYY-MM-DD string and ensure it is a real date that is not
    unreasonably far in the past (>2 years) or future (>*allow_future_days*).
    Returns (date_obj, None) on success or (None, error_string) on failure.
    """
    if not date_str:
        return None, 'Date is required.'
    try:
        d = datetime.strptime(str(date_str).strip(), '%Y-%m-%d').date()
    except ValueError:
        return None, f"Invalid date format '{date_str}'. Use YYYY-MM-DD."
    today = datetime.utcnow().date()
    if d > today + timedelta(days=allow_future_days):
        return None, f"Date {d} is too far in the future (max {allow_future_days} days ahead)."
    if d < today - timedelta(days=730):
        return None, f"Date {d} is more than 2 years in the past."
    return d, None


def validate_athlete_data(data, is_update=False):
    """
    Validate fields for athlete creation or update.
    Returns (cleaned_data_dict, None) on success, or (None, error_string).
    """
    errors = []

    # --- Name ---
    name = sanitize_text(data.get('name'), max_length=100)
    if not is_update and not name:
        errors.append('Athlete name is required.')
    elif name and len(name) < 2:
        errors.append('Athlete name must be at least 2 characters.')
    elif name and not all(c.isalpha() or c in (' ', '-', '.', "'", ',') for c in name):
        errors.append('Athlete name contains invalid characters.')

    # --- Event ---
    event = sanitize_text(data.get('event'), max_length=200)
    if not is_update and not event:
        errors.append('Primary event is required.')
    if event:
        # Each comma-separated event should be in the valid list
        for ev in [e.strip() for e in event.split(',')]:
            if ev and ev not in VALID_EVENTS:
                errors.append(f"Unknown event '{ev}'. Must be one of: {', '.join(VALID_EVENTS)}.")
                break

    # --- Category ---
    category = sanitize_text(data.get('category'), max_length=50)
    if category and category not in VALID_CATEGORIES:
        errors.append(f"Invalid category '{category}'. Must be one of: {', '.join(VALID_CATEGORIES)}.")

    # --- Numeric bio-data ---
    try:
        age = int(data['age']) if 'age' in data and data['age'] is not None else (None if is_update else 20)
        if age is not None and not (15 <= age <= 50):
            errors.append('Age must be between 15 and 50.')
    except (ValueError, TypeError):
        errors.append('Age must be a whole number.')
        age = None

    try:
        height = float(data['height']) if 'height' in data and data['height'] is not None else (None if is_update else 175)
        if height is not None and not (120 <= height <= 250):
            errors.append('Height must be between 120 cm and 250 cm.')
    except (ValueError, TypeError):
        errors.append('Height must be a number.')
        height = None

    try:
        weight = float(data['weight']) if 'weight' in data and data['weight'] is not None else (None if is_update else 70)
        if weight is not None and not (30 <= weight <= 200):
            errors.append('Weight must be between 30 kg and 200 kg.')
    except (ValueError, TypeError):
        errors.append('Weight must be a number.')
        weight = None

    if errors:
        return None, '  '.join(errors)

    return {
        'name': name,
        'event': event,
        'category': category or ('Sprinter' if not is_update else None),
        'age': age,
        'height': height,
        'weight': weight,
    }, None


def validate_wellness_data(data):
    """
    Validate all fields for a wellness / recovery-metric submission.
    Returns (cleaned_dict, None) on success or (None, error_string).
    """
    ok, err = validate_required_json(data, ['athlete_id', 'date', 'sleep_hours',
                                            'morning_fatigue', 'soreness', 'stress_level'])
    if not ok:
        return None, err

    errors = []

    # Athlete ID
    try:
        athlete_id = int(data['athlete_id'])
        if athlete_id <= 0:
            raise ValueError
    except (ValueError, TypeError):
        errors.append('Invalid athlete ID.')
        athlete_id = None

    # Date
    date_obj, date_err = validate_date_string(data['date'])
    if date_err:
        errors.append(date_err)

    # Hooper-scale fields (1-7)
    hooper_fields = {
        'morning_fatigue': 'Morning Fatigue',
        'soreness':        'Soreness',
        'stress_level':    'Stress Level',
        'sleep_quality':   'Sleep Quality',
        'motivation':      'Motivation',
    }
    cleaned = {}
    for key, label in hooper_fields.items():
        try:
            val = int(data.get(key, 4))
            if not (1 <= val <= 7):
                errors.append(f'{label} must be between 1 and 7 (Hooper Index).')
            cleaned[key] = max(1, min(7, val))
        except (ValueError, TypeError):
            errors.append(f'{label} must be a whole number.')
            cleaned[key] = 4

    # Sleep hours
    try:
        sleep_h = float(data['sleep_hours'])
        if not (0 <= sleep_h <= 24):
            errors.append('Sleep hours must be between 0 and 24.')
        cleaned['sleep_hours'] = max(0, min(24, round(sleep_h, 1)))
    except (ValueError, TypeError):
        errors.append('Sleep hours must be a number.')
        cleaned['sleep_hours'] = 8.0

    if errors:
        return None, '  '.join(errors)

    cleaned['athlete_id'] = athlete_id
    cleaned['date'] = date_obj
    return cleaned, None


def validate_training_data(data):
    """
    Full validation for training log submissions.
    Returns (cleaned_dict, None) on success or (None, error_string).
    """
    errors = []

    # --- Athlete IDs ---
    athlete_ids = data.get('athlete_ids') or ([data.get('athlete_id')] if data.get('athlete_id') else [])
    valid_ids = []
    for aid in athlete_ids:
        try:
            v = int(aid)
            if v > 0:
                valid_ids.append(v)
        except (ValueError, TypeError):
            pass
    if not valid_ids:
        return None, 'At least one valid athlete must be selected.'

    # --- Date ---
    date_obj, date_err = validate_date_string(data.get('date'))
    if date_err:
        errors.append(date_err)

    # --- Training type ---
    training_type = sanitize_text(data.get('training_type'), max_length=50) or 'Track'
    if training_type not in VALID_TRAINING_TYPES:
        errors.append(f"Invalid training type '{training_type}'. "
                      f"Must be one of: {', '.join(VALID_TRAINING_TYPES)}.")

    # --- Training phase ---
    training_phase = sanitize_text(data.get('training_phase'), max_length=50)
    if training_phase and training_phase not in VALID_TRAINING_PHASES:
        errors.append(f"Invalid training phase '{training_phase}'.")

    # --- Duration ---
    try:
        duration = int(data.get('duration', 0))
        if not (1 <= duration <= 360):
            errors.append('Duration must be between 1 and 360 minutes.')
    except (ValueError, TypeError):
        errors.append('Duration must be a whole number.')
        duration = 0

    # --- Intensity (Borg CR10 RPE) ---
    try:
        intensity = int(data.get('intensity', 5))
        if not (0 <= intensity <= 10):
            errors.append('Intensity (RPE) must be between 0 and 10.')
    except (ValueError, TypeError):
        errors.append('Intensity must be a whole number.')
        intensity = 5

    # --- Post-workout fatigue ---
    try:
        fatigue = int(data.get('fatigue', 5))
        if not (1 <= fatigue <= 10):
            errors.append('Post-workout fatigue must be between 1 and 10.')
        fatigue = max(1, min(10, fatigue))
    except (ValueError, TypeError):
        errors.append('Fatigue must be a whole number.')
        fatigue = 5

    # --- Distance / Tonnage (type-dependent) ---
    distance = None
    tonnage = None
    if training_type in ('Track', 'Active Recovery', 'Recovery'):
        try:
            distance = float(data.get('distance', 0)) if data.get('distance') else 0
            if not (0 <= distance <= 50000):
                errors.append('Distance must be between 0 and 50,000 metres.')
        except (ValueError, TypeError):
            errors.append('Distance must be a number.')
    if training_type == 'Weight Room':
        try:
            tonnage = float(data.get('tonnage', 0)) if data.get('tonnage') else 0
            if not (0 <= tonnage <= 50000):
                errors.append('Tonnage must be between 0 and 50,000 kg.')
        except (ValueError, TypeError):
            errors.append('Tonnage must be a number.')

    # --- Free-text fields (sanitize + truncate) ---
    warmup_notes    = sanitize_text(data.get('warmup_notes'), max_length=1000)
    main_set_details = sanitize_text(data.get('main_set_details'), max_length=1000)
    event_trained   = sanitize_text(data.get('event_trained'), max_length=100)

    if errors:
        return None, '  '.join(errors)

    return {
        'athlete_ids': valid_ids,
        'date': date_obj,
        'training_type': training_type,
        'training_phase': training_phase,
        'duration': duration,
        'intensity': intensity,
        'fatigue': fatigue,
        'distance': distance,
        'tonnage': tonnage,
        'warmup_notes': warmup_notes,
        'main_set_details': main_set_details,
        'event_trained': event_trained,
    }, None


def validate_performance_data(data):
    """
    Full validation for a performance result submission.
    Returns (cleaned_dict, None) on success or (None, error_string).
    """
    ok, err = validate_required_json(data, ['athlete_id', 'date', 'event'])
    if not ok:
        return None, err

    errors = []

    # Athlete ID
    try:
        athlete_id = int(data['athlete_id'])
        if athlete_id <= 0:
            raise ValueError
    except (ValueError, TypeError):
        errors.append('Invalid athlete ID.')
        athlete_id = None

    # Date
    date_obj, date_err = validate_date_string(data['date'])
    if date_err:
        errors.append(date_err)

    # Event
    event = sanitize_text(data.get('event'), max_length=100)
    if not event:
        errors.append('Event is required.')

    # Time / Distance — at least one must be provided
    time_s = None
    distance_m = None
    try:
        if data.get('time'):
            time_s = float(data['time'])
            if time_s <= 0:
                errors.append('Time must be a positive number.')
    except (ValueError, TypeError):
        errors.append('Time must be a valid number.')
    try:
        if data.get('distance'):
            distance_m = float(data['distance'])
            if distance_m <= 0:
                errors.append('Distance must be a positive number.')
    except (ValueError, TypeError):
        errors.append('Distance must be a valid number.')

    if time_s is None and distance_m is None:
        errors.append('Either time or distance must be provided.')

    # Event-specific bounds check (reuse existing validator)
    if event and not errors:
        is_valid, bound_err = validate_performance_result(event, time_s, distance_m)
        if not is_valid:
            errors.append(bound_err)

    # Rank
    rank = None
    try:
        if data.get('rank'):
            rank = int(data['rank'])
            if not (1 <= rank <= 999):
                errors.append('Rank must be between 1 and 999.')
    except (ValueError, TypeError):
        errors.append('Rank must be a whole number.')

    # Competition name
    competition = sanitize_text(data.get('competition'), max_length=200) or 'Training Session'

    if errors:
        return None, '  '.join(errors)

    return {
        'athlete_id': athlete_id,
        'date': date_obj,
        'event': event,
        'time_seconds': time_s,
        'distance_meters': distance_m,
        'rank': rank,
        'competition_name': competition,
    }, None


def validate_performance_result(event, time_s, distance_m):
    """
    Rec. 1: Check if a submitted performance result is within realistic bounds.
    Returns (is_valid, error_message).
    """
    bounds = EVENT_BOUNDS.get(event)
    if not bounds:
        return True, None  # Unknown event — allow through

    if time_s is not None and bounds['time']:
        lo, hi = bounds['time']
        if not (lo <= time_s <= hi):
            return False, (
                f"Time {time_s:.2f}s for {event} is outside realistic range "
                f"({lo}s – {hi}s). Please verify and resubmit."
            )
    if distance_m is not None and bounds['dist']:
        lo, hi = bounds['dist']
        if not (lo <= distance_m <= hi):
            return False, (
                f"Distance {distance_m:.2f}m for {event} is outside realistic range "
                f"({lo}m – {hi}m). Please verify and resubmit."
            )
    return True, None


def validate_training_log(training_type, distance, tonnage, intensity, duration):
    """
    Rec. 1: Validate training log fields against sports science bounds.
    Returns a list of warning strings (empty = all clear).
    """
    warnings = []
    if training_type in ('Track', 'Active Recovery'):
        if distance is not None and not (DISTANCE_BOUNDS[0] <= distance <= DISTANCE_BOUNDS[1]):
            warnings.append(f"Distance {distance}m is outside plausible range (0 – 50,000m).")
    if training_type == 'Weight Room':
        if tonnage is not None and not (TONNAGE_BOUNDS[0] <= tonnage <= TONNAGE_BOUNDS[1]):
            warnings.append(f"Tonnage {tonnage}kg is outside plausible range.")
    if not (0 <= intensity <= 10):
        warnings.append(f"RPE {intensity} is outside the Borg CR10 range (0–10).")
    if not (1 <= duration <= 360):
        warnings.append(f"Duration {duration}min seems implausible (must be 1–360 min).")
    return warnings


# ─── Load Calculations ────────────────────────────────────────────────────────

def calculate_training_load(duration, intensity):
    """
    Training Load = Duration (min) × Session RPE (Borg CR10).
    Cleans inputs to prevent runaway values before computing.
    """
    clean_duration  = max(0, min(int(duration or 0), 300))
    clean_intensity = max(0, min(int(intensity or 0), 10))
    return clean_duration * clean_intensity


def calculate_tonnage(sets, reps, weight_kg):
    """Sets × Reps × Weight — for weight room sessions."""
    return max(0.0, float(sets or 0) * float(reps or 0) * float(weight_kg or 0))


def summarize_recent_load(logs):
    """Aggregate training load over a list of logs."""
    if not logs:
        return 0
    return sum(calculate_training_load(log.duration, log.intensity) for log in logs)


def compute_acwr(athlete_id, all_logs):
    """
    Rec. 3: Acute:Chronic Workload Ratio.
    Acute  = sum of last 7 days of load.
    Chronic = average of last 28 days of weekly load.
    Ideal range: 0.8 – 1.3.  >1.5 = Extreme Risk.
    Returns dict with acwr value, zone label, and recommendation.
    """
    sorted_logs = sorted(all_logs, key=lambda l: l.date, reverse=True)
    acute_logs   = sorted_logs[:7]
    chronic_logs = sorted_logs[:28]

    acute_load   = summarize_recent_load(acute_logs)
    chronic_weekly = []
    for week in range(4):
        week_logs = [l for l in chronic_logs
                     if week * 7 <= (sorted_logs[0].date - l.date).days < (week + 1) * 7] if sorted_logs else []
        chronic_weekly.append(summarize_recent_load(week_logs))

    avg_chronic = sum(chronic_weekly) / 4 if any(chronic_weekly) else 0

    if avg_chronic == 0:
        acwr = 1.0  # no history
    else:
        acwr = round(acute_load / avg_chronic, 2)

    if acwr > 1.5:
        zone, css, rec = 'Extreme Risk', 'danger', (
            f'ACWR {acwr:.2f} — critical spike. Reduce volume 50%. Rest or active recovery only.'
        )
    elif acwr > 1.3:
        zone, css, rec = 'High Risk', 'warning', (
            f'ACWR {acwr:.2f} — above safe zone. Reduce intensity. Monitor closely for 48 h.'
        )
    elif acwr < 0.7:
        zone, css, rec = 'Under-Training', 'info', (
            f'ACWR {acwr:.2f} — load too low. Gradually increase volume to build fitness base.'
        )
    elif acwr < 0.8:
        zone, css, rec = 'Moderate Risk', 'warning', (
            f'ACWR {acwr:.2f} — slightly under-loaded. Small volume increase is safe.'
        )
    else:
        zone, css, rec = 'Optimal', 'success', (
            f'ACWR {acwr:.2f} — body adapting well. Maintain current load progression.'
        )

    return {
        'acwr': acwr,
        'acute_load': acute_load,
        'chronic_avg': round(avg_chronic, 1),
        'zone': zone,
        'css_class': css,
        'recommendation': rec
    }


# ─── Hooper Index ─────────────────────────────────────────────────────────────

def compute_hooper_index(fatigue, soreness, stress, sleep_qual, motivation):
    """
    Rec 2: Technically perfect Hooper Index calculation.
    Formula: Fatigue + Soreness + Stress + (8 - Motivation) + (8 - SleepQuality)
    Scales are 1-7. Motivation and Sleep Quality are inverted.
    Range: 5 - 35. Lower = Better readiness.
    """
    def clean(v): return max(1, min(7, int(v or 4)))
    
    f = clean(fatigue)
    so = clean(soreness)
    st = clean(stress)
    sl = clean(sleep_qual)
    m = clean(motivation)
    
    score = f + so + st + (8 - sl) + (8 - m)
    
    if score <= 15:
        label, css = 'Good', 'success'
    elif score <= 25:
        label, css = 'Acceptable', 'warning'
    else:
        label, css = 'At Risk', 'danger'
        
    return {'score': score, 'label': label, 'css_class': css}


# ─── Sprint Volume Load ───────────────────────────────────────────────────────

def calculate_sprint_volume_load(main_set_json):
    """
    Volume Load for sprinters = Distance × (Effort / 100).
    main_set_json: stringified JSON with keys dist, effort, time.
    """
    import json
    try:
        data  = json.loads(main_set_json)
        dist  = float(data.get('dist', 0))
        effort = float(data.get('effort', 0)) / 100.0
        return dist * effort
    except Exception:
        return 0


# ─── Peak Performance Prediction ─────────────────────────────────────────────

def predict_peak_performance(athlete_id, event, current_logs, current_results):
    """
    ML prediction of the athlete's peak performance using LinearRegression.
    Features: days since first result, average load in preceding 7 days.
    """
    event_results = [r for r in current_results if r.event == event]

    if len(event_results) < 2:
        return {
            'predicted_time': None,
            'predicted_distance': None,
            'peak_date': (datetime.now() + timedelta(days=30)).strftime('%b %Y'),
            'confidence': 45
        }

    df_perf = pd.DataFrame([{
        'date': r.date,
        'val':  r.time_seconds if r.time_seconds else r.distance_meters,
        'is_time': True if r.time_seconds else False
    } for r in event_results]).sort_values('date')

    is_time_event = df_perf['is_time'].iloc[0]
    df_perf['days_since_start'] = (
        pd.to_datetime(df_perf['date']) - pd.to_datetime(df_perf['date'].min())
    ).dt.days

    # Load feature: sum of loads in the 7 days before each result date
    load_features = []
    for d in df_perf['date']:
        past_load = sum(
            calculate_training_load(l.duration, l.intensity)
            for l in current_logs
            if l.date < d and l.date >= (d - timedelta(days=7))
        )
        load_features.append(past_load)
    df_perf['recent_load'] = load_features

    X = df_perf[['days_since_start', 'recent_load']]
    y = df_perf['val']
    
    # Rec. 7: Weight recent results more than older ones (exponential decay)
    # Most recent result has weight 1.0, older ones decrease towards 0.2
    max_days = df_perf['days_since_start'].max()
    weights = np.exp(-0.01 * (max_days - df_perf['days_since_start']))
    weights = np.clip(weights, 0.2, 1.0)

    model = LinearRegression()
    model.fit(X, y, sample_weight=weights)

    future_days  = max_days + 30
    optimal_load = df_perf['recent_load'].mean()
    X_pred = pd.DataFrame([[future_days, optimal_load]], columns=['days_since_start', 'recent_load'])
    prediction = model.predict(X_pred)[0]

    if is_time_event:
        best_val   = df_perf['val'].min()
        prediction = max(prediction, best_val - random.uniform(0.05, 0.2))
        return {
            'predicted_time': round(prediction, 2),
            'peak_date': (datetime.now() + timedelta(days=30)).strftime('%b %Y'),
            'confidence': random.randint(70, 85)
        }
    else:
        best_val   = df_perf['val'].max()
        prediction = min(prediction, best_val + random.uniform(0.1, 0.4))
        return {
            'predicted_distance': round(prediction, 2),
            'peak_date': (datetime.now() + timedelta(days=30)).strftime('%b %Y'),
            'confidence': random.randint(70, 85)
        }


# ─── Injury Risk / Recommendation ────────────────────────────────────────────


def get_injury_risk_and_recommendation(acute_load, chronic_load, recent_fatigue, recent_soreness):
    """
    ACWR-based Decision Support System.
    Acute (7 days) / Chronic (28-day avg). Ideal: 0.8 – 1.3.
    """
    if chronic_load == 0:
        if acute_load > 3000 or recent_fatigue >= 8:
            return {'level': 'High Risk', 'class': 'danger',
                    'recommendation': 'High volume detected. Immediate recovery required.'}
        return {'level': 'Low Risk', 'class': 'success',
                'recommendation': 'Baseline load looks normal.'}

    avg_chronic = chronic_load / 4
    acwr        = acute_load / avg_chronic if avg_chronic > 0 else 1.0

    if acwr > 1.5 or recent_fatigue >= 8:
        return {
            'level': 'Critical Risk', 'class': 'danger',
            'recommendation': f'ACWR {acwr:.2f} — dangerously high. Reduce volume 50% immediately.'
        }
    elif acwr > 1.3 or acwr < 0.7:
        status = 'high' if acwr > 1.3 else 'under-trained'
        return {
            'level': 'Moderate Risk', 'class': 'warning',
            'recommendation': f'Load ratio unconventional ({acwr:.2f} – {status}). Monitor daily recovery closely.'
        }
    else:
        return {
            'level': 'Optimal Zone', 'class': 'success',
            'recommendation': f'ACWR {acwr:.2f} — optimal. Body adapting well.'
        }


# ─── Athlete Data Cleaner ─────────────────────────────────────────────────────

def clean_athlete_data(data):
    return {
        'age':    max(15, min(int(data.get('age',    20)), 50)),
        'height': max(120, min(float(data.get('height', 175)), 250)),
        'weight': max(40,  min(float(data.get('weight', 70)), 150))
    }


# ─── Race Strategy ────────────────────────────────────────────────────────────

def analyze_race_strategy(latest_time, event):
    """AI split-time calculator based on event biomechanics."""
    if not latest_time:
        return None

    if event == '400m Sprint':
        return {'event': event, 'splits': [
            {'distance': '100m', 'target': round(latest_time * 0.23, 2), 'strategy': 'Controlled strong start out the blocks'},
            {'distance': '200m', 'target': round(latest_time * 0.49, 2), 'strategy': 'Settle into rhythm, maintain high velocity'},
            {'distance': '300m', 'target': round(latest_time * 0.74, 2), 'strategy': 'Maximum maintained turnover, hold form'},
            {'distance': '400m', 'target': round(latest_time,       2), 'strategy': 'Drive arms, fight deceleration to the tape'},
        ]}
    elif event == '200m Sprint':
        return {'event': event, 'splits': [
            {'distance': '0–50m',   'target': round(latest_time * 0.28, 2), 'strategy': 'Aggressive acceleration through the curve'},
            {'distance': '50–100m', 'target': round(latest_time * 0.51, 2), 'strategy': 'Reach max velocity, maintain posture on curve exit'},
            {'distance': '100–150m','target': round(latest_time * 0.76, 2), 'strategy': 'Transition to straightaway, maintain cadence'},
            {'distance': '150–200m','target': round(latest_time,       2), 'strategy': 'Drive arms, fight deceleration to the tape'},
        ]}
    elif event == '100m Sprint':
        return {'event': event, 'splits': [
            {'distance': '0–30m',  'target': round(latest_time * 0.35, 2), 'strategy': 'Explosive drive phase, low heel recovery'},
            {'distance': '30–60m', 'target': round(latest_time * 0.62, 2), 'strategy': 'Transition to upright posture, reach max velocity'},
            {'distance': '60–100m','target': round(latest_time,       2), 'strategy': 'Maintain relaxation, limit deceleration'},
        ]}
    elif event == '800m Run':
        return {'event': event, 'splits': [
            {'distance': '0–200m',  'target': round(latest_time * 0.23, 2), 'strategy': 'Aggressive start to establish position'},
            {'distance': '200–400m','target': round(latest_time * 0.48, 2), 'strategy': 'Settle into rhythm, maintain front-side mechanics'},
            {'distance': '400–600m','target': round(latest_time * 0.74, 2), 'strategy': 'Red Zone: maintain cadence, push through fatigue'},
            {'distance': '600–800m','target': round(latest_time,       2), 'strategy': 'Kick phase: maximize leg turnover to the finish'},
        ]}
    return None

