"""agent/understand.py - rule-based interpreter (no language model).

understand(question, context) reads a plain-English question and returns the intent,
store, metric, date or range, product, weather flag, a confidence and the list of
required entities that are still missing. It also returns new_context, which the caller
keeps for the next question of the same session.
"""
import re
from datetime import date, timedelta
from difflib import SequenceMatcher

AS_OF_DATE = date(2026, 6, 30)      # "yesterday" is 2026-06-29
THRESHOLD = 0.7                      # below this the agent asks for clarification

STORES = ["Mumbai", "Pune", "Hyderabad", "Bengaluru", "Ahmedabad"]
ALIASES = {"bangalore": "Bengaluru"}
PRODUCTS = ["Amul Milk 1L", "Toor Dal 1kg", "Basmati Rice 5kg", "Sunflower Oil 1L",
            "Iodised Salt 1kg", "Instant Noodles 70g", "Glucose Biscuits 200g",
            "Detergent Powder 1kg"]


def _forms(*words):
    out = set()
    for w in words:
        out |= {w, w + "s", w + "es"}
        if w.endswith("y"):
            out.add(w[:-1] + "ies")
    return out


# ---------- word lists (closed) ----------
METRIC_OF = {}
for _w in ("revenue", "revenues", "sales", "turnover", "turnovers", "earnings", "earning"):
    METRIC_OF[_w] = "revenue_inr"
for _w in ("target", "targets"):
    METRIC_OF[_w] = "daily_target_inr"
for _w in ("footfall", "footfalls", "visitors", "visitor"):
    METRIC_OF[_w] = "footfall"
for _w in ("stockout", "stockouts"):
    METRIC_OF[_w] = "stockout_hours"
for _w in ("discount", "discounts"):
    METRIC_OF[_w] = "discount_pct"

OVERRIDE = {"ignore", "ignores", "ignoring", "disregard", "disregards", "override", "overrides",
            "bypass", "bypasses", "forget", "send", "sends", "sending", "email", "emails",
            "whatsapp", "purchase", "purchases", "buy", "buys", "restock", "restocks"}
UNSUPPORTED = _forms("profit", "margin", "marketing", "cost", "expense", "shortfall",
                     "efficiency", "weekend")
DIAGNOSTIC = _forms("why", "trend", "reason")
INVENTORY_W = {"reorder", "reorders", "inventory", "inventories"}
FEEDBACK_W = _forms("feedback", "review", "rating")
TARGET_W = {"target", "targets"}
TARGET_PARTNER = {"hit", "hits", "met", "meet", "meets", "miss", "misses", "missed", "beat",
                  "beats", "exceed", "exceeds", "exceeded", "achieve", "achieves", "achieved",
                  "reach", "reaches", "reached", "below", "above", "against", "versus"}
ACHIEVEMENT_W = {"achievement", "achievements"}
COMPARISON = {"which", "highest", "lowest", "best", "worst"}
WEATHER = _forms("weather", "rain", "temperature", "humidity", "hot", "cold")

MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august",
          "september", "october", "november", "december"]
MONTH_NUM = {m: i + 1 for i, m in enumerate(MONTHS)}
MONTH_ALWAYS = {"january", "february", "april", "june", "july", "august", "september",
                "october", "november", "december",
                "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec"}
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
PLURAL_WEEKDAYS = {w + "s" for w in WEEKDAYS} | {"weekdays"}
PREPS = {"in", "on", "of", "during", "since", "for", "from", "until", "till", "by", "to",
         "through", "throughout", "before", "after", "within", "over"}

# words that name a time period outside the closed date grammar
DATE_PHRASE_WORDS = ({"today", "tonight", "tomorrow", "past", "previous", "ago", "recent",
                      "recently", "latest", "now", "lately", "last", "next", "morning",
                      "afternoon", "evening", "fortnight", "fortnights", "ytd", "mtd", "qtd",
                      "eod", "eom", "eoy", "between"}
                     | _forms("week", "month", "quarter", "year"))
FREQUENCY_W = {"daily", "weekly", "monthly", "quarterly", "yearly", "annual"}

STOP = {"hello", "thanks", "thank", "kindly", "please", "display", "compare", "which", "what",
        "whats", "how", "why", "did", "and", "show", "check", "report", "where", "would",
        "could", "can", "will", "give", "tell", "list"}
BRAND = {"dmart", "avenue", "supermarts", "kavita", "rao", "meteo", "github", "python",
         "sqlite", "postgresql", "markdown"}

KEYWORDS = (set(METRIC_OF) | OVERRIDE | UNSUPPORTED | DIAGNOSTIC | INVENTORY_W | FEEDBACK_W
            | TARGET_PARTNER | ACHIEVEMENT_W | COMPARISON | WEATHER | DATE_PHRASE_WORDS
            | FREQUENCY_W | set(MONTHS) | MONTH_ALWAYS | set(WEEKDAYS) | PLURAL_WEEKDAYS
            | {"yesterday", "order", "reorder", "place", "customers", "customer", "say", "says",
               "saying", "performance", "band", "bands", "fall", "falls", "short", "average",
               "averages", "threshold", "stock", "units"})

REQUIRED = {"lookup": ["store", "metric", "date"], "target_vs_actual": ["store", "date"],
            "comparison": ["metric", "date"], "inventory": ["product"],
            "feedback": ["store"], "weather": ["store", "date"]}
SINGLE_DATE = {"target_vs_actual", "weather"}      # a range is not allowed here
STORE_INTENTS = {"lookup", "target_vs_actual", "comparison", "inventory", "feedback", "weather"}

# ---------- date grammar ----------
_MON = "(?:" + "|".join(MONTHS) + ")"
_DMY = r"\d{1,2}\s+" + _MON + r"\s+\d{4}"
_ISO = r"\d{4}-\d{2}-\d{2}"
_ANY = "(?:" + _DMY + "|" + _ISO + ")"
BETWEEN_RE = re.compile(r"(?<![\w-])between\s+(" + _ANY + r")\s+and\s+(" + _ANY + r")(?![\w-])", re.I)
DMY_RE = re.compile(r"(?<![\w-])(\d{1,2})\s+(" + _MON + r")\s+(\d{4})(?![\w-])", re.I)
ISO_RE = re.compile(r"(?<![\w-])(\d{4})-(\d{2})-(\d{2})(?![\w-])")
LOOKS_LIKE_DATE = re.compile(
    r"\b\d{4}-\d{1,2}-\d{1,2}\b|\b\d{4}-w\d{1,2}(?:-\d)?\b|\b\d{8}\b"
    r"|\b\d{1,4}[/.]\d{1,2}[/.]\d{1,4}\b|\b\d{1,2}-\d{1,2}-\d{2,4}\b"
    r"|\b\d{1,2}(?:st|nd|rd|th)\b|\b(?:19|20)\d{2}\b|\bq[1-4]\b|\bfy\s?\d{2,4}\b", re.I)


def _mk(y, m, d):
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _parse_any(s):
    s = s.strip()
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return _mk(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", s)
    if m:
        return _mk(int(m.group(3)), MONTH_NUM[m.group(2).lower()], int(m.group(1)))
    return None


def _parse_dates(work):
    """Returns {'state': none|single|range|unresolved, 'start': iso|None, 'end': iso|None}."""
    s = work
    flags = {"unresolved": False}
    singles, ranges = [], []

    def take_between(m):
        a, b = _parse_any(m.group(1)), _parse_any(m.group(2))
        if a is None or b is None or a > b:
            flags["unresolved"] = True
        else:
            ranges.append((a, b))
        return " "

    def take_dmy(m):
        d = _mk(int(m.group(3)), MONTH_NUM[m.group(2).lower()], int(m.group(1)))
        if d is None:
            flags["unresolved"] = True
        else:
            singles.append(d)
        return " "

    def take_iso(m):
        d = _mk(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d is None:
            flags["unresolved"] = True
        else:
            singles.append(d)
        return " "

    s = BETWEEN_RE.sub(take_between, s)
    s = DMY_RE.sub(take_dmy, s)
    s = ISO_RE.sub(take_iso, s)
    if re.search(r"\byesterday\b", s, re.I):
        singles.append(AS_OF_DATE - timedelta(days=1))
        s = re.sub(r"\byesterday\b", " ", s, flags=re.I)
    s = re.sub(r"\bper\s+(?:day|week|month|year)s?\b", " ", s, flags=re.I)   # frequency, not a date

    if LOOKS_LIKE_DATE.search(s):
        flags["unresolved"] = True
    toks = [m.group() for m in re.finditer(r"[A-Za-z]+", s)]
    weekday_hits, plural_hits = [], []
    for i, w in enumerate(toks):
        lw = w.lower()
        prev = toks[i - 1].lower() if i else ""
        nxt = toks[i + 1].lower() if i + 1 < len(toks) else ""
        if lw in DATE_PHRASE_WORDS or lw in MONTH_ALWAYS:
            flags["unresolved"] = True
        elif lw == "march":
            if w[0].isupper() or prev in PREPS:
                flags["unresolved"] = True
        elif lw == "may":
            if w[0].isupper():
                if nxt not in {"i", "we", "you", "be"}:
                    flags["unresolved"] = True
            elif prev in PREPS:
                flags["unresolved"] = True
        elif lw in WEEKDAYS:
            weekday_hits.append(lw)
        elif lw in PLURAL_WEEKDAYS:
            plural_hits.append(lw)
    if weekday_hits:
        ok = (len(singles) == 1 and not ranges
              and all(WEEKDAYS.index(w) == singles[0].weekday() for w in weekday_hits))
        if not ok:
            flags["unresolved"] = True
    if plural_hits and not ranges:
        flags["unresolved"] = True
    if len(singles) + len(ranges) > 1:
        flags["unresolved"] = True

    if flags["unresolved"]:
        return {"state": "unresolved", "start": None, "end": None}
    if len(ranges) == 1:
        return {"state": "range", "start": ranges[0][0].isoformat(), "end": ranges[0][1].isoformat()}
    if len(singles) == 1:
        return {"state": "single", "start": singles[0].isoformat(), "end": singles[0].isoformat()}
    return {"state": "none", "start": None, "end": None}


# ---------- tokens, products, metrics, stores ----------
def _tokenize(work):
    out = []
    for m in re.finditer(r"[A-Za-z]+(?:'s)?|\d+", work):
        tok = m.group()
        poss = tok.lower().endswith("'s")
        base = tok[:-2] if poss else tok
        out.append({"text": tok, "base": base, "lower": base.lower(), "poss": poss, "pos": m.start()})
    return out


def _find_product(work):
    for name in PRODUCTS:
        base = re.sub(r"\s+\d+\w*$", "", name)
        size = name[len(base):].strip()
        pat = r"\b" + r"\s+".join(re.escape(w) for w in base.split())
        if size:
            pat += r"(?:\s+" + re.escape(size) + r")?"
        pat += r"\b"
        if re.search(pat, work, re.I):
            return name, {w.lower() for w in name.split()}
    return None, set()


def _find_metrics(words):
    found = []
    for w in words:
        m = METRIC_OF.get(w)
        if m and m not in found:
            found.append(m)
    return found


def _find_stores(work, toks, product_words, has_metric, has_weather, has_date):
    """Returns ({store: confidence}, unresolved_named_store)."""
    stores = {}
    for s in STORES:
        if re.search(r"\b" + s + r"\b", work, re.I):
            stores[s] = 1.0
    for alias, s in ALIASES.items():
        if re.search(r"\b" + alias + r"\b", work, re.I):
            stores[s] = 1.0
    exact_names = {s.lower() for s in STORES} | set(ALIASES)

    cands = []
    for i, t in enumerate(toks):
        base = t["base"]
        if len(base) < 5 or not base.isalpha():
            continue
        if not (base[0].isupper() or t["poss"]):
            continue
        if i == 0 and not t["poss"]:
            continue
        b = t["lower"]
        if b in KEYWORDS or b in STOP or b in BRAND or b in product_words or b in exact_names:
            continue
        scores = {s: SequenceMatcher(None, b, s.lower()).ratio() for s in STORES}
        best = max(scores, key=scores.get)
        cands.append((i, t, best, scores[best]))

    for i, t, best, sc in cands:
        if sc >= THRESHOLD:
            stores[best] = max(stores.get(best, 0.0), round(sc, 2))
    resolved_any = bool(stores)

    unresolved = False
    for i, t, best, sc in cands:
        if sc >= THRESHOLD:
            continue
        prev = toks[i - 1]["lower"] if i else ""
        if t["poss"] or prev in {"and", "or", "vs", "versus", "than", "for"}:
            unresolved = True
        elif not resolved_any and (prev in {"about", "in", "at"} or has_metric
                                   or has_weather or has_date):
            unresolved = True
    if not resolved_any:                      # brand or persona noun used as a store name
        for i, t in enumerate(toks):
            prev = toks[i - 1]["lower"] if i else ""
            if t["lower"] in BRAND and (t["poss"] or prev in {"for", "about", "in", "at"}):
                unresolved = True
    return stores, unresolved


# ---------- intent ----------
def _is_override(work, low, toks, words):
    if any(w in OVERRIDE for w in words):
        return True
    if re.search(r"\bplace\s+an\s+order\b", low):
        return True
    for i, w in enumerate(words):
        if w not in ("order", "reorder"):
            continue
        nxt = words[i + 1] if i + 1 < len(words) else ""
        if nxt in {"threshold", "thresholds", "level", "levels", "point", "points"}:
            continue
        prev = words[i - 1] if i else ""
        two = words[i - 2:i] if i >= 2 else []
        three = words[i - 3:i] if i >= 3 else []
        before = work[:toks[i]["pos"]].rstrip()
        if (i == 0 or prev in {"please", "kindly"}
                or two in (["can", "you"], ["could", "you"], ["will", "you"], ["would", "you"])
                or three == ["go", "ahead", "and"] or before.endswith(",")):
            return True
    return False


def _decide_intent(work, low, toks, words, product, metrics, weather, dstate, store_named, ctx):
    wset = set(words)
    if _is_override(work, low, toks, words):                                   # 1
        return "out_of_scope"
    if wset & UNSUPPORTED or re.search(r"\bper\s+(?:footfall|visitor)s?\b", low):   # 2
        return "unsupported_metric"
    if wset & DIAGNOSTIC:                                                      # 3
        return "diagnostic"
    if product or wset & INVENTORY_W:                                          # 4
        return "inventory"
    if wset & FEEDBACK_W or re.search(r"\bcustomers?\s+(?:say|says|saying)\b", low):   # 5
        return "feedback"
    if ((wset & TARGET_W and (wset & TARGET_PARTNER or re.search(r"\bfalls?\s+short\b", low)))
            or wset & ACHIEVEMENT_W or re.search(r"\bperformance\s+bands?\b", low)):   # 6
        return "target_vs_actual"
    if wset & COMPARISON and not store_named:                                  # 7
        return "comparison"
    if metrics:                                                                # 8
        return "lookup"
    if weather:                                                                # 9
        return "weather"
    if store_named or dstate != "none":                                        # 10
        return "target_vs_actual" if ctx.get("last_tva") else "lookup"
    return "out_of_scope"                                                      # 11


# ---------- main entry ----------
def understand(question, context=None):
    ctx = dict(context or {})
    work = question.replace("\u2019", "'").replace("_", " ")
    low = work.lower()
    toks = _tokenize(work)
    words = [t["lower"] for t in toks]

    product, product_words = _find_product(work)
    metrics = _find_metrics(words)
    weather = any(w in WEATHER for w in words)
    ds = _parse_dates(work)
    stores, unresolved_store = _find_stores(work, toks, product_words, bool(metrics),
                                            weather, ds["state"] != "none")
    store_named = bool(stores) or unresolved_store
    intent = _decide_intent(work, low, toks, words, product, metrics, weather,
                            ds["state"], store_named, ctx)

    rank_word = "highest"
    for w in words:
        if w in ("highest", "lowest", "best", "worst"):
            rank_word = w
            break

    store_val = metric_val = product_val = start = end = None
    store_conf = None
    is_range = False
    missing, unresolved_list, ambiguous = [], [], []
    req = REQUIRED.get(intent, [])

    if intent in STORE_INTENTS:
        # store
        if unresolved_store:
            unresolved_list.append("store")
        elif len(stores) > 1:
            ambiguous.append({"kind": "store", "options": sorted(stores)})
        elif stores:
            store_val, store_conf = next(iter(stores.items()))
        elif "store" in req:
            if ctx.get("store"):
                store_val, store_conf = ctx["store"], 1.0
            else:
                missing.append("store")
        # metric
        if intent in ("lookup", "comparison"):
            if len(metrics) > 1:
                ambiguous.append({"kind": "metric", "options": metrics})
            elif metrics:
                metric_val = metrics[0]
            elif ctx.get("metric"):
                metric_val = ctx["metric"]
            else:
                missing.append("metric")
        elif intent == "target_vs_actual":
            metric_val = "revenue_inr"          # fixed: revenue against target
        # date (inventory and feedback drop any date)
        if "date" in req:
            st = ds["state"]
            if st == "unresolved":
                unresolved_list.append("date")
            elif st == "range":
                if intent in SINGLE_DATE:
                    unresolved_list.append("date")
                else:
                    start, end, is_range = ds["start"], ds["end"], True
            elif st == "single":
                start, end = ds["start"], ds["end"]
            else:
                cd = ctx.get("date_value")
                if cd:
                    if cd["is_range"] and intent in SINGLE_DATE:
                        unresolved_list.append("date")
                    else:
                        start, end, is_range = cd["start"], cd["end"], cd["is_range"]
                else:
                    missing.append("date")
        # product
        if intent == "inventory":
            if product:
                product_val = product
            elif ctx.get("product"):
                product_val = ctx["product"]
            else:
                missing.append("product")

    problems = [e for e in ("store", "metric", "date", "product")
                if e in missing or e in unresolved_list]
    if problems or ambiguous:
        confidence = 0.4
    else:
        confs = []
        if store_val:
            confs.append(store_conf)
        confidence = min(confs) if confs else 1.0

    # session context: only the used entities that were resolved are stored
    new_ctx = dict(ctx)
    if intent in REQUIRED:
        stored_store = "store" not in unresolved_list and not any(a["kind"] == "store" for a in ambiguous)
        if store_val and stored_store:
            new_ctx["store"] = store_val
        if intent in ("lookup", "comparison") and metric_val and not any(a["kind"] == "metric" for a in ambiguous):
            new_ctx["metric"] = metric_val
        if start:
            new_ctx["date_value"] = {"start": start, "end": end, "is_range": is_range}
        if product_val:
            new_ctx["product"] = product_val
        new_ctx["last_tva"] = intent == "target_vs_actual"

    return {
        "question": question, "intent": intent, "store": store_val, "metric": metric_val,
        "date": start if (start and not is_range) else None,
        "start": start, "end": end, "is_range": is_range, "product": product_val,
        "weather": weather, "confidence": round(confidence, 2), "missing": problems,
        "unresolved": unresolved_list, "ambiguous": ambiguous or None, "rank_word": rank_word,
        "needs_clarification": confidence < THRESHOLD, "new_context": new_ctx,
    }