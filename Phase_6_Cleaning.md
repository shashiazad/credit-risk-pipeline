# Phase 6: Data Cleaning & Feature Engineering

Data Cleaning translates raw, erratic, and corrupt data into a consistent, correct, and structured format. In this phase, we learn standard cleaning patterns and implement a cleaning module that prepares our loan risk data for loading into Google BigQuery.

---

## 1. Handling Missing Values (Nulls)

Null values occur regularly due to system dropouts, optional user entries, or integration glitches. We handle them using three main strategies:

### A. Deletion (Listwise Deletion)
*   **When to use:** When the missing value is critical and cannot be logically guessed. For example, if a record lacks a `loan_id` (Primary Key) or a `loan_amount` (the core analytical metric), we drop the row.
*   **Tradeoff:** Can lead to losing a large portion of your dataset if missing values are spread across many columns.

### B. Imputation (Replacement)
*   **Statistical Imputation:** Replacing nulls with statistical metrics like mean, median, or mode.
    *   *Best Practice:* Impute using **segmented groupings**. In our loan dataset, interest rates are directly tied to the loan's credit risk grade. Imputing a missing rate with the *overall global median* rate would be highly inaccurate. Instead, we impute the missing rate using the **median interest rate of that specific loan's Grade**.
*   **Constant Imputation:** Replacing nulls with a fixed indicator (e.g., replacing nulls in `emp_length` with `0`).

---

## 2. Deduplication Strategies

Duplicates can lead to severe double-counting errors in analytical aggregates (e.g., summing up total approved capital).
*   **Strategy:** In a data warehouse staging area, we identify duplicates using the logical Primary Key (`loan_id`). We sort the records (often keeping the latest timestamp or the most complete record) and call pandas `.drop_duplicates(subset=['loan_id'], keep='first')`.

---

## 3. Logical Boundaries & Standardizations

Raw data values can pass basic data type validation but fail logical checks (e.g., negative numbers for values that must be positive, or text inconsistencies like lowercase names).
*   **Logical Boundaries:** We filter out records with negative `loan_amount` values, and cap or drop records with DTIs above 100% (unless specific subprime portfolios allow it).
*   **Categorical Imputation:** If a record has an invalid rating category (like Grade `X`), we write a helper function that infers the correct grade based on the loan's `interest_rate`.
*   **Date Standardizations:** Date fields in raw logs often arrive in mixed formats (e.g., `2025-05-30` mixed with `04/02/2025`). We parse them dynamically using robust format parser engines and write them back as standard ISO strings (`YYYY-MM-DD`).

---

## 4. Feature Engineering

Feature Engineering is the process of using domain knowledge to extract new variables (features) from raw data.
*   **Derived Columns:** We create a binary target variable **`is_default`**:
    $$\text{is\_default} = \begin{cases} 1 & \text{if loan\_status is 'Charged Off' or 'Late'} \\ 0 & \text{otherwise} \end{cases}$$
*   **Debt-to-Income / Leverage Ratios:** Creating derived columns like `loan_to_income_ratio` ($\frac{\text{loan\_amount}}{\text{annual\_income}}$) to help risk analysts understand borrower burden.
