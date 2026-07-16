import os
import pandas as pd
import great_expectations as gx
from src.utils.logger import get_logger
from src.utils.helpers import load_yaml

logger = get_logger(__name__)

class DataValidator:
    """
    Executes Data Quality validations on datasets using Great Expectations (GX) 1.x.
    """
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = load_yaml(config_path)
        self.raw_data_dir = os.getenv("RAW_DATA_PATH", "data/raw")
        self.raw_file_name = self.config["ingestion"]["raw_file_name"]
        self.source_path = os.path.join(self.raw_data_dir, self.raw_file_name)
        
        # Load File Data Context to enable Data Docs generation
        self.context = gx.get_context(mode="file")
        self.datasource_name = "loan_pipeline_datasource"
        self.suite_name = "credit_risk_expectations"
        self.asset_name = "raw_loans_asset"
        
        # Configure/retrieve datasource
        try:
            self.datasource = self.context.data_sources.add_pandas(name=self.datasource_name)
        except Exception:
            self.datasource = self.context.data_sources.get(self.datasource_name)

    def run_validation(self, df: pd.DataFrame) -> bool:
        """
        Sets up expectations, validates the DataFrame, logs summary details, and builds Data Docs.
        Returns True if validation passes, False otherwise.
        """
        logger.info("Setting up Great Expectations validation suite...")
        
        # 1. Clean up existing asset to avoid persistent name conflict in FileContext
        try:
            self.datasource.delete_asset(self.asset_name)
        except Exception:
            pass

        # 2. Add/Read DataFrame as Asset to get a Batch
        batch = self.datasource.read_dataframe(
            df,
            asset_name=self.asset_name
        )

        # 3. Create or retrieve the expectation suite
        try:
            suite = self.context.suites.get(name=self.suite_name)
        except Exception:
            suite = self.context.suites.add(gx.ExpectationSuite(name=self.suite_name))

        # 4. Get Validator
        validator = self.context.get_validator(
            batch=batch,
            expectation_suite=suite
        )

        # 5. Define Data Quality Expectations
        logger.info("Applying Data Quality Expectations...")
        
        # A. Uniqueness of Primary Key
        validator.expect_column_values_to_be_unique(column="loan_id")
        
        # B. Completeness of Loan Amount
        validator.expect_column_values_to_not_be_null(column="loan_amount")
        
        # C. Valid range for interest rates (5% to 35%)
        validator.expect_column_values_to_be_between(column="interest_rate", min_value=5.0, max_value=35.0)
        
        # D. Validate category values for loan_status
        allowed_statuses = ["Fully Paid", "Charged Off", "Current", "Late"]
        validator.expect_column_values_to_be_in_set(column="loan_status", value_set=allowed_statuses)
        
        # E. Validate DTI range
        validator.expect_column_values_to_be_between(column="dti", min_value=0.0, max_value=100.0)
        
        # F. Date format matching YYYY-MM-DD
        validator.expect_column_values_to_match_strftime_format(column="issue_date", strftime_format="%Y-%m-%d")

        # 6. Save/update suite configuration
        self.context.suites.add_or_update(validator.expectation_suite)

        # 7. Run validation
        logger.info("Executing validation checks...")
        validation_results = validator.validate()
        
        # 8. Build Data Docs
        logger.info("Compiling validation results into Data Docs...")
        self.context.build_data_docs()
        
        # Print summary report details to console
        total_evals = len(validation_results.results)
        successful_evals = sum(1 for r in validation_results.results if r.success)
        failed_evals = total_evals - successful_evals
        
        logger.info("="*50)
        logger.info("DATA QUALITY VALIDATION SUMMARY")
        logger.info("="*50)
        logger.info(f"Overall Success: {validation_results.success}")
        logger.info(f"Total Rules Checked: {total_evals}")
        logger.info(f"Rules Passed: {successful_evals}")
        logger.info(f"Rules Failed: {failed_evals}")
        logger.info("="*50)
        
        # Detailed failure logging
        if not validation_results.success:
            logger.warning("Data quality rules that failed:")
            for r in validation_results.results:
                if not r.success:
                    col = r.expectation_config.kwargs.get("column", "dataset")
                    rule = r.expectation_config.type
                    anomaly_count = r.result.get("unexpected_count", "N/A")
                    anomaly_pct = r.result.get("unexpected_percent", 0.0)
                    logger.warning(f" - Column '{col}' failed check '{rule}'. Bad values count: {anomaly_count} ({anomaly_pct:.2f}%)")
                    
        return validation_results.success

if __name__ == "__main__":
    from src.ingestion import DataIngester
    
    # 1. Ingest raw CSV data
    ingester = DataIngester()
    raw_df = ingester.ingest_data()
    
    if raw_df is not None:
        # 2. Run validations
        validator = DataValidator()
        validator.run_validation(raw_df)
    else:
        logger.error("Failed to run validator because ingestion failed.")
