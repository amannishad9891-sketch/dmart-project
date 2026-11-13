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

## 3. Handling rules

**Store names.** An exact store name is matched case-insensitively anywhere in the question
(confidence 1.0). Bangalore is an explicit alias of Bengaluru (confidence 1.0). A misspelling
is matched with difflib.SequenceMatcher against the five store names, and the best score is
the confidence. Only a candidate word is tried: at least 5 letters, capitalised or carrying 's,
not the first word (unless it carries 's), and not a keyword or stop word. A named store that
scores below 0.7 is an unresolved named store: confidence 0.4, and the agent asks which store.
It is never replaced by a store from session context.

**Metric synonyms.** revenue, sales, turnover and earnings mean revenue_inr; target means
daily_target_inr; footfall and visitors mean footfall; stockout means stockout_hours;
discount means discount_pct. The list is closed.

**Dates (closed grammar).** Only these forms are accepted: YYYY-MM-DD, D Month YYYY (full month
name), yesterday, and between <date> and <date> (inclusive). AS_OF_DATE is 2026-06-30, so
yesterday is 2026-06-29. Anything else that looks like a date (20260515, 15 Jun 2026, last week,
today, a month name alone, a second date outside a between range, a range for a single-date
intent) is an unresolved named date: confidence 0.4, and the agent asks for the date. It is
never replaced by a date from session context.

**Confidence.** Confidence is the minimum over the entities the intent uses: 1.0 for an exact
store, alias, product, synonym or any date resolved by the grammar; the fuzzy score for a fuzzy
store; 0.4 for a missing required entity, an unresolved store or date, or an ambiguous question.
The clarification threshold is 0.7: below 0.7 the agent asks instead of answering. If the
question uses two different stores or two different metrics, it is ambiguous (confidence 0.4)
and the agent asks which one.

**Session context.** An entity named in the new question overrides the old one. A required
entity left out is taken from the last resolved value in the same session. Context never
crosses sessions. A range held in context is never carried into a single-date intent
(target_vs_actual, weather). unsupported_metric, diagnostic and out_of_scope questions do not
update the context; every other question stores the entities it resolved. A target_vs_actual
question stores only the store and the date and marks the session, so a bare follow-up such as
"And Mumbai?" means target_vs_actual again.

**Intent order.** (1) override or prohibited action: out_of_scope; (2) a field outside the 11
approved fields: unsupported_metric; (3) why, trend or reason: diagnostic; (4) a product name,
reorder or inventory: inventory; (5) feedback, reviews, ratings or "customers say": feedback;
(6) target with hit, met, miss, beat, below, above and similar words, or achievement, or
performance band: target_vs_actual; (7) which, highest, lowest, best or worst with no store:
comparison; (8) a metric: lookup; (9) a weather word with no metric: weather; (10) a store
and/or a date but no metric: lookup; (11) nothing recognisable: out_of_scope.

## 4. Statuses

| Status | Exact condition |
|---|---|
| Answered | The question is understood, the entities are complete, the query ran, the answer is grounded, and no alert fired |
| Drafted | The answer is composed but held for human approval because an alert fired: a target_vs_actual result in the Poor band (below 75% of target) |
| Clarification Needed | Confidence is below 0.7, a required entity is missing, a store or date is unresolved, or the question has two different stores or metrics |
| Escalated | The question is out_of_scope or diagnostic, or a data query failed 3 times |
| Safe Failure | A field outside the approved list, a date outside 2026-04-01 to 2026-06-29, or no record found |

**Precedence (first rule that applies decides):**
1. The intent itself: unsupported_metric gives Safe Failure; out_of_scope and diagnostic give Escalated.
2. A required entity missing, an unresolved store or date, two different stores or metrics, or confidence below 0.7 gives Clarification Needed.
3. For intents that use a date (lookup, target_vs_actual, comparison, weather), a date outside the data range gives Safe Failure.
4. The data queries: 3 failed attempts give Escalated; no record found gives Safe Failure.
5. Otherwise Drafted when the alert fired, else Answered.

## 5. Escalation and retry rules

A data query gets at most three attempts in total: the first try plus two retries. If the
third attempt also fails, the status is Escalated and the reply contains no figure. The
attempts field in the log is the highest attempt count among the question's data queries,
and 0 when no data query runs. For testing, SIMULATE_DB_FAILURES=<n> makes the first n
attempts of every query fail.

## 6. Success criteria

- Every number in an answer appears in the fetched data: ungrounded_numbers is 0 for every reply.
- A reply never states a correlation as a cause.
- Every question writes exactly one log line with all the required keys.
- No non-answer reply (Safe Failure, Escalated, Clarification Needed) states an INR figure.
- Each reply stays within 150 words for question plus answer (budget_exceeded is false).
- The 20 acceptance cases return the required status, intent and content.

## 7. Completion states

Every question ends in exactly one of the five statuses: Answered, Drafted, Clarification
Needed, Escalated or Safe Failure.

## 8. Test-case categories (Part D)

lookup, target_vs_actual, comparison, inventory, feedback, weather, diagnostic, typo, synonym,
ambiguity, unsupported_metric, out_of_scope, injection, out_of_range_date, unresolved_store,
unresolved_date and retry.