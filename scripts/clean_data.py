import numpy as np
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP


def r2(x):
    """Round half-up to 2 decimals."""
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


df = pd.read_csv("data/store_daily.csv")
log = []

# Step 1: exact duplicates hatao (pehli rakho)
df = df.drop_duplicates(keep="first").reset_index(drop=True)

# Step 2: negative footfall -> missing
neg = df["footfall"] < 0
for i in df[neg].index:
    log.append({"store": df.at[i, "store"], "date": df.at[i, "date"],
                "old_footfall": df.at[i, "footfall"], "new_footfall": "",
                "rule": "negative_to_missing"})
df.loc[neg, "footfall"] = np.nan

# Step 3: har store ke bounds, bahar wali value ko bound par cap karo
bounds = {}
for store, g in df.groupby("store"):
    x = g["footfall"].dropna()
    q1, q3 = x.quantile(0.25), x.quantile(0.75)
    iqr = q3 - q1
    bounds[store] = (q1 - 1.5 * iqr, q3 + 1.5 * iqr)

for i in df.index:
    f = df.at[i, "footfall"]
    if pd.notna(f):
        lo, hi = bounds[df.at[i, "store"]]
        if f < lo or f > hi:
            new = r2(lo if f < lo else hi)
            log.append({"store": df.at[i, "store"], "date": df.at[i, "date"],
                        "old_footfall": f, "new_footfall": new,
                        "rule": "iqr_cap"})
            df.at[i, "footfall"] = new

# Step 4: bache hue missing ko us store ke median se bharo
medians = df.groupby("store")["footfall"].median()
for i in df[df["footfall"].isna()].index:
    med = medians[df.at[i, "store"]]
    log.append({"store": df.at[i, "store"], "date": df.at[i, "date"],
                "old_footfall": "", "new_footfall": med,
                "rule": "median_impute"})
    df.at[i, "footfall"] = med

# Step 5: feature columns (revenue_inr aur baaki columns untouched)
d = pd.to_datetime(df["date"])
df["revenue_per_footfall"] = (df["revenue_inr"] / df["footfall"]).apply(r2)
df["marketing_efficiency"] = (df["revenue_inr"] / df["marketing_spend_inr"]).apply(r2)
df["achievement_pct"] = (df["revenue_inr"] / df["daily_target_inr"] * 100).apply(r2)
df["shortfall_inr"] = (df["daily_target_inr"] - df["revenue_inr"]).apply(r2)
df["weekend_flag"] = np.where(d.dt.dayofweek >= 5, "Yes", "No")
df["performance_band"] = np.select(
    [df["achievement_pct"] >= 100, df["achievement_pct"] >= 75],
    ["Excellent", "Good"], default="Poor")

df.to_csv("data/store_daily_clean.csv", index=False)
pd.DataFrame(log, columns=["store", "date", "old_footfall", "new_footfall", "rule"]) \
    .to_csv("analysis/cleaning_log.csv", index=False)

print("rows:", len(df), "| nulls:", int(df.isnull().sum().sum()))
print(pd.DataFrame(log)["rule"].value_counts())