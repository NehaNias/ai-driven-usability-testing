from playwright.sync_api import Page

def execute_action(page: Page, action: dict):
    try:
        act = action["action"]

        if isinstance(action.get("x"), list) and len(action["x"]) == 2 and action.get("y") is None:
            action["y"] = action["x"][1]
            action["x"] = action["x"][0]

        def to_pixels(v, axis: str):
            if isinstance(v, list):
                v = v[0]
            if v <= 1.0:
                size = page.viewport_size["width"] if axis == "x" else page.viewport_size["height"]
                return int(v * size)
            return int(v)  

        x_px = to_pixels(action.get("x", 0), "x")
        y_px = to_pixels(action.get("y", 0), "y")

        if act == "CLICK":
            page.mouse.click(x_px, y_px)

        elif act == "DOUBLE_CLICK":
            page.mouse.dblclick(x_px, y_px)

        elif act == "HOVER":
            page.mouse.move(x_px, y_px)

        elif act == "DRAG":
            to_x_px = to_pixels(action["to_x"], "x")
            to_y_px = to_pixels(action["to_y"], "y")
            page.mouse.move(x_px, y_px)
            page.mouse.down()
            page.mouse.move(to_x_px, to_y_px)
            page.mouse.up()

        elif act == "LONG_PRESS":
            duration_ms = action.get("duration_ms", 800)
            page.mouse.move(x_px, y_px)
            page.mouse.down()
            page.wait_for_timeout(duration_ms)
            page.mouse.up()

        elif act == "TYPE":
            text = action.get("text", "")
            page.keyboard.type(text)

        elif act == "SCROLL":
            amount = 600 #action.get("amount", 500)
            direction = action.get("direction", "down").lower()
            #direction = -amount if "up" in action.get("reasoning", "").lower() else amount

            """if amount <= 1.0:
                amount = amount * page.viewport_size["height"]
            else:
                amount = amount * 300"""

            dx, dy = 0, amount
            if direction == "up":    dy = -amount
            elif direction == "left":  dx, dy = -amount, 0
            elif direction == "right": dx, dy =  amount, 0

            page.mouse.wheel(dx, dy)
            page.wait_for_timeout(500)

        elif act == "PRESS_ENTER":
            page.keyboard.press("Enter")

        else:
            print(f"Warning: Unknown action: {act}")

    except Exception as e:
        print(f"Action execution failed: {e}")