import json
import os
import re
import sys
import time
import uuid
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# --- CONFIGURATION ---
# Define the path to the configuration file (.env) and load it.
# Environment variables that have already been set override the values in the .env file.
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=False)

# Check whether the configuration is complete.
REQUIRED = ["OPENAI_BASE_URL", "OPENAI_API_KEY", "MODEL", "DATA_BASE_URL"]
missing = [name for name in REQUIRED if not os.environ.get(name)]
if missing:
    print(f"Missing configuration: {', '.join(missing)} (see README.md)", file=sys.stderr)
    sys.exit(1)

# Initialize the model and API client.
MODEL = os.environ["MODEL"]
DATA_BASE_URL = os.environ["DATA_BASE_URL"].rstrip("/")
client = OpenAI(base_url=os.environ["OPENAI_BASE_URL"], api_key=os.environ["OPENAI_API_KEY"])

# --- LOGGING ---
# Generate a random UUID, create the folder for the log files, and add a new log file to it.
RUN_ID = uuid.uuid4().hex[:12]
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H-%M')}_{RUN_ID}.jsonl"


def log(event, ok=True, tool=None, args=None, duration_ms=None, **extra):
    """Write an entry and add it to the respective log file."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "run_id": RUN_ID,
        "event": event,  # user_task | tool_call | tool_result | final | error
        "tool": tool,
        "args": args,
        "ok": ok,
        "model": MODEL,
        "duration_ms": duration_ms,
        **extra,
    }
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# --- THE TOOLS ---
# Description of the tools that are passed to the language model.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_calendar_day",
            "description": (
                "Reads all appointments of a single day from the user's calendar. "
                "Always call it when a question is about appointments, times or plans on a date. "
                "If there is no data for that day, the result has found=false."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in the format YYYY-MM-DD, e.g. 2026-10-29.",
                    }
                },
                "required": ["date"],
            },
        },
    }
]


def get_calendar_day(date: str) -> dict:
    """Fetch the appointments of one day from the calendar data service."""
    # Check whether the date matches the required pattern YYYY-MM-DD and construct the corresponding URL.
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise ValueError(f"Invalid date '{date}', expected YYYY-MM-DD")
    url = f"{DATA_BASE_URL}/calendar/{date}.json"

    # Try to download the JSON file for that day and return its content.
    # If the file is missing, the date is treated as a day without data.
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return {"date": date, "found": True, "data": json.load(resp)}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"date": date, "found": False, "data": None,
                    "note": "There is no calendar data for this day."}
        raise

# Link the python function and the according tool 
TOOL_FUNCTIONS = {"get_calendar_day": get_calendar_day}


# --- THE AGENT ---
# Link the user's query, the language model, the calendar function and the response.
def run(task: str) -> str:
    log("user_task", args={"task": task}) # task = user's question

    # Create the message for the language model.
    # The system section defines the behaviour and rules of the assistant, whilst user contains the specific question.
    messages = [
        {
            "role": "system",
            "content": (
                f"You are a calendar assistant. Today is {date.today().isoformat()}. "
                "For questions about appointments, always use the tool get_calendar_day. "
                "Base your answer on the tool results, never invent appointments. "
                "Always reply in the same language as the user's question, even if the "
                "calendar data is in another language."
            ),
        },
        {"role": "user", "content": task},
    ]

    # Start a loop for multiple tool calls (max. 5).
    for _ in range(5):
        # Execute the API request and save the response.
        response = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS, tool_choice="auto"
        )

        # Get the first response of the model.
        msg = response.choices[0].message

        # Check whether the model is complete. It is complete if there are no more tool calls.
        if not msg.tool_calls:
            answer = msg.content or ""
            log("final", args={"answer": answer})
            return answer

        # Include the tool calls in the call transcript.
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ],
        })

        # Process the requested tools one by one.
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            log("tool_call", tool=name, args=args)

            # Execute the corresponding function and measure the duration.
            start = time.perf_counter()
            try:
                result = TOOL_FUNCTIONS[name](**args)
                ok = True
            except Exception as e:  # Return the error to the model as the tool's result.
                result = {"error": str(e)}
                ok = False
            duration = round((time.perf_counter() - start) * 1000)

            # Log the process.
            log("tool_result", ok=ok, tool=name, args=args, duration_ms=duration)

            # Return the tool result to the model.
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

    # Deal with the maximum number of runs.
    raise RuntimeError("Too many tool calls without an answer.")

# Define how the program starts from the command line.
def main() -> int:
    # Check whether a question has been provided. 
    if len(sys.argv) < 2:
        print('Usage: python -m agent "Your question"', file=sys.stderr)
        return 2

    # Construct the question correctly, using spaces.
    task = " ".join(sys.argv[1:])

    # Run the process and catch the errors.
    try:
        print(run(task))
        return 0
    except Exception as e:
        log("error", ok=False, error=str(e))
        print(f"Error: {e}", file=sys.stderr)
        return 1

# Ensure, that main() is automatically executed only when the file is launched directly (entry point).
if __name__ == "__main__":
    sys.exit(main())
