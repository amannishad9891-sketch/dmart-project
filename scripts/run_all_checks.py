"""Runs every check so far and writes a short report to check_report.txt (also printed).
Run from the repository root:  python scripts/run_all_checks.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
out = []


def say(text=""):
    print(text)
    out.append(text)


def run(script):
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / script)], cwd=ROOT,
                       capture_output=True, text=True)
    return r.stdout.strip().splitlines(), r.stderr.strip().splitlines(), r.returncode


# 1. required files
say("=== 1. FILES ===")
need = ["README.md", ".gitignore", "requirements.txt", "data/store_daily.csv", "data/inventory.csv",
        "data/feedback.csv", "data/store_daily_clean.csv", "scripts/generate_data.py",
        "scripts/clean_data.py", "scripts/analyze.py", "scripts/run_acceptance.py",
        "analysis/data_quality_report.md", "analysis/cleaning_log.csv", "analysis/findings.md",
        "analysis/executive_summary.md", "docs/requirement.md", "docs/data_context.md",
        "docs/agent_spec.md", "docs/release_gate.md", "agent/understand.py", "agent/fetch.py",
        "agent/answer.py", "agent/run_agent.py", "tools/weather.py", "tests/weather_tool_tests.md",
        "outputs/acceptance_transcript.md", "logs/runs.jsonl", "eval/golden_set.csv",
        "eval/golden_set_derivation.md", "eval/run_eval.py", "eval/eval_results.csv",
        "eval/eval_runs.jsonl", "eval/eval_summary.md"]
missing = [p for p in need if not (ROOT / p).exists()]
say("missing so far: " + (", ".join(missing) if missing else "none"))

# 2. fetch
say("\n=== 2. check_fetch ===")
lines, err, rc = run("check_fetch.py")
say(f"OK: {sum(l.startswith('OK') for l in lines)}  FAIL: {sum(l.startswith('FAIL') for l in lines)}")
for l in lines:
    if l.startswith("FAIL"):
        say(l)
for l in err[-5:]:
    say("ERROR " + l)

# 3. understand
say("\n=== 3. check_understand ===")
lines, err, rc = run("check_understand.py")
for l in lines:
    if l.startswith("FAIL"):
        say(l)
say(lines[-1] if lines else "no output")
for l in err[-5:]:
    say("ERROR " + l)

# 4. acceptance
say("\n=== 4. run_acceptance ===")
lines, err, rc = run("run_acceptance.py")
for l in lines:
    if l.strip():
        say(l)
for l in err[-5:]:
    say("ERROR " + l)

# 5. weather tool tests
say("\n=== 5. make_weather_tests ===")
lines, err, rc = run("make_weather_tests.py")
for l in lines:
    say(l)
for l in err[-5:]:
    say("ERROR " + l)

# 6. weather inside the agent
say("\n=== 6. agent with weather ===")
code = ("import os; os.environ['AGENT_LOG_PATH']='logs/_check.jsonl'; "
        "from agent.run_agent import handle; "
        "r=handle('What was Mumbai revenue on 15 May 2026 and what was the weather like?','chk1'); "
        "print(r['status'], r['route'], r['tools_called'], r['tool_calls'], r['ungrounded_numbers']); "
        "print(r['answer_text']); "
        "r=handle('What was the weather in Pune on 2026-05-16?','chk2'); "
        "print(r['status'], r['route'], r['tools_called'], r['tool_calls']); "
        "print(r['answer_text']); "
        "r=handle('What was Pune revenue on 15 May 2026?','chk3'); "
        "print(r['status'], r['tools_called'], r['tool_calls'])")
r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
for l in r.stdout.strip().splitlines():
    say(l)
for l in r.stderr.strip().splitlines()[-5:]:
    say("ERROR " + l)
tmp = ROOT / "logs" / "_check.jsonl"
if tmp.exists():
    tmp.unlink()

(ROOT / "check_report.txt").write_text("\n".join(out), encoding="utf-8")
print("\nReport saved in check_report.txt")