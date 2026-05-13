ai-driven-usability-testing
An automated usability test preparation system that generates structured, metric-aligned test tasks and executes them on real-world web interfaces using a vision-based LLM agent. The system produces session recordings and structured JSON reports that serve as usability test material for human analysis.
---
Overview
The system consists of two main components:
Task generation pipeline — automatically generates and validates usability test tasks grounded in ISO 9241-11 and Nielsen's heuristics, using a four-stage validation loop (feasibility check, quality check, metric alignment, redundancy and coverage check)
Agent execution loop — executes each task on a live website using only screenshots, without any DOM access, and produces a session video and JSON report per task
---
Requirements
Python 3.10 or higher
A Gemini API key (for task generation and action verification)
An Ollama Cloud account with access to `qwen3-vl:235b` (for action decisions)
Playwright installed with Chromium
---
Installation
1. Clone the repository
```bash
git clone https://github.com/your-username/ai-driven-usability-testing.git
cd ai-driven-usability-testing
```
2. Create and activate a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate        

3. Install dependencies
```bash
pip install -r requirements.txt
```
4. Install Playwright browsers
```bash
playwright install chromium
```
5. Set up API keys
The system requires two API keys. You can set them as environment variables or pass them directly in the code.
```bash
export GEMINI_API_KEY="your-gemini-api-key"
export OLLAMA_API_KEY="your-ollama-bearer-token"
```

Project Structure
```
ai-driven-usability-testing/
│
├── agent/
│   ├── base_agent.py           # Abstract base class for agents
│   └── screenshot_agent.py     # Concrete agent using Qwen3-VL
│
├── tasks/
│   ├── task_generator.py       # Four-stage task generation pipeline
│   └── generated_tasks.py      # Output of task generation (auto-generated)
│
├── utils/
│   ├── actions.py              # Action execution via Playwright
│   ├── action_verifier.py      # Action verification
│   ├── response_parser.py      # JSON and prose parsing of VLM output
│   └── vision.py               # VLM inference via Ollama
│
├── metrics/
│   └── usability_metrics.py    # Metric computation from action history
│
├── batch_run/
│   └── main.py                 # Batch execution of all tasks
│
├── run_test.py                 # Run a single task
├── requirements.txt
└── README.md
```
---
Usage
Step 1 — Generate tasks
Run the task generator to produce a validated set of usability test tasks for your target website.
```bash
python3 -c "
from tasks.task_generator import TaskGenerator

generator = TaskGenerator(api_key='your-gemini-api-key')
generator.generate_and_save(
    website_url='https://www.example.com',
    website_context='Brief description of the website and its core workflows.',
    num_tasks=15,
    filename='generated_tasks.py'
)
"
```
This will save the generated tasks to `tasks/generated_tasks.py`. Review the tasks manually before running the agent — remove any that are unclear or not suitable for your evaluation.
The generated task file contains a list of task objects in the following format:
```python
TASKS_WITH_METRICS = [
    {
        "task": "Search for 'running shoes' and sort the results by Average Customer Review.",
        "metrics": ["visibility", "efficiency"],
        "rationale": "..."
    },
    ...
]
```
---
Step 2 — Run a single task
To run the agent on a single task:
```bash
python3 run_test.py
```
Or call it programmatically:
```python
from run_test import run_usability_test

run_usability_test(
    task="Search for 'running shoes' and sort results by Average Customer Review.",
    url="https://www.example.com",
    max_steps=35
)
```
The session will be recorded and saved to `outputs/videos/`. A JSON report will be saved to `outputs/reports/`.
---
Step 3 — Run all tasks in batch
To run all tasks from `tasks/generated_tasks.py` sequentially:
```bash
python3 batch_run/main.py
```
The batch runner reloads the Ollama model between tasks to prevent performance degradation over long sessions. Each task produces:
A session video at `outputs/videos/[task_name].webm`
A JSON report at `outputs/reports/[task_name].json`
Per-step screenshots at `outputs/screenshots/[task_name]/step_NNN.png`
---
Step 4 — Analyse results
After the batch completes, run the analysis script to extract quantitative metrics across all tasks:
```bash
python3 analysis.py
```
This prints a summary table including task completion rate, average steps, average time, and retry rate, and identifies the highest-effort or failed sessions for further inspection.
---
Output Format
Each JSON report contains the following fields:
Field	Description
`task`	Task description string
`url`	Target website URL
`success`	Boolean — whether the agent reached COMPLETE
`reasoning`	Agent's final reasoning string
`steps_taken`	Total number of steps logged
`total_time_seconds`	Wall clock elapsed time from start to final action
`video_path`	Path to the session recording
`metrics`	Summary dict: task_success, retry_rate, termination_reason, total_time_sec, final_action
`full_history`	Complete action history list with per-step action, reasoning, success, and timestamp
---
Configuration
Key parameters can be adjusted directly in the relevant files:
Parameter	Location	Default	Description
`max_steps`	`run_test.py`	35	Maximum steps per session
`num_tasks`	`task_generator.py`	15	Number of tasks to generate
`temperature`	`task_generator.py`	0.6	LLM temperature for task generation
Scroll distance	`utils/actions.py`	600px	Fixed scroll distance per scroll action
Action history size	`utils/vision.py`	5	Number of recent steps passed to VLM
VLM model	`agent/screenshot_agent.py`	`qwen3-vl:235b`	Model used for action decisions
Verification model	`utils/action_verifier.py`	`gemini-2.5-flash`	Model used for action verification
---
Models Used
Component	Model	Provider
Action decisions	Qwen3-VL 235B	Ollama Cloud
Task generation	Gemini 2.5 Flash	Google Gemini API
Action verification	Gemini 2.5 Flash	Google Gemini API
OCR extraction	Gemini 2.5 Flash	Google Gemini API
---
Notes
The agent operates entirely through screenshots — no DOM access is used at any point
Each task starts from a fresh browser session; login state is not preserved across tasks
If tasks require authentication, add credentials to the agent prompt in `utils/vision.py`
Session time includes API retry wait periods and per-step pauses — reported times are wall clock elapsed time
The Ollama Cloud free tier may impose rate limits during periods of high demand; the system implements exponential backoff retry logic for both Ollama and Gemini API calls
