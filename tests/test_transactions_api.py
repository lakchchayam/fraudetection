from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models


def seed_basic_rules(db: Session) -> None:
    """
    Seed a small set of rules used by multiple tests.
    For simplicity, rule.definition is a compact string understood by the engine:
    - amount_gt:<value>
    - velocity_count:<n>:<window_seconds>
    - geo_mismatch
    """
    # High amount rule
    db.add(
        models.RiskRule(
            code="AMOUNT_GT_1000",
            version=1,
            name="Amount > 1000",
            description="Block or review high amount transactions",
            definition="amount_gt:1000",
            active=True,
        )
    )
    # Simple velocity rule: >3 tx per 60s for same account is suspicious
    db.add(
        models.RiskRule(
            code="VELOCITY_ACCOUNT_3_IN_60S",
            version=1,
            name="Velocity 3 tx per 60s",
            definition="velocity_count:3:60",
            active=True,
        )
    )
    db.commit()


def create_transaction(
    db: Session,
    *,
    external_id: str,
    account_id: str,
    amount: float,
    merchant_id: str = "M1",
    created_at: datetime | None = None,
) -> models.Transaction:
    tx = models.Transaction(
        external_id=external_id,
        account_id=account_id,
        amount=amount,
        currency="USD",
        merchant_id=merchant_id,
        created_at=created_at or datetime.utcnow(),
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def test_ingest_transaction_idempotent(client: TestClient, db_session: Session) -> None:
    seed_basic_rules(db_session)
    payload = {
        "external_id": "tx-1",
        "account_id": "acc-1",
        "amount": 50.0,
        "currency": "USD",
        "merchant_id": "M1",
    }

    r1 = client.post("/api/v1/transactions", json=payload)
    assert r1.status_code == 201
    body1 = r1.json()
    assert body1["transaction"]["external_id"] == "tx-1"

    # Second call with same external_id should be idempotent and return same transaction.
    r2 = client.post("/api/v1/transactions", json=payload)
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["transaction"]["id"] == body1["transaction"]["id"]
    assert body2["transaction"]["external_id"] == "tx-1"


def test_rules_evaluation_amount_threshold_creates_alert(
    client: TestClient, db_session: Session
) -> None:
    seed_basic_rules(db_session)

    payload = {
        "external_id": "tx-high-amount",
        "account_id": "acc-2",
        "amount": 5000.0,
        "currency": "USD",
        "merchant_id": "M1",
    }

    r = client.post("/api/v1/transactions", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body["decision"] in {"REVIEW", "BLOCK"}
    assert body["alerts"]
    assert body["alerts"][0]["severity"] in {"HIGH", "CRITICAL"}
    assert any(rule["code"] == "AMOUNT_GT_1000" for rule in body["rules_fired"])


def test_velocity_rule_triggers_review(
    client: TestClient, db_session: Session
) -> None:
    seed_basic_rules(db_session)

    base_time = datetime.utcnow() - timedelta(seconds=10)
    # Preload 3 transactions in the last 60 seconds.
    for i in range(3):
        create_transaction(
            db_session,
            external_id=f"pre-{i}",
            account_id="acc-velocity",
            amount=10.0,
            created_at=base_time + timedelta(seconds=i * 2),
        )

    payload = {
        "external_id": "tx-velocity",
        "account_id": "acc-velocity",
        "amount": 15.0,
        "currency": "USD",
        "merchant_id": "M1",
    }

    r = client.post("/api/v1/transactions", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body["decision"] in {"REVIEW", "BLOCK"}
    assert any(
        rule["code"] == "VELOCITY_ACCOUNT_3_IN_60S" for rule in body["rules_fired"]
    )


def test_list_transactions_pagination(client: TestClient, db_session: Session) -> None:
    seed_basic_rules(db_session)
    for i in range(15):
        payload = {
            "external_id": f"tx-{i}",
            "account_id": f"acc-{i%3}",
            "amount": float(i),
            "currency": "USD",
            "merchant_id": "M1",
        }
        r = client.post("/api/v1/transactions", json=payload)
        assert r.status_code in (201, 200)

    r = client.get("/api/v1/transactions?limit=5&offset=0")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 15
    assert len(body["items"]) == 5



