import os
import pandas as pd
from data_prep import load_data, clean_data


def test_clean_data_basic():
    # Load a small sample from the committed CSV
    path = os.path.join(os.path.dirname(__file__), '..', 'azure_compute_storage_demand_10000_rows.csv')
    path = os.path.normpath(path)
    df = load_data(path)
    assert 'timestamp' in df.columns
    # Run cleaning on a subset to keep test fast
    dfc = clean_data(df.head(20))
    assert 'usage_to_prov_ratio' in dfc.columns
    # timestamps should be parsed
    assert not dfc['timestamp'].isna().any()
