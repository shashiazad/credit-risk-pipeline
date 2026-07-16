# Phase 4: Apache Airflow Tutorial

Apache Airflow is the industry-standard orchestrator for data pipelines. In this phase, we learn Airflow's architecture, core concepts, how to install it, and write our first Directed Acyclic Graph (DAG).

---

## 1. Why Airflow Exists

### The Old Way: Cron Jobs
Before modern orchestrators, pipelines were scheduled using system **cron jobs** (e.g., run a script every night at 2:00 AM).
*   **The Issues with Cron:**
    1.  **No Dependency Management:** If Script B depends on Script A, you have to time them (e.g., Script A at 2 AM, Script B at 3 AM). If Script A runs slow and takes 90 minutes, Script B will start before Script A finishes, causing data corruption.
    2.  **No Visual Monitoring:** There is no UI to see what succeeded or failed.
    3.  **No Automatic Retries:** If a network connection drops for 2 seconds, the cron job fails completely.
    4.  **Difficult Log Management:** System logs are scattered across files, making debugging painful.

### The Airflow Solution
Airflow represents pipelines as **Code** (Configuration as Code). You define task dependencies, retry policies, alert conditions, and execution schedules programmatically in Python.

---

## 2. Airflow Architecture

Airflow is composed of several components working together:

```
                  ┌──────────────┐
                  │  Webserver   │ <── (UI for Monitoring)
                  └──────┬───────┘
                         │
                         ▼
  ┌──────────┐    ┌──────────────┐    ┌──────────────┐
  │   DAG    │ ──>│  Scheduler   │ ──>│   Executor   │
  │  Files   │    └──────┬───────┘    └──────┬───────┘
  └──────────┘           │                   │
                         ▼                   ▼
                  ┌──────────────────────────┐
                  │    Metadata Database     │ <── (SQLite/PostgreSQL)
                  └──────────────────────────┘
                         ▲
                         │
                  ┌──────┴───────┐
                  │   Workers    │ <── (Executes actual tasks)
                  └──────────────┘
```

*   **Scheduler:** The heart of Airflow. A daemon process that constantly monitors DAGs and schedules tasks that are ready to run.
*   **Metadata Database:** The central database (SQLite by default, PostgreSQL/MySQL in production) where Airflow stores state, configuration, logs, variables, and history.
*   **Executor:** The worker-driver that determines *how* tasks get run.
    *   *SequentialExecutor:* Default for local test. Runs one task at a time sequentially.
    *   *LocalExecutor:* Runs multiple tasks in parallel using subprocesses on the scheduler host.
    *   *CeleryExecutor:* Distributes tasks to a cluster of worker nodes.
*   **Webserver:** The Flask UI that lets you visualize, trigger, pause, and debug DAGs.
*   **Workers:** The actual compute instances that execute the task logic (active under Celery/Kubernetes executors).

---

## 3. Core Concepts

### A. DAG (Directed Acyclic Graph)
A DAG is a collection of tasks organized to reflect their relationships and execution rules:
*   **Directed:** A clear path from task to task (e.g., Task A $\rightarrow$ Task B).
*   **Acyclic:** No loops or cycles. If Task A leads to Task B, Task B cannot loop back to Task A. This ensures deterministic execution.

### B. Tasks and Operators
*   **Operator:** The template for a task. An operator is class-based logic that defines *what* to do.
    *   `PythonOperator`: Runs a custom Python function.
    *   `BashOperator`: Executes a shell command.
    *   `BigQueryOperator`: Runs a SQL query in Google BigQuery.
*   **Task:** The instantiated operator that represents a node in the DAG.

### C. TaskFlow API
In newer versions of Airflow (2.0+), the **TaskFlow API** allows you to define tasks using python decorators (`@dag` and `@task`). This simplifies data passing and removes boilerplate code.

### D. XCom (Cross-Communication)
Tasks in Airflow run in isolated processes or even different servers. They cannot share memory. **XComs** allow tasks to pass small messages (e.g., file paths, keys) by writing the values to Airflow's metadata database and reading them in subsequent tasks.
*   *Warning:* Never pass large dataframes through XCom. It will bloat and crash the metadata database. Pass the file path instead!

### E. Variables and Connections
*   **Variables:** Global configuration settings stored in the database (e.g., paths, project names).
*   **Connections:** Secure credentials (usernames, API keys, passwords) to external systems (GCP, Slack, Postgres).

### F. The Scheduler's Logical Date (Execution Date)
A common beginner trap is **Airflow's scheduling interval logic**.
*   Airflow runs a DAG run at the **end** of its scheduling interval.
*   If your DAG is daily, and `start_date` is `2026-07-01`, and the first scheduled run interval is `2026-07-01` to `2026-07-02`, the scheduler will trigger that run on **`2026-07-02 00:00:00`**. The `logical_date` (historically `execution_date`) for this run will be `2026-07-01`.

### G. Catchup and Backfill
*   **Catchup (Boolean):** If `catchup=True` (default) and your `start_date` is 10 days in the past, when you unpause the DAG, Airflow will immediately spin up 10 historical DAG runs to "catch up" to the present.
*   **Backfill:** A command-line operation to manually force Airflow to run the DAG for historical dates.
