import re
import json

ACTION_PRIORITY = [
    "DOUBLE_CLICK", "LONG_PRESS", "PRESS_ENTER",
    "CLICK", "HOVER", "DRAG", "SCROLL", "TYPE",
    "COMPLETE", "FAIL"
]

ACTION_PATTERNS = {
    "DOUBLE_CLICK": r'\bdouble[\s_-]?click\b',
    "LONG_PRESS":   r'\blong[\s_-]?press\b',
    "PRESS_ENTER":  r'\bpress[\s_-]?enter\b',
    "CLICK":        r'\bclick\b',
    "HOVER":        r'\bhover\b',
    "DRAG":         r'\bdrag\b',
    "SCROLL":       r'\bscroll\b',
    "TYPE":         r'\btype\b',
    "COMPLETE":     r'\bcomplete\b',
    "FAIL":         r'\bfail\b',
}


class ResponseParser:
    def __init__(self, screen_w: int = 1280, screen_h: int = 720):
        self.screen_w = screen_w
        self.screen_h = screen_h

    def parse(self, text: str) -> dict | None:
        result = self._try_parse_json(text)
        if result:
            return result
        return self._extract_from_prose(text)


    def _try_parse_json(self, text: str) -> dict | None:
        # Find all {...} blocks and try from last to first
        matches = list(re.finditer(r'\{[^{}]*\}', text, re.DOTALL))
        for match in reversed(matches):
            try:
                data = json.loads(match.group())
                if "action" in data:
                    return self._normalize_json_action(data)
            except json.JSONDecodeError:
                continue
        return None

    def _normalize_json_action(self, data: dict) -> dict | None:
        action = data.get("action", "").upper()
        data["action"] = action

        # Normalize x,y coordinates if present
        for x_key, y_key in [("x", "y"), ("from_x", "from_y"), ("to_x", "to_y")]:
            if x_key in data and y_key in data:
                data[x_key], data[y_key] = self._normalize_coords(
                    float(data[x_key]), float(data[y_key])
                )
        return data




    def _extract_from_prose(self, text: str) -> dict | None:
        action = self._extract_action(text)
        if not action:
            return None

        reasoning = self._extract_reasoning(text)

        if action == "COMPLETE":
            return {"action": "COMPLETE"}

        if action == "FAIL":
            return {"action": "FAIL"}

        if action == "TYPE":
            typed = self._extract_typed_text(text)
            if not typed:
                return None
            return {"action": "TYPE", "text": typed, "reasoning": reasoning}

        if action == "SCROLL":
            direction, amount = self._extract_scroll_info(text)
            return {"action": "SCROLL", "direction": direction, "amount": amount, "reasoning": reasoning}

        if action == "DRAG":
            return self._extract_drag(text, reasoning)

        if action == "LONG_PRESS":
            coords = self._extract_last_coordinates(text)
            if not coords:
                return None
            return {
                "action": "LONG_PRESS",
                "x": coords[0], "y": coords[1],
                "duration_ms": self._extract_duration_ms(text),
                "reasoning": reasoning
            }

        # CLICK, DOUBLE_CLICK, HOVER, PRESS_ENTER
        coords = self._extract_last_coordinates(text)
        if not coords:
            return None
        return {"action": action, "x": coords[0], "y": coords[1], "reasoning": reasoning}

   

    def _extract_action(self, text: str) -> str | None:
        t = text.lower()
        for action in ACTION_PRIORITY:
            if re.search(ACTION_PATTERNS[action], t):
                return action
        return None

    def _extract_last_coordinates(self, text: str) -> tuple[float, float] | None:
        matches = re.findall(r'\((\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)\)', text)
        if not matches:
            return None
        x, y = float(matches[-1][0]), float(matches[-1][1])
        return self._normalize_coords(x, y)

    def _normalize_coords(self, x: float, y: float) -> tuple[float, float]:
        if x > 1 or y > 1:
            x, y = x / self.screen_w, y / self.screen_h
        return round(x, 4), round(y, 4)

    def _extract_reasoning(self, text: str) -> str:
        for marker in ["therefore", "because", "reasoning:", "thus", "so,"]:
            idx = text.lower().rfind(marker)
            if idx != -1:
                return text[idx:].strip().rstrip(".")
        lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
        return lines[-1] if lines else ""

    def _extract_typed_text(self, text: str) -> str | None:
        match = re.search(r'["\'](.+?)["\']', text)
        if match:
            return match.group(1)
        match = re.search(r'typ(?:e|ing)\s+(.+?)(?:\.|$)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _extract_scroll_info(self, text: str) -> tuple[str, int]:
        direction = "down"
        for d in ["up", "down", "left", "right"]:
            if d in text.lower():
                direction = d
                break
        amounts = re.findall(r'\b(\d+)\s*(?:pixels?|px|steps?|units?)?\b', text.lower())
        amount = int(amounts[-1]) if amounts else 3
        return direction, amount

    def _extract_drag(self, text: str, reasoning: str) -> dict | None:
        matches = re.findall(r'\((\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)\)', text)
        if len(matches) < 2:
            return None
        fx, fy = self._normalize_coords(float(matches[-2][0]), float(matches[-2][1]))
        tx, ty = self._normalize_coords(float(matches[-1][0]), float(matches[-1][1]))
        return {"action": "DRAG", "from_x": fx, "from_y": fy, "to_x": tx, "to_y": ty, "reasoning": reasoning}

    def _extract_duration_ms(self, text: str) -> int:
        match = re.search(r'(\d+)\s*ms', text.lower())
        if match:
            return int(match.group(1))
        match = re.search(r'(\d+(?:\.\d+)?)\s*s(?:ec)?', text.lower())
        if match:
            return int(float(match.group(1)) * 1000)
        return 1000