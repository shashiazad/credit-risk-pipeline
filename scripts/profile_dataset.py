import pandas as pd
from src.utils.logger import get_logger

logger = get_logger(__name__)

def profile_dataset(file_path="data/raw/credit_risk_dataset.csv"):
    """
    Profiles the dataset using Pandas to understand its schema,
    null distribution, unique categories, and duplicates.
    """
    logger.info(f"Starting profiling for {file_path}")
    
    # 1. Load data
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        logger.error(f"Failed to read dataset: {e}")
        return
        
    # 2. Shape
    num_rows, num_cols = df.shape
    print("\n" + "="*50)
    print("DATASET OVERVIEW")
    print("="*50)
    print(f"Total Rows: {num_rows}")
    print(f"Total Columns: {num_cols}")
    
    # 3. Data types
    print("\nCOLUMN TYPES:")
    print(df.dtypes)
    
    # 4. Missing values
    print("\nMISSING VALUES (NULLS):")
    missing = df.isnull().sum()
    missing_pct = (missing / num_rows) * 100
    missing_df = pd.DataFrame({'Missing Count': missing, 'Percentage (%)': missing_pct})
    print(missing_df[missing_df['Missing Count'] > 0])
    
    # 5. Duplicates
    print("\nDUPLICATE RECORDS:")
    total_duplicates = df.duplicated().sum()
    loan_id_duplicates = df.duplicated(subset=['loan_id']).sum()
    print(f"Total fully duplicate rows: {total_duplicates}")
    print(f"Duplicate loan_id values (Primary Key Violations): {loan_id_duplicates}")
    
    # 6. Basic Numerical Statistics
    print("\nNUMERICAL STATISTICS:")
    numerical_cols = ['loan_amount', 'interest_rate', 'annual_income', 'dti', 'emp_length']
    # Cast column to numeric forcing errors to NaN for quick profiling statistics
    temp_df = df[numerical_cols].apply(pd.to_numeric, errors='coerce')
    print(temp_df.describe())
    
    # 7. Category distributions
    print("\nCATEGORY VALUE COUNTS:")
    categorical_cols = ['grade', 'loan_status', 'purpose']
    for col in categorical_cols:
        print(f"\nDistribution of '{col}':")
        print(df[col].value_counts(dropna=False))
        
    print("\n" + "="*50)
    logger.info("Profiling complete.")

if __name__ == "__main__":
    profile_dataset()
