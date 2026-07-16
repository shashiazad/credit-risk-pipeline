import os
import time
import pandas as pd
from typing import Optional, Dict, Any
from src.utils.logger import get_logger
from src.utils.helpers import load_yaml

logger = get_logger(__name__)

class DataIngester:
    """
    Handles defensive data ingestion from raw CSV sources.
    """
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = load_yaml(config_path)
        self.raw_data_dir = os.getenv("RAW_DATA_PATH", "data/raw")
        self.raw_file_name = self.config["ingestion"]["raw_file_name"]
        self.source_path = os.path.join(self.raw_data_dir, self.raw_file_name)
        
        # Expected schema column headers (without strict types for raw ingestion)
        self.expected_columns = [
            "loan_id", "member_id", "loan_amount", "interest_rate", 
            "grade", "loan_status", "purpose", "annual_income", 
            "dti", "emp_length", "issue_date"
        ]

    def validate_file(self) -> bool:
        """
        Validates the existence and size of the raw source file.
        """
        if not os.path.exists(self.source_path):
            logger.error(f"Source file not found at: {self.source_path}")
            return False
            
        file_size = os.path.getsize(self.source_path)
        if file_size == 0:
            logger.error(f"Source file at {self.source_path} is empty (0 bytes).")
            return False
            
        logger.info(f"File validation passed. Size: {file_size / 1024:.2f} KB.")
        return True

    def validate_schema(self, df: pd.DataFrame) -> bool:
        """
        Validates that the columns in the ingested DataFrame match the expected columns.
        Supports checking for missing columns.
        """
        actual_cols = list(df.columns)
        missing_cols = [col for col in self.expected_columns if col not in actual_cols]
        
        if missing_cols:
            logger.error(f"Schema Validation Failed. Missing columns: {missing_cols}")
            return False
            
        logger.info("Schema Validation Successful. All expected columns are present.")
        return True

    def ingest_data(self) -> Optional[pd.DataFrame]:
        """
        Ingests data from raw CSV, handles exceptions, validates schema, and returns a DataFrame.
        """
        start_time = time.time()
        logger.info(f"Initiating ingestion process for: {self.source_path}")
        
        if not self.validate_file():
            logger.critical("Aborting ingestion due to file validation failure.")
            return None
            
        try:
            # We read the data. 
            # In a production context with very large datasets, we would process in chunks.
            # Here we read the full file but implement error handling for malformed rows.
            df = pd.read_csv(
                self.source_path,
                # on_bad_lines='warn' tells pandas to print a warning and skip bad lines
                # rather than crashing the execution. This represents defensive ingestion.
                on_bad_lines='warn' 
            )
            
            duration = time.time() - start_time
            logger.info(f"Read CSV successfully in {duration:.4f} seconds.")
            
        except pd.errors.EmptyDataError:
            logger.error("No data found in the CSV file (EmptyDataError).")
            return None
        except pd.errors.ParserError as e:
            logger.error(f"Failed to parse CSV file: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during ingestion: {e}")
            return None

        # Schema verification
        if not self.validate_schema(df):
            logger.critical("Aborting ingestion due to schema validation failure.")
            return None
            
        logger.info(f"Successfully ingested {len(df)} records. Memory usage: {df.memory_usage(deep=True).sum() / 1024:.2f} KB.")
        return df

if __name__ == "__main__":
    # Test script run
    ingester = DataIngester()
    df = ingester.ingest_data()
    if df is not None:
        print(f"\nIngestion successful! Loaded {len(df)} records.")
    else:
        print("\nIngestion failed.")
