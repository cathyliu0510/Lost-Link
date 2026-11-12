import argparse

import uvicorn

parser = argparse.ArgumentParser(description="Open Lost Link's isolated local dashboard")
parser.add_argument("--port", type=int, default=8765)
args = parser.parse_args()
print(f"Lost Link local dashboard: http://127.0.0.1:{args.port}", flush=True)
print("Synthetic data only; fresh temporary service/database. Press Ctrl+C to stop.", flush=True)
uvicorn.run("dashboard.app:app", host="127.0.0.1", port=args.port, log_level="warning")
