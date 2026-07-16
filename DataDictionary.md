# Data Warehouse Glossary & Schema Dictionary

This document details the data structures across the Raw, Staging, Warehouse, and Analytics layers.

---

## 1. Raw landed layer (`raw_loans`)
Matches the raw CSV structure before casting or imputations.

*   `loan_id` (INT64): Natural identifier (contains duplicate violations).
*   `member_id` (INT64): Client tracking key.
*   `loan_amount` (FLOAT64): Requested principal (contains negative anomalies).
*   `interest_rate` (FLOAT64): APR percent rate (contains null values & usurious outliers).
*   `grade` (STRING): Borrower risk ranking letter (contains invalid 'X' categories).
*   `loan_status` (STRING): Repayment status (contains invalid 'Unknown' states).
*   `purpose` (STRING): Use category.
*   `annual_income` (FLOAT64): Self-reported income (contains missing values).
*   `dti` (FLOAT64): Debt-to-income percentage (contains nulls & >100% anomalies).
*   `emp_length` (FLOAT64): Employment years (contains missing values).
*   `issue_date` (STRING): Disbursal date (mismatched string patterns).

---

## 2. Warehouse Layer (Star Schema)

### Table: `fact_loans`
Holds the core metrics of each loan transaction.
*   `loan_id` (INT64 - Primary Key): Unique record identifier.
*   `member_id` (INT64 - Foreign Key): Points to `dim_borrowers`.
*   `loan_amount` (FLOAT64): Positive loan principal.
*   `interest_rate` (FLOAT64): APR percent rate.
*   `grade` (STRING): Cleaned rating (A to G).
*   `loan_status` (STRING): Repayment status.
*   `purpose` (STRING): Use intent description.
*   `dti` (FLOAT64): Debt-to-income percentage.
*   `issue_date` (DATE string): Disbursal date standardized to `YYYY-MM-DD`.
*   `is_default` (INT64 - Engineered Feature): `1` if status is Charged Off/Late, else `0`.
*   `loan_to_income_ratio` (FLOAT64 - Engineered Feature): Principal divided by income.

### Table: `dim_borrowers`
Holds descriptive borrower profile attributes.
*   `member_id` (INT64 - Primary Key): Unique identifier.
*   `annual_income` (FLOAT64): Cleaned annual income.
*   `emp_length` (INT64): Employment duration in years.

---

## 3. Analytics Layer (SQL Views)

### View: `loan_summary`
Aggregates issued metrics grouped by rating and intent.
*   `grade` (STRING): Risk rating.
*   `purpose` (STRING): Intended use.
*   `total_loans` (INT64): Count of applications.
*   `total_capital_issued` (FLOAT64): Sum of principal capital.
*   `average_interest_rate` (FLOAT64): Mean APR.
*   `average_dti` (FLOAT64): Mean debt-to-income ratio.

### View: `risk_metrics`
Details credit defaults, leverage, and vintage metrics per rating class.
*   `grade` (STRING): Risk rating.
*   `total_applications` (INT64): Count of loans.
*   `total_defaults` (INT64): Count of defaults (Charged Off + Late).
*   `default_rate_pct` (FLOAT64): Default rate: $\frac{\text{total\_defaults}}{\text{total\_applications}} \times 100$.
*   `average_leverage` (FLOAT64): Mean loan-to-income ratio.
