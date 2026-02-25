import sys
import io
import pandas as pd
import numpy as np
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
import xgboost as xgb
import joblib

# Force UTF-8 stdout so XGBoost's internal Unicode output doesn't crash on Windows
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

FEATURES = [
    "hour", "day_of_week", "day_of_month", "month", "quarter", "is_weekend",
    "usage_lag_1", "usage_lag_7", "usage_rolling_mean_3", "usage_rolling_mean_7",
    "is_holiday", "usage_spike",
]
TARGET = "usage_units"


def _rmse(y_true, y_pred) -> float:
    """Compute RMSE in a way that is compatible with all scikit-learn versions."""
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def train_and_evaluate(input_file: str, model_output_path: str):
    print(f"Loading featured data from {input_file}...")
    df = pd.read_csv(input_file)

    # Validate that all required feature columns are present
    missing_features = [f for f in FEATURES if f not in df.columns]
    if missing_features:
        raise ValueError(
            f"Missing feature columns in dataset: {missing_features}. "
            "Ensure Milestone 2 has been run successfully."
        )
    if TARGET not in df.columns:
        raise ValueError(f"Target column '{TARGET}' not found in dataset.")

    X = df[FEATURES]
    y = df[TARGET]

    # Chronological 80/20 split (no shuffle — preserves time order)
    split_idx = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    print(f"Training set size : {len(X_train)}")
    print(f"Test set size     : {len(X_test)}")

    # --- Random Forest ---
    print("\nTraining Random Forest Regressor...")
    rf_model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    rf_model.fit(X_train, y_train)
    rf_preds = rf_model.predict(X_test)
    rf_mae = mean_absolute_error(y_test, rf_preds)
    rf_rmse = _rmse(y_test, rf_preds)
    print(f"  MAE : {rf_mae:.4f}")
    print(f"  RMSE: {rf_rmse:.4f}")

    # --- XGBoost ---
    print("\nTraining XGBoost Regressor...")
    xgb_model = xgb.XGBRegressor(
        n_estimators=100, learning_rate=0.1, max_depth=5,
        random_state=42, verbosity=0
    )
    xgb_model.fit(X_train, y_train)
    xgb_preds = xgb_model.predict(X_test)
    xgb_mae = mean_absolute_error(y_test, xgb_preds)
    xgb_rmse = _rmse(y_test, xgb_preds)
    print(f"  MAE : {xgb_mae:.4f}")
    print(f"  RMSE: {xgb_rmse:.4f}")

    # --- Select best model (lower MAE wins) ---
    if xgb_mae < rf_mae:
        print("\nXGBoost performed better → selected as final model.")
        best_model, best_name = xgb_model, "XGBoost"
        best_mae, best_rmse = xgb_mae, xgb_rmse
    else:
        print("\nRandom Forest performed better → selected as final model.")
        best_model, best_name = rf_model, "Random Forest"
        best_mae, best_rmse = rf_mae, rf_rmse

    joblib.dump(best_model, model_output_path)
    print(f"Best model saved to {model_output_path}")

    # Persist evaluation results
    with open("model_evaluation_results.txt", "w", encoding="utf-8") as f:
        f.write("=== Model Evaluation Results ===\n\n")
        f.write(f"Random Forest  — MAE: {rf_mae:.4f}  |  RMSE: {rf_rmse:.4f}\n")
        f.write(f"XGBoost        — MAE: {xgb_mae:.4f}  |  RMSE: {xgb_rmse:.4f}\n")
        f.write(f"\nSelected Model : {best_name}\n")
        f.write(f"Best MAE       : {best_mae:.4f}\n")
        f.write(f"Best RMSE      : {best_rmse:.4f}\n")

    return best_model


if __name__ == "__main__":
    input_csv = "milestone_2_featured_data.csv"
    model_path = "best_demand_forecast_model.pkl"

    if os.path.exists(input_csv):
        train_and_evaluate(input_csv, model_path)
    else:
        print(f"Error: '{input_csv}' not found. Please run Milestone 2 first.")
