"""agent/answer.py - builds the reply from fetched values (fixed templates, no language model).

Every number in a reply is registered in grounded_values at the moment it is written,
using the fetched value itself. grounded_values is never built by scanning the finished text.
"""
import re
from decimal import Decimal, ROUND_HALF_UP

STORE_LIST = "Mumbai, Pune, Hyderabad, Bengaluru or Ahmedabad"
PRODUCT_NAMES = ["Amul Milk 1L", "Toor Dal 1kg", "Basmati Rice 5kg", "Sunflower Oil 1L",
                 "Iodised Salt 1kg", "Instant Noodles 70g", "Glucose Biscuits 200g",
                 "Detergent Powder 1kg"]
LABEL = {"revenue_inr": "revenue", "daily_target_inr": "target", "footfall": "footfall",
         "stockout_hours": "stockout hours", "discount_pct": "discount"}
ENTITY_WORD = {"store": "the store", "metric": "the metric", "date": "the date",
               "product": "the product"}


# ---------- number formats ----------
def _q(v, places):
    exp = Decimal(1).scaleb(-places)
    return Decimal(str(v)).quantize(exp, rounding=ROUND_HALF_UP)


class Grounded:
    """Collects the numbers a reply takes from fetched records, exactly as written."""

    def __init__(self):
        self.values = []

    def _add(self, text):
        self.values.append(text)
        return text

    def money(self, v):
        return "INR " + self._add(f"{_q(v, 2)}")

    def pct(self, v):
        return self._add(f"{_q(v, 2)}") + "%"

    def d2(self, v):
        return self._add(f"{_q(v, 2)}")

    def d1(self, v):
        return self._add(f"{_q(v, 1)}")

    def integer(self, v):
        return self._add(str(int(v)))

    def metric(self, name, v):
        if name in ("revenue_inr", "daily_target_inr"):
            return self.money(v)
        if name == "discount_pct":
            return self.pct(v)
        return self.d2(v)


def count_ungrounded(text, grounded_values):
    """Numbers in the text that match no grounded value (ISO dates and sized product names removed)."""
    t = text
    for name in PRODUCT_NAMES:
        t = re.sub(re.escape(name), " ", t, flags=re.I)
    t = re.sub(r"\d{4}-\d{2}-\d{2}", " ", t)
    return sum(1 for n in re.findall(r"\d+(?:\.\d+)?", t) if n not in set(grounded_values))


def _span(start, end):
    return start if start == end else f"{start} to {end}"


def _ev(source, fields, store, date):
    return {"source": source, "fields": fields, "store": store, "date": date}


# ---------- fixed (non-data) replies ----------
def unsupported_reply():
    return ("That field is not available. I can report revenue, target, footfall, stockout hours, "
            "discount, achievement, performance band, stock units, reorder threshold, rating and theme.")


def out_of_scope_reply():
    return ("This question is out of scope. I can only report the five DMart stores' revenue, target, "
            "footfall, stockout hours, discount, inventory and customer feedback, and I cannot take "
            "actions such as sending messages or ordering stock.")


def diagnostic_reply():
    return ("This is a why question, so an analyst is needed. I can report the figures, but I cannot "
            "give a reason or call a link between figures a cause.")


def clarification_reply(u):
    parts = []
    if u.get("ambiguous"):
        for a in u["ambiguous"]:
            if a["kind"] == "store":
                parts.append("Your question names more than one store (" + ", ".join(a["options"])
                             + "). Which one do you mean?")
            else:
                parts.append("Your question names more than one metric (" + ", ".join(a["options"])
                             + "). Which one do you mean?")
    unresolved = u.get("unresolved", [])
    missing = [e for e in u.get("missing", []) if e not in unresolved]
    if unresolved:
        words = " and ".join(ENTITY_WORD[e] for e in unresolved)
        parts.append(f"I could not resolve {words}.")
    if missing:
        words = ", ".join(ENTITY_WORD[e] for e in missing[:-1])
        words = (words + " and " if words else "") + ENTITY_WORD[missing[-1]]
        parts.append(f"I need {words} to answer.")
    for e in u.get("missing", []):
        if e == "store":
            parts.append("Which store do you mean: " + STORE_LIST + "?")
        elif e == "metric":
            parts.append("Which metric: revenue, target, footfall, stockout hours or discount?")
        elif e == "date":
            if u["intent"] in ("target_vs_actual", "weather"):
                parts.append("Give one date in the form YYYY-MM-DD, or say yesterday. A range is not "
                             "allowed here.")
            else:
                parts.append("Which date? Use the form YYYY-MM-DD, yesterday, or between <date> and <date>.")
        elif e == "product":
            parts.append("Which product do you mean?")
    return " ".join(parts) if parts else "Could you rephrase the question?"


def safe_failure_reply(message):
    return message


def escalated_after_retries():
    return "The data query failed after three attempts, so this is escalated to an analyst."


def no_record_reply():
    return "No record was found for that request."


# ---------- data replies ----------
def lookup_reply(u, f):
    g = Grounded()
    label = LABEL[f["metric"]]
    if "value" in f and "start" not in f:        # one store, one date
        text = f"{f['store']}'s {label} on {f['date']} was {g.metric(f['metric'], f['value'])}."
        ev = _ev("store_daily", [f["metric"]], f["store"], f["date"])
    else:                                        # range average
        text = (f"{f['store']}'s average {label} between {f['start']} and {f['end']} was "
                f"{g.metric(f['metric'], f['value'])}.")
        ev = _ev("store_daily", [f["metric"]], f["store"], _span(f["start"], f["end"]))
    return text, [ev], g.values


def target_reply(u, f):
    g = Grounded()
    text = (f"{f['store']} on {f['date']}: revenue {g.money(f['revenue'])} against a target of "
            f"{g.money(f['target'])}, achievement {g.pct(f['achievement_pct'])}, band {f['band']}.")
    if f.get("alert"):
        text += (f" This is below the {g.d2(75)}% alert threshold, so the reply is held for approval.")
    ev = _ev("store_daily", ["revenue_inr", "daily_target_inr", "achievement_pct", "performance_band"],
             f["store"], f["date"])
    return text, [ev], g.values


def comparison_reply(u, f):
    g = Grounded()
    label = LABEL[f["metric"]]
    when = (f"on {f['start']}" if f["start"] == f["end"]
            else f"between {f['start']} and {f['end']}")
    head = f"{label.capitalize()} per store" if f["start"] == f["end"] else f"Average {label} per store"
    items = "; ".join(f"{r['store']} {g.metric(f['metric'], r['value'])}" for r in f["ranking"])
    text = (f"{head} {when}, {f['direction']} first: {items}. "
            f"{f['direction'].capitalize()}: {f['ranking'][0]['store']}.")
    ev = _ev("store_daily", [f["metric"]], "all", _span(f["start"], f["end"]))
    return text, [ev], g.values


def inventory_reply(u, f):
    g = Grounded()
    if not f["below"]:
        text = f"No store is below its reorder threshold for {f['product']}."
    else:
        items = "; ".join(
            f"{b['store']} {g.integer(b['stock_units'])} units (reorder threshold "
            f"{g.integer(b['reorder_threshold'])})" for b in f["below"])
        text = f"Below the reorder threshold for {f['product']}: {items}."
    ev = _ev("inventory", ["stock_units", "reorder_threshold"], f["store"] or "all", None)
    return text, [ev], g.values


def feedback_reply(u, f):
    g = Grounded()
    if f["avg_rating"] is None:
        text = (f"{f['store']} has no rated feedback rows. Most frequent theme: {f['top_theme']}.")
    else:
        text = (f"{f['store']} customers: average rating {g.d2(f['avg_rating'])} over "
                f"{g.integer(f['rated_rows'])} rated rows of {g.integer(f['all_rows'])} rows. "
                f"Most frequent theme: {f['top_theme']}.")
    ev = _ev("feedback", ["rating", "theme"], f["store"], None)
    return text, [ev], g.values


def weather_sentence(g, w):
    return (f"temperature {g.d1(w['temperature_c'])} C, humidity {g.d1(w['humidity_pct'])}%, "
            f"wind {g.d1(w['wind_kmh'])} km/h, rain {g.d1(w['rain_mm'])} mm")


def weather_evidence(w):
    return _ev("weather_tool", ["temperature_c", "humidity_pct", "wind_kmh", "rain_mm"],
               w["city"], w["date"])


def add_weather(text, evidence, grounded_values, w):
    """Append the weather to a lookup or target_vs_actual reply."""
    g = Grounded()
    sentence = weather_sentence(g, w)
    text = text + f" Weather in {w['city']} on {w['date']}: {sentence}."
    return text, evidence + [weather_evidence(w)], grounded_values + g.values


def weather_reply(w):
    g = Grounded()
    sentence = weather_sentence(g, w)
    return f"Weather in {w['city']} on {w['date']}: {sentence}.", [weather_evidence(w)], g.values