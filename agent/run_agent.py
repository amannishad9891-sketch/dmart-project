"""agent/run_agent.py - handle(question, session_id) runs the whole pipeline and logs the run.

Pipeline: Interpret (understand) -> Route -> Query (fetch) -> Validate (inside fetch, before the
query runs) -> Calculate (fetch) -> Synthesize (answer templates) -> Ground -> Record (log line).
Default settings: LLM_MODE=mock (rule-based interpreter), WEATHER_MODE=stub.
"""
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent import answer, fetch                      # noqa: E402
from agent.understand import understand              # noqa: E402

SESSIONS = {}          # session_id -> context (never shared between sessions)
BUDGET_TOKENS = 150
STATUSES = ("Answered", "Drafted", "Clarification Needed", "Escalated", "Safe Failure")


def _weather(city, date):
    try:
        from tools.weather import get_weather
    except ImportError:
        return {"ok": False, "error": "weather tool not available"}
    return get_weather(city, date)


def _log_path():
    p = Path(os.environ.get("AGENT_LOG_PATH", "logs/runs.jsonl"))   # read on every call
    return p if p.is_absolute() else ROOT / p


def _fetch_for(u):
    """Runs the data query for the intent. Returns the fetched dictionary."""
    intent = u["intent"]
    if intent == "lookup":
        if u["is_range"]:
            return fetch.get_average(u["store"], u["metric"], u["start"], u["end"])
        return fetch.get_value(u["store"], u["date"], u["metric"])
    if intent == "target_vs_actual":
        return fetch.target_vs_actual(u["store"], u["date"])
    if intent == "comparison":
        direction = fetch.direction_for(u["rank_word"], u["metric"])
        return fetch.compare_stores(u["metric"], u["start"], u["end"], direction)
    if intent == "inventory":
        return fetch.below_threshold(u["product"], u["store"])
    if intent == "feedback":
        return fetch.feedback_summary(u["store"])
    raise fetch.AgentError("no data route for this intent")


def _compose(u, f):
    return {"lookup": answer.lookup_reply, "target_vs_actual": answer.target_reply,
            "comparison": answer.comparison_reply, "inventory": answer.inventory_reply,
            "feedback": answer.feedback_reply}[u["intent"]](u, f)


def handle(question, session_id, user_id="u1"):
    t0 = time.perf_counter()
    u = understand(question, SESSIONS.get(session_id, {}))
    SESSIONS[session_id] = u["new_context"]
    intent = u["intent"]

    status, text = "Answered", ""
    evidence, grounded = [], []
    route, executed, attempts, tool_calls, tools_called = "none", None, 0, 0, []

    # Precedence 1: the intent itself
    if intent == "unsupported_metric":
        status, text = "Safe Failure", answer.unsupported_reply()
    elif intent in ("out_of_scope", "diagnostic"):
        status = "Escalated"
        text = answer.out_of_scope_reply() if intent == "out_of_scope" else answer.diagnostic_reply()
    # Precedence 2: clarification
    elif u["needs_clarification"]:
        status, text = "Clarification Needed", answer.clarification_reply(u)
    else:
        try:
            if intent == "weather":
                # Precedence 3: the date range check, before the weather tool is called
                fetch.check_dates(u["date"])
                w = _weather(u["store"], u["date"])
                route, tool_calls, tools_called = "weather", 1, ["weather_tool"]
                executed = f"get_weather(city={u['store']!r}, date={u['date']!r})"
                if w.get("ok"):
                    text, evidence, grounded = answer.weather_reply(w)
                else:
                    status, text = "Safe Failure", "Weather data is not available for that request."
            else:
                f = _fetch_for(u)                       # Precedence 3 and 4 happen inside fetch
                route, executed, attempts, tool_calls = f["route"], f["executed"], f["attempts"], 1
                if not f["found"]:
                    status, text = "Safe Failure", answer.no_record_reply()
                else:
                    text, evidence, grounded = _compose(u, f)
                    if f.get("alert"):
                        status = "Drafted"
                    # weather is added only to a one-store, one-date lookup or target check
                    if (u["weather"] and intent in ("lookup", "target_vs_actual")
                            and not u["is_range"]):
                        w = _weather(u["store"], u["date"])
                        route, tool_calls, tools_called = "python+weather", 2, ["weather_tool"]
                        if w.get("ok"):
                            text, evidence, grounded = answer.add_weather(text, evidence, grounded, w)
                        else:
                            text += " Weather is not available right now."
        except (fetch.DateOutOfRange, fetch.FieldNotApproved) as exc:
            status, text = "Safe Failure", answer.safe_failure_reply(str(exc))
            route, executed, attempts, tool_calls, tools_called = "none", None, 0, 0, []
            evidence, grounded = [], []
        except fetch.QueryFailed as exc:
            status, text = "Escalated", answer.escalated_after_retries()
            route, executed, attempts, tool_calls = exc.route, exc.executed, exc.attempts, 1
            evidence, grounded = [], []

    ungrounded = answer.count_ungrounded(text, grounded)
    tokens_est = len(question.split()) + len(text.split())
    record = {
        "run_id": uuid.uuid4().hex, "user_id": user_id, "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "question": question, "intent": intent, "confidence": u["confidence"],
        "route": route, "executed": executed, "attempts": attempts,
        "tools_called": tools_called, "status": status, "answer_text": text,
        "evidence": evidence, "grounded_values": grounded,
        "latency_ms": round((time.perf_counter() - t0) * 1000, 3),
        "tokens_est": tokens_est, "tool_calls": tool_calls,
        "ungrounded_numbers": ungrounded, "budget_exceeded": tokens_est > BUDGET_TOKENS,
    }
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    return record