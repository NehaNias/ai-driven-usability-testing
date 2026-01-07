import base64
import json
import time
import requests
from PIL import Image
import io
import os

def get_ai_action(screenshot_path: str, user_task: str, previous_actions: list, max_retries: int = 3) -> dict:
     # Check if screenshot exists
    if not os.path.exists(screenshot_path):
        print(f"Error: Screenshot not found at {screenshot_path}")
        return {"action": "FAIL", "reasoning": f"Screenshot file missing at {screenshot_path}"}
    
    # Resize image to reduce processing time
    try:
        img = Image.open(screenshot_path)
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


        Respond ONLY with a JSON object in this exact format, with no other text, tags (e.g., no <tool_call>), or explanations.
        Close any popups first.
        For each step, choose the most appropriate action from the following options:

        1. Identify clickable elements by visual position only.
        2. Estimate where the coordinates of the area is in the image ({screenshot_width}×{screenshot_height}) according to the reasoning.
        3. For small dismiss/X/close buttons, aim exactly at the center of the small icon, even if larger areas are nearby. Never click large surrounding elements.
        4. Use normalized coordinates (0.0 to 1.0 preferred).
        5. Respond ONLY with valid JSON using one of these actions:

        {{"action": "CLICK", "x": <x_value>, "y": <y_value>, "reasoning": "..."}}
        {{"action": "TYPE", "text": <text>, "reasoning": "..."}}
        {{"action": "SCROLL", "direction": <direction>, "amount": <amount>, "reasoning": "..."}}
        {{"action": "DRAG", "from_x": <from_x>, "from_y": <from_y>, "to_x": <to_x>, "to_y": <to_y>, "reasoning": "..."}}
        {{"action": "HOVER", "x": <x_value>, "y": <y_value>, "reasoning": "..."}}
        {{"action": "DOUBLE_CLICK", "x": <x_value>, "y": <y_value>, "reasoning": "..."}}
        {{"action": "LONG_PRESS", "x": <x_value>, "y": <y_value>, "duration_ms": <duration_ms>, "reasoning": "..."}}
        {{"action": "COMPLETE"}}
        {{"action": "FAIL"}}
        
        {conversation_history}
    """
    
    # Retry API call up to max_retries
    for attempt in range(max_retries):
        try:
            response = requests.post(
                "http://192.168.137.1:11434/api/chat",
                #"http://localhost:11434/api/chat",
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
