import os
import pandas as pd
import numpy as np
from typing import Optional
from src.utils.logger import get_logger
from src.utils.helpers import load_yaml
from src.ingestion import DataIngester
from src.validation import DataValidator

logger = get_logger(__name__)

class DataCleaner:
    """
    Cleans raw credit risk data, standardizes formats, handles nulls/duplicates,
    and performs feature engineering.
    """
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = load_yaml(config_path)
        self.processed_data_dir = os.getenv("PROCESSED_DATA_PATH", "data/processed")
        os.makedirs(self.processed_data_dir, exist_ok=True)
        self.output_path = os.path.join(self.processed_data_dir, "cleaned_loans.csv")

    def map_interest_to_grade(self, rate: float) -> str:
        """
        Maps an interest rate back to a credit grade.
        Used to fix categorical anomalies (Grade 'X') where the rate is known.
        """
        if pd.isna(rate):
            return "C"  # Default fallback grade
        if rate < 8.0:
            return "A"
        elif rate < 12.0:
            return "B"
        elif rate < 16.0:
            return "C"
        elif rate < 20.0:
            return "D"
        elif rate < 24.0:
            # Catch usurious rates and place in lower grades
            return "E"
        elif rate < 28.0:
            return "F"
        else:
            return "G"

    def clean_data(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Runs the full cleaning pipeline on the input DataFrame.
        """
        if df is None or df.empty:
            logger.error("Empty or null DataFrame passed to cleaner.")
            return None
            
        logger.info(f"Starting data cleaning process on {len(df)} raw records.")
        
        # Make a copy to avoid SettingWithCopyWarning
        df_clean = df.copy()

        # 1. Handle critical column nulls (Drop rows missing primary key or loan amount)
        initial_count = len(df_clean)
        df_clean = df_clean.dropna(subset=["loan_id", "loan_amount"])
        dropped_null_critical = initial_count - len(df_clean)
        if dropped_null_critical > 0:
            logger.info(f"Dropped {dropped_null_critical} rows with null loan_id or loan_amount.")

        # 2. Handle duplicates based on Primary Key (loan_id)
        before_dedup = len(df_clean)
        df_clean = df_clean.drop_duplicates(subset=["loan_id"], keep="first")
        dropped_duplicates = before_dedup - len(df_clean)
        if dropped_duplicates > 0:
            logger.info(f"Deduplicated {dropped_duplicates} duplicate primary key records.")

        # 3. Clean logical boundary anomalies
        # A. Remove negative loan amounts
        before_neg = len(df_clean)
        df_clean = df_clean[df_clean["loan_amount"] > 0]
        dropped_neg = before_neg - len(df_clean)
        if dropped_neg > 0:
            logger.info(f"Dropped {dropped_neg} records with negative loan amounts.")

        # B. Clean/Cap extreme interest rate values (Cap anything > 35% down to 35% or drop? We drop extreme rate anomalies)
        before_rate = len(df_clean)
        df_clean = df_clean[(df_clean["interest_rate"].isna()) | (df_clean["interest_rate"] <= 35.0)]
        dropped_rate = before_rate - len(df_clean)
        if dropped_rate > 0:
            logger.info(f"Dropped {dropped_rate} records with extreme/invalid interest rates.")

        # C. Remove rows where loan_status is 'Unknown'
        before_status = len(df_clean)
        df_clean = df_clean[df_clean["loan_status"] != "Unknown"]
        dropped_status = before_status - len(df_clean)
        if dropped_status > 0:
            logger.info(f"Dropped {dropped_status} records with 'Unknown' status.")

        # 4. Resolve categorical anomalies (Grade 'X')
        # If Grade is 'X', infer Grade based on interest rate
        def resolve_grade(row):
            if row["grade"] == "X":
                return self.map_interest_to_grade(row["interest_rate"])
            return row["grade"]
            
        df_clean["grade"] = df_clean.apply(resolve_grade, axis=1)

        # 5. Impute remaining missing values
        # A. Impute interest_rate: Calculate median rate per Grade (excluding any null rates)
        # We calculate the median of interest rates for each grade
        grade_medians = df_clean.groupby("grade")["interest_rate"].median().to_dict()
        grade_medians = {k: v for k, v in grade_medians.items() if not pd.isna(v)}
        
        # Fill null interest rates based on the median rate of their respective grade
        def fill_rate(row):
            if pd.isna(row["interest_rate"]):
                return grade_medians.get(row["grade"], 12.0)
            return row["interest_rate"]
            
        df_clean["interest_rate"] = df_clean.apply(fill_rate, axis=1)

        # B. Impute annual_income with median income
        median_income = df_clean["annual_income"].median()
        df_clean["annual_income"] = df_clean["annual_income"].fillna(median_income)

        # C. Impute dti: Cap DTIs > 100% to overall median, and fill nulls with median
        median_dti = df_clean["dti"].median()
        df_clean["dti"] = df_clean["dti"].fillna(median_dti)
        df_clean.loc[df_clean["dti"] > 100.0, "dti"] = median_dti

        # D. Impute emp_length with 0 (assuming no employment means 0 years)
        df_clean["emp_length"] = df_clean["emp_length"].fillna(0).astype(int)

        # 6. Standardize date formats (issue_date)
        # Parse mixed formats and convert to YYYY-MM-DD
        try:
            df_clean["issue_date"] = pd.to_datetime(df_clean["issue_date"], errors="coerce")
            # Drop rows where dates were completely unparseable
            before_date_drop = len(df_clean)
            df_clean = df_clean.dropna(subset=["issue_date"])
            dropped_dates = before_date_drop - len(df_clean)
            if dropped_dates > 0:
                logger.info(f"Dropped {dropped_dates} rows due to unparseable issue_date formats.")
                
            # Standardize back to string ISO date YYYY-MM-DD
            df_clean["issue_date"] = df_clean["issue_date"].dt.strftime("%Y-%m-%d")
        except Exception as e:
            logger.error(f"Error occurred during date parsing: {e}")

        # 7. Feature Engineering
        # A. is_default (1 if Late or Charged Off, else 0)
        df_clean["is_default"] = df_clean["loan_status"].apply(
            lambda status: 1 if status in ["Charged Off", "Late"] else 0
        )

        # B. loan_to_income_ratio (leverage ratio)
        df_clean["loan_to_income_ratio"] = round(df_clean["loan_amount"] / df_clean["annual_income"], 4)

        # Final logs
        final_count = len(df_clean)
        dropped_total = initial_count - final_count
        logger.info(f"Cleaning complete. Ingested: {initial_count}, Exported: {final_count}, Rejected: {dropped_total} records.")
        
        return df_clean

    def save_clean_data(self, df: pd.DataFrame) -> bool:
        """
        Writes the cleaned DataFrame to the processed output path.
        """
        try:
            df.to_csv(self.output_path, index=False)
            logger.info(f"Successfully saved clean dataset to: {self.output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to write clean dataset to disk: {e}")
            return False

if __name__ == "__main__":
    # Test cleaning pipeline execution
    ingester = DataIngester()
    raw_df = ingester.ingest_data()
    
    if raw_df is not None:
        cleaner = DataCleaner()
        cleaned_df = cleaner.clean_data(raw_df)
        
        if cleaned_df is not None:
            cleaner.save_clean_data(cleaned_df)
            
            # Run validator again to prove that cleaned data passes 100% of data quality checks!
            print("\n" + "="*50)
            print("RUNNING POST-CLEANING VALIDATIONS")
            print("="*50)
            validator = DataValidator()
            # Clean data should pass 100% of rules
            validator.run_validation(cleaned_df)
