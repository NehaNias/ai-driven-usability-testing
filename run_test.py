# run_test.py
import os
import json
from agent.screenshot_agent import ScreenshotAgent
from metrics.usability_metrics import UsabilityMetrics
from utils.actions import execute_action
from playwright.sync_api import sync_playwright


def run_usability_test(task: str, url: str = "https://www.amazon.com", max_steps: int = 25):
    agent = ScreenshotAgent(task=task, max_steps=max_steps)

    # Create output directories
    os.makedirs("outputs/screenshots", exist_ok=True)
    os.makedirs("outputs/videos", exist_ok=True)
    os.makedirs("outputs/reports", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir="outputs/videos",           # Videos saved here
            record_video_size={"width": 1280, "height": 720}
        )
        page = context.new_page()
        page.goto(url)

        print(f"\nStarting AI Usability Test")
        print(f"Task: {task}")
        print(f"URL: {url}")
        print("-" * 70)

        step = 0
        while step < agent.max_steps:
            step += 1
            screenshot_path = f"outputs/screenshots/step_{step:03d}.png"
            page.screenshot(path=screenshot_path)

            action = agent.get_next_action(screenshot_path)
            loop_fail = agent.log_step(step, action, screenshot_path)
            if loop_fail:
                action = loop_fail

            reasoning = action.get("reasoning", "")[:80]
            print(f"Step {step:2d} → {action['action']:<10} | {reasoning}")

            if action["action"] in ["COMPLETE", "FAIL"]:
                break

            execute_action(page, action)
            page.wait_for_timeout(1800)  # Natural human-like pause

        # Save the video with a clean name
        video = page.video
        page.close()
        if video:
            safe_task_name = task.lower()[:60].replace(" ", "_").replace("/", "").replace("\\", "")
            video_path = f"outputs/videos/{safe_task_name}.webm"
            video.save_as(video_path)
            print(f"Video saved: {video_path}")

        context.close()
        browser.close()

        # Generate final usability report
        metrics = UsabilityMetrics(agent.history)
        report = {
            "task": task,
            "url": url,
            "success": action["action"] == "COMPLETE",
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
    # Change this task whenever you want to test something new
    run_usability_test(
        task="Find a men's waterproof jacket under 100 Euros",
        url="https://www.amazon.com"
    )