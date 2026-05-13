import base64
import json
import time
import requests
from PIL import Image
import io
import os
from utils.response_parser import ResponseParser
import ollama as ollama_client



client = ollama_client.Client(
    host="https://ollama.com",
    headers={"Authorization": "Bearer " + os.getenv("OLLAMA_API_KEY", "")}
)
username = os.getenv("USER_NAME")
password = os.getenv("PASSWORD")

def get_ai_action(screenshot_path: str, user_task: str, previous_actions: list, max_retries: int = 5) -> dict:
    if not os.path.exists(screenshot_path):
        print(f"Error: Screenshot not found at {screenshot_path}")
        return {"action": "FAIL", "reasoning": f"Screenshot file missing at {screenshot_path}"}
    
    
    try:
        img = Image.open(screenshot_path)
        screenshot_width, screenshot_height = img.size
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"Error processing screenshot: {e}")
        return {"action": "FAIL", "reasoning": f"Failed to process screenshot: {e}"}
    
    conversation_history = ""
    for action in previous_actions: 
        conversation_history += f"Previous action taken: {action}\n"
    
    prompt = f"""
    You are an AI usability testing agent controlling a web browser via screenshots.
    Your goal is to complete the user's task by deciding the next single action to take.

    TASK: {user_task}

    RULES:
    1. FIRST ACTION ALWAYS: Look for log in or sign in button to click.
    2. Respond ONLY with a single valid JSON object. No explanations, no markdown, no <tags>.  
    3. Close any popups or overlays before doing anything else.
    4. Use ONLY normalized coordinates between 0.0 and 1.0, where (0.0, 0.0) is top-left and (1.0, 1.0) is bottom-right.
    5. Coordinates must be single decimal numbers, NOT lists or arrays. For example: \"x\": 0.286 is correct, \"x\": [0.286, 199] is wrong.
    6. To estimate coordinates: identify the element visually, estimate its center as a fraction of the total image width ({screenshot_width}px) and height ({screenshot_height}px).
    7. For small buttons (close/X/dismiss): be precise, aim at the exact center of the icon.
    8. Do NOT scroll if the target element is already visible on screen.
    9. Do NOT repeat an action that already succeeded.
    10. If the last action failed, try a slightly different position.
    11. If the last few actions failed, try a different strategy. 
    12. Use COMPLETE only when the task goal has been successfully achieved
    13. Use FAIL when the task is impossible, the target cannot be found, or you are stuck
    14. If action is TYPE and username or email is required, use {username} as text
    15. If action is TYPE and password is required, use {password} as text

    PROGRESS:
    {conversation_history}

    NEXT ACTION (respond with one JSON object only):
    {{"action": "CLICK", "x": <0.0-1.0>, "y": <0.0-1.0>, "reasoning": "..."}}
    {{"action": "TYPE", "text": "<text>", "reasoning": "..."}}
    {{"action": "SCROLL", "direction": "<up|down|left|right>", "reasoning": "..."}}
    {{"action": "DRAG", "from_x": <0.0-1.0>, "from_y": <0.0-1.0>, "to_x": <0.0-1.0>, "to_y": <0.0-1.0>, "reasoning": "..."}}
    {{"action": "HOVER", "x": <0.0-1.0>, "y": <0.0-1.0>, "reasoning": "..."}}
    {{"action": "DOUBLE_CLICK", "x": <0.0-1.0>, "y": <0.0-1.0>, "reasoning": "..."}}
    {{"action": "LONG_PRESS", "x": <0.0-1.0>, "y": <0.0-1.0>, "duration_ms": <ms>, "reasoning": "..."}}
    {{"action": "COMPLETE", "reasoning": "..."}}
    {{"action": "FAIL", "reasoning": "..."}}
    """


    # Retry API call up to max_retries
    for attempt in range(max_retries):
        try:
            """response = requests.post(
                #"http://192.168.0.14:11434/api/chat",
                #"http://192.168.137.1:11434/api/chat",
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
            response_text = response_data.get("message", {}).get("content", "")"""

            response = client.chat(
                model="qwen3-vl:235b",
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [base64_image]
                    }
                ]
            )
            response_text = response["message"]["content"] or ""
            print(f"Raw AI response (attempt {attempt + 1}): {response_text}")

            
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx == -1 or end_idx == 0 or (end_idx - start_idx) < 16:
                print(f"No valid JSON found in response: {response_text}")
                try:
                    parsed = ResponseParser(screenshot_width, screenshot_height).parse(response_text)
                    if parsed:
                        return parsed
                except Exception as e:
                    print(f"Could not extract valid JSON from response")
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
                time.sleep(2)  
                continue
            return {"action": "FAIL", "reasoning": f"API request failed after {max_retries} attempts: {e}"}
    
    return {"action": "FAIL", "reasoning": f"No valid response after {max_retries} attempts"}
