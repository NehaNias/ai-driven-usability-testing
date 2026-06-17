# AI-Driven Usability Testing

An automated usability test preparation system that generates structured, metric-aligned test tasks and executes them on real-world web interfaces using a vision-based LLM agent. The system produces session recordings and structured JSON reports that serve as usability test material for human analysis.

## Overview

The system consists of two main components:

- **Task Generation Pipeline**: Automatically generates and validates usability test tasks grounded in ISO 9241-11 and Nielsen's heuristics. It uses a four-stage validation loop (feasibility check, quality check, metric alignment, redundancy & coverage check).
- **Agent Execution Loop**: Executes each task on a live website using only screenshots (no DOM access). It produces a session video and a detailed JSON report per task.

## Requirements

- Python 3.10 or higher
- Gemini API key (for task generation and action verification)
- Ollama Cloud account with access to `qwen3-vl:235b` (for action decisions)
- Playwright with Chromium

## Installation

1. Clone the repository

   ```bash
   git clone https://github.com/your-username/ai-driven-usability-testing.git
   cd ai-driven-usability-testing

2. Create and activate a virtual environment
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate

3. Install dependencies
    ```bash
    pip install -r requirements.txt
4. Install Playwright browser
    ```bash
    playwright install chromium
5. Set up API keys in .env file
    ```bash
    GEMINI_API_KEY="your-gemini-api-key"
    OLLAMA_API_KEY="your-ollama-bearer-token"

## Project Structure
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
├── outputs/
│   ├── reports                 # JSON files from task executions
│   ├── screenshots             # Consists of one folder per task, each consisting of screenshots of every step
│   └── videos                  # Video recordings of task executions
│
├── evaluation/
│   ├── cohen_kappa.py          # Computes weighted Cohen's Kappa for inter-rater reliability
│   ├── entropy.py              # Computes Shannon entropy to assess metric coverage balance
│   ├── gwet.py                 # Computes Gwet's AC1 coefficient for inter-rater reliability
│   ├── metrics_report.py       # Aggregates and summarises metrics across all JSON reports
│   └── percentage.py           # Computes exact and within-tolerance percentage agreement between raters
│
├── batch_run                   # Batch execution of all tasks
│                   
├── run_test.py                 # Run a single task
├── requirements.txt
└── README.md
```


## Usage

1. Generate tasks

    ```bash
    python3 generate_tasks.py   
    --url "https://www.amazon.de"  
    --context "Amazon is the world's largest online retail platform that allows 
        users to search, browse, and purchase a vast range of physical and digital products with 
        fast delivery and convenient payment options. It offers personalized recommendations, 
        customer reviews, deal sections, and Prime membership benefits, and is used daily for 
        personal shopping, gift buying, business procurement, and deal hunting by millions of 
        consumers worldwide. IMPORTANT CONSTRAINT: Only generate tasks that can be completed WITHOUT 
        making any payment. Logging in is allowed."

The generated tasks are saved to tasks/generated_tasks.py.

2. Then run the generated tasks as a batch:

    ```bash
    python3 batch_run.py 
    --url "https://www.amazon.de"

Output is stored in the outputs folder which includes JSON reports, screenshots and video recordings.

3. To run a single task:

    ```bash
    python3 run_test.py \
    --task "Search for wireless headphones and filter by Prime delivery and 4 stars & up" \
    --url "https://www.amazon.de"   
## Output Format

Each JSON report contains:

| Field                | Description                                      |
|----------------------|--------------------------------------------------|
| `task`               | Task description string                          |
| `url`                | Target website URL                               |
| `success`            | Boolean — whether the agent reached COMPLETE     |
| `reasoning`          | Agent's final reasoning                          |
| `steps_taken`        | Total number of steps logged                     |
| `total_time_seconds` | Wall clock elapsed time                          |
| `video_path`         | Path to the session recording                    |
| `metrics`            | Summary dict (task_success, retry_rate, etc.)    |
| `full_history`       | Complete action history with per-step details    |

## Configuration

Key parameters (adjust directly in the files):

| Parameter           | Location                    | Default      | Description                              |
|---------------------|-----------------------------|--------------|------------------------------------------|
| `max_steps`         | `run_test.py`               | 35           | Maximum steps per session                |
| `num_tasks`         | `task_generator.py`         | 15           | Number of tasks to generate              |
| `temperature`       | `task_generator.py`         | 0.6          | LLM temperature for task generation      |
| Scroll distance     | `utils/actions.py`          | 600px        | Fixed scroll distance                    |
| Ollama model           | `batch_run`, `agent/screenshot_agent.py`, `utils/vision.py` | qwen3-vl:235b| Model used for action decisions          |
| Gemini model           | `run_test.py`, `tasks/task_generator.py` | gemini-2.5-flash| Model used for task generation and action verification          |




