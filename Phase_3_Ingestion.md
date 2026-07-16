# Phase 3: Data Ingestion

Data Ingestion is the entry gate of a data pipeline. A pipeline is only as reliable as its ingestion layer. In this phase, we design a defensive ingestion module that reads raw CSV data, performs safety checks, isolates errors, and logs performance.

---

## 1. What is Data Ingestion?
Data Ingestion is the process of extracting raw data from source systems (S3 buckets, web APIs, transactional DBs, third-party FTP servers) and loading it into the pipeline's storage layers.
*   **The Ingestion Rule:** Ingestion should do **minimal transformation**. The primary goal is to fetch data and write it to the landing zone as fast as possible, preserving the raw structure. This allows us to re-run transformations later if our business logic changes.

---

## 2. Ingestion Challenges in Production

When ingesting text-based files (like CSVs), pipelines regularly encounter three failure modes:

### A. Schema Drift
Source systems change. A developer might add a new column, delete an old column, or change the data type of an existing field (e.g., changing `loan_id` from integers to strings). If your pipeline is not defensive, this causes crash errors downstream.

### B. Corrupt / Mismatched Rows
A raw CSV might have a row with 12 comma-separated fields instead of 11 because a borrower wrote a comma in their text field (e.g., `"debt, credit card"` instead of wrapping it in quotes). This causes CSV parsers to throw exceptions.

### C. Large File Memory Exhaustion
If a source file is 20GB, running `pd.read_csv()` directly loads the entire file into RAM, crashing the server with an **Out Of Memory (OOM)** error. In production, we process large files in smaller, manageable **chunks** or stream them.

---

## 3. Designing a Defensive Ingestion Pipeline

To address these challenges, our ingestion module implements:
1.  **File Existence & Size Checks:** Fails early if the source file is missing or has a file size of 0 bytes.
2.  **Schema Check (Column Headers):** Compares the CSV column list against an expected set of columns. If columns are missing, it halts the pipeline.
3.  **Exception Wrapping:** Handles `EmptyDataError`, `ParserError`, and OS permission issues gracefully.
4.  **Logging Performance Metrics:** Logs the runtime duration, the total records ingested, and memory usage.
