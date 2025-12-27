from abc import ABC, abstractmethod
from typing import List, Dict, Any
import time

class BaseAgent(ABC):
    def __init__(self, task: str, max_steps: int = 25):
        self.task = task
        self.max_steps = max_steps
        self.history: List[Dict[str, Any]] = []
        self.start_time = time.time()
        self.repeat_count = 0

    @abstractmethod
    def get_next_action(self, screenshot_path: str) -> Dict[str, Any]:
        pass

    def log_step(self, step: int, action: Dict, screenshot_path: str, success: bool = True):
        entry = {
            "step": step,
            "action": action.get("action", "UNKNOWN"),
            "reasoning": action.get("reasoning", ""),
            "screenshot": screenshot_path,
            "success": success,
            "timestamp": time.time() - self.start_time
        }
        self.history.append(entry)

        # Loop detection
        if len(self.history) >= 4:
            recent_actions = [h["action"] for h in self.history[-4:]]
            if len(set(recent_actions)) == 1:
                self.repeat_count += 1
                if self.repeat_count >= 3:
                    return {"action": "FAIL", "reasoning": "Detected infinite loop (same action repeated)"}
            else:
                self.repeat_count = 0
        return None