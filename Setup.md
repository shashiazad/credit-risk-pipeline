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

## 5. Dockerized Execution (Airflow + Postgres)

We use Docker Compose to spin up a fully integrated Airflow orchestrator (LocalExecutor) backed by a PostgreSQL metadata database.

```bash
# 1. Build the local Airflow image and initialize Postgres
docker-compose up airflow-init

# 2. Spin up the scheduler, webserver, and database in the background
docker-compose up -d

# 3. Open your browser and navigate to the Airflow UI:
# URL: http://localhost:8080
# Username: admin
# Password: admin

# 4. To stop the containers when finished:
docker-compose down
```
When Airflow is active, toggle the `loan_risk_pipeline` DAG to "Active" and click "Trigger DAG" to execute the pipeline!
