import pytest
import pandas as pd
from src.loader import BigQueryLoader

def test_loader_dry_run_initialization():
    """
    Assert that the loader falls back to dry-run mode when no credentials file exists.
    """
    loader = BigQueryLoader()
    # If credentials are not present, loader must run in dry_run_mode
    assert loader.dry_run_mode is True
    assert loader.client is None

def test_loader_dry_run_load_dataframe_success():
    """
    Assert that load_dataframe returns True under dry-run simulation mode.
    """
    loader = BigQueryLoader()
    assert loader.dry_run_mode is True
    
    # Create simple dummy dataframe
    df = pd.DataFrame({
        "loan_id": [1],
        "issue_date": ["2025-01-01"],
        "grade": ["A"],
        "purpose": ["car"]
    })
    
    success = loader.load_dataframe(df, "test_table")
    assert success is True
