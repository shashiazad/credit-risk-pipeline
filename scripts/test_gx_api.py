import pandas as pd
import great_expectations as gx

# Create a small dummy DataFrame
data = {
    "loan_id": [1, 2, 2],
    "loan_amount": [10000.0, 15000.0, 20000.0],
    "interest_rate": [12.5, 14.2, 8.5],
    "loan_status": ["Fully Paid", "Current", "Late"],
    "dti": [12.5, 22.0, 45.0],
    "issue_date": ["2025-01-01", "2025-02-01", "2025-03-01"]
}
df = pd.DataFrame(data)

# Init Context in File Mode
context = gx.get_context(mode="file")
print("Context initialized.")

# Add Pandas Datasource
datasource_name = "my_pandas_datasource"
try:
    datasource = context.data_sources.add_pandas(name=datasource_name)
except Exception:
    datasource = context.data_sources.get(datasource_name)
print("Datasource configured.")

# Clean up existing asset to avoid conflicts
asset_name = "loan_data_asset"
try:
    datasource.delete_asset(asset_name)
    print(f"Cleaned up existing asset: {asset_name}")
except Exception:
    pass

# Read DataFrame to get Batch
batch = datasource.read_dataframe(
    df, 
    asset_name=asset_name
)
print("Batch created.")

# Create/Get Expectation Suite
suite_name = "my_suite"
try:
    suite = context.suites.get(name=suite_name)
    print("Expectation Suite retrieved.")
except Exception:
    suite = context.suites.add(gx.ExpectationSuite(name=suite_name))
    print("Expectation Suite created.")

# Get Validator
validator = context.get_validator(
    batch=batch,
    expectation_suite=suite
)
print("Validator created.")

# Define expectations on the validator
validator.expect_column_values_to_be_unique("loan_id")
validator.expect_column_values_to_not_be_null("loan_amount")
validator.expect_column_values_to_be_between("interest_rate", min_value=5.0, max_value=35.0)

# Save suite using add_or_update
context.suites.add_or_update(validator.expectation_suite)
print("Suite saved/updated.")

# Run validation directly on validator
results = validator.validate()
print("Validation complete. Success:", results.success)

# Build Data Docs
context.build_data_docs()
print("Data docs built successfully.")
