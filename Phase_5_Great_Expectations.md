# Phase 5: Data Quality with Great Expectations

Data Quality (DQ) ensures that decisions are made on trustworthy information. In this phase, we learn DQ fundamentals and write a programmatic validation layer using **Great Expectations** to verify our loan dataset.

---

## 1. What is Data Quality and Why Does It Matter?
In a data pipeline, **Garbage In = Garbage Out**. 
If a source system spits out negative loan amounts or invalid borrower grades, and we write this directly to our analytical models, the resulting risk scores will be false.

Data quality is measured by several dimensions:
1.  **Uniqueness:** No duplicate rows for unique identifiers (Primary Keys).
2.  **Completeness:** Check for missing values (Nulls) in critical fields.
3.  **Validity:** Values follow logical formatting (e.g. dates formatted as `YYYY-MM-DD`).
4.  **Accuracy / Range:** Numerical fields lie within logical boundaries (e.g. DTI between 0 and 100).
5.  **Consistency:** Categorical attributes belong to standard lists (e.g. Grade must be A, B, C, D, E, F, or G).

---

## 2. Great Expectations Architecture

Great Expectations (GE) is an open-source Python library for validating, documenting, and profiling data.

### Core Vocabulary:
*   **Expectations:** Assertions about data, written in Python (e.g., `expect_column_values_to_be_unique`).
*   **Validation Results:** The structured JSON report returned after running Expectations on a dataset.
*   **Data Docs:** Automatically compiled human-readable HTML reporting pages generated directly from validation results.
*   **Checkpoints:** Automated validation scripts that execute a list of expectation suites on a specific dataset and trigger actions (like sending notifications or dumping records to quarantine if tests fail).

---

## 3. Explaining Our Specific Validation Suite

For our loan risk pipeline, we construct 6 critical validation gates:

### A. Primary Key Uniqueness
*   **Expectation:** `expect_column_values_to_be_unique("loan_id")`
*   **Why:** Ensures that `loan_id` acts as a unique primary key. Duplicate loan IDs will cause duplication in our SQL aggregation summaries.

### B. Completeness of Loan Amount
*   **Expectation:** `expect_column_values_to_not_be_null("loan_amount")`
*   **Why:** The principal loan amount is the most critical metric for calculating credit risk exposure. A null value is unusable.

### C. Interest Rate Range Validation
*   **Expectation:** `expect_column_values_to_be_between("interest_rate", min_value=5.0, max_value=35.0)`
*   **Why:** Captures user entry typos or out-of-bounds rates (e.g., a rate of 99% or a negative rate).

### D. Categorical Inclusivity
*   **Expectation:** `expect_column_values_to_be_in_set("loan_status", value_set=["Fully Paid", "Charged Off", "Current", "Late"])`
*   **Why:** Ensures the status matches our business status model. Invalid codes (like "Unknown") will fail downstream queries.

### E. DTI Range Validation
*   **Expectation:** `expect_column_values_to_be_between("dti", min_value=0.0, max_value=100.0)`
*   **Why:** Validates that debt obligations do not exceed 100% of income, protecting calculations from extreme outliers.

### F. Date Format Validation
*   **Expectation:** `expect_column_values_to_match_strftime_format("issue_date", strftime_format="%Y-%m-%d")`
*   **Why:** Standardizes time formats. Mismatched date formats (like `MM/DD/YYYY` mixed with `YYYY-MM-DD`) cause database loader failures.
