"""Runs every golden-set case through handle() and writes eval_results.csv, eval_runs.jsonl and
eval_summary.md. Run from the repository root:  python eval/run_eval.py
"""
import csv
import json
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

RUNS = ROOT / "eval" / "eval_runs.jsonl"
os.environ["AGENT_LOG_PATH"] = str(RUNS)       # set explicitly, so the two logs never mix
os.environ["WEATHER_MODE"] = "stub"
RUNS.write_text("", encoding="utf-8")          # one line per case

from agent.run_agent import handle             # noqa: E402


def has(answer, needle):
    """Substring match; a decimal figure also matches within 0.01 of it."""
    if needle in answer:
        return True
    nums = re.findall(r"\d+\.\d+", needle)
    if not nums:
        return False
    parts = re.split(r"\d+\.\d+", needle)
    pattern = "".join(re.escape(p) + (r"(\d+\.\d+)" if i < len(nums) else "")
                      for i, p in enumerate(parts))
    for m in re.finditer(pattern, answer):
        if all(abs(float(g) - float(n)) <= 0.01 + 1e-9 for g, n in zip(m.groups(), nums)):
            return True
    return False


rows = list(csv.DictReader(open(ROOT / "eval" / "golden_set.csv", encoding="utf-8")))
results = []
for r in rows:
    os.environ["SIMULATE_DB_FAILURES"] = r["simulate_failures"] or "0"
    rec = handle(r["question"], r["session_id"])
    os.environ["SIMULATE_DB_FAILURES"] = "0"
    needles = [x for x in r["expected_contains"].split("|") if x]
    intent_match = rec["intent"] == r["expected_intent"]
    contains_match = all(has(rec["answer_text"], n) for n in needles)
    status_match = rec["status"] == r["expected_status"]
    results.append({
        "case_id": r["case_id"], "category": r["category"], "expected_status": r["expected_status"],
        "actual_status": rec["status"], "intent_match": intent_match, "contains_match": contains_match,
        "latency_ms": rec["latency_ms"], "tokens_est": rec["tokens_est"], "tool_calls": rec["tool_calls"],
        "ungrounded_numbers": rec["ungrounded_numbers"], "budget_exceeded": rec["budget_exceeded"],
        "passed": bool(status_match and intent_match and contains_match)})

cols = ["case_id", "category", "expected_status", "actual_status", "intent_match", "contains_match",
        "latency_ms", "tokens_est", "tool_calls", "ungrounded_numbers", "budget_exceeded", "passed"]
with open(ROOT / "eval" / "eval_results.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(results)

# ---------- eval_summary.md, computed from eval_results.csv ----------
df = pd.read_csv(ROOT / "eval" / "eval_results.csv")
runs = [json.loads(x) for x in RUNS.read_text(encoding="utf-8").splitlines() if x.strip()]
non_answer_inr = sum(1 for x in runs if x["status"] in ("Safe Failure", "Escalated", "Clarification Needed")
                     and re.search(r"INR\s*\d", x["answer_text"]))
safety_cats = ["injection", "unsupported_metric", "out_of_scope"]
safety = df[df.category.isin(safety_cats)]
gitignore_ok = ".env" in [ln.strip() for ln in (ROOT / ".gitignore").read_text().splitlines()]

lines = ["# Evaluation summary", "", f"Cases run: {len(df)} (WEATHER_MODE=stub, LLM_MODE=mock).", "",
         "## Cost", "",
         f"- Mean tokens_est: {df.tokens_est.mean():.2f}", f"- Maximum tokens_est: {int(df.tokens_est.max())}",
         f"- Total tool_calls: {int(df.tool_calls.sum())}",
         f"- Cases with budget_exceeded: {int(df.budget_exceeded.sum())}", "",
         "## Latency (ms)", "",
         f"- Mean: {df.latency_ms.mean():.3f}",
         f"- 90th percentile (linear interpolation): {np.percentile(df.latency_ms, 90):.3f}",
         f"- Maximum: {df.latency_ms.max():.3f}", "",
         "## Quality", "",
         f"- Overall pass rate: {df.passed.mean() * 100:.2f}% ({int(df.passed.sum())} of {len(df)})",
         "- Pass count per category:"]
for cat, g in df.groupby("category"):
    lines.append(f"  - {cat}: {int(g.passed.sum())} of {len(g)}")
lines += [f"- Total ungrounded_numbers: {int(df.ungrounded_numbers.sum())}", "",
          "## Safety", "",
          f"- Pass rate of the categories injection, unsupported_metric and out_of_scope: "
          f"{safety.passed.mean() * 100:.2f}% ({int(safety.passed.sum())} of {len(safety)})",
          f"- Non-answer replies (Safe Failure, Escalated, Clarification Needed) that state an INR figure: "
          f"{non_answer_inr}",
          f"- .gitignore lists .env: {'yes' if gitignore_ok else 'no'}", ""]
(ROOT / "eval" / "eval_summary.md").write_text("\n".join(lines), encoding="utf-8")

print("cases:", len(df), "| passed:", int(df.passed.sum()), "| failed:", len(df) - int(df.passed.sum()))
for r in results:
    if not r["passed"]:
        print("FAIL", r["case_id"], r["category"], "| status", r["actual_status"], "| intent_match",
              r["intent_match"], "| contains_match", r["contains_match"])