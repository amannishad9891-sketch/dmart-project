# Data Context

All data is synthetic practice data made by scripts/generate_data.py. It is not
DMart's real data. The three datasets are linked by the store name.

## 1. store_daily_clean.csv (cleaned daily store data)

**Rows:** 450 (453 raw rows minus 3 duplicates). **Columns:** 15.
**Date range:** 2026-04-01 to 2026-06-29 (90 days for each of 5 stores).

| Column | Type |
|---|---|
| date | text (ISO date) |
| store_id, store | text |
| footfall | float (whole numbers stored as 2099.0) |
| revenue_inr | float |
| daily_target_inr | integer |
| marketing_spend_inr | integer (not an approved field) |
| stockout_hours, discount_pct | float |
| revenue_per_footfall, marketing_efficiency, achievement_pct, shortfall_inr | float, 2 decimals |
| weekend_flag, performance_band | text |

**Data-quality facts (found in Part A):**
- 3 exact duplicate rows were removed (453 to 450 rows).
- 1 negative footfall (Hyderabad, 2026-04-21, value -150) was set to missing.
- 2 extreme footfall values were capped at the per-store IQR bound: Mumbai 6100 to 2986.00 and Ahmedabad 9800 to 2281.38.
- 5 missing footfall values (4 blanks and the negative one) were filled with that store's median.

**What the cleaned file guarantees:** exactly 450 rows, no missing value in any column, no negative footfall, and the 6 feature columns. revenue_inr and every other column except footfall are unchanged. The raw file data/store_daily.csv is never edited.

**Can support:** revenue, target, footfall, stockout hours and discount for a store on a date or over a date range; comparison of stores; target against actual with achievement and performance band.

## 2. inventory.csv

**Rows:** 40 (5 stores x 8 products). **Columns:** 6.
**Date range:** none. This file has no date column; it is a single snapshot.

| Column | Type |
|---|---|
| store_id, store, product_id, product | text |
| stock_units, reorder_threshold | integer |

**Data-quality facts:** no missing values and no duplicates were found. For Amul Milk 1L the reorder threshold is 100 in every store, and stock is Mumbai 240, Pune 85, Hyderabad 40, Bengaluru 130, Ahmedabad 100.

**Can support:** which stores are below the reorder threshold for a product (stock_units strictly below reorder_threshold).

## 3. feedback.csv

**Rows:** 200 (40 per store). **Columns:** 6.
**Date range:** 2026-04-01 to 2026-06-29.

| Column | Type |
|---|---|
| feedback_id, store_id, store, theme | text |
| date | text (ISO date) |
| rating | integer from 1 to 5, blank when missing |

**Data-quality facts:** 12 of the 200 rows have no rating. A missing rating is never replaced by an average; averages use the rated rows only. Themes: Stock availability, Queue time, Pricing, Freshness, Staff behaviour.

**Can support:** a store's average rating over the rated rows, the number of rated and all rows, and the most frequent theme.

## 4. Relationship between the datasets

All three datasets share the store name (Mumbai, Pune, Hyderabad, Bengaluru, Ahmedabad),
with store_id as the matching key. inventory and feedback are never joined to store_daily
by date. inventory has no date column, and feedback dates are not matched to daily revenue.