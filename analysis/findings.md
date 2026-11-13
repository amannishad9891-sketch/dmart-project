# Findings: DMart store diagnosis (cleaned data, 450 rows)

## 1. Store summary
| Store | Mean daily revenue | Mean footfall | Mean stockout hours | Revenue per footfall | Mean achievement_pct | Poor days |
|---|---|---|---|---|---|---|
| Ahmedabad | 782647.37 | 1922.59 | 3.19 | 407.08 | 92.08 | 1 |
| Bengaluru | 931065.68 | 2076.86 | 2.38 | 448.31 | 98.01 | 0 |
| Hyderabad | 893233.01 | 2209.51 | 3.85 | 404.27 | 94.02 | 0 |
| Mumbai | 1064371.60 | 2391.27 | 1.93 | 445.11 | 101.37 | 0 |
| Pune | 636358.55 | 1517.71 | 2.32 | 419.29 | 70.71 | 70 |
| All stores | 861535.24 | 2023.59 | 2.74 | 425.75 | 91.24 | 71 |

## 2. Premise test: does Pune have more stockouts?
Ranking by mean stockout hours (highest first): Hyderabad 3.85, Ahmedabad 3.19,
Bengaluru 2.38, Pune 2.32, Mumbai 1.93.
Pune ranks 4th of 5 (2.32 against an all-store 2.74), and Hyderabad is highest (3.85).
So the premise "Pune has the most stockouts" is not supported.

## 3. Correlations (Pearson)
| Rows | revenue-stockout | revenue-footfall |
|---|---|---|
| All 450 rows | -0.152 | 0.918 |
| Pune rows only | -0.254 | 0.735 |

Before cleaning (deduplicated raw, non-missing footfall, 446 rows), revenue-footfall = 0.548.
Cleaning raised this correlation, because the impossible -150 and the extreme 6100 and 9800
no longer distort it.
Correlation does not establish causation.

## 4. Facts
- Pune's mean daily revenue is 636358.55, while the all-store mean is 861535.24.
- Pune's mean footfall is 1517.71, while the all-store mean is 2023.59.
- Pune's mean stockout hours are 2.32, which ranks 4th of 5. Hyderabad is highest at 3.85.
- Pune is in the Poor band on 70 of the 71 Poor days across all stores; the one other Poor day belongs to Ahmedabad.
- Pune's revenue per footfall is 419.29, against 425.75 for all stores.

## 5. Insights
- Pune's revenue per footfall (419.29) is almost the same as the all-store figure
  (425.75), so each visitor spends about the same. The gap is in how many visitors come.
- Pune's footfall is 25.00% below the all-store mean and its revenue is 26.14% below,
  so the two gaps are almost equal. The revenue gap is a footfall gap.
- Revenue moves with footfall (correlation 0.918 across all rows) much more than with
  stockout hours (-0.152), and Pune is only 4th of 5 in stockout hours, so stockouts
  do not explain its low revenue.

## 6. Hypotheses (unconfirmed)
- Unconfirmed: nearby competitor stores pull customers away from Pune's store.
  Data needed: locations and footfall of competitor stores around Pune.
- Unconfirmed: Pune's store has a smaller catchment area than the other stores.
  Data needed: population and household data around each store.