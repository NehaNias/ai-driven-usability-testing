from typing import List, Dict

class UsabilityMetrics:
    def __init__(self, history: List[Dict]):
        self.history = history
        self.success = any(h["action"] == "COMPLETE" for h in history)
        self.steps = len(history)

    def summary(self) -> dict:
        retries = sum(1 for h in self.history if "fail" in h["reasoning"].lower() or not h["success"])
        backtracks = sum(1 for h in self.history if "back" in h["reasoning"].lower())
        return {
            "task_success": 1.0 if self.success else 0.0,
            "steps_taken": self.steps,
            "retry_rate": round(retries / max(self.steps, 1), 3),
            "backtrack_rate": round(backtracks / max(self.steps, 1), 3),
            "total_time_sec": round(self.history[-1]["timestamp"] if self.history else 0, 1),
            "final_action": self.history[-1]["action"] if self.history else "N/A"
        }