"""agent/fetch.py - data layer of the agent.

Runs only validated queries on approved fields, on cleaned data.
Python function: one value for one store and one date, target_vs_actual.
SQL (SQLite, ? placeholders): range average, comparison, inventory, feedback.
"""
import os
import sqlite3
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

DATA_START = "2026-04-01"
DATA_END = "2026-06-29"
MAX_ATTEMPTS = 3

# The 11 reportable fields, by table.
APPROVED = {
    "store_daily": {"revenue_inr", "daily_target_inr", "footfall", "stockout_hours",
                    "discount_pct", "achievement_pct", "performance_band"},
    "inventory": {"stock_units", "reorder_threshold"},
    "feedback": {"rating", "theme"},
}
# Key columns: only filters, group-by keys or row labels, never a measured value.
KEYS = {"store", "store_id", "date", "product", "product_id"}
# Numeric metrics that can be looked up or averaged.
LOOKUP_METRICS = {"revenue_inr", "daily_target_inr", "footfall", "stockout_hours", "discount_pct"}


class AgentError(Exception):
    pass


class FieldNotApproved(AgentError):
    pass


class DateOutOfRange(AgentError):
    pass


class SimulatedFailure(Exception):
    pass


class QueryFailed(AgentError):
    """Raised after the third failed attempt."""

    def __init__(self, message, attempts, route, executed):
        super().__init__(message)
        self.attempts = attempts
        self.route = route
        self.executed = executed


# ---------- database (built once from the CSV files) ----------
_df = None
_conn = None


def _create_table(conn, name, df):
    cols = ", ".join(df.columns)
    conn.execute(f"CREATE TABLE {name} ({cols})")
    rows = []
    for r in df.itertuples(index=False, name=None):
        rows.append(tuple(None if pd.isna(v) else (v.item() if hasattr(v, "item") else v) for v in r))
    marks = ",".join("?" * len(df.columns))
    conn.executemany(f"INSERT INTO {name} VALUES ({marks})", rows)


def _load():
    global _df, _conn
    if _conn is None:
        _df = pd.read_csv(DATA / "store_daily_clean.csv")   # cleaned file, not the raw one
        inv = pd.read_csv(DATA / "inventory.csv")
        fb = pd.read_csv(DATA / "feedback.csv")
        _conn = sqlite3.connect(":memory:")
        _create_table(_conn, "store_daily", _df)
        _create_table(_conn, "inventory", inv)
        _create_table(_conn, "feedback", fb)
    return _df, _conn


# ---------- checks ----------
def validate(table, measured=(), labels=()):
    """Approved-field and table check. Runs before any query."""
    if table not in APPROVED:
        raise FieldNotApproved(f"The table {table} is not available.")
    for c in measured:
        if c not in APPROVED[table]:
            raise FieldNotApproved(f"The field {c} is not available.")
    for c in labels:
        if c not in KEYS:
            raise FieldNotApproved(f"The column {c} is not available.")


def check_dates(start, end=None):
    end = end or start
    for d in (start, end):
        if not (DATA_START <= d <= DATA_END):
            raise DateOutOfRange(f"The data covers {DATA_START} to {DATA_END}.")


def _need_lookup_metric(metric):
    if metric not in LOOKUP_METRICS:
        raise FieldNotApproved(f"The field {metric} is not available for this question.")


# ---------- rounding ----------
def avg_half_up(sum_cents, count):
    """Exact mean from integer cents, rounded half-up to 2 decimals."""
    if not count:
        return None
    return (Decimal(sum_cents) / Decimal(count) / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ---------- retry ----------
def _simulated_failures():
    try:
        return int(os.environ.get("SIMULATE_DB_FAILURES", "0"))   # read on every call
    except ValueError:
        return 0


def run_with_retry(fn, route, executed):
    """A query gets at most 3 attempts. Returns (result, attempts_used)."""
    n = _simulated_failures()
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            if attempt <= n:
                raise SimulatedFailure("simulated database failure")
            return fn(), attempt
        except Exception as exc:
            if attempt == MAX_ATTEMPTS:
                raise QueryFailed(str(exc), attempt, route, executed)


def direction_for(word, metric):
    """highest/lowest/best/worst -> 'highest' or 'lowest' (lower is better for stockout_hours)."""
    if word == "lowest":
        return "lowest"
    if word == "best":
        return "lowest" if metric == "stockout_hours" else "highest"
    if word == "worst":
        return "highest" if metric == "stockout_hours" else "lowest"
    return "highest"


# ---------- Python function route ----------
def get_value(store, date, metric):
    """One value for one store and one date."""
    validate("store_daily", measured=[metric], labels=["store", "date"])
    _need_lookup_metric(metric)
    check_dates(date)
    executed = f"get_value(store={store!r}, date={date!r}, metric={metric!r})"

    def run():
        df, _ = _load()
        row = df[(df["store"] == store) & (df["date"] == date)]
        return None if row.empty else float(row.iloc[0][metric])

    value, attempts = run_with_retry(run, "python", executed)
    return {"route": "python", "executed": executed, "attempts": attempts,
            "found": value is not None, "store": store, "date": date,
            "metric": metric, "value": value}


def target_vs_actual(store, date):
    """Revenue against target for one store and one date."""
    validate("store_daily",
             measured=["revenue_inr", "daily_target_inr", "achievement_pct", "performance_band"],
             labels=["store", "date"])
    check_dates(date)
    executed = f"target_vs_actual(store={store!r}, date={date!r})"

    def run():
        df, _ = _load()
        row = df[(df["store"] == store) & (df["date"] == date)]
        if row.empty:
            return None
        r = row.iloc[0]
        return {"revenue": float(r["revenue_inr"]), "target": float(r["daily_target_inr"]),
                "achievement_pct": float(r["achievement_pct"]), "band": str(r["performance_band"])}

    data, attempts = run_with_retry(run, "python", executed)
    out = {"route": "python", "executed": executed, "attempts": attempts,
           "found": data is not None, "store": store, "date": date}
    if data:
        out.update(data)
        out["alert"] = data["band"] == "Poor"      # below 75% of target
    return out


# ---------- SQL route ----------
def get_average(store, metric, start, end):
    """One store's average of a metric over an inclusive date range."""
    validate("store_daily", measured=[metric], labels=["store", "date"])
    _need_lookup_metric(metric)
    check_dates(start, end)
    sql = (f"SELECT COUNT({metric}), SUM(CAST(ROUND({metric} * 100) AS INTEGER)) "
           "FROM store_daily WHERE store = ? AND date BETWEEN ? AND ?")

    def run():
        _, conn = _load()
        return conn.execute(sql, (store, start, end)).fetchone()

    (count, sum_cents), attempts = run_with_retry(run, "sql", sql)
    return {"route": "sql", "executed": sql, "attempts": attempts, "found": bool(count),
            "store": store, "metric": metric, "start": start, "end": end,
            "value": avg_half_up(sum_cents, count), "days": count}


def compare_stores(metric, start, end, direction="highest"):
    """Average per store over the range, ranked. Ties (equal at 2 decimals) go by store name."""
    validate("store_daily", measured=[metric], labels=["store", "date"])
    _need_lookup_metric(metric)
    check_dates(start, end)
    sql = (f"SELECT store, COUNT({metric}), SUM(CAST(ROUND({metric} * 100) AS INTEGER)) "
           "FROM store_daily WHERE date BETWEEN ? AND ? GROUP BY store")

    def run():
        _, conn = _load()
        return conn.execute(sql, (start, end)).fetchall()

    rows, attempts = run_with_retry(run, "sql", sql)
    ranked = [{"store": s, "value": avg_half_up(total, n)} for s, n, total in rows if n]
    if direction == "lowest":
        ranked.sort(key=lambda r: (r["value"], r["store"]))
    else:
        ranked.sort(key=lambda r: (-r["value"], r["store"]))
    return {"route": "sql", "executed": sql, "attempts": attempts, "found": bool(ranked),
            "metric": metric, "start": start, "end": end, "direction": direction,
            "ranking": ranked}


def below_threshold(product, store=None):
    """Stores where stock_units is strictly below reorder_threshold for a product."""
    validate("inventory", measured=["stock_units", "reorder_threshold"], labels=["store", "product"])
    sql = ("SELECT store, stock_units, reorder_threshold FROM inventory "
           "WHERE LOWER(product) = LOWER(?)")
    params = [product]
    if store:
        sql += " AND store = ?"
        params.append(store)
    sql += " ORDER BY store"

    def run():
        _, conn = _load()
        return conn.execute(sql, params).fetchall()

    rows, attempts = run_with_retry(run, "sql", sql)
    below = [{"store": s, "stock_units": int(u), "reorder_threshold": int(t)}
             for s, u, t in rows if u < t]
    return {"route": "sql", "executed": sql, "attempts": attempts, "found": bool(rows),
            "product": product, "store": store, "below": below}


def feedback_summary(store):
    """Average rating over rated rows only, rated count, all rows, most frequent theme."""
    validate("feedback", measured=["rating", "theme"], labels=["store"])
    sql_rating = ("SELECT COUNT(rating), SUM(CAST(ROUND(rating * 100) AS INTEGER)), COUNT(*) "
                  "FROM feedback WHERE store = ?")
    sql_theme = "SELECT theme, COUNT(*) FROM feedback WHERE store = ? GROUP BY theme"
    executed = sql_rating + "; " + sql_theme

    def run():
        _, conn = _load()
        rated, total_cents, all_rows = conn.execute(sql_rating, (store,)).fetchone()
        themes = conn.execute(sql_theme, (store,)).fetchall()
        return rated, total_cents, all_rows, themes

    (rated, total_cents, all_rows, themes), attempts = run_with_retry(run, "sql", executed)
    top = sorted(themes, key=lambda t: (-t[1], t[0]))[0][0] if themes else None
    return {"route": "sql", "executed": executed, "attempts": attempts, "found": bool(all_rows),
            "store": store, "avg_rating": avg_half_up(total_cents, rated),
            "rated_rows": rated, "all_rows": all_rows, "top_theme": top}