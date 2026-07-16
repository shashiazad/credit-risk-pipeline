# Local Setup & Execution Guide

Follow these steps to run the pipeline locally, execute tests, and configure Docker containers.

---

## 1. Local Python Environment Setup

We recommend using Python 3.9+ to match the Airflow image constraints.

```bash
# 1. Clone the repository and navigate to root
cd Loan_Risk_Pipeline

# 2. Initialize the isolated Python virtual environment
python3 -m venv venv

# 3. Activate the environment
source venv/bin/activate

# 4. Upgrade pip and install pinned package requirements
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 2. Setting Up Variables

Copy the environment variable template:
```bash
cp .env.example .env
```
Open the `.env` file and update your GCP Project ID or configuration paths as needed.

---

## 3. Running Pytest Suite

Ensure the codebase is functioning correctly by running the unit tests:
```bash
# Run the entire automated test suite (14 checks: ingestion, validation, cleaning, transformation, loader)
pytest
```

---

## 4. Running the Pipeline Locally

To run the pipeline components step-by-step outside of Airflow, execute:

```bash
# 1. Generate the raw credit dataset (if missing)
python scripts/generate_synthetic_data.py

# 2. Profile the raw dataset (flags nulls, outliers, and duplicates)
PYTHONPATH=. python scripts/profile_dataset.py

# 3. Run Ingestion, Validation, Cleaning, and Local Analytics Warehouse Deploy
PYTHONPATH=. python src/cleaning.py
PYTHONPATH=. python src/transformation.py
```

---

## 5. Running the Live Continuous Simulation

We have created a live orchestrator script that generates timestamped files in the landing zone and processes them sequentially in a continuous loop:

```bash
# Run the live simulation script (executes 3 cycles of live streaming and exits)
PYTHONPATH=. python scripts/run_live_pipeline.py
```
During the run, check the `data/landing/` directory to watch new batch files appear, and check `data/archive/` to see processed files move automatically!

---

## 6. Dockerized Execution (One-Command Full Deployment)

We have containerized all services so they run together. The `data-generator` runs as a background daemon container, continuously outputting live CSVs. The Airflow scheduler triggers the ingestion pipeline automatically every 2 minutes.

To build and launch the entire platform in a single command, run:

```bash
# 1. Initialize metadata database schemas, create admin profile, and spin up all containers (webserver, scheduler, database, and generator) in the background
docker-compose up --build -d
```

### Checking Active Services:
You can check which containers are running with:
```bash
docker-compose ps
```
You will see 4 active services:
*   `postgres`: Metadata database.
*   `airflow-webserver`: The UI console at [http://localhost:8080](http://localhost:8080). (Credentials: **admin / admin**)
*   `airflow-scheduler`: Auto-triggers our `loan_risk_pipeline` DAG every 2 minutes.
*   `data-generator`: Simulates real-time application records landing in `./data/landing/` in the host workspace.

### Monitoring In Action:
1. Log into [http://localhost:8080](http://localhost:8080).
2. Toggle the `loan_risk_pipeline` DAG to **Active** (Unpaused).
3. Airflow will immediately schedule the first execution and continue triggering runs every 2 minutes as long as the scheduler runs!
4. Watch files land in `data/landing/` and move to `data/archive/` automatically!

### Shutdown:
To stop and clean up the database container, volumes, and application daemons, run:
```bash
docker-compose down
```

---

## 7. Pipeline Monitoring Web Dashboard

We built a custom, glassmorphic pipeline monitoring console that reads local database and staging metrics directly and renders charts in real time.

### To start the dashboard server:
```bash
# Start the zero-dependency Python API server
python3 dashboard/server.py
```

### To view the dashboard:
1. Open your browser and navigate to: [http://localhost:8085](http://localhost:8085).
2. The UI will display:
   * **Landing Queue**: lists incoming raw CSV files in real time.
   * **Staging Inspector**: shows a preview of raw applications ingested.
   * **Risk Analytics Room**: renders live charts showing vintage defaults (%) and capital distribution per rating grade.
3. Toggle "Live Refresh (3s)" to watch new data update automatically as Airflow runs in the background!


