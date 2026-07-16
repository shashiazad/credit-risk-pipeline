# Credit/Loan Risk Data Pipeline: Architecture Guide & Interview Q&A

This document provides a comprehensive breakdown of the project architecture and a structured Q&A bank designed to help you explain this project in senior Data Engineering interviews.

---

## 1. Project Explanation (For Your Resume/Portfolio)

### The Business Case
Lending institutions process thousands of loan applications daily. To manage underwriting risk, analysts require access to cleansed, normalized, and aggregate metrics indicating applicant leverage (Loan-to-Income) and default frequency. 

This project implements an automated **ELT (Extract, Load, Transform)** pipeline that ingests dirty applicant data, runs automated data quality validations, structures the data into a Kimball Star Schema, and loads it into a high-performance cloud data warehouse (Google BigQuery).

### The ELT Architecture Flow
Rather than transforming data before loading it (traditional ETL), this pipeline follows **ELT**:
1.  **Extract (E):** Raw csv batches are generated and landed in `data/landing/`.
2.  **Load (L):** Ingested raw batches are consolidated and written directly into the warehouse database storage layer (`staging_raw_loans`) without modifications.
3.  **Transform (T):** Data is cleansed, deduplicated, imputed, and reshaped into Fact and Dimension tables (`fact_loans` and `dim_borrowers`) inside the warehouse. Analytics aggregates are then generated as database views (`loan_summary` and `risk_metrics`).

```
  [1. Ingestion]            [2. Data Docs]
  Extract CSVs ──► Great Expectations checks
                         │
                         ▼
  [3. Load Stage] ──► Write to staging_raw_loans.csv (Load)
                         │
                         ▼
  [4. Cleaning]   ──► Impute missing rates by grade median
                      Resolve invalid grades & negative values
                         │
                         ▼
  [5. Warehouse]  ──► Split to Fact & Dimension (Transform)
                      Deploy SQL Analytics Views (loan_summary, risk_metrics)
```

---

## 2. Technical Component Deep-Dive

*   **Ingestion:** Implemented defensively using Python and Pandas. Reads files matching glob patterns, drops corrupted lines using `on_bad_lines='warn'` to prevent execution crashes, and handles empty files gracefully.
*   **Data Quality (Great Expectations):** Automatically verifies schemas and checks metrics. Alerts engineers before dirty data pollutes down-stream warehouse layers.
*   **Orchestration (Apache Airflow):** Uses the modern TaskFlow API to schedule tasks. Runs on a LocalExecutor utilizing process workers, backed by a PostgreSQL database for state management.
*   **Warehouse Design:** Kimball Star Schema consisting of:
    *   `fact_loans`: Numeric transaction details. Date partitioned on `issue_date` and clustered on `grade` and `purpose` to optimize query costs.
    *   `dim_borrowers`: De-duplicated customer attributes.
*   **Containerization (Docker & Compose):** Isolates services (scheduler, webserver, database, data simulator) to guarantee identical executions in dev, test, and prod.

---

## 3. Interview Q&A Bank (20+ Target Questions)

### Category A: Architecture & ELT Concepts
1.  **Q: Why did you choose ELT over ETL for this pipeline?**
    *   *Answer:* "ELT is preferred for modern cloud warehouses like BigQuery. By loading raw data first, we ensure we preserve a historical audit log of our raw records. If we discover a bug in our transformation logic later, we don't have to re-extract the data from the source systems; we can just rebuild our transformations directly inside the warehouse. Additionally, ELT leverages the massive distributed compute scaling of the cloud warehouse to run transformations, rather than loading data into memory on a separate ETL server."
2.  **Q: How does your pipeline design handle source data auditability?**
    *   *Answer:* "In the Load stage, we write the raw extracted batch directly to a raw staging area. When executing downstream transformations, we preserve these raw files and write the results to a separate `/processed` workspace. This guarantees raw immutability and complete audit tracks."
3.  **Q: What is a Kimball Star Schema, and why did you use it here?**
    *   *Answer:* "A Kimball Star Schema organizes database tables into Facts (transaction events with metrics and foreign keys) and Dimensions (descriptive descriptive details). In our pipeline, we split loans into `fact_loans` and `dim_borrowers`. This reduces duplication (since borrower profiles are deduplicated) and accelerates analytical join performance inside columnar databases."

### Category B: Ingestion & Data Quality
4.  **Q: How did you implement defensive coding during file ingestion?**
    *   *Answer:* "We checked that incoming files exist and have a non-zero size before parsing them. When calling Pandas' `read_csv`, we wrapped the method in try-except statements catching `ParserError` and `EmptyDataError`, and passed `on_bad_lines='warn'` to write corrupted rows to logs rather than crashing the ingestion thread."
5.  **Q: What framework did you use for data quality, and how is it integrated?**
    *   *Answer:* "We used Great Expectations 1.x. It executes immediately after ingestion. We defined expectations verifying that `loan_id` is unique and non-null, `loan_amount` is positive, and variables like `interest_rate` and `dti` fall within expected mathematical percentage boundaries. If a critical validation fails, the pipeline raises an exception and aborts execution."
6.  **Q: How does your ingestion pipeline handle schema drift?**
    *   *Answer:* "We validate the headers of the ingested dataframes against a hardcoded list of expected columns. If any expected columns are missing, we immediately reject the batch to prevent loading incomplete schemas into our staging database."

### Category C: Cleaning & Feature Engineering
7.  **Q: How did you impute missing values for numerical credit columns?**
    *   *Answer:* "Instead of using global medians which bias statistical models, we calculated group-by medians. For example, if a loan has a missing interest rate, we look up the median interest rate of all loans in its specific credit risk Grade (A-G) and use that value. This preserves the variance and credit distribution of our underwriting model."
8.  **Q: How did you handle category anomalies like invalid Grade 'X'?**
    *   *Answer:* "Instead of dropping valuable rows with invalid Grade 'X', we dynamically re-mapped them. We wrote a mapping function that checks the interest rate of the loan and assigns it to grades A-G using interest rate ranges (e.g. rate < 8.0% is Grade A)."
9.  **Q: Why do you perform feature engineering in the pipeline instead of leaving it to the BI dashboard?**
    *   *Answer:* "Engineering parameters like `is_default` and `loan_to_income_ratio` inside our transformation layer guarantees a single source of truth across the organization. If left to individual dashboard queries, different analysts might calculate default or leverage using conflicting logic, resulting in mismatched financial reports."

### Category D: Warehouse Modeling & BigQuery
10. **Q: How does BigQuery's storage model differ from traditional databases?**
    *   *Answer:* "Traditional databases are row-oriented (storing full rows together), which is optimal for writes (OLTP). BigQuery is column-oriented (storing columns together), which is optimal for OLAP. If we run a query calculating the average loan amount, BigQuery only reads the data block containing the `loan_amount` column, completely skipping all other columns, reducing database I/O."
11. **Q: How do partitioning and clustering optimize costs in BigQuery?**
    *   *Answer:* "Partitioning splits a table into daily folders based on a date column. When a query filters by a date, BigQuery only scans that specific folder, reducing scanned bytes. Clustering sorts the data within each partition by specific high-cardinality columns (like `grade` and `purpose`). This speeds up aggregation and filtering operations by skipping irrelevant blocks."
12. **Q: Why did you choose 'WRITE_APPEND' for loading live data?**
    *   *Answer:* "For live streaming/micro-batching, we use `WRITE_APPEND` to append new incoming records to the warehouse tables. If we used `WRITE_TRUNCATE`, we would wipe out the historical data on every run. We reserve `WRITE_TRUNCATE` for initial full-load migrations or complete backfills."

### Category E: Orchestration (Apache Airflow)
13. **Q: Explain the differences between the Airflow SequentialExecutor and LocalExecutor.**
    *   *Answer:* "SequentialExecutor uses an SQLite database backend and can only execute one task at a time because SQLite locks the database file on write. LocalExecutor uses PostgreSQL or MySQL, enabling the scheduler to spawn parallel process workers to run multiple tasks concurrently, which is critical for scaling pipelines in production."
14. **Q: What is the Airflow TaskFlow API, and why did you use it?**
    *   *Answer:* "TaskFlow API uses Python decorators like `@dag` and `@task` to define workflows. It simplifies DAG code by automatically managing dependencies and sharing task outputs (XComs) implicitly, replacing old verbose operator declarations."
15. **Q: How did you implement monitoring and alerting for pipeline failures?**
    *   *Answer:* "We bound a custom Python function to the DAG's `on_failure_callback` parameter. If any task throws an exception, Airflow captures the runtime context (DAG name, task ID, execution timestamp, and error stack trace) and routes it to an alerting service (simulating notifications to Slack and email support lists)."

### Category F: Docker, Testing, and CI/CD
16. **Q: Why did you containerize your pipeline using Docker Compose?**
    *   *Answer:* "Data pipelines often fail due to differences in OS environments or missing library versions. Containerizing ensures that the database (Postgres), the scheduler, the webserver, and the code scripts run in a unified environment, guaranteeing identical execution locally, on staging, and in cloud production."
17. **Q: Why did you mount local project folders as volumes in Docker Compose?**
    *   *Answer:* "Mounting local directories as volumes (e.g. `./dags:/opt/airflow/dags`) links the host filesystem to the container. This enables us to write code in our IDE and see the changes reflected inside the running Airflow instance instantly without rebuilding the Docker image, speeding up development."
18. **Q: How did you test your pipeline code?**
    *   *Answer:* "We implemented automated tests using Pytest. We wrote unit tests for the ingestion checking logic, validation metrics, cleaning transformations (verifying that deduplications and segmented imputations behave correctly on mock dataframes), and database loaders. Our pipeline currently passes all 14 tests."
19. **Q: Describe your CI/CD setup.**
    *   *Answer:* "We configured a GitHub Actions pipeline (`.github/workflows/ci_pipeline.yml`). On every push or pull request to the main branches, the runner checkouts the code, sets up Python, installs requirements, generates our mock raw dataset, and executes the entire Pytest test suite. This acts as a quality gate to prevent broken code from being merged."
20. **Q: How do you handle database credentials securely in Docker and Airflow?**
    *   *Answer:* "We never hardcode keys or passwords. We use an `.env` file (which is git-ignored) to manage secrets. Docker Compose reads these variables and injects them into the containers as environment variables at runtime. In Airflow, we configure service connections using environment variables like `AIRFLOW_CONN_METADATA_DB` or load keys via `GOOGLE_APPLICATION_CREDENTIALS` paths."
