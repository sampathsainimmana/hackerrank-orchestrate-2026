"""Submission contract checks. Run: python code/validate.py"""
import csv
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
OUT,REQ=ROOT/"output.csv",ROOT/"dataset"/"requests.csv"
FIELDS=["request_id","amount_safe_to_pay","affordability_status","recommended_payment_method","payment_plan","earliest_date_for_full_payment","spending_changes_needed","decision_explanation"]
STATUSES={"affordable_now","affordable_with_plan","affordable_later","not_affordable"}
METHODS={"full_payment","partial_payment","installments","wait","not_recommended"}
def main():
    errors=[]
    with OUT.open(encoding="utf-8",newline="") as f:
        reader=csv.DictReader(f); output=list(reader); header=reader.fieldnames
    with REQ.open(encoding="utf-8",newline="") as f: requests={r["request_id"]:r for r in csv.DictReader(f)}
    if header!=FIELDS: errors.append("output columns are not exact")
    ids=[r["request_id"] for r in output]
    if len(ids)!=len(requests) or set(ids)!=set(requests): errors.append("request coverage mismatch")
    for r in output:
        if r["affordability_status"] not in STATUSES: errors.append(f'{r["request_id"]}: invalid status')
        if r["recommended_payment_method"] not in METHODS: errors.append(f'{r["request_id"]}: invalid payment method')
        try: float(r["amount_safe_to_pay"])
        except ValueError: errors.append(f'{r["request_id"]}: invalid amount')
        if r["earliest_date_for_full_payment"]:
            try: datetime.strptime(r["earliest_date_for_full_payment"],"%Y-%m-%d")
            except ValueError: errors.append(f'{r["request_id"]}: invalid date')
    for e in errors: print("ERROR:",e)
    if errors: return 1
    print(f"Validation passed for {len(output)} requests."); return 0
if __name__=="__main__": raise SystemExit(main())
