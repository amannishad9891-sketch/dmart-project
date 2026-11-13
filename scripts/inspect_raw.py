import pandas as pd

df = pd.read_csv("data/store_daily.csv")

print("SHAPE:", df.shape)
print("\nDTYPES:")
print(df.dtypes)
print("\nNULL COUNT:")
print(df.isnull().sum())
print("\nEXACT DUPLICATES:", df.duplicated().sum())
print("\nFOOTFALL MIN:", df["footfall"].min(), " MAX:", df["footfall"].max())

# Per-store IQR bounds (order: duplicates hatao -> negative ko NaN -> quantile)
d = df.drop_duplicates().copy()
d["footfall"] = d["footfall"].where(d["footfall"] >= 0)

print("\nPER-STORE BOUNDS:")
for store, g in d.groupby("store"):
    x = g["footfall"].dropna()
    q1 = x.quantile(0.25)
    q3 = x.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    print(f"\n{store}: Q1={q1}, Q3={q3}, IQR={iqr}, lower={lower}, upper={upper}")
    out = g[(g["footfall"] < lower) | (g["footfall"] > upper)]
    print("Rows outside bounds:")
    print(out[["date", "store", "footfall"]])