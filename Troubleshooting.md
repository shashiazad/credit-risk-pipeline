# Troubleshooting & FAQ Guide

Review these common issues and solutions encountered when setting up or running the pipeline.

---

## 1. Python Path / ModuleNotFound Errors

*   **Problem:** Python throws `ModuleNotFoundError: No module named 'src'` when running local scripts or test suites.
*   **Cause:** The python interpreter cannot find the root package folders because the directory of the script is added to system paths, but the project root folder is not.
*   **Solution:** Run scripts from the project root directory prefixing the command with `PYTHONPATH=.`:
    ```bash
    PYTHONPATH=. venv/bin/python3 src/cleaning.py
    ```

---

## 2. Airflow Dependency Conflicts (Pluggy/Packaging/etc.)

*   **Problem:** Running `pytest` throws `TypeError: __call__() got an unexpected keyword argument` or webserver UI fails.
*   **Cause:** Airflow’s official constraints file pins older versions of core package dependencies (like `pluggy==1.3.0` or `packaging==23.2`) to protect the scheduler, conflicting with modern versions of `pytest` or `google-cloud-bigquery`.
*   **Solution:** Re-align libraries to overlapping compliant versions:
    ```bash
    venv/bin/pip install "pluggy>=1.5.0" "packaging>=24.2.0"
    ```

---

## 3. Ephemeral Great Expectations Asset Errors

*   **Problem:** Great Expectations throws `ValueError: "loan_data_asset" already exists` during subsequent validation runs.
*   **Cause:** In Great Expectations 1.x File Data Contexts, data assets must be unique. Rerunning `datasource.read_dataframe(df, asset_name)` using the same name throws a collision error.
*   **Solution:** Delete the existing asset before instantiating the validator batch:
    ```python
    try:
        datasource.delete_asset("raw_loans_asset")
    except Exception:
        pass
    ```

---

## 4. Google Cloud Permission Denied (403 Errors)

*   **Problem:** Loader throws a `403 Forbidden` error when attempting to query or write datasets in BigQuery.
*   **Cause:** The Service Account is missing the required permissions in the GCP Project IAM roles tab.
*   **Solution:** Go to **IAM & Admin** in GCP Console. Find your service account and ensure it is assigned the **`BigQuery Admin`** role (or both `BigQuery Data Editor` and `BigQuery Job User`).

---

## 5. Airflow SQLite Database Locking Errors

*   **Problem:** Airflow throws `sqlite3.OperationalError: database is locked` or tasks hang.
*   **Cause:** SQLite does not support parallel execution writes. If you trigger multiple DAG runs at once using Sequential/LocalExecutor, the database locks.
*   **Solution:** Spin up the Docker environment (which uses **Postgres** as the metadata database) to support LocalExecutor's parallel processes:
    ```bash
    docker-compose up -d
    ```
