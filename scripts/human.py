"""
Holder's human console (terminal stand-in for the dashboard).
Uses FINDER_HUMAN_TOKEN, which no agent process is given.

    python scripts/human.py inbox
    python scripts/human.py approve C-XXXX --pickup "Hayden front desk, ask for Sam, 9-5"
    python scripts/human.py need-info C-XXXX --note "What color is the sticker?"
    python scripts/human.py reject C-XXXX
    python scripts/human.py returned C-XXXX
"""
import argparse
import json
import os
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get("LOSTLINK_URL", "http://127.0.0.1:8000")
env = dict(l.split("=", 1) for l in (ROOT / ".env.agents").read_text().split())
H = {"X-Human-Token": env["FINDER_HUMAN_TOKEN"]}


def show(resp: httpx.Response):
    print(resp.status_code, json.dumps(resp.json(), indent=2))


ap = argparse.ArgumentParser()
ap.add_argument("cmd", choices=["inbox", "approve", "need-info", "reject", "returned"])
ap.add_argument("case_id", nargs="?")
ap.add_argument("--pickup", help="pickup instructions released on approval")
ap.add_argument("--note")
a = ap.parse_args()

if a.cmd == "inbox":
    show(httpx.get(f"{BASE}/v1/human/inbox", headers=H))
elif a.cmd == "returned":
    show(httpx.post(f"{BASE}/v1/human/cases/{a.case_id}/returned", headers=H))
else:
    decision = {"approve": "approve", "need-info": "need_info", "reject": "reject"}[a.cmd]
    show(httpx.post(f"{BASE}/v1/human/cases/{a.case_id}/decision", headers=H,
                    json={"decision": decision, "note": a.note,
                          "pickup_instructions": a.pickup}))
