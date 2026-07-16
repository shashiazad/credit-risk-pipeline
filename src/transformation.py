import os
import pandas as pd
from typing import Tuple, Dict, Any
from src.utils.logger import get_logger
from src.utils.helpers import load_yaml
from src.loader import BigQueryLoader

logger = get_logger(__name__)

class BigQueryTransformer:
    """
    Handles data warehouse design, creating Star Schema tables (Fact & Dimensions)
    and generating analytics layer aggregates.
    """
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = load_yaml(config_path)
        self.loader = BigQueryLoader(config_path)
        self.processed_data_dir = os.getenv("PROCESSED_DATA_PATH", "data/processed")

    def build_star_schema(self, df_clean: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Splits the cleaned dataset into Fact and Dimension tables (Star Schema).
        - Fact Table: fact_loans (transaction records)
        - Dimension Table: dim_borrowers (borrower profiles)
        """
        logger.info("Designing Star Schema (Fact and Dimension splitting)...")
        
        # 1. Dimension Table: dim_borrowers
        # Extract borrower details, drop duplicates based on member_id
        dim_borrowers = df_clean[["member_id", "annual_income", "emp_length"]].copy()
        dim_borrowers = dim_borrowers.drop_duplicates(subset=["member_id"])
        
        # 2. Fact Table: fact_loans
        # Contains the core transactional metrics and points to dim_borrowers via foreign key member_id
        fact_cols = [
            "loan_id", "member_id", "loan_amount", "interest_rate", 
            "grade", "loan_status", "purpose", "dti", 
            "issue_date", "is_default", "loan_to_income_ratio"
        ]
        fact_loans = df_clean[fact_cols].copy()
        
        logger.info(f"Star Schema designed. fact_loans: {len(fact_loans)} rows. dim_borrowers: {len(dim_borrowers)} rows.")
        return fact_loans, dim_borrowers

    def run_local_analytics(self, fact_df: pd.DataFrame, dim_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Simulates SQL transformations locally using Pandas.
        Generates aggregates for the Analytics Layer (loan_summary & risk_metrics).
        """
        logger.info("Executing analytical aggregations (Local Simulation)...")
        
        # Join tables to simulate warehouse queries
        merged_df = pd.merge(fact_df, dim_df, on="member_id", how="inner")
        
        # Analytics View 1: loan_summary (Aggregations by Grade and Purpose)
        loan_summary = merged_df.groupby(["grade", "purpose"]).agg(
            total_loans=('loan_id', 'count'),
            total_capital_issued=('loan_amount', 'sum'),
            average_interest_rate=('interest_rate', 'mean'),
            average_dti=('dti', 'mean')
        ).reset_index()
        # Round averages
        loan_summary["average_interest_rate"] = round(loan_summary["average_interest_rate"], 2)
        loan_summary["average_dti"] = round(loan_summary["average_dti"], 2)
        
        # Analytics View 2: risk_metrics (Vintage risk indicators by Grade)
        risk_metrics = merged_df.groupby("grade").agg(
            total_applications=('loan_id', 'count'),
            total_defaults=('is_default', 'sum'),
            average_leverage=('loan_to_income_ratio', 'mean')
        ).reset_index()
        # Calculate Default Rate percentage
        risk_metrics["default_rate_pct"] = round((risk_metrics["total_defaults"] / risk_metrics["total_applications"]) * 100, 2)
        risk_metrics["average_leverage"] = round(risk_metrics["average_leverage"], 4)
        
        return {
            "loan_summary": loan_summary,
            "risk_metrics": risk_metrics
        }

    def deploy_warehouse(self, clean_df: pd.DataFrame) -> bool:
        """
        Splits clean data, loads to BigQuery (Fact/Dim), and deploys analytics views.
        """
        fact_loans, dim_borrowers = self.build_star_schema(clean_df)
        
        # 1. Load Fact & Dimension Tables
        logger.info("Deploying Star Schema tables to Warehouse Layer...")
        fact_success = self.loader.load_dataframe(fact_loans, table_name="fact_loans")
        dim_success = self.loader.load_dataframe(dim_borrowers, table_name="dim_borrowers")
        
        if not (fact_success and dim_success):
            logger.error("Failed to load Star Schema tables into BigQuery.")
            return False
            
        # 2. Deploy Views / Run Analytics
        if self.loader.dry_run_mode:
            logger.info("Dry-run active. Generating local analytical CSV reports...")
            analytics = self.run_local_analytics(fact_loans, dim_borrowers)
            
            # Save local CSV views to represent the analytics layer
            for name, df in analytics.items():
                out_path = os.path.join(self.processed_data_dir, f"{name}.csv")
                df.to_csv(out_path, index=False)
                logger.info(f"[DRY-RUN] Saved local analytics report: {out_path}")
            return True
            
        # Cloud Execution: Deploy Views in BigQuery using DDL SQL queries
        try:
            logger.info("Deploying SQL Views to BigQuery Analytics Layer...")
            client = self.loader.client
            dataset_ref = f"{self.loader.project_id}.{self.loader.dataset_name}"
            
            # SQL Query for loan_summary View
            summary_view_id = f"{dataset_ref}.loan_summary"
            client.delete_table(summary_view_id, not_found_ok=True)
            summary_sql = f"""
                CREATE OR REPLACE VIEW `{summary_view_id}` AS
                SELECT 
                    f.grade,
                    f.purpose,
                    COUNT(f.loan_id) as total_loans,
                    SUM(f.loan_amount) as total_capital_issued,
                    ROUND(AVG(f.interest_rate), 2) as average_interest_rate,
                    ROUND(AVG(f.dti), 2) as average_dti
                FROM `{dataset_ref}.fact_loans` f
                INNER JOIN `{dataset_ref}.dim_borrowers` b ON f.member_id = b.member_id
                GROUP BY grade, purpose
            """
            client.query(summary_sql).result()
            logger.info(f"Successfully created SQL View: {summary_view_id}")
            
            # SQL Query for risk_metrics View
            risk_view_id = f"{dataset_ref}.risk_metrics"
            client.delete_table(risk_view_id, not_found_ok=True)
            risk_sql = f"""
                CREATE OR REPLACE VIEW `{risk_view_id}` AS
                SELECT 
                    f.grade,
                    COUNT(f.loan_id) as total_applications,
                    SUM(f.is_default) as total_defaults,
                    ROUND(SAFE_DIVIDE(SUM(f.is_default), COUNT(f.loan_id)) * 100, 2) as default_rate_pct,
                    ROUND(AVG(f.loan_to_income_ratio), 4) as average_leverage
                FROM `{dataset_ref}.fact_loans` f
                INNER JOIN `{dataset_ref}.dim_borrowers` b ON f.member_id = b.member_id
                GROUP BY grade
            """
            client.query(risk_sql).result()
            logger.info(f"Successfully created SQL View: {risk_view_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create BigQuery SQL Views: {e}")
            return False

if __name__ == "__main__":
    # Test script transformation run
    clean_file = "data/processed/cleaned_loans.csv"
    if os.path.exists(clean_file):
        df_clean = pd.read_csv(clean_file)
        transformer = BigQueryTransformer()
        transformer.deploy_warehouse(df_clean)
    else:
        logger.error(f"Cleaned file not found at {clean_file}. Run cleaning.py first.")
