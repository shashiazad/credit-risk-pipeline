import os
import json
import csv
import glob
import http.server
import socketserver
from datetime import datetime

PORT = 8085
PROJECT_ROOT = os.getcwd()

class PipelineHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Serve static files from the 'dashboard' directory relative to project root
        super().__init__(*args, directory=os.path.join(PROJECT_ROOT, "dashboard"), **kwargs)

    def do_GET(self):
        # API Route: Landing zone queue
        if self.path == "/api/landing":
            self.send_json_response(self.get_landing_files())
        # API Route: Raw staging preview
        elif self.path == "/api/staging":
            self.send_json_response(self.get_staging_data())
        # API Route: Warehouse status
        elif self.path == "/api/warehouse":
            self.send_json_response(self.get_warehouse_stats())
        # API Route: Analytics aggregations
        elif self.path == "/api/analytics":
            self.send_json_response(self.get_analytics_data())
        else:
            # Default handler serving index.html and assets
            super().do_GET()

    def send_json_response(self, data):
        """Sends JSON formatted response to client."""
        try:
            response = json.dumps(data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*") # Enable CORS for easy local access
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
        except Exception as e:
            self.send_error(500, message=f"JSON serialization error: {e}")

    def get_landing_files(self):
        """Returns details of files sitting in the landing zone."""
        landing_dir = os.path.join(PROJECT_ROOT, "data/landing")
        if not os.path.exists(landing_dir):
            return []
            
        csv_pattern = os.path.join(landing_dir, "*.csv")
        files = glob.glob(csv_pattern)
        
        file_list = []
        for f in files:
            stat = os.stat(f)
            file_list.append({
                "name": os.path.basename(f),
                "size_kb": round(stat.st_size / 1024, 2),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
        # Sort by mtime (newest first)
        return sorted(file_list, key=lambda x: x["modified"], reverse=True)

    def get_staging_data(self, limit=30):
        """Returns preview records from the raw staging table."""
        staging_file = os.path.join(PROJECT_ROOT, "data/raw/staging_raw_loans.csv")
        if not os.path.exists(staging_file):
            return {"status": "No active staging file found", "data": []}
            
        try:
            records = []
            with open(staging_file, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    if i >= limit:
                        break
                    records.append(row)
            return {"status": "Success", "data": records}
        except Exception as e:
            return {"status": "Error", "message": str(e), "data": []}

    def get_warehouse_stats(self):
        """Returns record counts for fact and dimension tables."""
        stats = {
            "fact_loans_count": 0,
            "dim_borrowers_count": 0,
            "archived_batches_count": 0
        }
        
        # Count fact loans
        fact_path = os.path.join(PROJECT_ROOT, "data/processed/fact_loans.csv")
        if os.path.exists(fact_path):
            with open(fact_path, "r") as f:
                stats["fact_loans_count"] = max(0, sum(1 for line in f) - 1) # subtract header
                
        # Count dim borrowers
        dim_path = os.path.join(PROJECT_ROOT, "data/processed/dim_borrowers.csv")
        if os.path.exists(dim_path):
            with open(dim_path, "r") as f:
                stats["dim_borrowers_count"] = max(0, sum(1 for line in f) - 1)
                
        # Count archived files
        archive_dir = os.path.join(PROJECT_ROOT, "data/archive")
        if os.path.exists(archive_dir):
            stats["archived_batches_count"] = len(glob.glob(os.path.join(archive_dir, "*.csv")))
            
        return stats

    def get_analytics_data(self):
        """Reads loan_summary and risk_metrics report files."""
        result = {
            "loan_summary": [],
            "risk_metrics": []
        }
        
        # Read loan summary
        summary_path = os.path.join(PROJECT_ROOT, "data/processed/loan_summary.csv")
        if os.path.exists(summary_path):
            try:
                with open(summary_path, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    result["loan_summary"] = [row for row in reader]
            except Exception:
                pass
                
        # Read risk metrics
        risk_path = os.path.join(PROJECT_ROOT, "data/processed/risk_metrics.csv")
        if os.path.exists(risk_path):
            try:
                with open(risk_path, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    result["risk_metrics"] = [row for row in reader]
            except Exception:
                pass
                
        return result

def start_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), PipelineHTTPRequestHandler) as httpd:
        print("="*60)
        print(f"PIPELINE MONITORING BACKEND ACTIVE")
        print(f"URL: http://localhost:{PORT}")
        print(f"Serving assets from: {os.path.join(PROJECT_ROOT, 'dashboard')}")
        print("="*60)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer shutting down.")

if __name__ == "__main__":
    start_server()
