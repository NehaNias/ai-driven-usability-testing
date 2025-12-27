from agent.base_agent import BaseAgent
from utils.vision import get_ai_action
from typing import Dict, Any

class ScreenshotAgent(BaseAgent):
    def __init__(self, task: str, model: str = "qwen3-vl:latest", max_steps: int = 25):
        super().__init__(task, max_steps)
        self.model = model

    def get_next_action(self, screenshot_path: str) -> Dict[str, Any]:
        action = get_ai_action(
            screenshot_path=screenshot_path,
            user_task=self.task,
            previous_actions=[h["action"] + ": " + h["reasoning"][:50] for h in self.history[-3:]]
        )
        return action