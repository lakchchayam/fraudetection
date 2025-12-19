from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models


def test_alert_created_and_case_can_be_managed(
    client: TestClient, db_session: Session
) -> None:
    # Seed single blocking rule to force an alert.
    db_session.add(
        models.RiskRule(
            code="AMOUNT_GT_1000",
            version=1,
            name="Amount > 1000",
            definition="amount_gt:1000",
            active=True,
        )
    )
    db_session.commit()

    tx_payload = {
        "external_id": "tx-for-alert",
        "account_id": "acc-case",
        "amount": 5000.0,
        "currency": "USD",
        "merchant_id": "M1",
    }
    r_tx = client.post("/api/v1/transactions", json=tx_payload)
    assert r_tx.status_code == 201
    tx_body = r_tx.json()
    alerts = tx_body["alerts"]
    assert alerts
    alert_id = alerts[0]["id"]

    # Create case from alert.
    r_case = client.post(
        "/api/v1/cases",
        json={"alert_id": alert_id, "assignee": "analyst1"},
    )
    assert r_case.status_code == 201
    case_body = r_case.json()
    case_id = case_body["id"]
    assert case_body["status"] == "OPEN"

    # Update case status and resolution.
    r_update = client.patch(
        f"/api/v1/cases/{case_id}",
        json={"status": "CLOSED", "resolution": "Confirmed fraud"},
    )
    assert r_update.status_code == 200
    updated = r_update.json()
    assert updated["status"] == "CLOSED"
    assert updated["resolution"] == "Confirmed fraud"

    # Audit logs should record case updates.
    r_audit = client.get(f"/api/v1/audit?entity_type=Case&entity_id={case_id}")
    assert r_audit.status_code == 200
    audit_entries = r_audit.json()
    assert any(entry["event_type"] == "CASE_CREATED" for entry in audit_entries)
    assert any(entry["event_type"] == "CASE_UPDATED" for entry in audit_entries)



