import pytest
import pandas as pd
import os
from src.ingestion import DataIngester

def test_ingester_initialization():
    """
    Test that the DataIngester initializes config and directories.
    """
    ingester = DataIngester()
    assert ingester.raw_file_name == "credit_risk_dataset.csv"
    assert ingester.source_path.endswith("credit_risk_dataset.csv")

def test_validate_file_not_found():
    """
    Test file validation fails when file does not exist.
    """
    ingester = DataIngester()
    ingester.source_path = "non_existent_file.csv"
    assert ingester.validate_file() is False

def test_validate_schema_missing_columns():
    """
    Test schema validation fails if columns are missing.
    """
    ingester = DataIngester()
    # Create a dummy DataFrame with missing columns
    df = pd.DataFrame({
        "loan_id": [1, 2],
        "member_id": [100, 200]
    })
    assert ingester.validate_schema(df) is False

def test_validate_schema_success():
    """
    Test schema validation passes when all columns are present.
    """
    ingester = DataIngester()
    df = pd.DataFrame(columns=ingester.expected_columns)
    assert ingester.validate_schema(df) is True

def test_ingest_data_success():
    """
    Test ingestion completes successfully on standard raw data.
    """
    ingester = DataIngester()
    df = ingester.ingest_data()
    assert df is not None
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
