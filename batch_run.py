from run_test import run_usability_test
from tasks.task_generator import TaskGenerator
import time
import requests
from tasks.generated_tasks import TASKS_WITH_METRICS

def reset_ollama_model(model: str = "qwen3-vl:235b", api_url: str = "https://ollama.com/api/chat"):
    try:
        requests.post(f"{api_url}/api/generate", json={
            "model": model,
            "keep_alive": 0  
        })
        time.sleep(2)
        print(f"Model reset complete.")
    except Exception as e:
        print(f"Model reset failed: {e}")

def main():
    website_url = "https://www.amazon.de"
    website_context = """Amazon is the world's largest online retail platform that allows 
        users to search, browse, and purchase a vast range of physical and digital products with 
        fast delivery and convenient payment options. It offers personalized recommendations, 
        customer reviews, deal sections, and Prime membership benefits, and is used daily for 
        personal shopping, gift buying, business procurement, and deal hunting by millions of 
        consumers worldwide."""
    # Automatically generate tasks 
    """print("Generating usability test tasks...")
    generator = TaskGenerator()  
    tasks = generator.generate_tasks(website_url=website_url, website_context=website_context, num_tasks=20)

    if not tasks:
        print("Failed to generate tasks. Exiting.")
        return

    print(f"Successfully generated {len(tasks)} tasks:\n")
    for i, task in enumerate(tasks, 1):
        print(f"{i:2d}. {task}")

   # Save generated tasks 
    with open("tasks/generated_tasks.txt", "w", encoding="utf-8") as f:
        for task in tasks:
            f.write(task + "\n")
    print(f"\nTasks saved to tasks/generated_tasks.txt")"""

    tasks = [t["task"] for t in TASKS_WITH_METRICS]
    
    print(f"Loaded {len(tasks)} tasks from generated_tasks.py")
    for i, task in enumerate(tasks, 1):
        print(f"{i:2d}. {task}")


    print(f"\nStarting batch execution of {len(tasks)} tasks on {website_url}...")
    print("=" * 80)

    for i, task in enumerate(tasks, 1):
        print(f"\nTASK {i:02d}/{len(tasks):02d}: {task}")
        print("-" * 80)
        reset_ollama_model()
        try:
            run_usability_test(task=task, url=website_url)
            print(f"Task {i} completed.")
        except Exception as e:
            print(f"Task {i} failed with error: {e}")
        
        time.sleep(3)

    print("\n" + "="*80)
    print("Batch completed.")

if __name__ == "__main__":
    main()

    