import app, models
with app.app.app_context():
    r = models.PerformanceResult.query.filter_by(athlete_id=2, event='100m Sprint').first()
    if r:
        print(f"Miguel Result Found: {r.time_seconds}s at {r.competition_name}")
    else:
        print("No result found for Miguel Rivera in 100m Sprint.")
