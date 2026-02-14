"""Data preparation for Azure demand forecasting (Milestone 1).

Usage:
  python data_prep.py --input <input_csv> --output <output_csv>

Produces a cleaned CSV and a simple data report.
"""

import argparse
import os
from pathlib import Path
import pandas as pd
import numpy as np


def load_data(path):
    return pd.read_csv(path)


def basic_checks(df):
    info = {}
    info['rows'] = df.shape[0]
    info['cols'] = df.shape[1]
    info['dtypes'] = df.dtypes.apply(lambda x: x.name).to_dict()
    info['missing_per_col'] = df.isna().sum().to_dict()
    return info


def clean_data(df):
    # Parse timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

    # Standardize categorical fields
    df['region'] = df['region'].astype('category')
    df['service_type'] = df['service_type'].astype('category')

    # Numeric columns
    numeric_cols = ['usage_units', 'provisioned_capacity_allocated', 'cost_usd', 'availability_pct']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # is_holiday to int
    if 'is_holiday' in df.columns:
        df['is_holiday'] = pd.to_numeric(df['is_holiday'], errors='coerce').fillna(0).astype(int)

    # Impute numeric missing values with median (per region+service_type if possible)
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df.groupby(['region', 'service_type'])[col].transform(lambda x: x.fillna(x.median()))
            # fallback global median
            df[col] = df[col].fillna(df[col].median())

    # Drop rows with missing timestamp
    df = df.dropna(subset=['timestamp'])

    # Feature engineering: date parts
    df['date'] = df['timestamp'].dt.date
    df['year'] = df['timestamp'].dt.year
    df['month'] = df['timestamp'].dt.month
    df['day'] = df['timestamp'].dt.day
    df['dayofweek'] = df['timestamp'].dt.dayofweek
    df['is_weekend'] = df['dayofweek'].isin([5,6]).astype(int)

    # Seasonality buckets (quarter)
    df['quarter'] = df['timestamp'].dt.quarter

    # Usage per provisioned capacity (efficiency)
    df['usage_to_prov_ratio'] = df['usage_units'] / df['provisioned_capacity_allocated']
    df['usage_to_prov_ratio'] = df['usage_to_prov_ratio'].replace([np.inf, -np.inf], np.nan).fillna(0)

    # Sort
    df = df.sort_values(['region', 'service_type', 'timestamp']).reset_index(drop=True)

    return df


def save_report(info, path):
    lines = []
    lines.append(f"Rows: {info['rows']}")
    lines.append(f"Cols: {info['cols']}")
    lines.append("\nColumn dtypes:")
    for k, v in info['dtypes'].items():
        lines.append(f" - {k}: {v}")
    lines.append("\nMissing values per column:")
    for k, v in info['missing_per_col'].items():
        lines.append(f" - {k}: {v}")

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def main():
    parser = argparse.ArgumentParser(description='Prepare Azure demand dataset')
    parser.add_argument('--input', type=str, required=True, help='Input CSV path')
    parser.add_argument('--output', type=str, default='outputs/cleaned_azure_demand.csv', help='Output cleaned CSV')
    parser.add_argument('--report', type=str, default='outputs/data_report.txt', help='Data report path')
    args = parser.parse_args()

    df = load_data(args.input)
    info_before = basic_checks(df)
    df_clean = clean_data(df)
    info_after = basic_checks(df_clean)

    # Save cleaned
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_csv(out_path, index=False)

    # Save report (include before/after)
    report_lines = ["=== Data report: before cleaning ===", '']
    report_lines += [f"{k}: {v}" for k, v in info_before.items() if k != 'dtypes']
    report_lines += ['', '=== dtypes ===']
    report_lines += [f"{k}: {v}" for k, v in info_before['dtypes'].items()]
    report_lines += ['', '=== Missing before ===']
    report_lines += [f"{k}: {v}" for k, v in info_before['missing_per_col'].items()]

    report_lines += ['', '=== Data report: after cleaning ===', '']
    report_lines += [f"{k}: {v}" for k, v in info_after.items() if k != 'dtypes']
    report_lines += ['', '=== dtypes ===']
    report_lines += [f"{k}: {v}" for k, v in info_after['dtypes'].items()]
    report_lines += ['', 'Notes:', ' - Imputed numeric missing values by group median then global median', ' - Dropped rows with invalid timestamps', ' - Added date and seasonality features']

    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    with open(args.report, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

    print(f"Cleaned data saved to: {out_path}")
    print(f"Report saved to: {args.report}")


if __name__ == '__main__':
    main()
