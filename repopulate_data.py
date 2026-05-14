"""
repopulate_data.py
Clears existing logs and repopulates them correctly (time vs distance based on actual event names).
"""
import random
import json
from datetime import datetime, timedelta
from app import app, db
from models import Athlete, TrainingLog, PerformanceResult, RecoveryMetric
from seed import get_phase, gen_acwr_intensity, make_created_at_wellness, make_created_at_training

def is_distance_event(event_name):
    event_name = event_name.lower()
    if any(x in event_name for x in ['jump', 'throw', 'put', 'vault', 'discus', 'javelin']):
        return True
    return False

def get_event_benchmark(event_name):
    # Try to map common strings to benchmarks
    ev_lower = event_name.lower()
    
    if '100m' in ev_lower and 'hurdles' not in ev_lower: return {'type': 'time', 'range': (10.4, 11.8)}
    if '200m' in ev_lower: return {'type': 'time', 'range': (21.2, 24.5)}
    if '400m' in ev_lower and 'hurdles' not in ev_lower: return {'type': 'time', 'range': (47.5, 53.0)}
    if '110mh' in ev_lower or ('110m' in ev_lower and 'hurdles' in ev_lower): return {'type': 'time', 'range': (14.2, 16.5)}
    if '400mh' in ev_lower or ('400m' in ev_lower and 'hurdles' in ev_lower): return {'type': 'time', 'range': (51.0, 58.5)}
    if '800m' in ev_lower: return {'type': 'time', 'range': (110.0, 135.0)}
    if '1500m' in ev_lower: return {'type': 'time', 'range': (235.0, 280.0)}
    if '3k' in ev_lower or '3000m' in ev_lower: return {'type': 'time', 'range': (520.0, 600.0)}
    if '5k' in ev_lower or '5000m' in ev_lower: return {'type': 'time', 'range': (880.0, 1050.0)}
    if 'long jump' in ev_lower: return {'type': 'dist', 'range': (6.50, 7.80)}
    if 'high jump' in ev_lower: return {'type': 'dist', 'range': (1.90, 2.20)}
    if 'triple jump' in ev_lower: return {'type': 'dist', 'range': (14.0, 16.5)}
    if 'pole vault' in ev_lower: return {'type': 'dist', 'range': (4.50, 5.80)}
    if 'javelin' in ev_lower: return {'type': 'dist', 'range': (58.0, 75.0)}
    if 'discus' in ev_lower: return {'type': 'dist', 'range': (42.0, 58.0)}
    if 'shot put' in ev_lower: return {'type': 'dist', 'range': (13.5, 18.0)}
    if 'hammer' in ev_lower: return {'type': 'dist', 'range': (50.0, 70.0)}
    
    # Generic fallback based on name
    if is_distance_event(event_name):
        return {'type': 'dist', 'range': (5.0, 20.0)}
    else:
        return {'type': 'time', 'range': (12.0, 60.0)}

def repopulate():
    with app.app_context():
        # Clear data
        db.session.query(TrainingLog).delete()
        db.session.query(PerformanceResult).delete()
        db.session.query(RecoveryMetric).delete()
        db.session.commit()
        
        athletes = Athlete.query.all()
        if not athletes:
            print("No athletes found. Seeding initial athletes first...")
            from seed import generate_mock_data
            generate_mock_data()
            athletes = Athlete.query.all()
            if not athletes:
                print("Failed to seed athletes. Exiting.")
                return
            
        print(f"Repopulating 6-month data for {len(athletes)} existing athletes...")

        start_date = datetime.now() - timedelta(days=180)
        logs_count = 0
        perf_count = 0
        rec_count  = 0

        for athlete in athletes:
            events = [e.strip() for e in athlete.event.split(',') if e.strip()]
            if not events: events = ['100m Sprint']
            
            baselines = {}
            for ev in events:
                meta = get_event_benchmark(ev)
                lo, hi = meta['range']
                baselines[ev] = random.uniform(lo, hi)

            for day in range(181):
                current_date = (start_date + timedelta(days=day)).date()
                phase        = get_phase(day)
                weekday      = current_date.weekday()

                # WELLNESS
                wellness_ts = make_created_at_wellness(current_date)
                fatigue_base = 3 if day % 4 == 0 else 1
                
                if phase in ('General Preparation', 'Specific Preparation'):
                    sleep_h, sq = round(random.uniform(7.5, 9.2), 1), random.randint(5, 7)
                    fatigue, sore = min(7, random.randint(1, 3) + fatigue_base), min(7, random.randint(1, 3) + (fatigue_base // 2))
                    stress, motiv = random.randint(1, 3), random.randint(5, 7)
                elif phase in ('Pre-Competition', 'Competition'):
                    sleep_h, sq = round(random.uniform(7.0, 8.8), 1), random.randint(4, 7)
                    fatigue, sore = min(7, random.randint(2, 4) + fatigue_base), min(7, random.randint(2, 4) + (fatigue_base // 2))
                    stress, motiv = random.randint(3, 6), random.randint(6, 7)
                else: 
                    sleep_h, sq = round(random.uniform(8.2, 10.0), 1), random.randint(6, 7)
                    fatigue, sore = random.randint(1, 2), random.randint(1, 2)
                    stress, motiv = random.randint(1, 4), random.randint(4, 7)

                rec = RecoveryMetric(
                    athlete_id=athlete.id, date=current_date, sleep_hours=sleep_h, sleep_quality=sq,
                    morning_fatigue=fatigue, soreness=sore, stress_level=stress, motivation=motiv, created_at=wellness_ts
                )
                db.session.add(rec)
                rec_count += 1

                # TRAINING
                if weekday < 6:
                    focus_event = random.choice(events)
                    meta = get_event_benchmark(focus_event)
                    intensity = gen_acwr_intensity(day)

                    if phase == 'Transition/Taper': session_type = random.choices(['Track', 'Active Recovery'], weights=[0.4, 0.6])[0]
                    elif day % 7 in (1, 4): session_type = 'Weight Room'
                    else: session_type = 'Track'

                    duration = random.randint(45, 130)
                    distance = round(random.uniform(500, 2000)) if session_type == 'Track' else 0.0
                    tonnage = float(random.randint(3, 6) * random.randint(4, 10) * random.randint(40, 110)) if session_type == 'Weight Room' else 0.0

                    main_set = "Training Details"
                    log = TrainingLog(
                        athlete_id=athlete.id, date=current_date, training_type=session_type, training_phase=phase,
                        distance=distance, tonnage=tonnage, duration=duration, intensity=intensity,
                        fatigue_post_workout=min(10, intensity + random.randint(0, 2)), warmup_notes="Standard Warmup",
                        main_set_details=main_set, created_at=make_created_at_training(current_date)
                    )
                    db.session.add(log)
                    logs_count += 1

                # PERFORMANCE
                if day > 0 and day % 28 == 0:
                    for ev in events:
                        meta = get_event_benchmark(ev)
                        lo, hi = meta['range']
                        base = baselines[ev]
                        improvement = (day / 180) * random.uniform(0.02, 0.05)
                        
                        is_time = meta['type'] == 'time'

                        if is_time:
                            val = round(base * (1 - improvement) + random.uniform(-0.03, 0.03), 2)
                            val = max(lo, min(hi, val))
                        else:
                            val = round(base * (1 + improvement) + random.uniform(-0.03, 0.03), 2)
                            val = max(lo, min(hi, val))

                        perf = PerformanceResult(
                            athlete_id=athlete.id, date=current_date, event=ev,
                            time_seconds=val if is_time else 0.0,
                            distance_meters=0.0 if is_time else val,
                            rank=random.randint(1, 5), competition_name=f"Assessment Meet Cycle {day // 28}",
                            created_at=datetime.combine(current_date, datetime.min.time()).replace(hour=14, minute=random.randint(0, 59))
                        )
                        db.session.add(perf)
                        perf_count += 1

            # Log one main competition today
            today = datetime.now().date()
            for ev in events:
                meta = get_event_benchmark(ev)
                lo, hi = meta['range']
                base = baselines[ev]
                is_time = meta['type'] == 'time'
                val = round(random.uniform(lo, hi), 2)
                perf = PerformanceResult(
                    athlete_id=athlete.id, date=today, event=ev,
                    time_seconds=val if is_time else 0.0,
                    distance_meters=0.0 if is_time else val,
                    rank=random.randint(1, 5), competition_name="National Athletics Championship 2026",
                    created_at=datetime.utcnow()
                )
                db.session.add(perf)
                perf_count += 1

        db.session.commit()
        print(f"[OK] Repopulated {logs_count} logs, {rec_count} wellness, {perf_count} performances.")

if __name__ == '__main__':
    repopulate()
