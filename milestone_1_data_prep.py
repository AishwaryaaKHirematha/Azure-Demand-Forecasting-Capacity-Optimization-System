import pandas as pd
import numpy as np
import os

REQUIRED_COLUMNS = ['timestamp', 'region', 'service_type', 'usage_units']


def _cap_outliers_iqr(df: pd.DataFrame, numeric_cols: list) -> pd.DataFrame:
    """Winsorize numeric columns using the IQR method."""
    for col in numeric_cols:
        Q1, Q3 = df[col].quantile(0.25), df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower, upper = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
        n_outliers = ((df[col] < lower) | (df[col] > upper)).sum()
        if n_outliers > 0:
            print(f"  [{col}] Capping {n_outliers} outliers to [{lower:.2f}, {upper:.2f}]")
        df[col] = df[col].clip(lower=lower, upper=upper)
    return df


def prepare_data(input_file: str, output_file: str) -> pd.DataFrame:
    print(f"Loading data from {input_file}...")
    df = pd.read_csv(input_file)
    print(f"Initial shape: {df.shape}")
    print("Columns found:", df.columns.tolist())

    # 1. Schema validation
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    print(f"Schema OK — all required columns present.")

    # 2. Remove duplicate rows
    before = len(df)
    df = df.drop_duplicates()
    print(f"Duplicates removed: {before - len(df)} (kept {len(df)} rows)")

    # 3. Handle missing values (safe .loc-based assignment)
    print("\nMissing values before cleaning:")
    print(df.isnull().sum())

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    df.loc[:, numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())

    categorical_cols = df.select_dtypes(include="object").columns.tolist()
    for col in categorical_cols:
        fill_val = df[col].mode()[0] if not df[col].mode().empty else "Unknown"
        df.loc[:, col] = df[col].fillna(fill_val)

    # 4. Enforce dtypes on numeric columns
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")

    # 5. Outlier capping (IQR / Winsorization)
    print("\nCapping outliers (IQR)...")
    df = _cap_outliers_iqr(df, numeric_cols)

    # 6. Unify formats
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["region"] = df["region"].str.lower().str.strip()
    df["service_type"] = df["service_type"].str.lower().str.strip()

    # 7. Sort and reset index
    df = df.sort_values(by=["timestamp", "region"]).reset_index(drop=True)

    print("\nMissing values after cleaning:")
    print(df.isnull().sum())
    print(f"\nFinal shape: {df.shape}")

    df.to_csv(output_file, index=False)
    print(f"Cleaned data saved to {output_file}")
    return df


if __name__ == "__main__":
    input_csv = "azure_compute_storage_demand_10000_rows.csv"
    output_csv = "milestone_1_cleaned_data.csv"

    if os.path.exists(input_csv):
        cleaned_df = prepare_data(input_csv, output_csv)
    else:
        print(f"Error: '{input_csv}' not found. Place the dataset in the working directory.")
