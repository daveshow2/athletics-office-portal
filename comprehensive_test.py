import requests
import json
import time
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:5000"

def test_full_athlete_lifecycle():
    print("Starting Phase 6 Comprehensive Lifecycle Test...")
    
    # 1. Register a new athlete
    athlete_data = {
        "name": "Test Athlete QC",
        "event": "100m Sprint",
        "age": 22,
        "height": 180,
        "weight": 75
    }
    resp = requests.post(f"{BASE_URL}/api/athlete", json=athlete_data)
    assert resp.status_code in [200, 201], f"Failed to register: {resp.text}"
    athlete_id = resp.json()['id']
    print(f"[OK] Registered athlete ID: {athlete_id}")

    # 2. Add 30 days of training history to test ACWR
    print("Logging 30 days of training data...")
    start_date = datetime.now() - timedelta(days=30)
    for i in range(30):
        log_date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
        # High intensity for the first 20 days, then moderate
        intensity = 8 if i < 20 else 5
        duration = 90 if i < 20 else 60
        
        log_data = {
            "athlete_id": athlete_id,
            "date": log_date,
            "training_type": "Track",
            "distance": 2000,
            "duration": duration,
            "intensity": intensity,
            "fatigue": intensity # Simulating response
        }
        res = requests.post(f"{BASE_URL}/api/training", json=log_data)
        assert res.status_code == 201, f"Training log failed: {res.text}"
    
    # 3. Add some performance results
    print("Logging performance results...")
    perf_data = {
        "athlete_id": athlete_id,
        "date": (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d'),
        "event": "100m Sprint",
        "time": 11.2,
        "competition": "QC Trial 1"
    }
    res = requests.post(f"{BASE_URL}/api/perf_result", json=perf_data)
    assert res.status_code == 201, f"Perf result 1 failed: {res.text}"
    
    perf_data_latest = {
        "athlete_id": athlete_id,
        "date": (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
        "event": "100m Sprint",
        "time": 10.9,
        "competition": "QC Trial 2"
    }
    res = requests.post(f"{BASE_URL}/api/perf_result", json=perf_data_latest)
    assert res.status_code == 201, f"Perf result 2 failed: {res.text}"

    # 4. Verify Analytics and ML
    print("Verifying analytics and predictions...")
    analytics_resp = requests.get(f"{BASE_URL}/api/analytics/athlete/{athlete_id}")
    assert analytics_resp.status_code == 200
    data = analytics_resp.json()
    
    # Check Prediction
    prediction = data.get('peak_performance', {})
    print(f"Full Peak Data: {prediction}")
    print(f"Predicted Performance: {prediction.get('value')} {prediction.get('unit')}")
    assert prediction.get('value') is not None, f"Peak performance prediction failed. Full response: {json.dumps(data, indent=2)}"
    
    # Check ACWR Risk
    risk_obj = data.get('risk_assessment', {})
    risk = risk_obj.get('level', 'Unknown')
    print(f"Injury Risk Level: {risk}")
    # With the taper (lower intensity at the end), risk should be stabilizing
    assert risk in ["Green Zone", "Optimal Zone", "Moderate Risk", "Critical Risk", "Low Risk"], f"Unexpected risk level: {risk}"
    
    print(f"Recommendation: {risk_obj.get('recommendation')}")
    
    # 5. Check Dashboard Integration
    print("Verifying dashboard integration...")
    dash_resp = requests.get(f"{BASE_URL}/api/analytics/dashboard")
    assert dash_resp.status_code == 200
    dash_data = dash_resp.json()
    
    # Find our athlete in full list
    list_resp = requests.get(f"{BASE_URL}/api/athletes")
    assert list_resp.status_code == 200
    all_athletes = list_resp.json().get('athletes', [])
    found = any(a['name'] == "Test Athlete QC" for a in all_athletes)
    assert found, "Athlete not found in registry"
    
    # Verify stats incremented (at least one athlete exists)
    assert dash_data['stats']['total_athletes'] > 0, "Dashboard stats failed"
    
    print("\n[SUCCESS] Phase 6 Comprehensive Test Passed!")

if __name__ == "__main__":
    try:
        test_full_athlete_lifecycle()
    except Exception as e:
        print(f"\n[FAILED] Test encountered error: {e}")
        exit(1)
