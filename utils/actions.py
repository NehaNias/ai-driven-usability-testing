from playwright.sync_api import Page

def execute_action(page: Page, action: dict):
    try:
        act = action["action"]

        # Convert coordinates (0–1 normalized values or raw pixels)
        def to_pixels(v, axis: str):
            if v <= 1.0:
                size = page.viewport_size["width"] if axis == "x" else page.viewport_size["height"]
                return int(v * size)
            return int(v)  # already in pixels

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
            amount = action.get("amount", 500)
            direction = -amount if "up" in action.get("reasoning", "").lower() else amount
            page.mouse.wheel(0, direction)

        elif act == "PRESS_ENTER":
            page.keyboard.press("Enter")

        else:
            print(f"Warning: Unknown action: {act}")

    except Exception as e:
        print(f"Action execution failed: {e}")