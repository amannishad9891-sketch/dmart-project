import numpy as np
import pandas as pd

c = pd.read_csv("data/store_daily_clean.csv")
stores = ["Ahmedabad", "Bengaluru", "Hyderabad", "Mumbai", "Pune"]


def summary(g):
    return [round(g["revenue_inr"].mean(), 2),
            round(g["footfall"].mean(), 2),
            round(g["stockout_hours"].mean(), 2),
            round(g["revenue_inr"].sum() / g["footfall"].sum(), 2),
            round(g["achievement_pct"].mean(), 2),
            int((g["performance_band"] == "Poor").sum())]


print("| Store | Mean daily revenue | Mean footfall | Mean stockout hours | Revenue per footfall | Mean achievement_pct | Poor days |")
print("|---|---|---|---|---|---|---|")
for s in stores:
    print("|", s, "|", " | ".join(str(v) for v in summary(c[c.store == s])), "|")
print("| All stores |", " | ".join(str(v) for v in summary(c)), "|")

print("\nRANKING by mean stockout hours (highest first):")
print(c.groupby("store")["stockout_hours"].mean().round(2).sort_values(ascending=False))

pune = c[c.store == "Pune"]
print("\nCORRELATIONS:")
print("all rows   revenue-stockout:", round(np.corrcoef(c.revenue_inr, c.stockout_hours)[0, 1], 3))
print("all rows   revenue-footfall:", round(np.corrcoef(c.revenue_inr, c.footfall)[0, 1], 3))
print("Pune rows  revenue-stockout:", round(np.corrcoef(pune.revenue_inr, pune.stockout_hours)[0, 1], 3))
print("Pune rows  revenue-footfall:", round(np.corrcoef(pune.revenue_inr, pune.footfall)[0, 1], 3))

raw = pd.read_csv("data/store_daily.csv").drop_duplicates()
raw = raw[raw["footfall"].notna()]
print("before cleaning revenue-footfall:", round(np.corrcoef(raw.revenue_inr, raw.footfall)[0, 1], 3), "| rows:", len(raw))

print("\nPUNE GAP vs ALL STORES (%):")
pr, pf = summary(pune), summary(c)
print("revenue:", round((pr[0] / pf[0] - 1) * 100, 2))
print("footfall:", round((pr[1] / pf[1] - 1) * 100, 2))
print("revenue per footfall:", round((pr[3] / pf[3] - 1) * 100, 2))