"""
One-time local setup for the demo.

1. Writes secrets.json with fresh random tokens for three agents and one human:
     finder-agent  – personal agent of the person who picked up an item
     owner-agent   – personal agent of the person who lost an item
     campus-board  – stands in for "other users" so the search pool is not empty
     finder-human  – the finder's own operator session (acts_for finder-agent)
2. Writes .env.agents with ONE token per agent (each agent process only
   loads its own) and the human token separately.
3. Resets lostlink.db and seeds the 20 synthetic found reports
   (10 true + 10 distractors) as campus-board, through the real HTTP API.

Usage (server must be running):  python scripts/setup_demo.py --seed
          (before starting server): python scripts/setup_demo.py
"""
import argparse
import json
import os
import secrets
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get("LOSTLINK_URL", "http://127.0.0.1:8000")


def make_secrets():
    """Create tokens and write secrets.json (server) + .env.agents (clients)."""
    tok = {name: secrets.token_urlsafe(18) for name in
           ("finder-agent", "owner-agent", "campus-board", "finder-human")}
    server_secrets = {
        "agents": {tok[a]: a for a in ("finder-agent", "owner-agent", "campus-board")},
        "humans": {tok["finder-human"]: {"name": "finder-human", "acts_for": "finder-agent"}},
    }
    (ROOT / "secrets.json").write_text(json.dumps(server_secrets, indent=2))
    (ROOT / ".env.agents").write_text(
        f"FINDER_AGENT_TOKEN={tok['finder-agent']}\n"
        f"OWNER_AGENT_TOKEN={tok['owner-agent']}\n"
        f"CAMPUS_BOARD_TOKEN={tok['campus-board']}\n"
        f"FINDER_HUMAN_TOKEN={tok['finder-human']}\n")
    db = ROOT / "lostlink.db"
    if db.exists():
        db.unlink()  # fresh demo state
    print("wrote secrets.json and .env.agents; reset lostlink.db")


def read_env() -> dict:
    return dict(l.split("=", 1) for l in (ROOT / ".env.agents").read_text().split())


def seed():
    """Register the synthetic found reports through the public API."""
    env = read_env()
    data = json.loads((ROOT / "data" / "synthetic_reports.json").read_text())
    h = {"Authorization": f"Bearer {env['CAMPUS_BOARD_TOKEN']}"}
    for r in data["found"] + data["distractors"]:
        body = {k: r[k] for k in ("kind", "category", "color", "brand", "location",
                                  "date", "description", "private_detail")}
        body["request_id"] = f"seed-{r['report_id']}"
        resp = httpx.post(f"{BASE}/v1/reports", json=body, headers=h)
        resp.raise_for_status()
    print(f"seeded {len(data['found']) + len(data['distractors'])} found reports as campus-board")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", action="store_true", help="seed a running server")
    args = ap.parse_args()
    seed() if args.seed else make_secrets()
