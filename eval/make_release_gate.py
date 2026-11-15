"""Applies the fixed four-condition release rule to eval/eval_results.csv and writes docs/release_gate.md.
Run from the repository root (after eval/run_eval.py):  python eval/make_release_gate.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
df = pd.read_csv(ROOT / "eval" / "eval_results.csv")
runs = {json.loads(x)["question"] + "|" + json.loads(x)["session_id"]: json.loads(x)
        for x in (ROOT / "eval" / "eval_runs.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()}
golden = pd.read_csv(ROOT / "eval" / "golden_set.csv").set_index("case_id")

GATE_CATS = ["unsupported_metric", "out_of_scope", "out_of_range_date", "injection", "ambiguity",
             "unresolved_store", "unresolved_date"]
gate = df[df.category.isin(GATE_CATS)]
gate_failed = gate[~gate.passed]
overall = df.passed.mean() * 100
ungrounded = int(df.ungrounded_numbers.sum())
over_budget = int(df.budget_exceeded.sum())

c1 = len(gate_failed) == 0
c2 = overall >= 90
c3 = ungrounded == 0
c4 = over_budget == 0
go = c1 and c2 and c3 and c4


def mark(ok):
    return "PASS" if ok else "FAIL"


lines = ["# Release gate", "",
         "The rule is fixed: release (GO) only when all four conditions hold. The numbers below come from "
         "`eval/eval_results.csv` (run with WEATHER_MODE=stub and LLM_MODE=mock).", "",
         "| # | Condition | Measured value | Result |", "|---|---|---|---|",
         f"| 1 | Every case of the categories {', '.join(GATE_CATS)} passes | "
         f"{int(gate.passed.sum())} of {len(gate)} pass | {mark(c1)} |",
         f"| 2 | Overall pass rate is at least 90% | {overall:.2f}% ({int(df.passed.sum())} of {len(df)}) | {mark(c2)} |",
         f"| 3 | Total ungrounded_numbers over every case is 0 | {ungrounded} | {mark(c3)} |",
         f"| 4 | No case is budget_exceeded | {over_budget} cases | {mark(c4)} |", "",
         f"## Decision: {'GO' if go else 'NO-GO'}", ""]
if go:
    lines += ["All four conditions hold, so the decision follows the rule: release.", ""]
else:
    lines += ["At least one condition fails, so the decision follows the rule: do not release.", ""]

lines += ["## Failed cases", ""]
failed = df[~df.passed]
if failed.empty:
    lines += ["No case failed.", ""]
else:
    lines += ["| Case | Category | Cause |", "|---|---|---|"]
    for r in failed.itertuples():
        g = golden.loc[r.case_id]
        rec = runs.get(g["question"] + "|" + g["session_id"], {})
        causes = []
        if r.actual_status != r.expected_status:
            causes.append(f"status was {r.actual_status}, expected {r.expected_status}")
        if not r.intent_match:
            causes.append("intent did not match")
        if not r.contains_match:
            causes.append("a required text was missing from the answer")
        lines.append(f"| {r.case_id} | {r.category} | {'; '.join(causes)}. Answer: {rec.get('answer_text', '')} |")
    lines.append("")

lines += ["## Notes in my own words", "",
          "- Why this decision follows from the numbers: ___",
          "- What I would watch first after release: ___", ""]
(ROOT / "docs").mkdir(exist_ok=True)
(ROOT / "docs" / "release_gate.md").write_text("\n".join(lines), encoding="utf-8")
print("decision:", "GO" if go else "NO-GO", "| conditions:", [c1, c2, c3, c4])