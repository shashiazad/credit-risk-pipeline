import os
import sys
from datetime import datetime, timedelta

# Add project root to path so we can import src modules inside Airflow
PROJECT_ROOT = os.getenv("PROJECT_ROOT", "/Users/shashi/Projects/Personal/Loan_Risk_Pipeline")
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from airflow.decorators import dag, task
from src.ingestion import DataIngester

def on_failure_callback(context):
    """
    Callback function that runs when a task fails.
    Simulates sending Slack and Email alerts to operations teams.
    """
    task_instance = context.get('task_instance')
    task_id = task_instance.task_id
    dag_id = task_instance.dag_id
    logical_date = context.get('logical_date') or context.get('execution_date')
    exception = context.get('exception')
    
    print(f"\n[ALERT SYSTEM] Task '{task_id}' in DAG '{dag_id}' failed for execution date {logical_date}.")
    print(f"[ALERT SYSTEM] Exception logged: {exception}")
    print("[ALERT SYSTEM] Simulating Slack Notification sent to channel #alerts-data-ops...")
    print("[ALERT SYSTEM] Simulating Email Alert dispatched to data-engineering-oncall@company.com...\n")

# Define default arguments for the DAG
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
    "on_failure_callback": on_failure_callback,
}


@dag(
    dag_id="loan_risk_pipeline",
    default_args=default_args,
    description="Orchestrates ingestion and analysis of credit risk data.",
    schedule_interval="*/2 * * * *",  # Run every 2 minutes
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["credit_risk", "elt"],
)
def loan_risk_dag():
    """
    Main DAG definition for Loan Risk Pipeline using TaskFlow API.
    """
    
    @task()
    def ingest_raw_data() -> str:
        """
        Task 1: Run the DataIngester pipeline to fetch and validate the CSV dataset.
        Returns the output path of the ingested file.
        """
        # Set environment variables for the runtime session if not loaded
        os.environ["PROJECT_ROOT"] = PROJECT_ROOT
        os.environ["RAW_DATA_PATH"] = os.path.join(PROJECT_ROOT, "data/raw")
        
        ingester = DataIngester()
        df = ingester.ingest_data()
        
        if df is None or df.empty:
            raise ValueError("Ingestion returned empty or invalid DataFrame.")
            
        staging_path = os.path.join(PROJECT_ROOT, "data/raw/staging_raw_loans.csv")
        df.to_csv(staging_path, index=False)
        return staging_path

    @task()
    def validate_raw_data(filepath: str) -> bool:
        """
        Task 2: Run Data Quality checks using Great Expectations.
        """
        import pandas as pd
        from src.validation import DataValidator
        
        # Ensure path variables are loaded
        os.environ["PROJECT_ROOT"] = PROJECT_ROOT
        
        df = pd.read_csv(filepath)
        validator = DataValidator()
        success = validator.run_validation(df)
        return success

    @task()
    def clean_raw_data(filepath: str) -> str:
        """
        Task 3: Clean data, resolve anomalies, and save to processed data folder.
        """
        import pandas as pd
        from src.cleaning import DataCleaner
        
        # Ensure path variables are loaded
        os.environ["PROJECT_ROOT"] = PROJECT_ROOT
        
        df = pd.read_csv(filepath)
        cleaner = DataCleaner()
        cleaned_df = cleaner.clean_data(df)
        
        if cleaned_df is None or cleaned_df.empty:
            raise ValueError("Cleaning step produced an empty DataFrame.")
            
        cleaner.save_clean_data(cleaned_df)
        return cleaner.output_path

    @task()
    def validate_clean_data(filepath: str) -> bool:
        """
        Task 4: Run Data Quality checks on clean data. Must pass 100%.
        """
        import pandas as pd
        from src.validation import DataValidator
        
        # Ensure path variables are loaded
        os.environ["PROJECT_ROOT"] = PROJECT_ROOT
        
        df = pd.read_csv(filepath)
        validator = DataValidator()
        success = validator.run_validation(df)
        
        if not success:
            raise ValueError("Data quality validation failed on CLEANED staging dataset!")
            
        return success

    @task()
    def load_to_bigquery(filepath: str) -> bool:
        """
        Task 5: Load cleaned data into Google BigQuery.
        """
        import pandas as pd
        from src.loader import BigQueryLoader
        
        # Ensure path variables are loaded
        os.environ["PROJECT_ROOT"] = PROJECT_ROOT
        
        df = pd.read_csv(filepath)
        loader = BigQueryLoader()
        success = loader.load_dataframe(df, table_name="raw_loans")
        return success

    @task()
    def transform_warehouse(filepath: str) -> bool:
        """
        Task 6: Create Star Schema and deploy aggregates in BigQuery.
        """
        import pandas as pd
        from src.transformation import BigQueryTransformer
        
        # Ensure path variables are loaded
        os.environ["PROJECT_ROOT"] = PROJECT_ROOT
        
        df = pd.read_csv(filepath)
        transformer = BigQueryTransformer()
        success = transformer.deploy_warehouse(df)
        return success

    @task()
    def log_ingestion_summary(filepath: str, run_success: bool):
        """
        Task 7: Print final pipeline execution summary.
        """
        import pandas as pd
        df = pd.read_csv(filepath)
        print(f"Airflow Pipeline Execution Complete. Staging File: {filepath} ({len(df)} rows). Warehouse Deploy Success: {run_success}")

    # Define task dependencies using TaskFlow returns
    raw_file_path = ingest_raw_data()
    
    # Run raw validations (for reporting/monitoring)
    raw_validation_status = validate_raw_data(raw_file_path)
    
    # Proceed to clean the dataset
    clean_file_path = clean_raw_data(raw_file_path)
    
    # Run post-cleaning validation (must pass, else fails pipeline)
    clean_validation_status = validate_clean_data(clean_file_path)
    
    # Load cleaned data to BigQuery
    load_status = load_to_bigquery(clean_file_path)
    
    # Execute Star Schema and views
    transform_status = transform_warehouse(clean_file_path)
    
    # Final log summary
    log_ingestion_summary(clean_file_path, transform_status)

# Instantiate the DAG
loan_risk_pipeline_dag = loan_risk_dag()
