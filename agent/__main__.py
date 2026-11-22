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

import openai
from dotenv import load_dotenv
from openai import OpenAI

# --- EXIT CODES ---
# Short description of every exit code. The error descriptions are printed at the end of a run.
EXIT_CODES = {
    0: "Success: the agent answered the question.",
    1: "Error: the agent could not answer the question (see the error message above).",
    2: "Usage error: the agent was started incorrectly.",
}


def describe_exit(code: int) -> None:
    """Print the exit code and its meaning to stderr."""
    print(f"Exit code {code}: {EXIT_CODES[code]}", file=sys.stderr)

# --- LIMITS & ERRORS ---
# Every step is exactly one model call (also a failed one).
# After MAX_STEPS the run ends as an error, so that the agent doesn't get stuck in an endless loop.
MAX_STEPS = 8
# Only wait for MAX_WAIT_S after a rate limit (because the free tier limit is: 8,000 tokens per minute).
MAX_WAIT_S = 30
# Catch fatal errors that a retry cannot fix (wrong key, wrong model, no access), so that the run ends immediately.
FATAL_ERRORS = (openai.AuthenticationError, openai.PermissionDeniedError, openai.NotFoundError)

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
    describe_exit(1)
    sys.exit(1)

# Initialize the model and API client.
MODEL = os.environ["MODEL"]
DATA_BASE_URL = os.environ["DATA_BASE_URL"].rstrip("/")
# Setting max_retries=0, so that the agent doesn't retry silently. Retries should only occur
# in the loop, so that every attempt is counted as a step and is visible in the log.
# Setting timeout=60, so that the agent only waits for 60 seconds for an answer of the model server.
client = OpenAI(
    base_url=os.environ["OPENAI_BASE_URL"],
    api_key=os.environ["OPENAI_API_KEY"],
    max_retries=0,
    timeout=60,
)

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
        "event": event,  # user_task | model_error | tool_call | tool_result | final | error
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
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": (
                "Reads the weather forecast for one city on one day: temperature (temp_c), "
                "condition (in German, e.g. 'Regen' = rain, 'Schauer' = showers), "
                "rain_probability (0 to 1) and wind_kmh. "
                "Call it for questions about weather, rain, umbrella or clothing. "
                "For a trip, use the destination city. "
                "If there is no forecast for that city and day, the result has found=false."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, e.g. 'ulm' or 'muenchen' (Munich).",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date in the format YYYY-MM-DD, e.g. 2026-10-29.",
                    },
                },
                "required": ["city", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_train_connections",
            "description": (
                "Reads the train connections from one city to another on one day. Each connection "
                "has departure, arrival, changes, train and price_eur. "
                "Call it for questions about how to travel somewhere, trains or departure times. "
                "If there are no connections for that route and day, the result has found=false."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "from_city": {
                        "type": "string",
                        "description": "Departure city, e.g. 'ulm'. If the user does not say, use 'ulm'.",
                    },
                    "to_city": {
                        "type": "string",
                        "description": "Destination city, e.g. 'muenchen' (Munich).",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date in the format YYYY-MM-DD, e.g. 2026-10-29.",
                    },
                },
                "required": ["from_city", "to_city", "date"],
            },
        },
    },
]


def check_date(value: str) -> None:
    """Raise a ValueError if the date does not match the pattern YYYY-MM-DD or does not exist (e.g. 2026-02-31)."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"Invalid date '{value}', expected YYYY-MM-DD")
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"The date '{value}' does not exist in the calendar. "
                         "Tell the user and do not replace it with another date.") from None


# Different spellings of the cities in the data. Everything else is only lower-cased and transliterated.
CITY_ALIASES = {"munich": "muenchen", "munchen": "muenchen", "monaco di baviera": "muenchen"}


def city_slug(city: str) -> str:
    """Turn a city name like 'München' or 'Munich' into the short form used in the data ('muenchen')."""
    slug = city.strip().lower()
    slug = CITY_ALIASES.get(slug, slug)
    for umlaut, replacement in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        slug = slug.replace(umlaut, replacement)
    # Only letters are allowed, so that the city cannot change the URL path.
    if not re.fullmatch(r"[a-z]+", slug):
        raise ValueError(f"Invalid city '{city}', expected a city name like 'ulm' or 'muenchen'")
    return slug


def fetch_data(path: str):
    """Download one JSON file from the data service.

    Returns the parsed JSON, or None if the file does not exist. In the data service,
    HTTP 404 means "no data for this day/place" (see the README of the data repository),
    so it is a normal result and not an error. Every other HTTP error is raised.
    """
    try:
        with urllib.request.urlopen(f"{DATA_BASE_URL}/{path}", timeout=15) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def get_calendar_day(date: str) -> dict:
    """Fetch the appointments of one day from the calendar data service."""
    check_date(date)
    data = fetch_data(f"calendar/{date}.json")
    if data is None:
        # Every day of the data period has a calendar file (a free day has an empty list),
        # so a missing file means the day is outside the period, not that the day is free.
        return {"date": date, "found": False, "data": None,
                "note": "There is no calendar data for this day. It is unknown whether there are "
                        "appointments, so do not say that the day is free."}
    return {"date": date, "found": True, "data": data}


def get_weather(city: str, date: str) -> dict:
    """Fetch the weather forecast of one city on one day."""
    check_date(date)
    slug = city_slug(city)
    data = fetch_data(f"weather/{slug}/{date}.json")
    if data is None:
        return {"city": slug, "date": date, "found": False, "data": None,
                "note": "There is no weather forecast for this city and day. Do not guess the weather."}
    return {"city": slug, "date": date, "found": True, "data": data}


def get_train_connections(from_city: str, to_city: str, date: str) -> dict:
    """Fetch the train connections between two cities on one day."""
    check_date(date)
    origin, destination = city_slug(from_city), city_slug(to_city)
    data = fetch_data(f"transit/{origin}/{destination}/{date}.json")
    if data is None:
        return {"from": origin, "to": destination, "date": date, "found": False, "data": None,
                "note": "There are no train connections for this route and day. Do not make up trains or times."}
    return {"from": origin, "to": destination, "date": date, "found": True, "data": data}


# Link the Python functions and the corresponding tools.
TOOL_FUNCTIONS = {
    "get_calendar_day": get_calendar_day,
    "get_weather": get_weather,
    "get_train_connections": get_train_connections,
}


# --- LANGUAGE ---
# The data is in German, so a small model tends to answer in German even when the question is in English.
# Therefore the language of the question is detected in code, and a fixed sentence is sent as the very last
# message of every model call. 
GERMAN_WORDS = {
    "ich", "du", "mich", "mir", "mein", "meine", "meinen", "der", "die", "das", "den", "dem", "und", "oder",
    "ist", "sind", "bin", "wie", "was", "wann", "wo", "wohin", "welche", "welcher", "welches", "habe", "hast",
    "hat", "komme", "kommen", "nach", "nicht", "kein", "keine", "gibt", "es", "zum", "zur", "vom", "bei",
    "mit", "für", "ob", "brauche", "brauchen", "steht", "heute", "morgen", "übermorgen", "wetter", "zug",
    "termine", "termin", "kalender", "regenschirm", "verbindung", "verbindungen", "fahren", "einen", "eine",
    "ein", "auf", "noch", "dort", "wird", "vergleiche", "tag", "tagen", "mehr", "freie", "zeit",
}
ENGLISH_WORDS = {
    "i", "you", "me", "my", "the", "and", "or", "is", "are", "how", "what", "when", "where", "which", "do",
    "does", "did", "have", "has", "get", "go", "to", "on", "of", "for", "with", "there", "need", "any",
    "not", "no", "today", "tomorrow", "weather", "train", "trains", "calendar", "appointments", "appointment",
    "umbrella", "connection", "connections", "compare", "day", "days", "more", "free", "time", "it", "will",
    "should", "can", "a", "s",
}
LANGUAGE_HINTS = {
    "de": "Antworte ausschließlich auf Deutsch.",
    "en": "Answer only in English. Translate German titles and weather conditions from the data into English.",
}


def detect_language(text: str):
    """Return 'de' or 'en' for the language of the question, or None if it is unclear.

    Counts how many words of the text belong to each word list. Umlauts and ß count as German.
    If both counts are equal (e.g. a question with only a date), the result is None and only
    the general language rule in the system prompt applies.
    """
    words = re.findall(r"[a-zäöüß]+", text.lower())
    german = sum(w in GERMAN_WORDS for w in words) + len(re.findall(r"[äöüß]", text.lower()))
    english = sum(w in ENGLISH_WORDS for w in words)
    if german > english:
        return "de"
    if english > german:
        return "en"
    return None


# --- THE AGENT ---
# Catch and log the errors within an agent run
class AgentError(Exception):
    """An error that ends the whole run on purpose.

    max_steps           The loop in run() used up all MAX_STEPS steps without
                        getting an answer e.g. the model kept calling tools.

    fatal_model_error   A model call fails with an error that a retry cannot fix e.g. wrong API key (401), no access (403),
                        unknown model or wrong base URL (404).

    Errors that only affect a single step (rate limit, timeout, invalid tool call, a failing tool)
    are not AgentErrors, so they are logged and the run goes on with the next step.
    """

    def __init__(self, reason: str, message: str, steps: int):
        super().__init__(message)
        self.reason = reason  # max_steps | fatal_model_error (why)
        self.steps = steps  # how many steps were used

# Perform one call to the model
def call_model(messages: list, step: int, language_hint: str | None = None):
    """Performs one step of the agent, which is exactly one call to the language model.

    Therefore the whole conversation (`messages`) is sent to the model together with the tool
    descriptions. The model then either requests tool calls or answers with text.

    There are three possible outcomes:

    1. Success: returns the model's message. It contains either tool calls (executed in run())
                or a final text answer (so the run ends successfully in run()).

    2. The step failed and the run goes on: returns None. run() simply starts the next step with the same
       messages, so this is a retry. Each failed attempt still uses up one step, so MAX_STEPS
       stays a hard limit. This should cover:
         - RateLimitError (429): the token budget is used up. We wait as long as the server asks in the 
                                 "retry-after" header (min. 10s and max. MAX_WAIT_S).
         - Other API errors: e.g. (400) "tool_use_failed" or (500/503) "server problem". Here the agent waits 1 s.
         - APIConnectionError / APITimeoutError: no connection, or no response within the client's
           timeout (60 s). Here the agent waits 1 s.
         - An empty answer: no tool calls and no text. Here the agent doesn't wait.
       Each case is logged as an event "model_error" with ok=false, the step number and the error.

    3. Run cannot go on: this raises an AgentError("fatal_model_error"). This happens for FATAL_ERRORS,
                         where every retry would fail the same way. The main() function logs it as "error" and exits with code 1.

    If a language_hint is given, it is sent as the last message of this call only. It is not stored
    in `messages`, so it never piles up and is always directly before the model's answer.
    """
    start = time.perf_counter()
    request_messages = messages
    if language_hint:
        request_messages = messages + [{"role": "system", "content": language_hint}]
    try:
        # Execute the API request and save the response.
        response = client.chat.completions.create(
            model=MODEL, messages=request_messages, tools=TOOLS, tool_choice="auto"
        )
    except FATAL_ERRORS as e:
        # A retry would not help here so the run should be ended.
        raise AgentError("fatal_model_error", f"{type(e).__name__}: {e}", step) from e
    except (openai.APIStatusError, openai.APIConnectionError) as e:
        # If there are errors like rate limit, server error, timeout, invalid tool call (Groq: 400 tool_use_failed) 
        # then log them, wait if necessary and try again in the next step.
        duration = round((time.perf_counter() - start) * 1000)
        wait_s = 1.0
        if isinstance(e, openai.RateLimitError):
            try:
                wait_s = float(e.response.headers.get("retry-after", 10))
            except (TypeError, ValueError):
                wait_s = 10.0
        wait_s = min(wait_s, MAX_WAIT_S)
        log("model_error", ok=False, duration_ms=duration, step=step,
            error=f"{type(e).__name__}: {e}", wait_s=wait_s)
        if step < MAX_STEPS:
            time.sleep(wait_s)
        return None

    # Get the first response of the model.
    msg = response.choices[0].message
    # An answer without tool calls and without text is not an answer: count the step as failed.
    if not msg.tool_calls and not (msg.content or "").strip():
        log("model_error", ok=False, duration_ms=round((time.perf_counter() - start) * 1000),
            step=step, error="Empty answer from the model")
        return None
    return msg

# Execute one requested tool call
def execute_tool(tc, step: int) -> dict:
    """Execute one tool call requested by the model and return its result as a dict.

    The returned dict is sent back to the model as the tool's result (role "tool"). This function
    never raises: if something goes wrong, the result is {"error": "..."} instead. The model reads
    this error in the next step and can react to it, e.g. retry with a corrected date or tell the
    user that the data is unavailable. So a failing tool call never ends the run.

    Note: a day or place without data (HTTP 404) is not an error, but a result with found=false.
    """
    # Try to read the arguments of the function and check if they are in the correct format.
    name = tc.function.name
    try:
        args = json.loads(tc.function.arguments or "{}")
        if not isinstance(args, dict):
            raise ValueError("arguments must be a JSON object")
    except (json.JSONDecodeError, ValueError) as e:
        log("tool_call", ok=False, tool=name, args=tc.function.arguments, step=step,
            error=f"Invalid arguments: {e}")
        return {"error": f"Invalid arguments, expected a JSON object: {e}"}

    # Check if the called tool exists in the defined tools. If not: show the currently available tools.
    if name not in TOOL_FUNCTIONS:
        log("tool_call", ok=False, tool=name, args=args, step=step, error="Unknown tool")
        return {"error": f"Unknown tool '{name}'. Available: {', '.join(TOOL_FUNCTIONS)}"}

    log("tool_call", tool=name, args=args, step=step)

    # Execute the corresponding function and measure the duration.
    start = time.perf_counter()
    try:
        result = TOOL_FUNCTIONS[name](**args)
        ok, error = True, None
    except Exception as e:  # Return the error to the model as the tool's result.
        result = {"error": f"{type(e).__name__}: {e}"}
        ok, error = False, result["error"]
    duration = round((time.perf_counter() - start) * 1000)

    # Log the process.
    log("tool_result", ok=ok, tool=name, args=args, duration_ms=duration, step=step,
        result=result, error=error)
    return result


# Link the user's query, the language model, the calendar function and the response.
def run(task: str) -> str:
    """Let the model work step by step until it answers by itself or MAX_STEPS is reached."""
    # Detect the language of the question and choose the fixed sentence for it.
    language = detect_language(task)
    language_hint = LANGUAGE_HINTS.get(language)
    log("user_task", args={"task": task}) # task = user's question

    # Create the message for the language model.
    # The system section defines the behaviour and rules of the assistant, whilst user contains the specific question.
    messages = [
        {
            "role": "system",
            "content": (
                f"You are a day and travel planner assistant. Today is {date.today().isoformat()}. "
                "The user lives in Ulm. "
                "For questions about appointments, always use the tool get_calendar_day, "
                "once for every date the question is about. "
                "For weather, use get_weather; for travel by train, use get_train_connections. "
                "If a question needs several kinds of information, call every tool that is needed. "
                "If a tool call fails, check the error and try again with corrected arguments. "
                "But if a date does not exist (e.g. 31 February), tell the user and do not "
                "replace it with another date. "
                "Base your answer only on the tool results, never invent appointments, weather, "
                "trains or times, and do not use general knowledge to fill gaps. "
                "Only mention details that are in the tool results: do not add stations "
                "(e.g. main station), platforms, where to change trains or other facts that "
                "are not in the data. "
                "If a tool result has found=false, clearly say that there is no data for that "
                "place or day, and answer the rest of the question with the data you do have. "
                "When you have all the information you need, answer without calling any more tools. "
                "Language: write the whole answer in the language of the user's question. "
                "The data is in German; if the question is in English, translate titles and "
                "conditions into English and do not answer in German."
            ),
        },
        {"role": "user", "content": task},
    ]

    # Start a loop for multiple tool calls (max. MAX_STEPS).
    for step in range(1, MAX_STEPS + 1):
        # Call the language model
        msg = call_model(messages, step, language_hint)
        # If this step (model call) failed, the next step will try again.
        if msg is None:  
            continue

        # Check whether the model is complete. It is complete if there are no more tool calls.
        if not msg.tool_calls:
            answer = msg.content.strip()
            log("final", args={"answer": answer}, step=step, steps=step, reason="answer")
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
            result = execute_tool(tc, step)

            # Return the tool result to the model.
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

    # If the step limit was reached without an answer, then mark this as an error, not a success.
    raise AgentError("max_steps", f"Step limit of {MAX_STEPS} reached without an answer.", MAX_STEPS)


# Define how the program starts from the command line.
def main() -> int:
    # Make sure to always print in UTF-8, because the Windows console would otherwise fail on characters like ' '.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    # Check whether a question has been provided.
    if len(sys.argv) < 2:
        print(
            "No question given. Start the agent with your question in quotes, "
            'e.g. python -m agent "What is in the calendar on 29.10.2026?"',
            file=sys.stderr,
        )
        return 2

    # Construct the question correctly, using spaces.
    task = " ".join(sys.argv[1:])

    # Run the process and catch the errors.
    try:
        print(run(task))
        return 0
    except AgentError as e:
        log("error", ok=False, error=str(e), reason=e.reason, steps=e.steps)
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        log("error", ok=False, error=f"{type(e).__name__}: {e}", reason="exception")
        print(f"Error: {e}", file=sys.stderr)
        return 1


# Ensure, that main() is automatically executed only when the file is launched directly (entry point).
if __name__ == "__main__":
    exit_code = main()
    # Only describe if there are errors, not if it was a successful run.
    if exit_code != 0:
        describe_exit(exit_code)
    sys.exit(exit_code)
