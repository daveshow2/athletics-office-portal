"""
verify_audit.py - Audits all 5 data accuracy recommendations against the live DB.
"""
import sqlite3

conn = sqlite3.connect('sports_science.db')
cur = conn.cursor()

# ── 1. Schema Audit ────────────────────────────────────────────────────────────
cur.execute('PRAGMA table_info(training_log)')
tl_cols = [r[1] for r in cur.fetchall()]

cur.execute('PRAGMA table_info(recovery_metric)')
rm_cols = [r[1] for r in cur.fetchall()]

cur.execute('PRAGMA table_info(performance_result)')
pr_cols = [r[1] for r in cur.fetchall()]

print("=" * 60)
print("SCHEMA AUDIT")
print("=" * 60)
print("TrainingLog columns:    ", tl_cols)
print("RecoveryMetric columns: ", rm_cols)
print("PerformanceResult cols: ", pr_cols)

# Rec 1: Smart bounds - check no impossible times exist
cur.execute("SELECT event, time_seconds FROM performance_result WHERE event = '100m Sprint' AND time_seconds IS NOT NULL ORDER BY time_seconds LIMIT 5")
sprint_times = cur.fetchall()
print()
print("REC 1 - Sprint bounds check (should be 9.5-20s):")
for r in sprint_times:
    flag = "  PASS" if 9.5 <= r[1] <= 20.0 else "  FAIL"
    print(f"  {r[0]}: {r[1]}s{flag}")

cur.execute("SELECT event, distance_meters FROM performance_result WHERE event = 'Long Jump' AND distance_meters IS NOT NULL ORDER BY distance_meters LIMIT 5")
jump_rows = cur.fetchall()
print("Long Jump bounds check (should be 4.0-9.0m):")
for r in jump_rows:
    flag = "  PASS" if 4.0 <= r[1] <= 9.0 else "  FAIL"
    print(f"  {r[0]}: {r[1]}m{flag}")

# Rec 2: Event-adaptive (tonnage present for weight room)
cur.execute("SELECT COUNT(*) FROM training_log WHERE training_type='Weight Room' AND tonnage IS NOT NULL AND tonnage > 0")
wr_count = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM training_log WHERE training_type='Weight Room'")
wr_total = cur.fetchone()[0]
print()
print("REC 2 - Weight Room tonnage:")
print(f"  {wr_count}/{wr_total} Weight Room sessions have tonnage data")

# Training phase
cur.execute("SELECT training_phase, COUNT(*) FROM training_log GROUP BY training_phase")
phases = cur.fetchall()
print("  Training Phases in DB:")
for p in phases:
    print(f"    {p[0]}: {p[1]} sessions")

# Rec 3: ACWR - check load values are non-zero and varied
cur.execute("SELECT AVG(duration * intensity), MIN(duration * intensity), MAX(duration * intensity) FROM training_log")
load_stats = cur.fetchone()
print()
print("REC 3 - ACWR Load Stats:")
print(f"  Avg load: {round(load_stats[0],1)}, Min: {load_stats[1]}, Max: {load_stats[2]}")

# Rec 4: Temporal integrity - created_at for wellness should be morning (06:00-07:30)
cur.execute("SELECT date, created_at FROM recovery_metric LIMIT 5")
wellness_ts = cur.fetchall()
print()
print("REC 4 - Wellness temporal integrity (should be morning 06:xx-07:xx):")
for r in wellness_ts:
    ts = r[1]
    hour = int(ts[11:13]) if ts else None
    flag = "  PASS" if hour is not None and 6 <= hour <= 7 else "  FAIL"
    print(f"  date:{r[0]}  submitted:{ts}{flag}")

cur.execute("SELECT date, created_at FROM training_log LIMIT 5")
training_ts = cur.fetchall()
print("Training log temporal integrity (should be 09:xx-17:xx):")
for r in training_ts:
    ts = r[1]
    hour = int(ts[11:13]) if ts else None
    flag = "  PASS" if hour is not None and 9 <= hour <= 17 else "  FAIL"
    print(f"  date:{r[0]}  submitted:{ts}{flag}")

# Rec 5: Nutrition/Hydration
cur.execute("SELECT hydration_quality, nutritional_adherence FROM recovery_metric WHERE hydration_quality IS NOT NULL LIMIT 5")
nh_rows = cur.fetchall()
cur.execute("SELECT COUNT(*) FROM recovery_metric WHERE hydration_quality IS NOT NULL")
nh_count = cur.fetchone()[0]
print()
print("REC 5 - Nutrition/Hydration data:")
print(f"  {nh_count} wellness entries have hydration+nutrition data")
print("  Samples (hydration, nutrition):", nh_rows)

conn.close()
print()
print("Audit complete.")
