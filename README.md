# Azure-Demand-Forecasting-Capacity-Optimization-System
Project: Azure Demand Forecasting & Capacity Optimization System

Milestone 1 — Data Collection & Preparation

Files:
- `data_prep.py`: loads raw CSV, cleans data, engineers basic time features, and writes a cleaned CSV and a simple data report.
- `requirements.txt`: Python dependencies.

Quickstart:

1. Create a venv and install dependencies:

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

2. Run the data preparation step (uses the provided CSV by default path):

```bash
python data_prep.py --input "F:\\Projects\\Infosys_Project\\azure_compute_storage_demand_10000_rows.csv" --output outputs/cleaned_azure_demand.csv --report outputs/data_report.txt
```

What I implemented for Milestone 1:
- Inspect and clean the provided dataset (timestamp parsing, numeric coercion, group-median imputation).
- Add basic features: `year`, `month`, `day`, `dayofweek`, `is_weekend`, `quarter`, `usage_to_prov_ratio`.
- Save cleaned CSV and a simple before/after data report.

Next recommended steps:
- Add automated unit checks and richer EDA (visualizations).
- Source external variables (economic indicators, holidays, market indices) and implement merge logic.
- Add lag/rolling/time-series features for modeling.
