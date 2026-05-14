import sys
sys.path.insert(0, '.')
from app import app
from database import db
from models import TrainingLog, Athlete
import json

print('=== TESTING TRAINING LOG DELETION ===')

with app.app_context():
    from datetime import datetime
    athlete = Athlete.query.first()
    if not athlete:
        print('No athlete found to test with.')
        sys.exit(1)
        
    test_log = TrainingLog(
        athlete_id=athlete.id,
        date=datetime.now().date(),
        training_type='Test Session',
        intensity=5,
        duration=30
    )

    db.session.add(test_log)
    db.session.commit()
    log_id = test_log.id
    print(f'Created test log ID: {log_id}')
    
    # 2. Test the DELETE endpoint
    with app.test_client() as client:
        resp = client.delete(f'/api/training/{log_id}')
        print(f'DELETE /api/training/{log_id} -> Status: {resp.status_code}')
        print(f'Response: {resp.get_data(as_text=True)}')
        
        # 3. Verify deletion
        remaining = TrainingLog.query.get(log_id)
        if remaining is None:
            print('VERIFIED: Log successfully removed from database.')
        else:
            print('ERROR: Log still exists in database!')

print('=== TEST COMPLETE ===')
