import json
import glob
from statistics import mean
from pathlib import Path

print("ISSUE DETECTION")
print("=" * 70)
print("Loading reports from outputs/reports/\n")

reports_dir = Path("outputs/reports")
if not reports_dir.exists() or not any(reports_dir.glob("*.json")):
    print("No reports found.")
    exit()

reports = []
for filepath in glob.glob("outputs/reports/*.json"):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        history = data.get("full_history", [])
        steps = len(history)
        success = data["success"]
        time_sec = round(data.get("total_time_seconds", 0), 1)

        # Calculate issues
        retries = sum(1 for h in history if not h.get("success", True))
        scrolls = sum(1 for h in history if h["action"] == "SCROLL")
        backtracks = sum(1 for h in history if "back" in h.get("reasoning", "").lower())

        auto_issues = []
        if not success:
            auto_issues.append("TASK FAILED")
        if steps > 35:
            auto_issues.append(f"EXCESSIVE STEPS ({steps})")
        if retries >= 4:
            auto_issues.append(f"HIGH RETRIES ({retries})")
        if scrolls >= 6:
            auto_issues.append(f"EXCESSIVE SCROLLING ({scrolls} times)")
        if backtracks >= 3:
            auto_issues.append(f"FREQUENT BACKTRACKING ({backtracks})")

        reports.append({
            "task": data["task"],
            "success": success,
            "steps": steps,
            "time_sec": time_sec,
            "retry_count": retries,
            "scroll_count": scrolls,
            "backtrack_count": backtracks,
            "auto_issues": auto_issues,
            "video": data.get("video_path", "No video saved"),
            "report_file": Path(filepath).name
        })
    except Exception as e:
        print(f"Warning: Could not load {filepath}: {e}")

if not reports:
    print("No valid reports loaded.")
    exit()

# Overall Statistics
success_rate = sum(r["success"] for r in reports) / len(reports)
avg_steps = mean(r["steps"] for r in reports)
avg_time = mean(r["time_sec"] for r in reports)
avg_retries = mean(r["retry_count"] for r in reports)

print(f"OVERALL RESULTS ({len(reports)} tasks completed)\n")
print(f"Task Success Rate:     {success_rate:.1%}")
print(f"Average Steps Taken:   {avg_steps:.1f}")
print(f"Average Time:          {avg_time:.1f} seconds")
print(f"Average Retries/Task:  {avg_retries:.2f}\n")

# Summary
all_issues = [issue for r in reports for issue in r["auto_issues"]]
if all_issues:
    from collections import Counter
    issue_counts = Counter(all_issues)
    print("MOST COMMON AUTOMATICALLY DETECTED ISSUES")
    for issue, count in issue_counts.most_common():
        print(f" -{issue}: {count} tasks")
    print()

#Top 15 worst tasks
print("Top 15\n")
sorted_by_severity = sorted(
    reports,
    key=lambda x: (
        not x["success"],           # failed tasks first
        x["steps"],                 # then most steps
        x["retry_count"],           # then most retries
        x["scroll_count"],
        x["time_sec"]
    ),
    reverse=True
)

for i, r in enumerate(sorted_by_severity[:15], 1):
    status = "FAILED" if not r["success"] else "HIGH EFFORT"
    print(f"{i:2}. {status} — {r['task']}")
    print(f"     Steps: {r['steps']} | Retries: {r['retry_count']} | Scrolls: {r['scroll_count']} | Time: {r['time_sec']}s")
    if r["auto_issues"]:
        print(f"Auto-detected: {', '.join(r['auto_issues'])}")
    print(f"Video: {r['video']}")
    print(f"Report: {r['report_file']}")
    print()
