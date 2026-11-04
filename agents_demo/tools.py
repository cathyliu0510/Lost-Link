"""
Function tools that let an OpenAI Agents SDK agent call Lost Link.

`make_tools(token, name)` returns tools bound to ONE agent identity: the
token lives in the closure, so the model never sees or chooses credentials.
Every call and its raw JSON result are appended to `CALL_LOG`, which the
demo uses for its automatic result checks.
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Literal

import httpx
from agents import function_tool

BASE = os.environ.get("LOSTLINK_URL", "http://127.0.0.1:8000")
CALL_LOG: list[dict] = []  # [{"agent", "tool", "args", "status", "result"}]


def _rid(*parts) -> str:
    """Deterministic request_id: a retried call with the same arguments maps to
    the same id, so the server deduplicates it instead of creating a copy."""
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()[:16]


def make_tools(token: str, agent_name: str):
    headers = {"Authorization": f"Bearer {token}"}

    def call(tool: str, method: str, path: str, args: dict, body: dict | None = None) -> str:
        """HTTP call -> JSON string for the model. Errors are returned, not raised,
        so the agent can read the reason (e.g. 403) and adapt."""
        r = httpx.request(method, BASE + path, json=body, headers=headers, timeout=20)
        try:
            payload = r.json()
        except ValueError:
            payload = {"raw": r.text}
        if r.status_code >= 400:
            payload = {"error": r.status_code, "detail": payload.get("detail", payload)}
        CALL_LOG.append({"agent": agent_name, "tool": tool, "args": args,
                         "status": r.status_code, "result": payload})
        print(f"  [{agent_name}] {tool}({json.dumps(args)[:90]}) -> HTTP {r.status_code}")
        return json.dumps(payload)

    @function_tool
    def register_report(kind: Literal["lost", "found"], description: str,
                        category: str | None, color: str | None, brand: str | None,
                        location: str | None, date: str | None,
                        private_detail: str | None) -> str:
        """Register a lost or found item with Lost Link.

        Args:
            kind: "lost" if your user lost it, "found" if your user is holding it.
            description: One-sentence public description (no private details).
            category: Item type, e.g. "water bottle". null if unknown.
            color: Main color. null if unknown.
            brand: Brand if known, else null.
            location: Where it was lost/found on campus. null if unknown.
            date: ISO date YYYY-MM-DD, null if unknown. Never guess.
            private_detail: A detail only the true owner would know (sticker,
                engraving, contents). Stored privately and never shown in search.
        """
        args = dict(kind=kind, description=description, category=category, color=color,
                    brand=brand, location=location, date=date, private_detail=private_detail)
        return call("register_report", "POST", "/v1/reports", args,
                    {**args, "request_id": _rid(agent_name, args)})

    @function_tool
    def find_matches(lost_report_id: str) -> str:
        """Find candidate found reports for YOUR lost report. Returns up to 3
        candidates with score, reasons, unknown fields and conflicts, plus
        `missing` fields you could add. A candidate is not proof of ownership.

        Args:
            lost_report_id: report_id returned when you registered the lost item.
        """
        return call("find_matches", "GET", f"/v1/reports/{lost_report_id}/matches",
                    {"lost_report_id": lost_report_id})

    @function_tool
    def submit_claim(lost_report_id: str, found_report_id: str, claim_message: str) -> str:
        """Ask the holder to verify that a found item is your user's. A human
        holder reviews the claim; you cannot approve it yourself.

        Args:
            lost_report_id: Your lost report.
            found_report_id: The candidate found report.
            claim_message: Private details your user remembers about the item,
                so the holder can verify ownership.
        """
        args = dict(lost_report_id=lost_report_id, found_report_id=found_report_id,
                    claim_message=claim_message)
        return call("submit_claim", "POST", "/v1/claims", args,
                    {**args, "request_id": _rid(agent_name, args)})

    @function_tool
    def get_case_status(case_id: str) -> str:
        """Check a claim's status: submitted, needs_clarification, rejected,
        approved_for_pickup (pickup_instructions included) or returned.

        Args:
            case_id: case_id returned by submit_claim.
        """
        return call("get_case_status", "GET", f"/v1/cases/{case_id}", {"case_id": case_id})

    @function_tool
    def add_case_info(case_id: str, text: str) -> str:
        """Answer the holder's clarification request on a case.

        Args:
            case_id: The case that is in needs_clarification.
            text: Your user's answer.
        """
        return call("add_case_info", "POST", f"/v1/cases/{case_id}/info",
                    {"case_id": case_id, "text": text}, {"text": text})

    return {"register_report": register_report, "find_matches": find_matches,
            "submit_claim": submit_claim, "get_case_status": get_case_status,
            "add_case_info": add_case_info}
