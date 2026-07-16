import os
import time
import shutil
import glob
import pandas as pd
from typing import Optional, List
from src.utils.logger import get_logger
from src.utils.helpers import load_yaml

logger = get_logger(__name__)

class DataIngester:
    """
    Handles data ingestion. Support scanning a landing zone directory for live files,
    concatenating them, and moving them to an archive directory.
    Falls back to the static raw file if the landing zone is empty.
    """
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = load_yaml(config_path)
        self.raw_data_dir = os.getenv("RAW_DATA_PATH", "data/raw")
        self.raw_file_name = self.config["ingestion"]["raw_file_name"]
        self.source_path = os.path.join(self.raw_data_dir, self.raw_file_name)
        
        # Live landing zone and archive directory paths
        self.landing_dir = os.getenv("LANDING_DATA_PATH", "data/landing")
        self.archive_dir = os.getenv("ARCHIVE_DATA_PATH", "data/archive")
        
        os.makedirs(self.landing_dir, exist_ok=True)
        os.makedirs(self.archive_dir, exist_ok=True)
        
        # Expected schema column headers
        self.expected_columns = [
            "loan_id", "member_id", "loan_amount", "interest_rate", 
            "grade", "loan_status", "purpose", "annual_income", 
            "dti", "emp_length", "issue_date"
        ]

    def validate_schema(self, df: pd.DataFrame) -> bool:
        """
        Validates that the columns in the ingested DataFrame match the expected columns.
        """
        actual_cols = list(df.columns)
        missing_cols = [col for col in self.expected_columns if col not in actual_cols]
        
        if missing_cols:
            logger.error(f"Schema Validation Failed. Missing columns: {missing_cols}")
            return False
            
        logger.info("Schema Validation Successful. All expected columns are present.")
        return True

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

    def ingest_data(self) -> Optional[pd.DataFrame]:
        """
        Scans landing zone for CSVs, concatenates them, archives the sources,
        and returns the consolidated DataFrame. Falls back to static raw path if empty.
        """
        start_time = time.time()
        
        # 1. Scan landing zone
        csv_pattern = os.path.join(self.landing_dir, "*.csv")
        landing_files = glob.glob(csv_pattern)
        
        if landing_files:
            logger.info(f"Found {len(landing_files)} files in landing zone: {self.landing_dir}")
            dfs = []
            processed_files = []
            
            for file_path in landing_files:
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    logger.warning(f"Skipping empty landing file: {file_path}")
                    continue
                try:
                    df = pd.read_csv(file_path, on_bad_lines='warn')
                    dfs.append(df)
                    processed_files.append(file_path)
                except Exception as e:
                    logger.error(f"Failed to read landing file {file_path}: {e}")
                    
            if not dfs:
                logger.error("No valid data frames could be loaded from landing files.")
                return None
                
            combined_df = pd.concat(dfs, ignore_index=True)
            logger.info(f"Successfully ingested and concatenated {len(processed_files)} landing files.")
            
            # Archive successfully processed files to prevent duplicate processing
            for file_path in processed_files:
                dest = os.path.join(self.archive_dir, os.path.basename(file_path))
                # Handle potential duplicate filenames in archive by appending timestamps
                if os.path.exists(dest):
                    base, ext = os.path.splitext(os.path.basename(file_path))
                    dest = os.path.join(self.archive_dir, f"{base}_{int(time.time())}{ext}")
                try:
                    shutil.move(file_path, dest)
                    logger.debug(f"Archived landing file: {file_path} -> {dest}")
                except Exception as e:
                    logger.error(f"Failed to archive file {file_path}: {e}")
                    
            # Validate combined schema
            if not self.validate_schema(combined_df):
                logger.critical("Aborting landing ingestion due to schema validation failure.")
                return None
                
            logger.info(f"Landing Ingestion complete. Ingested {len(combined_df)} records in {time.time() - start_time:.4f}s.")
            return combined_df
            
        else:
            # 2. Fallback to raw dataset (compatible with our static tests)
            logger.info(f"Landing zone is empty. Checking fallback raw file: {self.source_path}")
            if not self.validate_file():
                logger.warning(f"Fallback raw file validation failed at: {self.source_path}")
                return None
                
            try:
                df = pd.read_csv(self.source_path, on_bad_lines='warn')
                duration = time.time() - start_time
                logger.info(f"Read fallback CSV successfully in {duration:.4f} seconds.")
            except Exception as e:
                logger.error(f"Failed to parse fallback CSV: {e}")
                return None
                
            if not self.validate_schema(df):
                logger.critical("Aborting fallback ingestion due to schema validation failure.")
                return None
                
            logger.info(f"Fallback Ingestion complete. Ingested {len(df)} records.")
            return df

if __name__ == "__main__":
    ingester = DataIngester()
    df = ingester.ingest_data()
    if df is not None:
        print(f"\nIngestion complete. Loaded {len(df)} rows.")
    else:
        print("\nNo data ingested.")
