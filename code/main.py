import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "dataset"
sys.path.insert(0, str(ROOT))

from engine import FinancialEngine

OUTPUT_FILE = ROOT / "output.csv"
REQUESTS_FILE = DATASET / "requests.csv"

def main():
    print("Loading financial data...")
    engine = FinancialEngine(data_dir=str(DATASET))
    engine.load_data()
    print("Loading requests...")
    with open(REQUESTS_FILE, "r", encoding="utf-8-sig", newline="") as f:
        requests = list(csv.DictReader(f))
    print(f"Requests loaded: {len(requests)}")
    results = [engine.evaluate_request(req) for req in requests]
    fields = ["request_id","amount_safe_to_pay","affordability_status","recommended_payment_method","payment_plan","earliest_date_for_full_payment","spending_changes_needed","decision_explanation"]
    print("Writing output.csv...")
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
    print(f"Output created: {OUTPUT_FILE}")
    print(f"Rows written: {len(results)}")

if __name__ == "__main__":
    main()
