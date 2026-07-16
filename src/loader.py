import os
import pandas as pd
from typing import Optional
from google.cloud import bigquery
from google.oauth2 import service_account
from src.utils.logger import get_logger
from src.utils.helpers import load_yaml

logger = get_logger(__name__)

class BigQueryLoader:
    """
    Handles loading cleaned datasets into Google BigQuery tables.
    Supports GCP Authentication and falls back to a descriptive DRY-RUN mode
    if credentials are not configured locally.
    """
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = load_yaml(config_path)
        self.project_id = os.getenv("GCP_PROJECT_ID", "your-gcp-project-id")
        self.dataset_name = os.getenv("GCP_DATASET_NAME", "loan_risk_dw")
        self.credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        self.client = None
        self.dry_run_mode = True
        
        # Authenticate if credentials file exists
        if self.credentials_path and os.path.exists(self.credentials_path):
            try:
                # Initialize the BigQuery client using explicit service account json key
                self.client = bigquery.Client.from_service_account_json(self.credentials_path)
                self.dry_run_mode = False
                logger.info(f"Successfully authenticated BigQuery Client for project: {self.project_id}")
            except Exception as e:
                logger.error(f"GCP Authentication failed: {e}. Loader falling back to DRY-RUN mode.")
        else:
            logger.warning(
                f"Google application credentials not found at: {self.credentials_path}. "
                "BigQueryLoader initialized in DRY-RUN mode (local logging only)."
            )

    def create_dataset_if_not_exists(self) -> bool:
        """
        Creates the BigQuery dataset if it does not already exist.
        """
        dataset_id = f"{self.project_id}.{self.dataset_name}"
        
        if self.dry_run_mode:
            logger.info(f"[DRY-RUN] Would create dataset if not exists: {dataset_id}")
            return True
            
        try:
            # Check if dataset exists
            self.client.get_dataset(dataset_id)
            logger.info(f"Dataset '{dataset_id}' already exists.")
            return True
        except Exception:
            # If get_dataset throws exception, it means the dataset does not exist
            logger.info(f"Dataset '{dataset_id}' not found. Attempting to create dataset...")
            try:
                dataset = bigquery.Dataset(dataset_id)
                dataset.location = "US"  # Standard location
                self.client.create_dataset(dataset, timeout=30)
                logger.info(f"Successfully created dataset: {dataset_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to create BigQuery dataset '{dataset_id}': {e}")
                return False

    def load_dataframe(self, df: pd.DataFrame, table_name: str = "raw_loans") -> bool:
        """
        Loads a Pandas DataFrame into BigQuery table with partitioning and clustering.
        """
        if df is None or df.empty:
            logger.error("Empty or null DataFrame passed to loader.")
            return False
            
        table_id = f"{self.project_id}.{self.dataset_name}.{table_name}"
        
        if not self.create_dataset_if_not_exists():
            logger.critical("Aborting database load due to dataset validation failure.")
            return False
            
        if self.dry_run_mode:
            logger.info(f"[DRY-RUN] Table ID Target: {table_id}")
            logger.info(f"[DRY-RUN] Row Count: {len(df)} rows.")
            logger.info("[DRY-RUN] Partitioning configuration: TimePartitioning(field='issue_date', type='DAY')")
            logger.info("[DRY-RUN] Clustering configuration: Clustering(fields=['grade', 'purpose'])")
            logger.info("[DRY-RUN] Write Disposition: WRITE_TRUNCATE (Overwrites existing data)")
            logger.info("[DRY-RUN] Load execution simulation successful.")
            return True
            
        try:
            # Configure the load job parameters
            job_config = bigquery.LoadJobConfig(
                # WRITE_TRUNCATE replaces the table contents if it exists.
                # Alternative is WRITE_APPEND (inserts new rows) or WRITE_EMPTY (fails if data exists).
                write_disposition="WRITE_TRUNCATE",
                
                # Setup Time Partitioning by our standardized issue_date column (DATE/TIMESTAMP)
                time_partitioning=bigquery.TimePartitioning(
                    type_=bigquery.TimePartitioningType.DAY,
                    field="issue_date"
                ),
                
                # Setup Clustering to speed up filter searches by grade and loan purpose
                clustering_fields=["grade", "purpose"]
            )
            
            logger.info(f"Starting BigQuery load job for table: {table_id}")
            
            # Start the load job from dataframe
            load_job = self.client.load_table_from_dataframe(
                df,
                table_id,
                job_config=job_config
            )
            
            # Wait for the load job to complete (blocking call)
            load_job.result()
            
            destination_table = self.client.get_table(table_id)
            logger.info(
                f"Successfully loaded {destination_table.num_rows} rows into target table '{table_id}'."
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to load data to BigQuery table {table_id}: {e}")
            return False

if __name__ == "__main__":
    # Test script load run
    from src.cleaning import DataCleaner
    
    cleaner = DataCleaner()
    # Read locally cleaned dataset if exists
    if os.path.exists(cleaner.output_path):
        clean_df = pd.read_csv(cleaner.output_path)
        loader = BigQueryLoader()
        loader.load_dataframe(clean_df)
    else:
        logger.error(f"No cleaned dataset found at {cleaner.output_path}. Run cleaning.py first.")
