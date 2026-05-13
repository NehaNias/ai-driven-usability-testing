from abc import ABC, abstractmethod
from typing import List, Dict, Any
import time

class BaseAgent(ABC):
    def __init__(self, task: str, max_steps: int = 35):
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
        return None
