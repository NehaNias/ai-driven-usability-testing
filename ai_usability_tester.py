import base64
import json
import time
import requests
from PIL import Image
import io
from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv

# Load environment variables (if needed for other APIs later)
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def get_ai_action(screenshot_path, user_task, previous_actions, max_retries=3):
    """Sends the screenshot and task to mlvoca.com's DeepSeek R1 and returns the next action."""
    # Check if screenshot exists
    if not os.path.exists(screenshot_path):
        print(f"Error: Screenshot not found at {screenshot_path}")
        return {"action": "FAIL", "reasoning": f"Screenshot file missing at {screenshot_path}"}
    
    # Resize image to reduce processing time
    try:
        img = Image.open(screenshot_path)
        #img = img.resize((800, 450))  # Optimize for faster processing
        screenshot_width, screenshot_height = img.size
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"Error processing screenshot: {e}")
        return {"action": "FAIL", "reasoning": f"Failed to process screenshot: {e}"}
    
    # Prepare the conversation history
    conversation_history = ""
    for action in previous_actions[-3:]:  # Reduced to 3 for efficiency
        conversation_history += f"Previous action taken: {action}\n"
    
    # Create the prompt
    prompt = f"""
    You are an AI usability testing agent controlling a web browser via screenshots. Your goal is to complete the user's task step-by-step on this given webpage (starting at https://www.amazon.com). Respond with a valid JSON object specifying the *next single action* to progress toward the task. Study the page, look for any buttons or icons that help towards achieving the task. Again, specify one single action that has to be done next, like typing, or clicking, or scrolling using JSON commands below


    TASK: {user_task}

    
        Respond ONLY with a JSON object in this exact format, with no other text, tags (e.g., no <think>), or explanations.

        For each step, choose the most appropriate action from the following options:

        1. Identify clickable elements by visual position only.
        2. Look for text like: "Search", "Go", "Add to Cart", "Buy Now", filters, etc.
        3. Estimate where the coordinates of the area is in the image ({screenshot_width}×{screenshot_height}) according to the reasoning.
        4. For CLICK you **MUST** include `x` and `y` in the JSON.
        5. For TYPE you **MUST** include `text` in the JSON of the text to type.
        5. The response must be in the following format, as an **example**. Do NOT copy this example exactly:
    {{
        "action": <your-action>,
        "x": <your-x>,
        "y": <your-y>,
        "reasoning": "<your short reasoning>"
    }}

        6. The "action" field must be one of: ["CLICK", "TYPE", "SCROLL", "PRESS_ENTER", "COMPLETE", "FAIL"]
    {conversation_history}
    """
    
    # Retry API call up to max_retries
    for attempt in range(max_retries):
        try:
            response = requests.post(
                #"http://192.168.137.1:11434/api/chat",
                "http://localhost:11434/api/chat",
                json={
                    "model": "qwen3-vl:latest",
                    "messages": [
                        {"role": "user", "content": prompt},
                        {"role": "user", "content": "", "images": [base64_image]}
                    ],
                    "stream": False
                }
            )
            response.raise_for_status()
            response_data = response.json()
            response_text = response_data.get("message", {}).get("content", "")
            print(f"Raw AI response (attempt {attempt + 1}): {response_text}")

            # Strip out non-JSON content
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx == -1 or end_idx == 0:
                print(f"No valid JSON found in response: {response_text}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return {"action": "FAIL", "reasoning": f"No valid JSON found after {max_retries} attempts"}
            json_str = response_text[start_idx:end_idx]

            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON (attempt {attempt + 1}): {json_str}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return {"action": "FAIL", "reasoning": f"Could not parse JSON after {max_retries} attempts: {e}"}
        except requests.RequestException as e:
            print(f"API request failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait before retrying
                continue
            return {"action": "FAIL", "reasoning": f"API request failed after {max_retries} attempts: {e}"}
    
    return {"action": "FAIL", "reasoning": f"No valid response after {max_retries} attempts"}

def run_usability_test(task_description, start_url, max_steps=15):
    """Main function that runs the automated usability test."""
    action_history = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Headless for efficiency
        context = browser.new_context(
            viewport={'width': 1280, 'height': 720},
            record_video_dir="usability_videos/",
        )
        page = context.new_page()
        page.goto(start_url)
        page.wait_for_timeout(3000)
        os.makedirs("screenshots", exist_ok=True)
        print(f"\nStarting usability test: '{task_description}'")
        print("=" * 50)
        
        for step in range(1, max_steps + 1):
            print(f"\n--- Step {step} ---")
            screenshot_path = f"screenshots/step_{step}.png"
            try:
                page.screenshot(path=screenshot_path)
                print(f"Screenshot saved at {screenshot_path}")
            except Exception as e:
                print(f"Error saving screenshot: {e}")
                action_history.append(f"Screenshot Error: {e}")
                break
            
            print("Consulting AI for next action...")
            time.sleep(2)  # Delay to avoid overwhelming the server
            next_action = get_ai_action(screenshot_path, task_description, action_history)
            
            action_type = next_action.get("action", "FAIL")
            reasoning = next_action.get("reasoning", "No reasoning provided.")
            print(f"AI Decision: {action_type}")
            print(f"Reasoning: {reasoning}")
            
            # Check for repetitive actions
            if len(action_history) >= 3 and action_history[-3:] == [f"{action_type}: {reasoning}"] * 3:
                print("❌ Task failed: AI is repeating the same action.")
                break
            action_history.append(f"{action_type}: {reasoning}")
            
            if action_type == "COMPLETE":
                print("✅ Task completed successfully!")
                break
            elif action_type == "FAIL":
                print("❌ Task failed.")
                break
            
            try:
                if action_type == "CLICK":
                    selector = next_action.get("selector")
                    # Try to click using the selector first (preferred)
                    '''if selector:
                        try:
                            print(f"Attempting to click element with selector: {selector}")
                            page.click(selector, timeout=3000)
                            print(f"Clicked element with selector: {selector}")
                            action_history.append(f"Clicked selector: {selector}")
                            continue  # Move to next step after successful click
                        except Exception as e:
                            print(f"⚠️ Failed to click selector '{selector}': {e}")
                            action_history.append(f"Failed selector '{selector}', falling back to coordinates.")'''
                    if "x" in next_action and "y" in next_action:
                        x, y = float(next_action["x"]), float(next_action["y"])
                        print(x,y)
                        x = x /1280.0 if x > 1 else x
                        y = y / 720.0 if y > 1 else y
                        if not (0 <= x <= 1 and 0 <= y <= 1):
                            print(f"Invalid coordinates: x={x}, y={y}")
                            action_history.append(f"Invalid coordinates: x={x}, y={y}")
                            continue
                        viewport_size = page.evaluate("() => ({ width: window.innerWidth, height: window.innerHeight })")
                        x_pixels = x * viewport_size["width"]
                        y_pixels = y * viewport_size["height"]
                        page.mouse.click(x_pixels, y_pixels)
                        print(f"Clicked at ({x_pixels:.0f}, {y_pixels:.0f})")
                        action_history.append(f"Clicked coordinates: ({x_pixels:.0f}, {y_pixels:.0f})")
                    else:
                        print("No valid selector or coordinates provided for CLICK.")
                        action_history.append("No valid click target found.")        
                elif action_type == "TYPE":
                    text_to_type = next_action.get("text", "")
                    page.keyboard.type(text_to_type)
                    print(f"Typed: '{text_to_type}'")
                elif action_type == "SCROLL":
                    direction = next_action.get("direction", "down")
                    scroll_amount = next_action.get("amount", 1000) if direction == "down" else -2000
                    page.mouse.wheel(0, scroll_amount)
                    print(f"Scrolled {direction}")
                elif action_type == "PRESS_ENTER":
                    page.keyboard.press("Enter")
                    print("Pressed Enter")
                page.wait_for_timeout(2000)
                page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception as e:
                print(f"Error executing action: {e}")
                action_history.append(f"Execution Error: {e}")
                break
        
        context.close()
        browser.close()
        print("\n" + "=" * 50)
        print("Usability test complete.")
        print(f"Video saved in: usability_videos/")
        print(f"Screenshots saved in: screenshots/")
        print(f"Total steps: {step}")
        print("Action History:")
        for i, action in enumerate(action_history, 1):
            print(f"{i}. {action}")

if __name__ == "__main__":
    YOUR_TASK = "Find a men's waterproof jacket under 100 Euros"
    START_URL = "https://www.amazon.com"
    run_usability_test(YOUR_TASK, START_URL)