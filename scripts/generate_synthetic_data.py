import os
import random
import csv
from datetime import datetime, timedelta

def generate_data(num_records=5000, output_path="data/raw/credit_risk_dataset.csv"):
    """
    Generates a realistic synthetic credit/loan risk dataset.
    Includes intentional anomalies (nulls, duplicates, outliers) to test data engineering pipelines.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Categories for columns
    grades = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'X']  # 'X' is an anomaly
    statuses = ['Fully Paid', 'Charged Off', 'Current', 'Late', 'Unknown'] # 'Unknown' is an anomaly
    purposes = ['debt_consolidation', 'credit_card', 'home_improvement', 'medical', 'major_purchase', 'car']
    
    # Base date for issue_date
    start_date = datetime(2025, 1, 1)
    
    # We will generate specific headers
    headers = [
        "loan_id", "member_id", "loan_amount", "interest_rate", 
        "grade", "loan_status", "purpose", "annual_income", 
        "dti", "emp_length", "issue_date"
    ]
    
    records = []
    
    # Keep track of generated loan_ids to insert duplicates
    loan_ids = list(range(100000, 100000 + num_records))
    
    for i in range(num_records):
        # 1. loan_id (We introduce ~1% duplicates)
        if i > 0 and random.random() < 0.01:
            loan_id = records[-1][0]
        else:
            loan_id = loan_ids[i]
            
        # 2. member_id
        member_id = 900000 + i
        
        # 3. loan_amount (0.5% nulls, 0.5% negative values)
        rand_val = random.random()
        if rand_val < 0.005:
            loan_amount = ""
        elif rand_val < 0.01:
            loan_amount = -random.randint(1000, 5000)
        else:
            loan_amount = round(random.uniform(1000.0, 40000.0), 2)
            
        # 4. interest_rate (1% nulls, 0.5% outliers > 35%)
        rand_val = random.random()
        if rand_val < 0.01:
            interest_rate = ""
        elif rand_val < 0.015:
            interest_rate = round(random.uniform(50.0, 99.9), 2) # outlier
        else:
            interest_rate = round(random.uniform(5.0, 28.0), 2)
            
        # 5. grade (1% invalid 'X')
        grade = 'X' if random.random() < 0.01 else random.choice(grades[:-1])
        
        # 6. loan_status (1% invalid 'Unknown')
        loan_status = 'Unknown' if random.random() < 0.01 else random.choice(statuses[:-1])
        
        # 7. purpose
        purpose = random.choice(purposes)
        
        # 8. annual_income (1% nulls)
        if random.random() < 0.01:
            annual_income = ""
        else:
            annual_income = round(random.uniform(20000.0, 250000.0), 2)
            
        # 9. dti (Debt-to-Income) (1% nulls, 0.5% anomalies > 100)
        rand_val = random.random()
        if rand_val < 0.01:
            dti = ""
        elif rand_val < 0.015:
            dti = round(random.uniform(101.0, 150.0), 2)
        else:
            dti = round(random.uniform(1.0, 45.0), 2)
            
        # 10. emp_length (2% nulls)
        if random.random() < 0.02:
            emp_length = ""
        else:
            emp_length = random.randint(0, 15)
            
        # 11. issue_date (1% incorrect date format MM/DD/YYYY instead of YYYY-MM-DD)
        days_offset = random.randint(0, 365)
        dt = start_date + timedelta(days=days_offset)
        if random.random() < 0.01:
            issue_date = dt.strftime("%m/%d/%Y") # anomaly format
        else:
            issue_date = dt.strftime("%Y-%m-%d")
            
        records.append([
            loan_id, member_id, loan_amount, interest_rate,
            grade, loan_status, purpose, annual_income,
            dti, emp_length, issue_date
        ])
        
    # Write to CSV
    with open(output_path, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(records)
        
    print(f"Successfully generated {num_records} synthetic credit risk records at '{output_path}'.")

if __name__ == "__main__":
    generate_data()
