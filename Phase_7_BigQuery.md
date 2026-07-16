# Phase 7: Google BigQuery Data Loading

Google BigQuery is a serverless, highly scalable cloud data warehouse. In this phase, we learn BigQuery's architecture, resource hierarchy, costing, security, and implement a loader module to transfer our cleaned credit risk data into the cloud.

---

## 1. What is Google BigQuery?
BigQuery is a **Cloud Data Warehouse** designed to store and analyze petabytes of data using SQL. It is "serverless," meaning Google manages all hardware, scaling, and performance tuning behind the scenes.

### A. Columnar Storage (Colossus)
Traditional transactional databases (like PostgreSQL or MySQL) store data **row-by-row**. 
*   **Transactional DB (Row-Oriented):** Good for writing individual records fast (e.g., a user submitting a loan application).
*   **Analytical DW (Column-Oriented):** BigQuery stores data **column-by-column**. If you run `SELECT SUM(loan_amount) FROM credit_loans`, BigQuery only reads the `loan_amount` column from disk, ignoring name, date, and status columns. This reduces disk I/O operations and runs aggregates in seconds instead of hours.

### B. Decoupled Compute (Dremel) and Storage (Colossus)
*   In older systems, to get more query processing power (compute), you had to buy more hard drives (storage).
*   BigQuery separates them. Storage is cheap (approx. \$0.02 per GB/month). Compute is scaled dynamically on demand. You only pay for the bytes scanned during your query (approx. \$6.25 per Terabyte scanned).

---

## 2. Resource Hierarchy in BigQuery

BigQuery resources are organized in a parent-child relationship:

```
  GCP Project (Billing boundary)
   └── Dataset (Logical database schema container)
        └── Tables & Views (Physical data storage & logical SQL definitions)
```

1.  **Project:** The root organization unit containing billing settings and API controls.
2.  **Dataset:** A schema namespace that holds tables, views, and procedures. Access controls (permissions) are set at the dataset level.
3.  **Table:** The structural rows and columns containing active data records.

---

## 3. Cost and Performance Optimization

To protect your budget in production, two optimization features are mandatory:

### A. Partitioning
Divides a massive table into smaller segments based on a date column (like `issue_date`) or an integer range.
*   **Why use it:** If you query a 5TB table for a single date (`WHERE issue_date = '2026-07-01'`), BigQuery only scans the partition folder for that date (scanning perhaps 50MB instead of 5TB), cutting your query cost by 99%.

### B. Clustering
Sorts and organizes data within each partition based on the values of specified columns (like `grade` or `purpose`).
*   **Why use it:** When filtering or grouping by a clustered column (e.g., `WHERE grade = 'A'`), BigQuery skips blocks of data that do not match the filter, accelerating query execution.

---

## 4. Security, Service Accounts, and Authentication

In modern cloud pipelines, humans do not run code using their personal usernames. Instead, we use **Service Accounts**.
*   **Service Account (SA):** A special Google identity representing an application (like our Airflow script).
*   **IAM (Identity & Access Management):** We grant role permissions (like `BigQuery Data Editor` and `BigQuery Job User`) to this Service Account.
*   **Service Account Key (JSON):** A key file containing cryptographic credentials. In Python, we load this key by pointing the environment variable `GOOGLE_APPLICATION_CREDENTIALS` to this JSON path.
