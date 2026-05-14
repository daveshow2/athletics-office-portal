import os
from app import app
from database import db
from models import Athlete, TrainingLog, PerformanceResult, RecoveryMetric

def clear_all_athlete_data():
    """
    Safely deletes all data related to athletes and their logs.
    Keep the database structure intact.
    """
    with app.app_context():
        try:
            print("Cleaning up training logs...")
            db.session.query(TrainingLog).delete()
            
            print("Cleaning up performance results...")
            db.session.query(PerformanceResult).delete()
            
            print("Cleaning up recovery metrics...")
            db.session.query(RecoveryMetric).delete()
            
            print("Cleaning up athletes...")
            db.session.query(Athlete).delete()
            
            db.session.commit()
            print("Successfully cleared all athlete data.")
        except Exception as e:
            db.session.rollback()
            print(f"Error during cleanup: {str(e)}")

if __name__ == "__main__":
    confirm = input("Are you sure you want to delete ALL athlete records and their history? This cannot be undone. (y/n): ")
    if confirm.lower() == 'y':
        clear_all_athlete_data()
    else:
        print("Cleanup cancelled.")
