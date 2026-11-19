"""Standalone client for the authorized Lost Link cold-start task."""

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parent
ACCESS = json.loads((ROOT / "access.json").read_text())
TOKEN = ACCESS["agent_token"]
BASE_URL = ACCESS["base_url"].rstrip("/")
STATE_PATH = ROOT / "client_state.json"
LOG_PATH = ROOT / "request_response.jsonl"


def sanitize(value):
    if isinstance(value, dict):
        return {
            key: "[REDACTED]"
            if key.lower() in {"authorization", "agent_token", "x-human-token"}
            else sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, str):
        return value.replace(TOKEN, "[REDACTED]")
    return value


def write_json(path, value):
    path.write_text(json.dumps(sanitize(value), indent=2) + "\n")


def request(method, path, body=None):
    entry = {
        "time": datetime.now(timezone.utc).isoformat(),
        "request": {
            "method": method,
            "url": BASE_URL + path,
            "headers": {"Authorization": "Bearer [REDACTED]"},
            "json": body,
        },
    }
    try:
        response = httpx.request(
            method,
            BASE_URL + path,
            headers={"Authorization": "Bearer " + TOKEN},
            json=body,
            timeout=10,
            trust_env=False,
        )
        try:
            data = response.json()
        except ValueError:
            data = {"non_json_response": response.text}
        entry["response"] = {"status_code": response.status_code, "json": data}
    except Exception as error:
        entry["error"] = {"type": type(error).__name__, "message": str(error)}
        with LOG_PATH.open("a") as log:
            log.write(json.dumps(sanitize(entry)) + "\n")
        print(json.dumps(sanitize(entry), indent=2))
        raise SystemExit(1)
    with LOG_PATH.open("a") as log:
        log.write(json.dumps(sanitize(entry)) + "\n")
    print(json.dumps(sanitize(entry), indent=2))
    if not response.is_success:
        raise SystemExit(1)
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["search", "claim", "case", "finalize"])
    parser.add_argument("--found-id")
    args = parser.parse_args()
    state = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {}
    if args.operation == "search":
        if "report_request" not in state:
            state["report_request"] = {
                "kind": "lost",
                "description": "Navy flask lost in the library on 2026-11-17.",
                "category": "flask",
                "color": "navy",
                "brand": None,
                "location": "library",
                "date": "2026-11-17",
                "private_detail": "A green cactus sticker near its cap.",
                "request_id": "coldstart-lost-" + str(uuid.uuid4()),
            }
            write_json(STATE_PATH, state)
        if "report_response" not in state:
            state["report_response"] = request("POST", "/v1/reports", state["report_request"])
            write_json(STATE_PATH, state)
        report_id = state["report_response"]["report_id"]
        state["matches_response"] = request("GET", f"/v1/reports/{report_id}/matches?limit=5")
        write_json(STATE_PATH, state)
    elif args.operation == "claim":
        if not args.found_id:
            parser.error("--found-id must be a candidate returned by the service")
        candidates = state.get("matches_response", {}).get("candidates", [])
        if not any(item["report_id"] == args.found_id for item in candidates):
            parser.error("The chosen found ID is not in the saved service candidates")
        if "claim_request" not in state:
            state["claim_request"] = {
                "lost_report_id": state["report_response"]["report_id"],
                "found_report_id": args.found_id,
                "claim_message": (
                    "I lost my navy flask in the library on 2026-11-17. "
                    "I do not know the brand. As a private ownership detail, "
                    "there is a green cactus sticker near its cap. "
                    "Please verify this detail before deciding whether to release the item."
                ),
                "request_id": "coldstart-claim-" + str(uuid.uuid4()),
            }
            write_json(STATE_PATH, state)
        if state["claim_request"]["found_report_id"] != args.found_id:
            parser.error("An existing claim request refers to a different candidate")
        state["claim_response"] = request("POST", "/v1/claims", state["claim_request"])
        write_json(STATE_PATH, state)
        case_id = state["claim_response"]["case_id"]
        state["case_response"] = request("GET", f"/v1/cases/{case_id}")
        write_json(STATE_PATH, state)
    elif args.operation == "case":
        case_id = state["claim_response"]["case_id"]
        state["case_response"] = request("GET", f"/v1/cases/{case_id}")
        write_json(STATE_PATH, state)
    elif args.operation == "finalize":
        selected_id = state["claim_request"]["found_report_id"]
        selected = next(
            item for item in state["matches_response"]["candidates"]
            if item["report_id"] == selected_id
        )
        case = state["case_response"]
        if case["status"] != "submitted":
            raise SystemExit("Case status changed; inspect it before writing the user message.")
        message = (
            f"I registered your lost flask report ({state['report_response']['report_id']}) "
            f"and submitted recovery case {case['case_id']} for a blue water bottle "
            "found at Hayden Library on November 17. Its type, color, location, and "
            "date match your report. I included the cactus-sticker detail privately "
            "for the holder to verify.\n\n"
            "The case is submitted and awaiting the holder's review. There is no "
            "pickup approval or pickup information yet. Next, wait for the holder's "
            "decision and answer any clarification request in the case. Follow the "
            "pickup instructions if the holder approves.\n"
        )
        result = {
            "outcome": "recovery_claim_submitted_awaiting_holder_review",
            "lost_report": state["report_response"],
            "selected_candidate": selected,
            "selection_reason": (
                "The selected open candidate matches the user-supplied item type, "
                "color, library location, and 2026-11-17 date after service "
                "normalization, with no reported conflicts. The other candidate "
                "has color and location conflicts and a seven-day date difference. "
                "This supports asking the holder to verify ownership, not declaring it."
            ),
            "claim": state["claim_response"],
            "case": case,
            "verification_detail_sent_privately": True,
            "ownership_confirmed": False,
            "pickup_approved": False,
            "next_step": (
                "Await holder review; answer a clarification request if one appears; "
                "use pickup instructions only after human approval."
            ),
            "friction": [
                "The initial localhost request failed with ConnectError: [Errno 1] "
                "Operation not permitted. A sandbox escalation allowed the same "
                "persisted request ID to complete.",
                "The initial access.json read mistakenly displayed the credential "
                "in tool output. No credential value is present in saved client "
                "code, request/response logs, client state, or result files."
            ],
            "manual_task_help_needed": False,
            "setup_help": "Localhost sandbox execution approval only.",
            "service_requests_after_network_access": 4,
        }
        write_json(ROOT / "client_result.json", result)
        (ROOT / "user_message.txt").write_text(message)
        print(message)


if __name__ == "__main__":
    main()
