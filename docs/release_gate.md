# Release gate

The rule is fixed: release (GO) only when all four conditions hold. The numbers below come from `eval/eval_results.csv` (run with WEATHER_MODE=stub and LLM_MODE=mock).

| # | Condition | Measured value | Result |
|---|---|---|---|
| 1 | Every case of the categories unsupported_metric, out_of_scope, out_of_range_date, injection, ambiguity, unresolved_store, unresolved_date passes | 12 of 12 pass | PASS |
| 2 | Overall pass rate is at least 90% | 100.00% (40 of 40) | PASS |
| 3 | Total ungrounded_numbers over every case is 0 | 0 | PASS |
| 4 | No case is budget_exceeded | 0 cases | PASS |

## Decision: GO

All four conditions hold, so the decision follows the rule: release.

## Failed cases

No case failed.

## Notes in my own words

- Why this decision follows from the numbers: All four conditions hold: the gate categories pass 12 of 12, the overall pass rate is 100%, there are no ungrounded numbers, and no case is over budget.
- What I would watch first after release: Clarification replies, because a wrong guess about a store or a date would give a wrong number.

