# Evaluation summary

Cases run: 40 (WEATHER_MODE=stub, LLM_MODE=mock).

## Cost

- Mean tokens_est: 24.25
- Maximum tokens_est: 48
- Total tool_calls: 27
- Cases with budget_exceeded: 0

## Latency (ms)

- Mean: 2.440
- 90th percentile (linear interpolation): 3.099
- Maximum: 44.481

## Quality

- Overall pass rate: 100.00% (40 of 40)
- Pass count per category:
  - ambiguity: 3 of 3
  - comparison: 4 of 4
  - diagnostic: 1 of 1
  - feedback: 2 of 2
  - injection: 1 of 1
  - inventory: 2 of 2
  - lookup: 8 of 8
  - out_of_range_date: 2 of 2
  - out_of_scope: 2 of 2
  - retry: 2 of 2
  - synonym: 1 of 1
  - target_vs_actual: 4 of 4
  - typo: 2 of 2
  - unresolved_date: 1 of 1
  - unresolved_store: 1 of 1
  - unsupported_metric: 2 of 2
  - weather: 2 of 2
- Total ungrounded_numbers: 0

## Safety

- Pass rate of the categories injection, unsupported_metric and out_of_scope: 100.00% (5 of 5)
- Non-answer replies (Safe Failure, Escalated, Clarification Needed) that state an INR figure: 0
- .gitignore lists .env: yes
