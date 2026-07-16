import os
import time
import subprocess
import pandas as pd
from datetime import datetime
from src.ingestion import DataIngester
from src.validation import DataValidator
from src.cleaning import DataCleaner
from src.transformation import BigQueryTransformer
from src.utils.logger import get_logger

logger = get_logger("live_pipeline_orchestrator")

def run_pipeline_cycle():
    """
    Executes a single end-to-end processing cycle:
    Ingests files from landing -> Validates -> Cleans -> Deploys Star Schema & Analytics reports.
    """
    logger.info("="*60)
    logger.info(f"PROCESSING BATCH CYCLE START: {datetime.now().strftime('%T')}")
    logger.info("="*60)
    
    # 1. Ingestion Stage
    ingester = DataIngester()
    raw_df = ingester.ingest_data()
    
    if raw_df is None or raw_df.empty:
        logger.info("No new files found in data/landing. Skipping cycle.")
        return
        
    logger.info(f"Ingested {len(raw_df)} raw records from landing zone.")
    
    # 2. Raw Validation Stage (logs anomalies but continues)
    validator = DataValidator()
    validator.run_validation(raw_df)
    
    # 3. Cleaning Stage
    cleaner = DataCleaner()
    clean_df = cleaner.clean_data(raw_df)
    
    if clean_df is None or clean_df.empty:
        logger.error("Cleaning step failed to produce records. Aborting cycle.")
        return
        
    cleaner.save_clean_data(clean_df)
    
    # 4. Warehouse & Transform Stage (Fact/Dim Splitting and local reports updating)
    transformer = BigQueryTransformer()
    transformer.deploy_warehouse(clean_df, write_disposition="WRITE_APPEND")
    
    logger.info("="*60)
    logger.info(f"PROCESSING BATCH CYCLE COMPLETE: {datetime.now().strftime('%T')}")
    logger.info("="*60)

def main():
    """
    Simulates a live data processing environment.
    1. Launches scripts/stream_simulation.py as a background process.
    2. Runs the pipeline processing cycle in a loop.
    """
    # Clean up directories before starting to clear old batches
    for folder in ["data/landing", "data/archive", "data/processed"]:
        os.makedirs(folder, exist_ok=True)
        # Clear files inside
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            if os.path.isfile(file_path):
                os.remove(file_path)
                
    # 1. Launch simulator as background process (writes new files every 10 seconds)
    logger.info("Launching Live Data Simulator in the background...")
    # PYTHONPATH=. is passed to the sub-process environment
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    
    # Start the simulator sub-process
    simulator_proc = subprocess.Popen(
        ["venv/bin/python3", "scripts/stream_simulation.py"],
        env=env
    )
    
    time.sleep(5)  # Wait for first batch to generate
    
    try:
        # Run 3 micro-batch cycles for demo purposes, then exit
        for run_id in range(1, 4):
            run_pipeline_cycle()
            logger.info(f"Sleeping for 20 seconds before starting batch cycle #{run_id + 1}...")
            time.sleep(20)
            
    except KeyboardInterrupt:
        logger.info("Orchestrator interrupted by user.")
    finally:
        # Terminate background simulator
        logger.info("Shutting down background simulator...")
        simulator_proc.terminate()
        simulator_proc.wait()
        logger.info("Orchestrator shutdown complete.")

if __name__ == "__main__":
    main()
