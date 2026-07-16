import pytest
import pandas as pd
from src.validation import DataValidator

def test_data_validator_clean_data_success():
    """
    Test that a clean dataset with perfect values passes all validator expectations.
    """
    validator = DataValidator()
    
    # Create clean compliant dataframe matching all expectations
    clean_data = {
        "loan_id": [200001, 200002, 200003],
        "member_id": [900001, 900002, 900003],
        "loan_amount": [10000.0, 15000.0, 20000.0],
        "interest_rate": [12.5, 14.2, 8.5],
        "grade": ["B", "C", "A"],
        "loan_status": ["Fully Paid", "Current", "Late"],
        "purpose": ["credit_card", "car", "debt_consolidation"],
        "annual_income": [80000.0, 95000.0, 120000.0],
        "dti": [12.5, 22.0, 45.0],
        "emp_length": [5, 10, 2],
        "issue_date": ["2025-01-01", "2025-02-01", "2025-03-01"]
    }
    df = pd.DataFrame(clean_data)
    
    # Run validation
    success = validator.run_validation(df)
    
    # Assert validation succeeded
    assert success is True, "Clean compliant data should pass all validation rules."

def test_data_validator_dirty_data_failure():
    """
    Test that a dataset containing logical anomalies fails validation.
    """
    validator = DataValidator()
    
    # Create dirty dataframe with anomalies
    dirty_data = {
        "loan_id": [200001, 200001, 200003], # Duplicate ID
        "member_id": [900001, 900002, 900003],
        "loan_amount": [10000.0, None, 20000.0], # Null amount
        "interest_rate": [12.5, 99.0, 8.5], # 99% is out of range (max 35)
        "grade": ["B", "X", "A"], # Invalid grade X
        "loan_status": ["Fully Paid", "Unknown", "Late"], # Invalid status Unknown
        "purpose": ["credit_card", "car", "debt_consolidation"],
        "annual_income": [80000.0, 95000.0, 120000.0],
        "dti": [12.5, 120.0, 45.0], # DTI 120% out of range (max 100)
        "emp_length": [5, 10, 2],
        "issue_date": ["2025-01-01", "04/02/2025", "2025-03-01"] # Invalid date format
    }
    df = pd.DataFrame(dirty_data)
    
    # Run validation
    success = validator.run_validation(df)
    
    # Assert validation failed
    assert success is False, "Dirty data containing anomalies should fail validations."
