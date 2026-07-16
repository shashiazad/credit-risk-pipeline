import pytest
import pandas as pd
from src.transformation import BigQueryTransformer

def test_build_star_schema():
    """
    Verify that the dataset splits correctly into fact and dimension tables.
    """
    transformer = BigQueryTransformer()
    
    # Create simple cleaned df mock
    df_clean = pd.DataFrame({
        "loan_id": [101, 102],
        "member_id": [901, 901], # Same borrower applying twice
        "loan_amount": [10000.0, 15000.0],
        "interest_rate": [12.5, 14.2],
        "grade": ["B", "C"],
        "loan_status": ["Current", "Late"],
        "purpose": ["car", "credit_card"],
        "dti": [12.5, 22.0],
        "annual_income": [80000.0, 80000.0], # Same income
        "emp_length": [5, 5],
        "issue_date": ["2025-01-01", "2025-02-01"],
        "is_default": [0, 1],
        "loan_to_income_ratio": [0.1250, 0.1875]
    })
    
    fact, dim = transformer.build_star_schema(df_clean)
    
    # Assert dimensions has deduplicated borrower profile
    assert len(dim) == 1
    assert list(dim["member_id"]) == [901]
    assert list(dim["annual_income"]) == [80000.0]
    
    # Assert fact has all transaction records
    assert len(fact) == 2
    assert "loan_amount" in fact.columns
    assert "annual_income" not in fact.columns

def test_run_local_analytics():
    """
    Verify local aggregations generate accurate summaries and default rates.
    """
    transformer = BigQueryTransformer()
    
    # Simple fact
    fact = pd.DataFrame({
        "loan_id": [1, 2, 3],
        "member_id": [10, 10, 20],
        "loan_amount": [10000.0, 10000.0, 20000.0],
        "interest_rate": [10.0, 10.0, 20.0],
        "grade": ["A", "A", "B"],
        "loan_status": ["Current", "Fully Paid", "Charged Off"],
        "purpose": ["car", "car", "medical"],
        "dti": [10.0, 10.0, 30.0],
        "issue_date": ["2025-01-01", "2025-01-01", "2025-01-01"],
        "is_default": [0, 0, 1],
        "loan_to_income_ratio": [0.1, 0.1, 0.4]
    })
    
    # Simple dim
    dim = pd.DataFrame({
        "member_id": [10, 20],
        "annual_income": [100000.0, 50000.0],
        "emp_length": [10, 2]
    })
    
    results = transformer.run_local_analytics(fact, dim)
    
    # 1. Check loan_summary
    loan_summary = results["loan_summary"]
    # We should have Grade A / car and Grade B / medical
    assert len(loan_summary) == 2
    row_a = loan_summary[loan_summary["grade"] == "A"].iloc[0]
    assert row_a["total_loans"] == 2
    assert row_a["total_capital_issued"] == 20000.0
    
    # 2. Check risk_metrics
    risk_metrics = results["risk_metrics"]
    row_b_risk = risk_metrics[risk_metrics["grade"] == "B"].iloc[0]
    assert row_b_risk["total_applications"] == 1
    assert row_b_risk["total_defaults"] == 1
    assert row_b_risk["default_rate_pct"] == 100.0
