# Golden set: how the expected figures of our own cases were calculated

Each figure below was calculated with pandas and the decimal module on the data files, not copied from the agent's output. The 24 fixed cases (A01-A20, W01-W03, R01) take their expected values from the brief.

| Case | Calculation | Value |
|---|---|---|
| G01 | `daily[(daily.store=='Bengaluru') & (daily.date=='2026-05-15')].revenue_inr.iloc[0]` | 970774.76 |
| G02 | `daily[(daily.store=='Mumbai') & (daily.date=='2026-05-15')].revenue_inr.iloc[0]` | 1093374.78 |
| G12 | `mean of daily[(daily.store=='Ahmedabad') & (daily.date between 2026-05-01 and 2026-05-31)].footfall, exact Decimal mean rounded half-up to 2 decimals` | 1947.01 |
| G13 | `inv[(inv['product']=='Toor Dal 1kg') & (inv.stock_units < inv.reorder_threshold)] -> stores and stock_units` | Ahmedabad 47 units |
| G14 | `may.groupby('store').stockout_hours mean (exact Decimal, half-up), sorted ascending, ties by name` | Mumbai 2.17, Pune 2.21, Bengaluru 2.29, Ahmedabad 3.12, Hyderabad 3.70 |
| G15 | `mean of fb[(fb.store=='Pune') & fb.rating.notna()].rating (exact Decimal, half-up)` | 3.71 |
| G15 | `len(fb[(fb.store=='Pune') & fb.rating.notna()])` | 38 |
| G15 | `fb[fb.store=='Pune'].theme.value_counts(), top theme, ties by name` | Pricing |
| G16 | `revenue_inr / daily_target_inr * 100 for Bengaluru on 2026-06-10 (Decimal, half-up)` | revenue 848248.05, target 950000.00, achievement 89.29%, band Good |
