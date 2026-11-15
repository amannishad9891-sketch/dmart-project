# DMart Regional Director Assistant

Author: aman

## Purpose

Kavita Rao, regional director of five DMart stores (Mumbai, Pune, Hyderabad, Bengaluru, Ahmedabad), believes Pune's low revenue is caused by stockouts. This repository (1) cleans the store data and tests that premise, (2) specifies a conversational assistant, (3) builds it so that every number in a reply can be traced to a data field, and (4) measures it and decides whether it is fit to release. All data is synthetic practice data made by `scripts/generate_data.py`. It is not DMart's real data.

**Part A finding:** Pune's revenue is 26.14% below the all-store mean and its footfall is 25.00% below, while revenue per footfall is only 1.52% below. Pune ranks 4th of 5 by mean stockout hours, so the gap is a footfall gap, not a stockout gap (see `analysis/findings.md` and `analysis/executive_summary.md`).

## Setup and run order

Python 3.9 or later. Run every command from the repository root.

```
pip install -r requirements.txt
python scripts/generate_data.py          # writes the three raw files in data/
python scripts/inspect_raw.py            # numbers for analysis/data_quality_report.md
python scripts/clean_data.py             # data/store_daily_clean.csv and analysis/cleaning_log.csv
python scripts/analyze.py                # numbers for analysis/findings.md
python scripts/run_acceptance.py         # 20 acceptance cases: outputs/acceptance_transcript.md, logs/runs.jsonl
python scripts/make_weather_tests.py     # tests/weather_tool_tests.md
python eval/build_golden_set.py          # eval/golden_set.csv and eval/golden_set_derivation.md
python eval/run_eval.py                  # eval_results.csv, eval_runs.jsonl, eval_summary.md
python eval/make_release_gate.py         # docs/release_gate.md
```

The raw files in `data/` are never edited. Cleaning always writes a new file.

## Free offline path

Everything graded runs offline with Python, pandas, numpy and the standard library. No account and no API key are needed.

- `LLM_MODE=mock` (default): the interpreter in `agent/understand.py` is rule-based, and replies are fixed templates. There is no language model.
- `WEATHER_MODE=stub` (default): `tools/weather.py` returns deterministic values from a formula.
- Local database: SQLite, built in memory from the CSV files.
- Optional and not graded: `WEATHER_MODE=live` calls the Open-Meteo archive service (needs the `requests` library). Weather data by Open-Meteo.com https://open-meteo.com/
- API keys, if ever used, go in an untracked `.env` file (listed in `.gitignore`).

## Repository layout

```
README.md
.gitignore  requirements.txt
data/       store_daily.csv  inventory.csv  feedback.csv  store_daily_clean.csv
scripts/    generate_data.py  inspect_raw.py  clean_data.py  analyze.py  run_acceptance.py  make_weather_tests.py
analysis/   data_quality_report.md  cleaning_log.csv  findings.md  executive_summary.md
docs/       requirement.md  data_context.md  agent_spec.md  release_gate.md
agent/      understand.py  fetch.py  answer.py  run_agent.py
tools/      weather.py
tests/      weather_tool_tests.md
outputs/    acceptance_transcript.md
logs/       runs.jsonl
eval/       build_golden_set.py  golden_set.csv  golden_set_derivation.md  run_eval.py
            eval_results.csv  eval_runs.jsonl  eval_summary.md  make_release_gate.py
```

## Rounding method

Averages use integer-cent arithmetic: SQL returns, per store, the count of non-null values and the sum of whole cents, and Python divides them with the decimal module using ROUND_HALF_UP to 2 decimals.

## Known limitations

- The interpreter is rule-based. A question phrased outside its closed word lists or date grammar gets a clarification question or an out-of-scope reply instead of a guess.
- The date grammar is closed: only YYYY-MM-DD, D Month YYYY, yesterday and between <date> and <date>. Phrases such as last week or today ask for the date.
- One store and one metric per question. A question naming two stores or two metrics asks which one.
- Session context lives in memory only. It is lost when the program stops, and it never crosses sessions.
- Diagnostic (why) questions are escalated. The assistant reports figures, never causes.
- The data is synthetic and covers 2026-04-01 to 2026-06-29 only. Feedback and inventory answers ignore any date.
- Live weather is optional code that is read, not run, by the grader. All graded weather work uses the stub.

## Iteration-2 backlog (in priority order)

| # | Feature | Input | Output | Success criteria | Failure behaviour |
|---|---|---|---|---|---|
| 1 | Trend questions | A store, a metric and two date ranges, for example "Pune revenue this week against last week" | The two averages and the difference, all fetched | Every number is fetched and appears in grounded_values; the difference matches a pandas calculation | A range outside the data or an unresolved range gives Safe Failure or Clarification Needed |
| 2 | Deeper follow-up questions | A short follow-up that changes one entity, for example "and Mumbai?" after a comparison | The same question with the new entity, answered from fetched data | The follow-up gives the same answer as the full question typed out | An entity that cannot be resolved is never filled from context; the assistant asks |
| 3 | Hosted database | The same questions, with the data in a hosted PostgreSQL database | The same replies as the local SQLite version | The 40 golden-set cases still pass and latency stays within the measured range | A failed connection is retried at most three times, then Escalated; no figure is invented |