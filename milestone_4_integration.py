import sys
import io
import pandas as pd
import numpy as np
import joblib
import os
import matplotlib
matplotlib.use("Agg")  # Headless / non-interactive backend
import matplotlib.pyplot as plt

# Force UTF-8 stdout so any library Unicode output doesn't crash on Windows
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

FEATURES = [
    "hour", "day_of_week", "day_of_month", "month", "quarter", "is_weekend",
    "usage_lag_1", "usage_lag_7", "usage_rolling_mean_3", "usage_rolling_mean_7",
    "is_holiday", "usage_spike",
]
REPORT_COLS = [
    "timestamp", "region", "service_type", "usage_units",
    "provisioned_capacity_allocated", "forecasted_usage",
    "recommended_capacity", "infrastructure_action",
]
CAPACITY_COL = "provisioned_capacity_allocated"
UNIT_COST = 1_000        # $ per unit of over-provisioned capacity
BUFFER_PCT = 0.15        # 15% headroom above forecast
ACTION_MARGIN = 0.10     # 10% band around recommended capacity


def _get_action(row: pd.Series) -> str:
    """Determine infrastructure action for a given row."""
    if row["recommended_capacity"] > row[CAPACITY_COL] * (1 + ACTION_MARGIN):
        return "UPSCALE"
    elif row["recommended_capacity"] < row[CAPACITY_COL] * (1 - ACTION_MARGIN):
        return "DOWNSCALE"
    return "MAINTAIN"


def run_integration(
    featured_data_path: str,
    model_path: str,
    output_report: str,
) -> pd.DataFrame:

    print("Loading data and model...")
    df = pd.read_csv(featured_data_path)
    model = joblib.load(model_path)

    # --- Validate required columns ---
    required = FEATURES + ["usage_units", CAPACITY_COL]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in featured data: {missing}")

    # --- 1. Real-time Forecasting Simulation (latest 500 rows) ---
    latest = df.tail(500).copy().reset_index(drop=True)
    latest["forecasted_usage"] = model.predict(latest[FEATURES])
    latest["timestamp"] = pd.to_datetime(latest["timestamp"])

    model_mae = np.mean(np.abs(latest["usage_units"] - latest["forecasted_usage"]))
    naive_mae = np.mean(np.abs(latest["usage_units"] - latest["usage_lag_1"]))

    accuracy_gain_pct = ((naive_mae - model_mae) / (naive_mae + 1e-6)) * 100
    # $120M annual value per 1% accuracy gain (project assumption)
    estimated_savings = max(0.0, accuracy_gain_pct * 120_000_000)

    print(f"\nModel MAE   : {model_mae:.4f}")
    print(f"Naive MAE   : {naive_mae:.4f}")
    print(f"Accuracy Gain vs Naive: {max(accuracy_gain_pct, 0):.2f}%")
    print(f"Estimated Annual Savings Impact: ${estimated_savings:,.2f}")

    # --- 2. Capacity Planning ---
    latest["recommended_capacity"] = latest["forecasted_usage"] * (1 + BUFFER_PCT)
    latest["potential_savings"] = (
        latest[CAPACITY_COL] - latest["recommended_capacity"]
    ).clip(lower=0) * UNIT_COST

    # --- 3. Infrastructure Actions ---
    latest["infrastructure_action"] = latest.apply(_get_action, axis=1)
    total_sim_savings = latest["potential_savings"].sum()

    # --- 4. Report ---
    report = (
        latest[REPORT_COLS]
        .sort_values("timestamp")
        .tail(100)
    )
    report.to_csv(output_report, index=False)
    print(f"Provisioning actions report saved to {output_report}")

    # --- 5. Visualization ---
    fig, ax = plt.subplots(figsize=(15, 8))
    plot_df = latest.tail(200)
    count = 0
    for (region, s_type), grp in plot_df.groupby(["region", "service_type"]):
        if count >= 3:
            break
        ax.plot(
            grp["timestamp"], grp["usage_units"],
            label=f"Actual ({region}-{s_type})", marker="o", alpha=0.6,
        )
        ax.plot(
            grp["timestamp"], grp["forecasted_usage"],
            label=f"Forecast ({region}-{s_type})", linestyle="--", alpha=0.8,
        )
        count += 1

    ax.set_title("Azure Demand Forecast: Actual vs Predicted (Strategic Sample)")
    ax.set_xlabel("Time")
    ax.set_ylabel("Usage Units")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()
    plot_path = "forecast_vs_actual.png"
    fig.savefig(plot_path)
    plt.close(fig)   # Prevent memory leak
    print(f"Visualization saved to {plot_path}")

    # --- 6. Summary Report ---
    with open("milestone_4_summary_report.txt", "w", encoding="utf-8") as f:
        f.write("Azure Capacity Optimization — Summary Report\n")
        f.write("=" * 46 + "\n\n")
        f.write(f"Snapshots analyzed             : {len(latest)}\n")
        f.write(f"Model MAE                      : {model_mae:.4f}\n")
        f.write(f"Naive Baseline MAE             : {naive_mae:.4f}\n")
        f.write(
            f"Accuracy Gain (vs Naive)       : "
            f"{max(accuracy_gain_pct, 0):.2f}%"
            + (" [!] Model underperforms naive baseline" if accuracy_gain_pct < 0 else "") + "\n"
        )
        f.write(f"Proj. Annual Savings (Accuracy): ${estimated_savings:,.2f}\n")
        f.write(f"Simulation Savings (Waste Red.): ${total_sim_savings:,.2f}\n")
        f.write("\nAction Summary:\n")
        f.write(latest["infrastructure_action"].value_counts().to_string() + "\n")
        f.write(f"\nDetailed actions: see '{output_report}'\n")
        f.write(
            "\nRetraining trigger: bias drift > 10% OR latency metric anomaly detected.\n"
        )

    print("\nIntegration & Optimization complete.")
    return latest


if __name__ == "__main__":
    featured_csv = "milestone_2_featured_data.csv"
    model_pkl = "best_demand_forecast_model.pkl"
    report_csv = "optimization_actions_report.csv"

    if os.path.exists(featured_csv) and os.path.exists(model_pkl):
        run_integration(featured_csv, model_pkl, report_csv)
    else:
        print("Required files missing. Please run Milestones 1–3 first.")
