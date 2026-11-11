# agentic-interaction-ws2627

A day and travel planner agent that works with a simulated calendar, timetable, weather service and notes. It solves tasks in several steps, shows its plan for approval before acting, and uses no real accounts or personal data. A typical task:

> "Get me to my 14:00 meeting in Stuttgart on Thursday by train, and remind me to take an umbrella if it rains."

## Requirements

- Python 3.11 or newer
- Git
- An API key for an OpenAI-compatible endpoint. By default the project uses Groq; you can create a free key at [console.groq.com](https://console.groq.com/keys).

## Setup

Clone the repository and change into it. All following commands are run from the repository root.

```bash
git clone https://github.com/<github-username>/agentic-interaction-ws2627.git
cd agentic-interaction-ws2627
```

Then create a virtual environment and install the dependencies.

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell)**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configuration

Create a file named `.env` in the repository root with the following content and replace the placeholder with your own API key. The other values can stay as they are. To use a different OpenAI-compatible endpoint or model, change `OPENAI_BASE_URL` and `MODEL`.

```
OPENAI_BASE_URL=https://api.groq.com/openai/v1
MODEL=openai/gpt-oss-20b
OPENAI_API_KEY=<your-api-key>
DATA_BASE_URL=https://jhbelz.github.io/agentic-interaction-data/v1
```

`.env` is listed in `.gitignore` and must never be committed. Environment variables that are already set take precedence over `.env`.

## Example

```bash
python -m agent "What is in the calendar on 29.10.2026?"
```

The answer is printed to standard output. Each run writes a log file to `logs/`.
