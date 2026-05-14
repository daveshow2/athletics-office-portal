import app, models
with app.app.app_context():
    athletes = models.Athlete.query.all()
    for a in athletes[:10]:
        print(f"{a.id}: {a.name} ({a.event})")
