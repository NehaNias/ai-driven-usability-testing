import json
import os
import pandas as pd

results = []
report_dir = "outputs/reports"

for filename in os.listdir(report_dir):
    if not filename.endswith(".json"):
        continue
    with open(os.path.join(report_dir, filename)) as f:
        report = json.load(f)
    
    history = report.get("full_history", [])
    retries = sum(1 for h in history if not h.get("success", True))
    
    # Termination reason
    if report.get("success"):
        termination = "COMPLETE"
    elif report.get("steps_taken", 0) >= 35:
        termination = "MAX STEPS"
    else:
        termination = "FAIL"

    results.append({
        "task": report["task"],
        "success": report["success"],
        "steps_taken": report["steps_taken"],
        "time_seconds": report["total_time_seconds"],
        "retries": retries,
        "termination": termination
    })

df = pd.DataFrame(results)
print(df.to_string())
print(f"\nCompletion rate: {df['success'].mean():.1%}")
print(f"Average steps:  {df['steps_taken'].mean():.1f}")
print(f"Average time:   {df['time_seconds'].mean():.1f}s")
print(f"Average retries:{df['retries'].mean():.1f}")