import os
import time
import random
import csv
from datetime import datetime, timedelta

def generate_live_records(num_records=5) -> list:
    """
    Generates a small batch of synthetic credit risk records,
    including occasional data quality anomalies.
    """
    grades = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'X']
    statuses = ['Fully Paid', 'Charged Off', 'Current', 'Late', 'Unknown']
    purposes = ['debt_consolidation', 'credit_card', 'home_improvement', 'medical', 'major_purchase', 'car']
    
    records = []
    current_time = datetime.now()
    
    for _ in range(num_records):
        # loan_id (random integer key)
        loan_id = random.randint(300000, 999999)
        member_id = random.randint(800000, 899999)
        
        # loan_amount (0.5% negative anomaly)
        if random.random() < 0.005:
            loan_amount = -random.randint(1000, 5000)
        else:
            loan_amount = round(random.uniform(2000.0, 35000.0), 2)
            
        # interest_rate (1% nulls)
        if random.random() < 0.01:
            interest_rate = ""
        else:
            interest_rate = round(random.uniform(5.5, 26.5), 2)
            
        # grade (1% invalid 'X')
        grade = 'X' if random.random() < 0.01 else random.choice(grades[:-1])
        
        # loan_status
        loan_status = 'Unknown' if random.random() < 0.01 else random.choice(statuses[:-1])
        purpose = random.choice(purposes)
        
        # annual_income
        annual_income = round(random.uniform(25000.0, 180000.0), 2)
        
        # dti
        dti = round(random.uniform(1.0, 42.0), 2)
        emp_length = random.randint(0, 12)
        
        # issue_date
        issue_date = current_time.strftime("%Y-%m-%d")
        
        records.append([
            loan_id, member_id, loan_amount, interest_rate,
            grade, loan_status, purpose, annual_income,
            dti, emp_length, issue_date
        ])
        
    return records

def run_simulation(interval_seconds=30, output_dir="data/landing"):
    """
    Main loop writing timestamped batch CSV files to data/landing directory.
    """
    os.makedirs(output_dir, exist_ok=True)
    headers = [
        "loan_id", "member_id", "loan_amount", "interest_rate", 
        "grade", "loan_status", "purpose", "annual_income", 
        "dti", "emp_length", "issue_date"
    ]
    
    print("="*60)
    print(f"LIVE DATA SIMULATOR STARTED")
    print(f"Writing timestamped CSV files to '{output_dir}' every {interval_seconds} seconds.")
    print("Press Ctrl+C to terminate.")
    print("="*60)
    
    batch_counter = 1
    try:
        while True:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"loans_{timestamp}.csv"
            file_path = os.path.join(output_dir, file_name)
            
            # Generate 3 to 8 random applications
            num_rows = random.randint(3, 8)
            records = generate_live_records(num_rows)
            
            with open(file_path, mode="w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(headers)
                writer.writerows(records)
                
            print(f"[{datetime.now().strftime('%T')}] Batch #{batch_counter} generated: {num_rows} records -> {file_name}")
            batch_counter += 1
            
            time.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        print("\nSimulator stopped by user.")

if __name__ == "__main__":
    # Runs the generator every 10 seconds by default for high responsiveness during tests
    run_simulation(interval_seconds=10)
