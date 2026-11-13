# Data Quality Report: store_daily.csv (raw)

## 1. Shape
453 rows x 9 columns.

## 2. Data types
(har column ka dtype, df.dtypes se)

## 3. Null count
(har column ka null count; footfall ke 4)

## 4. Exact duplicates
3 exact duplicate rows.

## 5. Footfall minimum and maximum
Minimum: -150, Maximum: 9800.

## 6. Per-store IQR bounds
(Har store ke liye Q1, Q3, lower bound, upper bound ki table.
Note: duplicates hataye, negative ko missing maana, sirf non-missing values.)

Rows outside the bounds: Mumbai 6100, Ahmedabad 9800.

## Decisions
### Duplicates
### Negative values
### Extreme values
### Missing values

Decisions

1. Duplicates

What I did: removed the 3 exact duplicate rows and kept the first occurrence of each. The clean file therefore has 450 rows (453 - 3).

Why this and not the alternative: a row repeated word for word is the same store-day recorded twice, not a second real day. Keeping it would count that day's revenue and footfall twice and pull every average and total towards that store. I only removed rows that match on all 9 columns, so two different days that merely look similar are never touched.

What the raw file still contains: all 3 duplicate rows. Nothing was deleted from data/store_daily.csv.

2. Negative values

What I did: treated the negative footfall (-150, Hyderabad, 2026-04-21) as a data error and set it to missing. This happens before the IQR bounds are computed.

Why this and not the alternative: a count of people cannot be below zero, so -150 is a recording error, not an unusual day. I did not cap it, because the nearest bound would turn an error into a believable-looking number. I did not set it to zero either, because a store with revenue of that size was clearly not empty. Setting it to missing first also keeps this bad value out of the Q1/Q3 calculation.

What the raw file still contains: the value -150 on that row.

3. Extreme values

What I did: capped the two extreme values at their store's nearest IQR bound: Ahmedabad 9800 became 2281.38 and Mumbai 6100 became 2986.00 (rounded half-up to 2 decimals).

Why this and not the alternative: a very busy day is possible in a real store, so the row is still a real day with real revenue, only its footfall figure is suspicious. Deleting the row would throw away that day's revenue and the other columns. Capping keeps the row and the fact that it was a busy day, but stops one huge number from distorting means and the revenue-footfall correlation.

What the raw file still contains: the original 6100 and 9800 values.

4. Missing values

What I did: filled each remaining missing footfall with the median of the non-missing footfall of the same store. This is done after capping, so the median is not affected by the extreme values. There are 5 such cells: the 4 originally blank plus the one that became missing from the negative value.

Why this and not the alternative: I did not use zero, because a store does not have zero visitors on a normal trading day, and zero would pull averages down and fake a collapse in footfall. I used the median and not the mean because the median is not pulled by outliers, so it is a safer typical value. I used each store's own median and not one median for all stores, because the stores are very different in size (Pune is around 1500 a day, Mumbai around 2400), and an all-store value would be wrong for every store.

What the raw file still contains: the 4 blank footfall cells