# Agent Specification

## 1. Pipeline (eight steps)

The agent reads a plain-English question and runs it through these eight steps in order.
Validate checks the approved-field and table rules, and in this design it runs before the
query executes: Query builds the statement, Validate checks it, and only then is it run.

| # | Step | What it does | Type | Technique |
|---|---|---|---|---|
| 1 | Interpret | Reads the question and finds intent, store, metric, date or range, product, weather flag and a confidence score | Generative (built without a language model) | Rule-based interpreter: keyword rules, difflib.SequenceMatcher for misspelt store names |
| 2 | Route | Picks the data route for the intent: a Python function, a SQL query, the weather tool, or none | Deterministic | Fixed intent-to-route table |
| 3 | Query | Builds the statement for the chosen route | Deterministic | Python function for one store and one date; SQL on SQLite with ? placeholders for ranges, comparisons, inventory and feedback |
| 4 | Validate | Checks the table and the columns against the 11 approved fields before anything runs, and checks the date range | Deterministic | Whitelist check; values only as ? parameters, column and ASC/DESC only after checking |
| 5 | Calculate | Computes averages, rankings, shortfall against target and the performance band | Deterministic | Integer-cent sums divided with the decimal module, ROUND_HALF_UP to 2 decimals |
| 6 | Synthesize | Writes the reply text | Generative (built without a language model) | Fixed answer templates filled with fetched values |
| 7 | Ground | Builds evidence and grounded_values from the fetched values and counts ungrounded numbers | Deterministic | grounded_values built from fetched data, never by scanning the finished text |
| 8 | Record | Writes one JSON line to the log for every question | Deterministic | Append to logs/runs.jsonl (path from AGENT_LOG_PATH) |

## 2. Intents (nine)

| Intent | Example question | Route | Required entities |
|---|---|---|---|
| lookup | What was Pune's revenue on 15 May 2026? | Python function (one date) or SQL (a date range gives that store's average) | store, metric, date or range |
| target_vs_actual | Did Pune hit its target on 2026-05-16? | Python function | store, one date |
| comparison | Which store had the highest average revenue between 2026-05-01 and 2026-05-31? | SQL | metric, date or range |
| inventory | Which stores are below the reorder threshold for Amul Milk? | SQL | product (store optional) |
| feedback | What are customers saying about Hyderabad? | SQL | store |
| weather | What was the weather in Pune on 2026-05-16? | Weather tool | store, one date |
| unsupported_metric | What was Pune's profit margin on 2026-05-15? | None | none |
| out_of_scope | What is the capital of India? | None | none |
| diagnostic | Why is Pune's revenue so low? | None | none |