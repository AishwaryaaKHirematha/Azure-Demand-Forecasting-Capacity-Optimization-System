import pandas as pd
import numpy as np
import os


def engineer_features(input_file: str, output_file: str) -> pd.DataFrame:
    print(f"Loading cleaned data from {input_file}...")
    df = pd.read_csv(input_file)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Sort for correct lag ordering within each group
    df = df.sort_values(by=["timestamp", "region", "service_type"]).reset_index(drop=True)

    # 1. Time-based features
    print("Engineering time-based features...")
    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["day_of_month"] = df["timestamp"].dt.day
    df["month"] = df["timestamp"].dt.month
    df["quarter"] = df["timestamp"].dt.quarter
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

    # 2. Lag features and rolling averages (grouped by region + service_type)
    print("Creating lag variables and rolling averages...")

    lag_and_roll_cols = [
        "usage_lag_1",
        "usage_lag_7",
        "usage_rolling_mean_3",
        "usage_rolling_mean_7",
    ]

    # Use .transform() so the result aligns correctly with the DataFrame index
    grp = df.groupby(["region", "service_type"])["usage_units"]
    df["usage_lag_1"] = grp.transform(lambda x: x.shift(1))
    df["usage_lag_7"] = grp.transform(lambda x: x.shift(7))
    df["usage_rolling_mean_3"] = grp.transform(
        lambda x: x.rolling(window=3, min_periods=1).mean()
    )
    df["usage_rolling_mean_7"] = grp.transform(
        lambda x: x.rolling(window=7, min_periods=1).mean()
    )

    # Usage spike relative to 7-step rolling mean (uses lag_1 to avoid data leakage)
    df["usage_spike"] = df["usage_lag_1"] / (df["usage_rolling_mean_7"] + 1e-6)

    # 3. Fill ONLY the lag/rolling NaNs (first rows per group) with 0
    #    Avoid globally filling all columns, which hides real data issues.
    df[lag_and_roll_cols + ["usage_spike"]] = df[
        lag_and_roll_cols + ["usage_spike"]
    ].fillna(0)

    print("\nFeature engineering complete. New columns added:")
    new_cols = ["hour", "day_of_week", "day_of_month", "month", "quarter",
                "is_weekend"] + lag_and_roll_cols + ["usage_spike"]
    print(new_cols)

    print(f"\nFinal shape: {df.shape}")
    df.to_csv(output_file, index=False)
    print(f"Feature-enriched data saved to {output_file}")
    return df


if __name__ == "__main__":
    input_csv = "milestone_1_cleaned_data.csv"
    output_csv = "milestone_2_featured_data.csv"

    if os.path.exists(input_csv):
        featured_df = engineer_features(input_csv, output_csv)
    else:
        print(f"Error: '{input_csv}' not found. Please run Milestone 1 first.")
