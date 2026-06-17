import argparse
import os
from dotenv import load_dotenv
import google.genai as genai
from google.genai import types
import requests
import json
import time

class TaskGenerator:
    

    def __init__(self, api_key: str = None):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Set GEMINI_API_KEY env var or pass api_key")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-2.5-flash"

    def _call_llm(self, prompt: str):
        max_retries = 10
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,  
                config=types.GenerateContentConfig(
                temperature=0.6,
                response_mime_type="application/json"  
                )     
                )   
                return response.text
            except Exception as e:
                error_msg = str(e).lower()
                if "503" in error_msg or "unavailable" in error_msg:
                    wait_time = (2 ** attempt) + 1   # 1, 3, 5, 9, 17, 33 seconds
                    print(f"Gemini 503 (high demand) - Retrying in {wait_time} seconds... "
                          f"(Attempt {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                print(f"LLM error: {e}")
                return ""

    def generate_raw_tasks(self, website_url: str, website_context: str, num_tasks: int = 25) -> list:
        

        prompt = f"""
        You are an expert in generating usability testing tasks for websites.

        Generate {num_tasks} tasks for {website_url} that meet ALL of the following requirements:

        CONTENT REQUIREMENTS:
        - Tasks must be grounded in the website's actual core workflows
        - Every task must be specific. Never use vague language. 
        - Tasks must reflect realistic user goals — something a real visitor to this site would actually want to do
        - Only use English terms

        COMPLETION REQUIREMENTS:
        - Every task must have a clear, verifiable endpoint that the agent can recognise as COMPLETE
        - "Locate" and "find" and "navigate to" are only acceptable if the task specifies what to do or confirm upon arrival
        
        INTERACTION REQUIREMENTS:
        - Tasks must require at least one active interaction beyond just arriving at a page
        - Tasks must be completable without making any payment. Logging in is allowed

        METRIC COVERAGE REQUIREMENTS:
        Ensure that ALL the metrics are covered collectively by the tasks. Each metric should be covered at least once.
        Here is what each metric requires:

        - effectiveness: tasks where success is binary and clear — did the user reach the goal or not?
        - efficiency: tasks involving multiple steps where the number of steps and time matter
        - learnability: tasks where a first-time user must discover non-obvious features
        - error-proneness: tasks with steps where users commonly make mistakes
        - satisfaction: tasks involving multi-step workflows where the overall experience matters
        - visibility: tasks where finding the right element is the core challenge
        - flexibility: tasks that can be completed via multiple different paths


        DIVERSITY REQUIREMENTS:
        - Cover a range of different workflows — do not generate more than 3 tasks on the same workflow
        - Include tasks of varying difficulty — some straightforward, some requiring multiple steps

        System context:
        {website_context}

        Output ONLY a JSON list of {num_tasks} task strings. No explanations, no markdown.
        """

        print(f"Generating {num_tasks + 10} raw tasks...")
        raw = self._call_llm(prompt)
        return self._parse_json_list(raw)

    def feasibility_check(self, tasks: list, website_url: str, context: str) -> list:
        #Stage 1: Feasibility Check.
        feasible = []
        raws = []
        for task in tasks:
            prompt = f"""
            Evaluate feasibility of this task: "{task}"

            System context for {website_url}: {context}

            Reject the task if ANY of these are true:
            - Requires payment
            - Has no clear observable endpoint (e.g. reaching a page, applying a filter)
            - Requires prior knowledge of a specific product that may not exist on the site

            Respond in JSON:
            {{"feasible": "YES" or "NO", "reason": "short explanation"}}
            """

            raw = self._call_llm(prompt)
            raws.append(raw)
            try:
                result = json.loads(raw)
                if result["feasible"].upper() == "YES":
                    feasible.append(task)
            except:
                print(f"Failed to parse feasibility for: {task}")

        print(f"Feasibility check: {len(feasible)}/{len(tasks)} tasks kept.")
        print("Feasibility raw responses:", raws)
        return feasible

    def quality_check(self, tasks: list) -> list:
        #Stage 2: Quality Check & Rewrite.
        improved = []
        raws = []
        for task in tasks:
            prompt = f"""
    Evaluate task: "{task}"
    Be strict in scoring each dimension (1-5) and only rewrite if necessary based on the rules.

    Scores (1-5):
    - Clarity: Is the task description unambiguous and specific?
    - Atomicity: Does it describe exactly one goal?
    - Neutrality: Does it avoid implying a specific UI path?

    Rules for rewriting if any score is below 4:
    - The rewritten task must end with a clear action — reaching a page, applying a filter, selecting a product, or navigating to a section
    - Tasks must be completable without making a payment
    - Do not add UI-specific wording like "click the search bar" or "use the dropdown"

    If any <4, rewrite to improve.
    ONLY respond with JSON. Response cannot be empty, this is crucial.

    JSON:
    {{"clarity": num, "atomicity": num, "neutrality": num, "improved_task": "rewritten or original"}}
    """
            raw = self._call_llm(prompt)
            raws.append(raw)
            try:
                result = json.loads(raw)
                if "improved_task" in result:
                    if result["improved_task"].strip() == "original":
                        result["improved_task"] = task
                    improved.append(result["improved_task"])
                else:
                    improved.append(task)
            except Exception as e:
                print(f"Quality check failed for: {task}")
                improved.append(task)

        print(f"Quality check complete: {len(improved)} tasks refined.")
        print("Quality check raw responses:", raws)
        return improved

    def metric_alignment(self, tasks: list) -> list:
        #Stage 3: Metric Alignment.
        aligned = []
        for task in tasks:
            prompt = f"""
            Map task: "{task}" to exactly 2 metrics from below:
            # ISO 9241-11 metrics — measured by task outcomes
            - effectiveness: assign when the core question is whether the user achieves the goal 
            accurately and completely — measured by task completion rate and error rate

            - efficiency: assign when the resources expended matter — measured by steps taken, 
            time on task, or navigation path length

            - satisfaction: assign when the subjective experience of the interaction matters — 
            typically multi-step workflows where friction or smoothness affects how the user feels

            # Nielsen heuristic-derived metrics — measured by interface observations
            - visibility: assign when the target element is not in the primary visual hierarchy 
            and requires deliberate searching (Nielsen H1 — Visibility of system status, 
            H6 — Recognition rather than recall)

            - error-proneness: assign when specific steps risk incorrect user actions 
            (Nielsen H5 — Error prevention)

            - learnability: assign when a first-time user would struggle to discover the feature 
            (Nielsen H6 — Recognition rather than recall)

            - flexibility: assign when multiple valid paths exist to complete the task 
            (Nielsen H7 — Flexibility and efficiency of use)

            STRICT INSTRUCTIONS:
            1. Assign exactly 2 metrics per task, no more, no less.
            2. Avoid defaulting to effectiveness and efficiency for every task, unless truly the core of the task.

            JSON:
            {{"task": "{task}", "metrics": ["metric1", "metric2"], "rationale": "short reason"}}
            """

            raw = self._call_llm(prompt)
            try:
                result = json.loads(raw)
                aligned.append(result)
            except:
                print(f"Metric alignment failed for: {task}")

        print(f"Metric alignment: {len(aligned)} tasks tagged.")
        return aligned

    def redundancy_and_coverage(self, tasks: list, num_tasks: int, website_url: str, website_context: str) -> list:
        #Stage 4: Redundancy & Coverage.
        prompt = f"""
        Review these usability test tasks for {website_url}:
        {json.dumps(tasks, indent=2)}

        Website context: {website_context}
        
        Instructions:
        1. Remove any duplicate or near-duplicate tasks
        2. Remove any tasks that are redundant with another task
        3. Remove any tasks that only require reading, counting, or identifying information rather than active interaction
        4. Check metric coverage — every metric from this list must appear in at least 2 tasks:
        ["effectiveness", "efficiency", "learnability", "error-proneness", "satisfaction", "visibility", "flexibility"]
        5. For any metric with fewer than 2 tasks, add new active interaction tasks that genuinely target that metric:
            - effectiveness: ONLY when the core question is "can the user complete the goal at all?"
            - efficiency: ONLY when the core question is "how quickly or with how few steps?"
            - learnability: when the task involves discovering unfamiliar features or navigation for the first time
            - error-proneness: when the task involves steps where a user could easily make a mistake or get confused
            - satisfaction: when the task involves a multi-step process where the overall experience matters
            - visibility: when the task involves finding something that may not be immediately obvious
            - flexibility: when there are multiple ways to complete the task or shortcuts available
        6. Limit final set to {num_tasks} tasks total, prioritising diversity of metrics and workflows

        Output ONLY JSON list of final objects.
        """

        raw = self._call_llm(prompt)
        final = self._parse_json_list(raw)

        validated = []
        for task_obj in final:
            task_str = task_obj.get("task", "") if isinstance(task_obj, dict) else task_obj
            
            original_tasks = [t.get("task", "") if isinstance(t, dict) else t for t in tasks]
            if task_str in original_tasks:
                validated.append(task_obj)
                continue
            
            feasible = self.feasibility_check([task_str], website_url, website_context)
            if not feasible:
                print(f"Coverage task failed feasibility: {task_str}")
                continue
                
            quality = self.quality_check(feasible)
            if quality:
                if isinstance(task_obj, dict):
                    task_obj["task"] = quality[0]
                validated.append(task_obj)
            else:
                print(f"Coverage task failed quality: {task_str}")
        
        print(f"Final set: {len(validated)} tasks after redundancy/coverage + validation.")
        return validated

    def _parse_json_list(self, text: str) -> list:
        try:
            start = text.find("[")
            end = text.rfind("]") + 1
            return json.loads(text[start:end])
        except:
            print("Parse failed.")
            return []

    def generate_tasks(self, website_url: str, website_context: str, num_tasks: int = 15) -> list:
        raw_tasks = self.generate_raw_tasks(website_url, website_context, num_tasks)
        feasible = self.feasibility_check(raw_tasks, website_url, website_context)
        quality = self.quality_check(feasible)
        aligned = self.metric_alignment(quality)
        final = self.redundancy_and_coverage(aligned, num_tasks, website_url, website_context)
        return final

    def generate_and_save(self, website_url: str, website_context: str, num_tasks: int = 15, filename: str = "generated_tasks.py"):
        tasks = self.generate_tasks(website_url, website_context, num_tasks)
        if tasks:
            content = f"# AI-Generated Validated Tasks for {website_url}\n"
            content += f"# Generated: {time.strftime('%Y-%m-%d %H:%M')}\n\n"
            content += f"TASKS_WITH_METRICS = {json.dumps(tasks, indent=2)}\n"

            filepath = f"tasks/{filename}"
            with open(filepath, "w") as f:
                f.write(content)
            print(f"Saved to {filepath}")
        return tasks

    def main():
        load_dotenv()
        parser = argparse.ArgumentParser(description="Task Generation")
        parser.add_argument("--url", required=True, help="Target website URL")
        parser.add_argument("--context", required=True, help="Brief description of the website and its core workflows")
        parser.add_argument("--num-tasks", type=int, default=15, help="Number of tasks to generate (default: 15)")
        parser.add_argument("--output", default="generated_tasks.py", help="Output filename (default: generated_tasks.py)")
        
        args = parser.parse_args()

        print(f"Starting task generation for {args.url}")
        
        generator = TaskGenerator() 
        
        generator.generate_and_save(
            website_url=args.url,
            website_context=args.context,
            num_tasks=args.num_tasks,
            filename=args.output
        )


    if __name__ == "__main__":
        main()

# Test
"""if __name__ == "__main__":
    generator = TaskGenerator()
    website_context =""" """Amazon is the world's largest online retail platform that allows 
        users to search, browse, and purchase a vast range of physical and digital products with 
        fast delivery and convenient payment options. It offers personalized recommendations, 
        customer reviews, deal sections, and Prime membership benefits, and is used daily for 
        personal shopping, gift buying, business procurement, and deal hunting by millions of 
        consumers worldwide. IMPORTANT CONSTRAINT: Only generate tasks that can be completed WITHOUT 
        making any payment. Logging in is allowed."""

    #generator.generate_and_save("https://www.amazon.de", website_context, 15)