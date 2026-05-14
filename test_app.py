import requests
import time
import sys

BASE_URL = "http://127.0.0.1:5000"

endpoints = [
    "/",
    "/api/athletes",
    "/api/analytics/dashboard",
    "/api/analytics/trend/100m",
    "/api/analytics/load_fatigue",
    "/athlete/1",
    "/api/analytics/athlete/1"
]

def test_endpoints():
    print("Testing GET endpoints...")
    all_passed = True
    for ep in endpoints:
        url = BASE_URL + ep
        try:
            res = requests.get(url)
            if res.status_code == 200:
                print(f"[OK] GET {ep}")
            else:
                print(f"[FAILED] GET {ep} - Status Code: {res.status_code}")
                all_passed = False
        except Exception as e:
            print(f"Error GET {ep}: {e}")
            all_passed = False
            
    print("\nTesting POST endpoints...")
    # Test Athlete Add
    try:
        a_res = requests.post(BASE_URL + "/api/athlete", json={"name": "Test Runner", "event": "100m Sprint"})
        if a_res.status_code == 201:
            print(f"[OK] POST /api/athlete")
            athlete_id = a_res.json()['id']
            
            # Test Training Add
            t_res = requests.post(BASE_URL + "/api/training", json={
                "athlete_id": athlete_id, "date": "2026-03-13", "training_type": "Track",
                "distance": 1000, "duration": 60, "intensity": 8, "fatigue": 5
            })
            if t_res.status_code == 201: print(f"[OK] POST /api/training")
            else: print(f"[FAILED] POST /api/training: {t_res.text}"); all_passed = False

            # Test Wellness Add
            w_res = requests.post(BASE_URL + "/api/wellness", json={
                "athlete_id": athlete_id, "date": "2026-03-13", "sleep_hours": 8,
                "morning_fatigue": 3, "soreness": 2, "stress_level": 4
            })
            if w_res.status_code == 201: print(f"[OK] POST /api/wellness")
            else: print(f"[FAILED] POST /api/wellness: {w_res.text}"); all_passed = False
        else:
            print(f"[FAILED] POST /api/athlete: {a_res.text}")
            all_passed = False
    except Exception as e:
        print(f"POST Error: {e}")
        all_passed = False
            
    return all_passed

if __name__ == "__main__":
    if test_endpoints():
        print("\nAll endpoints working perfectly!")
        sys.exit(0)
    else:
        print("\nSome endpoints failed.")
        sys.exit(1)
