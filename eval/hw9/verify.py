"""Check the preserved HW9 execution record without credentials or a live API.

This verifies recorded evidence; it does not run another cold-start agent.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "recorded"


def read(name):
    return json.loads((ROOT / name).read_text())


def rows(name):
    return [json.loads(line) for line in (ROOT / name).read_text().splitlines() if line]


def verify():
    manifest = read("pre_run_manifest.json")
    # The credential itself is intentionally excluded, including after revocation.
    for name, expected in manifest["sha256"].items():
        if name == "coldstart/access.json":
            continue
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name

    client = rows("coldstart/request_response.jsonl")
    successes = [row for row in client if "response" in row]
    assert len(successes) == 4
    assert sum("error" in row for row in client) == 1
    assert all(row["response"]["status_code"] == 200 for row in successes)
    assert [row["request"]["method"] for row in successes] == ["POST", "GET", "POST", "GET"]
    report, search, claim, status = successes
    request = report["request"]["json"]
    assert request["brand"] is None and request["date"] == "2026-11-17"
    assert request["category"] == "flask" and request["color"] == "navy"
    lost_id = report["response"]["json"]["report_id"]
    candidates = search["response"]["json"]["candidates"]
    result = read("coldstart/client_result.json")
    selected = result["selected_candidate"]
    assert selected in candidates
    assert selected["score"] == 0.94 and candidates[1]["score"] == 0.47
    assert claim["request"]["json"]["lost_report_id"] == lost_id
    assert claim["request"]["json"]["found_report_id"] == selected["report_id"]
    case = status["response"]["json"]
    assert case["case_id"] == claim["response"]["json"]["case_id"]
    assert case == result["case"]
    assert case["status"] == "submitted" and case["human_decisions"] == []
    assert "pickup_instructions" not in case
    assert result["ownership_confirmed"] is False and result["pickup_approved"] is False
    message = (ROOT / "coldstart/user_message.txt").read_text()
    assert case["case_id"] in message and "awaiting the holder's review" in message

    # Server-side recording and the client's transcript must describe the same
    # actual requests/results, rather than only a generated success summary.
    http = rows("evidence/http.jsonl")
    for row in successes:
        request = row["request"]
        route = request["url"].split("127.0.0.1:8869", 1)[1]
        matches = [item for item in http
                   if item["method"] == request["method"]
                   and item["path"] + ("?" + item["query"] if item["query"] else "") == route
                   and item["request"] == request["json"]
                   and item["status"] == row["response"]["status_code"]
                   and item["response"] == row["response"]["json"]]
        assert len(matches) == 1, route

    snapshot = read("evidence/coldstart_verification.json")
    assert len(snapshot["cases"]) == 1 and snapshot["human_action_count"] == 0
    db_case = snapshot["cases"][0]
    assert db_case["case_id"] == case["case_id"]
    assert db_case["lost_report_id"] == lost_id
    assert db_case["found_report_id"] == selected["report_id"]
    assert db_case["status"] == "submitted" and db_case["pickup_instructions"] is None
    assert len(snapshot["reports"]) == 4
    for row in successes:
        serialized = json.dumps(row["response"]["json"])
        assert "SYNTHETIC-HW9-VERIFY-" not in serialized
        assert '"private_detail"' not in serialized
    assert len(snapshot["checks"]) == 6 and all(snapshot["checks"].values())

    before, after = (read(f"evidence/boundary_{phase}.json") for phase in ["before", "after"])
    before_body, after_body = (dict(row["request"]) for row in [before, after])
    before_body.pop("request_id")
    after_body.pop("request_id")
    assert before_body == after_body and before_body["date"] == "2026-02-30"
    assert before["actual_status"] == 200 and after["actual_status"] == 422
    assert any(error["loc"][-1] == "date" for error in after["response"]["detail"])
    assert manifest["recorded_at"] < successes[0]["time"] < before["at"] < after["at"]
    regression = read("evidence/postfix_http_regression.json")
    assert regression["all_checks_passed"] is True
    assert [row["actual_status"] for row in regression["requests"]] == [422, 200, 422, 200, 200, 200]
    assert all(row["actual_status"] == row["expected_status"] for row in regression["requests"])
    assert regression["database_after_bad_patch"]["version"] == 1
    assert regression["database_after_bad_patch"]["date"] == "2024-02-29"
    assert regression["database_after_null_patch"]["date"] == "2026-11-17"
    assert regression["source_sha256"] == hashlib.sha256((ROOT.parents[2] / "lostlink/server.py").read_bytes()).hexdigest()
    assert not (ROOT / "coldstart/access.json").exists()
    assert not (ROOT / "private").exists()
    return {"recorded_coldstart_checks": snapshot["checks"],
            "successful_client_http_requests": 4,
            "setup_errors": 1, "boundary_before": 200, "boundary_after": 422,
            "final_http_regression": "PASS (6 operator requests)",
            "context": "Self-run fresh session; not an independent builder",
            "verification": "PASS (recorded evidence, not a new client run)"}


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
