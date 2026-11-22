import pandas as pd

df = pd.read_csv("Laundry_Customer.csv")
df.columns = df.columns.str.strip()

# Remove duplicate rows
df = df.drop_duplicates()

# Clean text
for col in ["Name", "Service"]:
    df[col] = df[col].astype("string").str.strip()

# Convert date
df["Date"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)

# Convert weight: comma decimal -> dot decimal
df["Weight (kg)"] = (
    df["Weight (kg)"].astype("string").str.replace(",", ".", regex=False)
)
df["Weight (kg)"] = pd.to_numeric(df["Weight (kg)"], errors="coerce")

# Convert price
df["Total Price"] = pd.to_numeric(df["Total Price"], errors="coerce")

# Remove rows missing essential customer/order identifiers
df = df.dropna(subset=["Customer ID", "No", "Date"])

# Remove invalid weights and prices, but keep missing weights
df = df[
    (df["Weight (kg)"].isna() | (df["Weight (kg)"] > 0)) &
    (df["Total Price"] >= 0)
]

# Save cleaned data
df.to_csv("Laundry_Customer_Cleaned.csv", index=False)

print("Cleaned rows:", len(df))
print("\nMissing values after cleaning:")
print(df.isnull().sum())
print("\nCleaned file saved!")