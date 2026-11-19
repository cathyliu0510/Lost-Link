"""HW9: invalid calendar dates must not silently enter retrieval scoring."""
import pytest

from tests.test_service import A, LOST, client


INVALID_DATES = ["2026-02-30", "2026-13-01", "2025-02-29", "tomorrow", "20261117", "2026-W47-2"]


@pytest.mark.parametrize("invalid", INVALID_DATES)
def test_invalid_date_is_rejected_without_consuming_the_request_id(client, invalid):
    payload = {**LOST, "date": invalid, "request_id": "same-intent"}
    response = client.post("/v1/reports", json=payload, headers=A("owner"))
    assert response.status_code == 422
    assert any(error["loc"][-1] == "date" for error in response.json()["detail"])
    # The client can repair the field and reuse its intent ID. No invalid
    # record may have been inserted or cached as a successful creation.
    repaired = client.post("/v1/reports", json={**payload, "date": "2026-11-17"}, headers=A("owner"))
    assert repaired.status_code == 200
    assert repaired.json()["duplicate_request"] is False


@pytest.mark.parametrize("invalid", INVALID_DATES)
def test_patch_cannot_bypass_date_validation_or_consume_the_version(client, invalid):
    report = client.post("/v1/reports", json=LOST, headers=A("owner")).json()
    path = "/v1/reports/" + report["report_id"]
    response = client.patch(path, json={"expected_version": 1, "date": invalid}, headers=A("owner"))
    assert response.status_code == 422
    assert any(error["loc"][-1] == "date" for error in response.json()["detail"])

    from lostlink import server
    with server.get_db() as conn:
        row = conn.execute("SELECT date, version FROM reports WHERE report_id=?", (report["report_id"],)).fetchone()
        assert (row["date"], row["version"]) == (LOST["date"], 1)
    repaired = client.patch(path, json={"expected_version": 1, "date": "2024-02-29"}, headers=A("owner"))
    assert repaired.status_code == 200
    assert repaired.json()["version"] == 2
    with server.get_db() as conn:
        assert conn.execute("SELECT date FROM reports WHERE report_id=?", (report["report_id"],)).fetchone()[0] == "2024-02-29"


@pytest.mark.parametrize("valid", [None, "2024-02-29", "2026-11-17"])
def test_unknown_and_real_iso_dates_remain_usable(client, valid):
    response = client.post("/v1/reports", json={**LOST, "date": valid}, headers=A("owner"))
    assert response.status_code == 200
