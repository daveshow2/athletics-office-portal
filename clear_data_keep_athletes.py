from app import app
from database import db
from models import TrainingLog, PerformanceResult, RecoveryMetric

with app.app_context():
    db.session.query(TrainingLog).delete()
    db.session.query(PerformanceResult).delete()
    db.session.query(RecoveryMetric).delete()
    db.session.commit()
    print("Records cleared except athletes")
