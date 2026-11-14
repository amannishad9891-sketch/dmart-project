import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agent import fetch


def check(name, got, expected):
    print(("OK   " if got == expected else "FAIL ") + name, "| got:", got, "| expected:", expected)


def ranking(r):
    return [(x["store"], str(x["value"])) for x in r["ranking"]]


check("A01 lookup", fetch.get_value("Pune", "2026-05-15", "revenue_inr")["value"], 623845.0)
check("A05 lookup", fetch.get_value("Hyderabad", "2026-05-15", "revenue_inr")["value"], 786399.27)
check("A06 yesterday", fetch.get_value("Hyderabad", "2026-06-29", "revenue_inr")["value"], 784954.9)

t = fetch.target_vs_actual("Pune", "2026-05-16")
check("A07 target", (t["revenue"], t["target"], t["achievement_pct"], t["band"]),
      (671332.65, 900000.0, 74.59, "Poor"))
t = fetch.target_vs_actual("Mumbai", "2026-05-21")
check("A09 target", (t["revenue"], t["achievement_pct"], t["band"]), (1133910.49, 107.99, "Excellent"))

check("A10 comparison", ranking(fetch.compare_stores("revenue_inr", "2026-05-01", "2026-05-31")),
      [("Mumbai", "1071614.03"), ("Bengaluru", "916766.02"), ("Hyderabad", "900317.89"),
       ("Ahmedabad", "798849.31"), ("Pune", "643251.34")])
check("A11 lowest", ranking(fetch.compare_stores("revenue_inr", "2026-06-10", "2026-06-10", "lowest")),
      [("Pune", "602942.85"), ("Hyderabad", "807522.21"), ("Ahmedabad", "819290.32"),
       ("Bengaluru", "848248.05"), ("Mumbai", "903822.34")])
check("R01 full period", ranking(fetch.compare_stores("revenue_inr", "2026-04-01", "2026-06-29", "lowest")),
      [("Pune", "636358.55"), ("Ahmedabad", "782647.37"), ("Hyderabad", "893233.01"),
       ("Bengaluru", "931065.68"), ("Mumbai", "1064371.60")])
check("range lookup", str(fetch.get_average("Pune", "revenue_inr", "2026-05-01", "2026-05-31")["value"]),
      "643251.34")

inv = fetch.below_threshold("Amul Milk 1L")
check("A12 inventory", [(b["store"], b["stock_units"], b["reorder_threshold"]) for b in inv["below"]],
      [("Hyderabad", 40, 100), ("Pune", 85, 100)])

fb = fetch.feedback_summary("Hyderabad")
check("A13 feedback", (str(fb["avg_rating"]), fb["rated_rows"], fb["all_rows"], fb["top_theme"]),
      ("2.63", 38, 40, "Stock availability"))

try:
    fetch.get_value("Mumbai", "2026-07-15", "revenue_inr")
    check("A16 out of range", "no error", "DateOutOfRange")
except fetch.DateOutOfRange:
    check("A16 out of range", "DateOutOfRange", "DateOutOfRange")

try:
    fetch.get_value("Pune", "2026-05-15", "marketing_spend_inr")
    check("field check", "no error", "FieldNotApproved")
except fetch.FieldNotApproved:
    check("field check", "FieldNotApproved", "FieldNotApproved")

os.environ["SIMULATE_DB_FAILURES"] = "2"
check("A19 retry", fetch.get_value("Pune", "2026-05-15", "revenue_inr")["attempts"], 3)
os.environ["SIMULATE_DB_FAILURES"] = "3"
try:
    fetch.get_value("Pune", "2026-05-15", "revenue_inr")
    check("A20 retry", "no error", "QueryFailed")
except fetch.QueryFailed as e:
    check("A20 retry", (type(e).__name__, e.attempts), ("QueryFailed", 3))
os.environ["SIMULATE_DB_FAILURES"] = "0"