import os
import json
from agent.screenshot_agent import ScreenshotAgent
from metrics.usability_metrics import UsabilityMetrics
from utils.action_verifier import ActionVerifier
from utils.actions import execute_action
from playwright.sync_api import sync_playwright
from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY")) 
verifier = ActionVerifier(client=client, model="gemini-2.5-flash")


def run_usability_test(task: str, url: str = "https://www.amazon.com", max_steps: int = 35):
    agent = ScreenshotAgent(task=task, max_steps=max_steps)
    action_history = []         
    safe_task_name = task.lower()[:60].replace(" ", "_").replace("/", "").replace("\\", "")


    os.makedirs(f"outputs/screenshots/{safe_task_name}", exist_ok=True)
    os.makedirs("outputs/videos", exist_ok=True)
    os.makedirs("outputs/reports", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir="outputs/videos",          
            record_video_size={"width": 1280, "height": 720}
        )
        page = context.new_page()
        page.goto(url)
        page.wait_for_timeout(3000)

        print(f"\nStarting AI Usability Test")
        print(f"Task: {task}")
        print(f"URL: {url}")
        print("-" * 70)

        step = 0
        while step < agent.max_steps:
            step += 1
            screenshot_path = f"outputs/screenshots/{safe_task_name}/step_{step:03d}.png"
            page.screenshot(path=screenshot_path)

            action = agent.get_next_action(screenshot_path, action_history)

            reasoning = action.get("reasoning", "")[:80]
            print(f"Step {step:2d} → {action['action']:<10} | {reasoning}")

            if action["action"] in ["COMPLETE", "FAIL"]:
                agent.log_step(step, action, screenshot_path, success=action["action"] == "COMPLETE")
                break

            before_state = {
                "url": page.url,
                "title": page.title(),
                "hash": ActionVerifier.get_screenshot_hash(page),
                "ocr_text": verifier.get_screenshot_text(page), 
                "raw_screenshot": page.screenshot(),
            }
            execute_action(page, action)
            success, reason = verifier.verify_action_success(page, action, before_state)

            if not success:
                print(f"Action verification FAILED: {reason}")
                action_history.append(ActionVerifier.get_verification_feedback(action, success, reason))
            else:
                print(f"Action verified: {reason}")
                history_entry = "SUCCESS" + ": " + action["action"] + " - " + action.get("reasoning", "")
                action_history.append(history_entry)

            agent.log_step(step, action, screenshot_path, success=success)
            page.wait_for_timeout(1800)  

         
        video = page.video
        page.close()
        if video:
            video_path = f"outputs/videos/{safe_task_name}.webm"
            video.save_as(video_path)
            print(f"Video saved: {video_path}")

        context.close()
        browser.close()

    
        metrics = UsabilityMetrics(agent.history)
        report = {
            "task": task,
            "url": url,
            "success": action["action"] == "COMPLETE",
            "reasoning": action.get("reasoning", ""),
            "steps_taken": len(agent.history),
            "total_time_seconds": round(agent.history[-1]["timestamp"] if agent.history else 0, 1),
            "video_path": video_path if video else None,
            "metrics": metrics.summary(),
            "full_history": agent.history
        }

        report_filename = f"outputs/reports/{safe_task_name}.json"
        with open(report_filename, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        print("\n" + "="*70)
        print("USABILITY TEST COMPLETE")
        print(f"Success: {'Yes' if report['success'] else 'No'}")
        print(f"Steps: {report['steps_taken']}")
        print(f"Time: {report['total_time_seconds']}s")
        print(f"Video: {report['video_path']}")
        print(f"Report: {report_filename}")
        print(json.dumps(metrics.summary(), indent=2))
        print("="*70)


if __name__ == "__main__":
    run_usability_test(
        task="Find a men's waterproof jacket under 100 Euros",
        url="https://www.amazon.com"
    )