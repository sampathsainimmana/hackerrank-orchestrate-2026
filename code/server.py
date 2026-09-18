"""Local UI/API server using the same FinancialEngine as the CSV pipeline."""
import csv, json, sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "dataset"
sys.path.insert(0, str(ROOT))
from engine import FinancialEngine

ENGINE = FinancialEngine(data_dir=str(DATASET))
ENGINE.load_data()
with (DATASET / "requests.csv").open(encoding="utf-8-sig", newline="") as f:
    REQUESTS = list(csv.DictReader(f))

class App(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/requests":
            body = json.dumps([{"request_id": r["request_id"]} for r in REQUESTS]).encode()
            self.send_response(200); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/decision/"):
            request_id = self.path.rsplit("/", 1)[-1]
            found = next((r for r in REQUESTS if r["request_id"] == request_id), None)
            if not found: self.send_error(404, "Unknown request ID"); return
            body = json.dumps(ENGINE.evaluate_request(found)).encode()
            self.send_response(200); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body); return
        if self.path in {"/", "/index.html"}:
            body = (ROOT / "frontend" / "index.html").read_bytes()
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body); return
        self.send_error(404)

if __name__ == "__main__":
    print("Buy or Wait is running at http://localhost:8000")
    ThreadingHTTPServer(("127.0.0.1", 8000), App).serve_forever()
