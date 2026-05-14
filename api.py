from flask import Blueprint, jsonify, request, session
from database import db
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd

api = Blueprint('api', __name__)

@api.route('/athletes', methods=['GET'])
def get_athletes():
    from models import Athlete
    athletes = Athlete.query.all()
    return jsonify({'athletes': [{
        'id': a.id,
        'name': a.name,
        'username': a.name.lower().replace(' ', ''),
        'password': 'athlete123',
        'category': a.category,
        'event': a.event,
        'age': a.age,
        'height': a.height,
        'weight': a.weight
    } for a in athletes]})

@api.route('/export/athletes', methods=['GET'])
def export_athletes():
    from models import Athlete
    import csv
    from io import StringIO
    from flask import Response
    
    athletes = Athlete.query.all()
    
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Name', 'Category', 'Event', 'Age', 'Height (cm)', 'Weight (kg)'])
    for a in athletes:
        cw.writerow([a.id, a.name, a.category, a.event, a.age, a.height, a.weight])
        
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=athletes.csv"}
    )

@api.route('/export/training', methods=['GET'])
def export_training():
    from models import TrainingLog, Athlete
    import csv
    from io import StringIO
    from flask import Response
    import calendar
    from datetime import date
    
    month = request.args.get('month')
    query = db.session.query(TrainingLog, Athlete).join(Athlete, TrainingLog.athlete_id == Athlete.id)
    
    if month:
        try:
            y, m = map(int, month.split('-'))
            last_day = calendar.monthrange(y, m)[1]
            start_date = date(y, m, 1)
            end_date = date(y, m, last_day)
            query = query.filter(TrainingLog.date >= start_date, TrainingLog.date <= end_date)
        except Exception:
            pass
            
    logs = query.order_by(TrainingLog.date.desc()).all()
    
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Athlete Name', 'Date', 'Type', 'Phase', 'Distance (m)', 'Duration (min)', 'Intensity', 'Fatigue', 'Status'])
    for log, athlete in logs:
        cw.writerow([
            log.id, 
            athlete.name, 
            log.date.strftime('%Y-%m-%d'), 
            log.training_type, 
            log.training_phase,
            log.distance, 
            log.duration, 
            log.intensity, 
            log.fatigue_post_workout,
            log.status
        ])
        
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=training_logs.csv"}
    )

def format_performance_time(seconds):
    """Formats float seconds into SS.ss or M:SS.ss"""
    if seconds is None: return "N/A"
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes = int(seconds // 60)
    rem_seconds = seconds % 60
    return f"{minutes}:{rem_seconds:05.2f}"

@api.route('/analytics/dashboard', methods=['GET'])
def get_dashboard_analytics():
    """
    Simulates the Data Processing Layer and Analytics Engine for the main dashboard.
    Calculates derived metrics like Training Load and assigns Risk/Form logic.
    """
    from models import Athlete, TrainingLog, PerformanceResult, RecoveryMetric
    from analytics import predict_peak_performance, get_injury_risk_and_recommendation, summarize_recent_load
    
    from models import PerformanceResult
    event_filter = request.args.get('event')
    if event_filter:
        # Rec. 1 & User Req: Join with PerformanceResult to find ANY athlete who participates,
        # not just those who have the event in their registered primary event profile.
        athletes = Athlete.query.join(PerformanceResult, Athlete.id == PerformanceResult.athlete_id, isouter=True).filter(
            (Athlete.event.like(f"%{event_filter}%")) | (PerformanceResult.event == event_filter)
        ).distinct().all()
    else:
        athletes = Athlete.query.all()
        
    dashboard_data = []
    
    for a in athletes:
        # Correct date-based filtering for ACWR calculation (handles multiple sessions per day)
        today = datetime.utcnow().date()
        acute_start = today - timedelta(days=7)
        chronic_start = today - timedelta(days=28)
        
        # Analytics only uses CONFIRMED data
        all_logs = TrainingLog.query.filter_by(athlete_id=a.id, status='confirmed').all()
        all_logs_28 = [l for l in all_logs if l.date >= chronic_start]
        acute_logs = [l for l in all_logs_28 if l.date >= acute_start]
        
        acute_load = summarize_recent_load(acute_logs)
        # Chronic is usually the sum of all 28 days LOAD for the risk function which internally divides by 4.
        chronic_load = summarize_recent_load(all_logs_28)
        
        # Get recent recovery
        recent_recovery = RecoveryMetric.query.filter_by(athlete_id=a.id).order_by(RecoveryMetric.date.desc()).first()
        current_fatigue = recent_recovery.morning_fatigue if recent_recovery else 5
        current_soreness = recent_recovery.soreness if recent_recovery else 5
        
        # Decision Support System: ACWR based Risk & Recommendation
        risk_data = get_injury_risk_and_recommendation(acute_load, chronic_load, current_fatigue, current_soreness)
            
        # Get historical performances (Confirmed only)
        all_perf = PerformanceResult.query.filter_by(athlete_id=a.id, status='confirmed').order_by(PerformanceResult.date).all()
        
        # Determine which event to display metrics for (respects the dashboard filter)
        # If filtered by '100m', show 100m results even if primary is '100m, 200m'
        target_event = a.event.split(',')[0].strip() # Default to first registered event
        if event_filter:
            # If an event filter is active, check if they have results for IT specifically first
            has_specific_perf = any(p.event == event_filter for p in all_perf)
            if has_specific_perf:
                target_event = event_filter
            else:
                # Fallback: check profile substring match
                for ev in a.event.split(','):
                    ev = ev.strip()
                    if event_filter.lower() in ev.lower() or ev.lower() in event_filter.lower():
                        target_event = ev
                        break

        # ML: Predict Peak Performance for the target event
        peak_pred = predict_peak_performance(a.id, target_event, all_logs, all_perf)
        
        primary_perf = [p for p in all_perf if p.event == target_event]
        latest_perf = primary_perf[-1] if primary_perf else None
        
        # Determine if result is time-based
        is_time = any(x in target_event for x in ['Sprint', 'Run', 'Hurdles', 'Steeplechase', 'Walk', '110mH', '400mH'])
        
        if latest_perf:
            if is_time:
                perf_str = format_performance_time(latest_perf.time_seconds)
                sort_val = latest_perf.time_seconds
            else:
                dist = latest_perf.distance_meters
                perf_str = f"{dist:.2f}m" if dist is not None else "N/A"
                sort_val = dist if dist is not None else (0 if not is_time else 999)
        else:
            perf_str = "N/A"
            sort_val = 999 if is_time else 0

        
        # Format prediction
        if is_time:
            pred_val = format_performance_time(peak_pred.get('predicted_time'))
        else:
            pred_val = f"{peak_pred.get('predicted_distance')} m" if peak_pred.get('predicted_distance') else "N/A"

        dashboard_data.append({
            'id': a.id,
            'name': a.name,
            'event': a.event,
            'latest_result': perf_str,
            'predicted_peak': f"{pred_val} ({peak_pred['peak_date']})",
            'injury_risk': risk_data['level'],
            'risk_class': risk_data['class'],
            'recommendation': risk_data['recommendation'],
            'training_load': acute_load,
            'fatigue': current_fatigue,
            'sort_val': sort_val,
            'is_time': is_time
        })
    
    # Sort by performance if event filter is active, otherwise sort by risk
    if event_filter:
        is_time_event = any(x in event_filter for x in ['Sprint', 'Run', 'Hurdles', 'Steeplechase', 'Walk', '110mH', '400mH'])
        dashboard_data.sort(key=lambda x: x['sort_val'], reverse=not is_time_event)
    else:
        RISK_ORDER = {'Critical Risk': 0, 'High Risk': 1, 'Moderate Risk': 2, 'Under-Training': 3, 'Optimal Zone': 4, 'Low Risk': 5}
        dashboard_data.sort(key=lambda x: RISK_ORDER.get(x['injury_risk'], 9))
    
    # Aggregated Stats
    total_athletes = Athlete.query.count() # Use total count for stats, even if filtered
    active_logs = TrainingLog.query.count()
    high_risk_count = sum(1 for d in dashboard_data if d['injury_risk'] == 'High Risk')
    peak_approaching = sum(1 for d in dashboard_data if d['injury_risk'] == 'Low Risk' and '10' in d['predicted_peak']) # Dummy highlight

    return jsonify({
        'athletes': dashboard_data[:10], # Top 10 for dashboard
        'stats': {
            'total_athletes': total_athletes,
            'active_logs': active_logs,
            'high_risk_count': high_risk_count,
            'peak_approaching': peak_approaching,
            'pending_count': TrainingLog.query.filter_by(status='pending').count() + PerformanceResult.query.filter_by(status='pending').count()
        }
    })

@api.route('/training', methods=['POST'])
def add_training_log():
    from models import TrainingLog, Athlete
    from analytics import validate_training_data
    data = request.json
    if not data:
        return jsonify({'error': 'Request body must be JSON.'}), 400

    # ── Full server-side validation ──
    cleaned, err = validate_training_data(data)
    if err:
        return jsonify({'error': err}), 422

    # Verify every athlete_id exists in the database
    for a_id in cleaned['athlete_ids']:
        if not Athlete.query.get(a_id):
            return jsonify({'error': f'Athlete with ID {a_id} does not exist.'}), 404

    # Default to pending so the Coach can test the Approval Center workflow
    status = 'pending'

    try:
        for a_id in cleaned['athlete_ids']:
            log = TrainingLog(
                athlete_id=a_id,
                date=cleaned['date'],
                training_type=cleaned['training_type'],
                training_phase=cleaned['training_phase'],
                distance=cleaned['distance'],
                tonnage=cleaned['tonnage'],
                duration=cleaned['duration'],
                intensity=cleaned['intensity'],
                fatigue_post_workout=cleaned['fatigue'],
                warmup_notes=cleaned['warmup_notes'],
                main_set_details=cleaned['main_set_details'],
                event_trained=cleaned['event_trained'],
                status=status,
                created_at=datetime.utcnow()
            )
            db.session.add(log)

        db.session.commit()
        return jsonify({
            'message': f'Training logs added for {len(cleaned["athlete_ids"])} athlete(s)',
            'status': status
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api.route('/training/<int:log_id>', methods=['DELETE'])
def delete_training_log(log_id):
    from models import TrainingLog
    log = TrainingLog.query.get_or_404(log_id)
    try:
        db.session.delete(log)
        db.session.commit()
        return jsonify({'message': 'Training log deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api.route('/training/all', methods=['GET'])
def get_all_training_logs():
    from models import TrainingLog, Athlete
    import calendar
    from datetime import date
    
    month = request.args.get('month')
    query = db.session.query(TrainingLog, Athlete).join(Athlete, TrainingLog.athlete_id == Athlete.id)
    
    if month:
        try:
            y, m = map(int, month.split('-'))
            last_day = calendar.monthrange(y, m)[1]
            start_date = date(y, m, 1)
            end_date = date(y, m, last_day)
            query = query.filter(TrainingLog.date >= start_date, TrainingLog.date <= end_date)
        except Exception:
            pass
            
    logs = query.order_by(TrainingLog.date.desc()).limit(200).all()
    return jsonify({
        'logs': [{
            'id': log.id,
            'athlete_name': athlete.name,
            'athlete_id': athlete.id,
            'date': log.date.strftime('%Y-%m-%d'),
            'type': log.training_type,
            'phase': log.training_phase,
            'distance': log.distance,
            'tonnage': log.tonnage,
            'duration': log.duration,
            'intensity': log.intensity,
            'fatigue': log.fatigue_post_workout,
            'warmup_notes': log.warmup_notes,
            'main_set_details': log.main_set_details,
            'event_trained': log.event_trained,
            'status': log.status,
            'load': (log.duration * log.intensity) if log.duration and log.intensity else 0,
            'submitted_at': log.created_at.strftime('%Y-%m-%d %H:%M') if log.created_at else None
        } for log, athlete in logs]
    })

@api.route('/wellness', methods=['POST'])
def add_wellness_log():
    from models import RecoveryMetric, Athlete
    from analytics import validate_wellness_data
    data = request.json
    if not data:
        return jsonify({'error': 'Request body must be JSON.'}), 400

    # ── Full server-side validation ──
    cleaned, err = validate_wellness_data(data)
    if err:
        return jsonify({'error': err}), 422

    # Ensure only one wellness log per day (Daily Check-in)
    existing = RecoveryMetric.query.filter_by(athlete_id=cleaned['athlete_id'], date=cleaned['date']).first()
    if existing:
        return jsonify({'error': 'You have already submitted your wellness check-in for this date.'}), 409

    try:
        rec = RecoveryMetric(
            athlete_id=cleaned['athlete_id'],
            date=cleaned['date'],
            sleep_hours=cleaned['sleep_hours'],
            sleep_quality=cleaned['sleep_quality'],
            morning_fatigue=cleaned['morning_fatigue'],
            soreness=cleaned['soreness'],
            stress_level=cleaned['stress_level'],
            motivation=cleaned['motivation'],
            created_at=datetime.utcnow()  # Rec. 4: temporal integrity
        )
        db.session.add(rec)
        db.session.commit()
        return jsonify({'message': 'Wellness log submitted successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api.route('/acwr/<int:athlete_id>', methods=['GET'])
def get_acwr(athlete_id):
    """Rec. 3: Return the ACWR data for a specific athlete."""
    from models import TrainingLog
    from analytics import compute_acwr
    logs = TrainingLog.query.filter_by(athlete_id=athlete_id).order_by(TrainingLog.date.desc()).limit(28).all()
    return jsonify(compute_acwr(athlete_id, logs))

@api.route('/perf_result', methods=['POST'])
def add_performance_result():
    from models import PerformanceResult, Athlete
    from analytics import validate_performance_data
    data = request.json
    if not data:
        return jsonify({'error': 'Request body must be JSON.'}), 400

    # ── Full server-side validation ──
    cleaned, err = validate_performance_data(data)
    if err:
        return jsonify({'error': err}), 422

    # Verify athlete exists
    if not Athlete.query.get(cleaned['athlete_id']):
        return jsonify({'error': f'Athlete with ID {cleaned["athlete_id"]} does not exist.'}), 404

    # Default to pending for testing the Approval workflow
    status = 'pending'

    try:
        res = PerformanceResult(
            athlete_id=cleaned['athlete_id'],
            date=cleaned['date'],
            event=cleaned['event'],
            time_seconds=cleaned['time_seconds'],
            distance_meters=cleaned['distance_meters'],
            rank=cleaned['rank'],
            competition_name=cleaned['competition_name'],
            status=status,
            created_at=datetime.utcnow()
        )
        db.session.add(res)
        db.session.commit()
        return jsonify({
            'message': 'Performance result added successfully',
            'status': status
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api.route('/wellness/<int:idx>', methods=['DELETE'])
def delete_wellness_log(idx):
    from models import RecoveryMetric
    log = RecoveryMetric.query.get_or_404(idx)
    try:
        db.session.delete(log)
        db.session.commit()
        return jsonify({'message': 'Wellness log deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api.route('/perf_result/<int:idx>', methods=['DELETE'])
def delete_performance_result(idx):
    from models import PerformanceResult
    res = PerformanceResult.query.get_or_404(idx)
    try:
        db.session.delete(res)
        db.session.commit()
        return jsonify({'message': 'Performance result deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api.route('/perf_result/<int:result_id>', methods=['GET', 'PUT'])
def handle_performance_result(result_id):
    from models import PerformanceResult
    from analytics import validate_date_string, sanitize_text, validate_performance_result, VALID_EVENTS
    result = PerformanceResult.query.get_or_404(result_id)

    if request.method == 'GET':
        return jsonify({
            'id': result.id,
            'athlete_id': result.athlete_id,
            'date': result.date.strftime('%Y-%m-%d'),
            'event': result.event,
            'time_seconds': result.time_seconds,
            'distance_meters': result.distance_meters,
            'rank': result.rank,
            'competition_name': result.competition_name
        })

    elif request.method == 'PUT':
        data = request.json
        if not data:
            return jsonify({'error': 'Request body must be JSON.'}), 400
        errors = []
        try:
            if 'date' in data:
                d, d_err = validate_date_string(data['date'])
                if d_err:
                    errors.append(d_err)
                else:
                    result.date = d
            if 'event' in data:
                ev = sanitize_text(data['event'], max_length=100)
                if ev and ev not in VALID_EVENTS:
                    errors.append(f"Unknown event '{ev}'.")
                elif ev:
                    result.event = ev
            if 'competition' in data:
                result.competition_name = sanitize_text(data['competition'], max_length=200)
            if 'time' in data:
                if data['time']:
                    t = float(data['time'])
                    if t <= 0:
                        errors.append('Time must be a positive number.')
                    else:
                        result.time_seconds = t
                else:
                    result.time_seconds = None
            if 'distance' in data:
                if data['distance']:
                    dist = float(data['distance'])
                    if dist <= 0:
                        errors.append('Distance must be a positive number.')
                    else:
                        result.distance_meters = dist
                else:
                    result.distance_meters = None
            if 'rank' in data:
                if data['rank']:
                    r = int(data['rank'])
                    if not (1 <= r <= 999):
                        errors.append('Rank must be between 1 and 999.')
                    else:
                        result.rank = r
                else:
                    result.rank = None

            # Cross-field bounds validation
            ev_final = result.event
            is_valid, bound_err = validate_performance_result(ev_final, result.time_seconds, result.distance_meters)
            if not is_valid:
                errors.append(bound_err)

            if errors:
                db.session.rollback()
                return jsonify({'error': '  '.join(errors)}), 422

            db.session.commit()
            return jsonify({'message': 'Result updated successfully'})
        except (ValueError, TypeError) as e:
            db.session.rollback()
            return jsonify({'error': f'Invalid data: {e}'}), 422
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

@api.route('/athlete', methods=['POST'])
def add_athlete():
    from models import Athlete
    from analytics import validate_athlete_data
    data = request.json
    if not data:
        return jsonify({'error': 'Request body must be JSON.'}), 400

    # ── Full server-side validation ──
    cleaned, err = validate_athlete_data(data, is_update=False)
    if err:
        return jsonify({'error': err}), 422

    try:
        a = Athlete(
            name=cleaned['name'],
            category=cleaned['category'],
            event=cleaned['event'],
            age=cleaned['age'],
            height=cleaned['height'],
            weight=cleaned['weight']
        )
        db.session.add(a)
        db.session.commit()
        return jsonify({'message': 'Athlete registered successfully', 'id': a.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api.route('/athlete/<int:athlete_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_athlete(athlete_id):
    from models import Athlete, TrainingLog, PerformanceResult, RecoveryMetric
    from analytics import validate_athlete_data
    athlete = Athlete.query.get_or_404(athlete_id)
    
    if request.method == 'GET':
        return jsonify({
            'id': athlete.id,
            'name': athlete.name,
            'category': athlete.category,
            'event': athlete.event,
            'age': athlete.age,
            'height': athlete.height,
            'weight': athlete.weight
        })
        
    elif request.method == 'PUT':
        data = request.json
        if not data:
            return jsonify({'error': 'Request body must be JSON.'}), 400

        # ── Full server-side validation (update mode) ──
        cleaned, err = validate_athlete_data(data, is_update=True)
        if err:
            return jsonify({'error': err}), 422

        try:
            if cleaned['name']:     athlete.name     = cleaned['name']
            if cleaned['category']: athlete.category = cleaned['category']
            if cleaned['event']:    athlete.event    = cleaned['event']
            if cleaned['age']   is not None: athlete.age    = cleaned['age']
            if cleaned['height'] is not None: athlete.height = cleaned['height']
            if cleaned['weight'] is not None: athlete.weight = cleaned['weight']
            
            db.session.commit()
            return jsonify({'message': 'Profile updated successfully', 'athlete': {'id': athlete.id, 'name': athlete.name}})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400
            
    elif request.method == 'DELETE':
        try:
            # Delete related data first
            TrainingLog.query.filter_by(athlete_id=athlete_id).delete()
            PerformanceResult.query.filter_by(athlete_id=athlete_id).delete()
            RecoveryMetric.query.filter_by(athlete_id=athlete_id).delete()
            
            db.session.delete(athlete)
            db.session.commit()
            return jsonify({'message': 'Athlete and all related data deleted successfully'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

@api.route('/analytics/trend/<string:event_type>', methods=['GET'])
def get_performance_trend(event_type):
    """
    Get aggregated performance trend data for the chart.
    Supports events like '100m Sprint', '200m Sprint', etc.
    """
    from models import PerformanceResult
    # Normalize event type if needed
    event_query = event_type
    mapping = {
        '100m': '100m Sprint',
        '200m': '200m Sprint',
        '400m': '400m Sprint',
        '800m': '800m Run',
        '1500m': '1500m Run',
        '3km': '3000m Run',
        '5km': '5000m Run',
        '110mH': '110m Hurdles',
        '400mH': '400m Hurdles',
        'Steeplechase': '3000m Steeplechase',
        'Javelin': 'Javelin Throw',
        'Discus': 'Discus Throw',
        'Shotput': 'Shot Put'
    }
    event_query = mapping.get(event_type, event_type)
    
    results = PerformanceResult.query.filter(PerformanceResult.event == event_query).all()
    
    # Using pandas for easy time-series grouping
    if not results:
        return jsonify({'labels': [], 'data': [], 'event': event_query})
        
    df = pd.DataFrame([{
        'date': r.date,
        'val': r.time_seconds if r.time_seconds else r.distance_meters,
        'is_time': True if r.time_seconds else False
    } for r in results])
    
    # Group by week and average
    df['date'] = pd.to_datetime(df['date'])
    df_grouped = df.groupby(df['date'].dt.isocalendar().week)['val'].mean().reset_index()
    
    labels = [f"Week {int(w)}" for w in df_grouped['week']]
    data = [round(v, 2) for v in df_grouped['val']]
    
    # Add formatted values for tooltips/display
    formatted_data = []
    for v in data:
        if df['is_time'].iloc[0]:
            formatted_data.append(format_performance_time(v))
        else:
            formatted_data.append(f"{v:.2f}m")

    return jsonify({
        'labels': labels,
        'data': data,
        'formatted_data': formatted_data,
        'event': event_query,
        'is_time': bool(df['is_time'].iloc[0])
    })
    
@api.route('/analytics/athlete/<int:athlete_id>', methods=['GET'])
def get_athlete_analytics(athlete_id):
    """
    Get detailed predictive analytics and history for a single athlete.
    """
    from models import Athlete, TrainingLog, PerformanceResult, RecoveryMetric
    from analytics import predict_peak_performance, get_injury_risk_and_recommendation, analyze_race_strategy, summarize_recent_load, calculate_sprint_volume_load
    
    a = Athlete.query.get_or_404(athlete_id)
    
    # Get all unique events this athlete has performance records for
    available_events = [res.event for res in PerformanceResult.query.with_entities(PerformanceResult.event).filter_by(athlete_id=a.id).distinct().all()]
    
    # Also include all registered events for this athlete (split by comma if multi-event)
    registered_events = [e.strip() for e in a.event.split(',')]
    for r_ev in registered_events:
        if r_ev not in available_events:
            available_events.append(r_ev)
            
    # Get selected event from query params. 
    # Default to the first registered event if none specified or if selected is not in available.
    selected_event = request.args.get('event')
    if not selected_event or selected_event not in available_events:
        selected_event = registered_events[0]
    
    # Get confirmed logs for analytics
    all_logs = TrainingLog.query.filter_by(athlete_id=a.id, status='confirmed').order_by(TrainingLog.date.desc()).limit(28).all()
    recent_recovery = RecoveryMetric.query.filter_by(athlete_id=a.id).order_by(RecoveryMetric.date.desc()).first()
    
    # Get filtered performance results (Confirmed only)
    all_perf = PerformanceResult.query.filter_by(athlete_id=a.id, status='confirmed').order_by(PerformanceResult.date).all()
    filtered_perf = [p for p in all_perf if p.event == selected_event]
    
    # Calculate Load (Phase 4: ACWR)
    acute_load = summarize_recent_load(all_logs[:7])
    chronic_load = sum([summarize_recent_load(all_logs[i:i+7]) for i in range(0, 28, 7)])
    
    current_fatigue = recent_recovery.morning_fatigue if recent_recovery else 5
    current_soreness = recent_recovery.soreness if recent_recovery else 5
    
    # ML & DSS - Pass the specific selected_event
    peak_pred = predict_peak_performance(a.id, selected_event, all_logs, all_perf)
    risk_data = get_injury_risk_and_recommendation(acute_load, chronic_load, current_fatigue, current_soreness)
    
    latest_val = filtered_perf[-1].time_seconds if filtered_perf and filtered_perf[-1].time_seconds else (filtered_perf[-1].distance_meters if filtered_perf else None)
    strategy = analyze_race_strategy(latest_val, selected_event)
    
    is_time = any(x in selected_event for x in ['Sprint', 'Run', 'Hurdles', 'Steeplechase'])
    
    # Format Training History for Table and Charts (last 14 days)
    full_training_history = []
    
    # Get last 14 days for charts and tables
    dates = []
    load_vals = []
    fatigue_vals = []
    daily_details = []
    
    # Get all training logs and recovery metrics for the athlete sorted by date
    all_raw_logs = TrainingLog.query.filter_by(athlete_id=a.id).order_by(TrainingLog.date.desc()).all()
    all_raw_wellness = RecoveryMetric.query.filter_by(athlete_id=a.id).order_by(RecoveryMetric.date.desc()).all()
    
    # confirmed-only logs for load calculation in the loop
    confirmed_raw_logs = [l for l in all_raw_logs if l.status == 'confirmed']

    for i in range(13, -1, -1):
        target_date = (datetime.now() - pd.Timedelta(days=i)).date()
        date_logs = [l for l in confirmed_raw_logs if l.date == target_date]
        rec = next((r for r in all_raw_wellness if r.date == target_date), None)
        
        load = sum([(l.intensity * l.duration) for l in date_logs])
        fatigue = rec.morning_fatigue if rec else 4
        
        dates.append(target_date.strftime('%m/%d'))
        load_vals.append(load)
        fatigue_vals.append(fatigue)
        
        # Detailed metadata for the "Day Details" modal (aggregated)
        if date_logs or rec:
            main_log = date_logs[0] if date_logs else None
            daily_details.append({
                'date': target_date.strftime('%A, %b %d'),
                'has_data': True,
                'training': {
                    'id': main_log.id if main_log else None,
                    'type': main_log.training_type if main_log else 'N/A',
                    'load': load,
                    'volume_load': round(sum([calculate_sprint_volume_load(l.main_set_details) for l in date_logs]), 1),
                    'duration': sum([l.duration for l in date_logs]),
                    'distance': sum([(l.distance or 0) for l in date_logs]),
                    'intensity': max([l.intensity for l in date_logs]) if date_logs else 0,
                    'warmup_notes': " | ".join([l.warmup_notes for l in date_logs if l.warmup_notes]),
                    'main_set_details': " | ".join([l.main_set_details for l in date_logs if l.main_set_details])
                } if date_logs else None,
                'wellness': {
                    'id': rec.id if rec else None,
                    'fatigue': rec.morning_fatigue if rec else 'N/A',
                    'soreness': rec.soreness if rec else 'N/A',
                    'sleep_hours': rec.sleep_hours if rec else 'N/A',
                    'sleep_quality': rec.sleep_quality if rec else 'N/A',
                    'stress_level': rec.stress_level if rec else 'N/A',
                    'motivation': rec.motivation if rec else 'N/A'
                } if rec else None
            })
        else:
            daily_details.append({
                'date': target_date.strftime('%A, %b %d'),
                'has_data': False,
                'training': None,
                'wellness': None
            })

    # Historical Training Logs (Paginated or limit to recent 10 for table)
    for l in all_raw_logs[:20]:
        full_training_history.append({
            'id': l.id,
            'date': l.date.strftime('%Y-%m-%d'),
            'type': l.training_type,
            'distance': l.distance,
            'duration': l.duration,
            'intensity': l.intensity,
            'status': l.status,
            'load': l.intensity * l.duration,
            'fatigue': l.fatigue_post_workout,
            'warmup_notes': l.warmup_notes,
            'main_set_details': l.main_set_details
        })

    # Format Performance History (Filtered by event)
    perf_history = []
    for p in filtered_perf:
        perf_history.append({
            'result_id': p.id,
            'date': p.date.strftime('%Y-%m-%d'),
            'competition': p.competition_name,
            'rank': p.rank,
            'status': p.status,
            'value': p.time_seconds if is_time else p.distance_meters,
            'formatted_value': format_performance_time(p.time_seconds) if is_time else f"{p.distance_meters:.2f}m"
        })
    
    if is_time:
        peak_val = format_performance_time(peak_pred.get('predicted_time'))
    else:
        peak_val = f"{peak_pred.get('predicted_distance'):.2f}m" if peak_pred.get('predicted_distance') else "N/A"

    return jsonify({
        'athlete': {'id': a.id, 'name': a.name, 'event': a.event, 'selected_event': selected_event},
        'available_events': available_events,
        'peak_performance': {
            'value': peak_val,
            'unit': '', 
            'date': peak_pred.get('peak_date'),
            'confidence': peak_pred.get('confidence')
        },
        'risk_assessment': risk_data,
        'strategy': strategy,
        'training_history': {
            'dates': dates,
            'load': load_vals,
            'fatigue': fatigue_vals,
            'details': daily_details,
            'history': full_training_history
        },
        'performance_history': perf_history
    })

@api.route('/analytics/load_fatigue', methods=['GET'])
def get_load_fatigue_trend():
    """
    Get aggregated load vs fatigue data for the team for the last 7 days.
    """
    from models import TrainingLog, RecoveryMetric
    from analytics import summarize_recent_load
    
    today = datetime.now().date()
    dates = []
    load_data = []
    fatigue_data = []
    daily_summaries = []
    
    for i in range(6, -1, -1):
        target_date = today - timedelta(days=i)
        
        # Calculate Team Training Load for this day (Confirmed only)
        logs = TrainingLog.query.filter_by(date=target_date, status='confirmed').all()
        daily_load = summarize_recent_load(logs)
        
        # Calculate Team Average Fatigue for this day
        recovered = RecoveryMetric.query.filter_by(date=target_date).all()
        avg_fatigue = sum([r.morning_fatigue for r in recovered]) / len(recovered) if recovered else 0
        
        # Summary details for team chart
        workout_types = [l.training_type for l in logs]
        top_workout = max(set(workout_types), key=workout_types.count) if workout_types else 'N/A'
        
        dates.append(target_date.strftime('%a'))
        load_data.append(daily_load)
        fatigue_data.append(round(avg_fatigue, 1))
        
        daily_summaries.append({
            'date': target_date.strftime('%A, %b %d'),
            'athletes_trained': len(logs),
            'avg_load': round(daily_load / len(logs), 1) if logs else 0,
            'avg_fatigue': round(avg_fatigue, 1),
            'top_workout': top_workout,
            'total_volume': sum([(l.distance or 0) for l in logs])
        })
    
    return jsonify({
        'labels': dates,
        'load': load_data,
        'fatigue': fatigue_data,
        'summaries': daily_summaries
    })


# ─── Auth: Change Password (Athlete) ──────────────────────────────────────────
@api.route('/auth/change-password', methods=['POST'])
def change_password():
    from models import Athlete
    data = request.json or {}
    athlete_id   = session.get('athlete_id')
    current_pwd  = data.get('current_password', '').strip()
    new_pwd      = data.get('new_password', '').strip()
    confirm_pwd  = data.get('confirm_password', '').strip()

    if not athlete_id:
        return jsonify({'error': 'Unauthorized. Please log in as an athlete.'}), 401
    if not current_pwd or not new_pwd or not confirm_pwd:
        return jsonify({'error': 'All fields are required.'}), 400
    if len(new_pwd) < 6:
        return jsonify({'error': 'New password must be at least 6 characters.'}), 400
    if new_pwd != confirm_pwd:
        return jsonify({'error': 'New password and confirmation do not match.'}), 400

    athlete = Athlete.query.get(athlete_id)
    if not athlete:
        return jsonify({'error': 'Athlete not found.'}), 404
    if not athlete.password_hash or not check_password_hash(athlete.password_hash, current_pwd):
        return jsonify({'error': 'Current password is incorrect.'}), 403

    athlete.password_hash = generate_password_hash(new_pwd)
    db.session.commit()
    return jsonify({'message': 'Password updated successfully!'}), 200


# ─── Coach: Reset Athlete Password ────────────────────────────────────────────
@api.route('/athletes/<int:athlete_id>/reset-password', methods=['POST'])
def reset_athlete_password(athlete_id):
    from models import Athlete
    if session.get('role') != 'coach':
        return jsonify({'error': 'Unauthorized. Coach access required.'}), 401
    athlete = Athlete.query.get_or_404(athlete_id)
    new_pwd = 'athlete123'
    athlete.password_hash = generate_password_hash(new_pwd)
    db.session.commit()
    return jsonify({'message': f"Password for {athlete.name} has been reset to: {new_pwd}"}), 200

# ─── Approval Endpoints ──────────────────────────────────────────────────────

@api.route('/training/confirm/<int:log_id>', methods=['POST'])
def confirm_training_log(log_id):
    if session.get('role') != 'coach':
        return jsonify({'error': 'Unauthorized'}), 403
    from models import TrainingLog
    log = TrainingLog.query.get_or_404(log_id)
    log.status = 'confirmed'
    db.session.commit()
    return jsonify({'message': 'Training log confirmed'})

@api.route('/training/confirm-all', methods=['POST'])
def confirm_all_training():
    if session.get('role') != 'coach':
        return jsonify({'error': 'Unauthorized'}), 403
    from models import TrainingLog
    athlete_id = request.json.get('athlete_id') if request.is_json else None
    query = TrainingLog.query.filter_by(status='pending')
    if athlete_id:
        query = query.filter_by(athlete_id=athlete_id)
    
    count = query.update({TrainingLog.status: 'confirmed'})
    db.session.commit()
    return jsonify({'message': f'{count} training logs confirmed'})

@api.route('/perf_result/confirm/<int:result_id>', methods=['POST'])
def confirm_performance_result(result_id):
    if session.get('role') != 'coach':
        return jsonify({'error': 'Unauthorized'}), 403
    from models import PerformanceResult
    res = PerformanceResult.query.get_or_404(result_id)
    res.status = 'confirmed'
    db.session.commit()
    return jsonify({'message': 'Performance result confirmed'})

@api.route('/perf_result/confirm-all', methods=['POST'])
def confirm_all_results():
    if session.get('role') != 'coach':
        return jsonify({'error': 'Unauthorized'}), 403
    from models import PerformanceResult
    athlete_id = request.json.get('athlete_id') if request.is_json else None
    query = PerformanceResult.query.filter_by(status='pending')
    if athlete_id:
        query = query.filter_by(athlete_id=athlete_id)
        
    count = query.update({PerformanceResult.status: 'confirmed'})
    db.session.commit()
    return jsonify({'message': f'{count} performance results confirmed'})
@api.route('/approvals/training', methods=['GET'])
def get_pending_training():
    from models import TrainingLog, Athlete
    logs = db.session.query(TrainingLog, Athlete).join(Athlete).filter(TrainingLog.status == 'pending').order_by(TrainingLog.date.desc()).all()
    return jsonify({
        'logs': [{
            'id': l.id,
            'athlete_name': a.name,
            'date': l.date.strftime('%Y-%m-%d'),
            'type': l.training_type,
            'distance': l.distance,
            'duration': l.duration,
            'intensity': l.intensity,
            'load': l.intensity * l.duration
        } for l, a in logs]
    })

@api.route('/approvals/results', methods=['GET'])
def get_pending_results():
    from models import PerformanceResult, Athlete
    results = db.session.query(PerformanceResult, Athlete).join(Athlete).filter(PerformanceResult.status == 'pending').order_by(PerformanceResult.date.desc()).all()
    return jsonify({
        'results': [{
            'id': r.id,
            'athlete_name': a.name,
            'date': r.date.strftime('%Y-%m-%d'),
            'event': r.event,
            'value': f"{r.time_seconds}s" if r.time_seconds else f"{r.distance_meters}m",
            'competition': r.competition_name
        } for r, a in results]
    })

@api.route('/approvals/count', methods=['GET'])
def get_pending_count():
    from models import TrainingLog, PerformanceResult
    count = TrainingLog.query.filter_by(status='pending').count() + \
            PerformanceResult.query.filter_by(status='pending').count()
    return jsonify({'count': count})
