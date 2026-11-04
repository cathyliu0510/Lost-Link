"""
Service-level checks for the rules the agents rely on.
Run:  pytest -q
"""
import importlib
import json
import os

import pytest
from fastapi.testclient import TestClient

TOK = {"finder": "tok-finder", "owner": "tok-owner", "other": "tok-other", "human": "tok-human"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Fresh DB + secrets for every test
    secrets_file = tmp_path / "secrets.json"
    secrets_file.write_text(json.dumps({
        "agents": {TOK["finder"]: "finder-agent", TOK["owner"]: "owner-agent",
                   TOK["other"]: "other-agent"},
        "humans": {TOK["human"]: {"name": "finder-human", "acts_for": "finder-agent"}}}))
    monkeypatch.setenv("LOSTLINK_DB", str(tmp_path / "t.db"))
    monkeypatch.setenv("LOSTLINK_SECRETS", str(secrets_file))
    import lostlink.server as server
    importlib.reload(server)  # pick up env vars
    with TestClient(server.app) as c:
        yield c


def A(who):  # agent auth header
    return {"Authorization": f"Bearer {TOK[who]}"}


HUMAN = {"X-Human-Token": TOK["human"]}
FOUND = {"kind": "found", "category": "water bottle", "color": "blue", "location": "Hayden Library",
         "date": "2026-10-27", "description": "blue water bottle",
         "private_detail": "green cactus sticker", "request_id": "f1"}
LOST = {"kind": "lost", "category": "flask", "color": "navy", "location": "library",
        "date": "2026-10-27", "description": "navy flask", "request_id": "l1"}


def setup_case(c, who="owner", rid="c1"):
    f = c.post("/v1/reports", json=FOUND, headers=A("finder")).json()["report_id"]
    l = c.post("/v1/reports", json={**LOST, "request_id": f"l-{who}"}, headers=A(who)).json()["report_id"]
    case = c.post("/v1/claims", json={"lost_report_id": l, "found_report_id": f,
                                      "claim_message": "cactus sticker", "request_id": rid},
                  headers=A(who)).json()
    return f, l, case["case_id"]


def test_match_found_without_leaking_private_detail(client):
    f = client.post("/v1/reports", json=FOUND, headers=A("finder")).json()["report_id"]
    l = client.post("/v1/reports", json=LOST, headers=A("owner")).json()["report_id"]
    r = client.get(f"/v1/reports/{l}/matches", headers=A("owner"))
    assert r.status_code == 200
    assert r.json()["candidates"][0]["report_id"] == f
    assert "cactus" not in r.text and "finder-agent" not in r.text


def test_cannot_search_someone_elses_report(client):
    l = client.post("/v1/reports", json=LOST, headers=A("owner")).json()["report_id"]
    assert client.get(f"/v1/reports/{l}/matches", headers=A("other")).status_code == 403


def test_retry_does_not_duplicate(client):
    a = client.post("/v1/reports", json=FOUND, headers=A("finder")).json()
    b = client.post("/v1/reports", json=FOUND, headers=A("finder")).json()
    assert a["report_id"] == b["report_id"] and b["duplicate_request"]


def test_stale_version_conflict_and_owner_only_edit(client):
    f = client.post("/v1/reports", json=FOUND, headers=A("finder")).json()["report_id"]
    assert client.patch(f"/v1/reports/{f}", json={"expected_version": 1, "brand": "x"},
                        headers=A("owner")).status_code == 403
    assert client.patch(f"/v1/reports/{f}", json={"expected_version": 1, "brand": "x"},
                        headers=A("finder")).status_code == 200
    assert client.patch(f"/v1/reports/{f}", json={"expected_version": 1, "brand": "y"},
                        headers=A("finder")).status_code == 409


def test_agent_cannot_self_approve(client):
    f, l, cid = setup_case(client)
    # agent token on human endpoint
    r = client.post(f"/v1/human/cases/{cid}/decision", headers=A("finder"),
                    json={"decision": "approve", "pickup_instructions": "x"})
    assert r.status_code == 403
    # forged field
    r = client.post("/v1/claims", headers=A("owner"), json={
        "lost_report_id": l, "found_report_id": f, "claim_message": "m",
        "request_id": "z", "human_approved": True})
    assert r.status_code == 422
    assert client.get(f"/v1/cases/{cid}", headers=A("owner")).json()["status"] == "submitted"


def test_full_lifecycle_and_pickup_release(client):
    f, l, cid = setup_case(client)
    s = client.get(f"/v1/cases/{cid}", headers=A("owner")).json()
    assert "pickup_instructions" not in s
    assert client.get(f"/v1/cases/{cid}", headers=A("other")).status_code == 403
    inbox = client.get("/v1/human/inbox", headers=HUMAN).json()
    assert inbox[0]["your_private_detail"] == "green cactus sticker"
    client.post(f"/v1/human/cases/{cid}/decision", headers=HUMAN,
                json={"decision": "approve", "pickup_instructions": "front desk"})
    s = client.get(f"/v1/cases/{cid}", headers=A("owner")).json()
    assert s["status"] == "approved_for_pickup" and s["pickup_instructions"] == "front desk"
    assert client.post(f"/v1/human/cases/{cid}/returned", headers=HUMAN).status_code == 200
    assert client.get(f"/v1/cases/{cid}", headers=A("owner")).json()["status"] == "returned"


def test_only_one_approval_per_found_report(client):
    f, _, c1 = setup_case(client, "owner", "c1")
    l2 = client.post("/v1/reports", json={**LOST, "request_id": "l2"}, headers=A("other")).json()["report_id"]
    c2 = client.post("/v1/claims", headers=A("other"), json={
        "lost_report_id": l2, "found_report_id": f, "claim_message": "also mine",
        "request_id": "c2"}).json()["case_id"]
    ok = client.post(f"/v1/human/cases/{c1}/decision", headers=HUMAN,
                     json={"decision": "approve", "pickup_instructions": "desk"})
    dup = client.post(f"/v1/human/cases/{c2}/decision", headers=HUMAN,
                      json={"decision": "approve", "pickup_instructions": "desk"})
    assert ok.status_code == 200 and dup.status_code == 409


def test_clarification_loop(client):
    _, _, cid = setup_case(client)
    client.post(f"/v1/human/cases/{cid}/decision", headers=HUMAN,
                json={"decision": "need_info", "note": "What color is the sticker?"})
    s = client.get(f"/v1/cases/{cid}", headers=A("owner")).json()
    assert s["status"] == "needs_clarification" and "sticker" in s["clarification_request"]
    r = client.post(f"/v1/cases/{cid}/info", headers=A("owner"), json={"text": "green"})
    assert r.json()["status"] == "submitted"
