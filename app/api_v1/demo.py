from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app import models
from app.api_v1.transactions import get_db
from app.services.rules_engine import evaluate_rules_for_transaction


router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/seed", status_code=status.HTTP_204_NO_CONTENT)
def seed_demo_data(
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    """
    Seed a small demo dataset:
    - Two risk rules (amount threshold + velocity)
    - A few transactions that trigger different decisions
    """
    # Seed rules idempotently.
    if not db.query(models.RiskRule).filter_by(code="AMOUNT_GT_1000", version=1).first():
        db.add(
            models.RiskRule(
                code="AMOUNT_GT_1000",
                version=1,
                name="Amount > 1000",
                description="Review high-amount transactions",
                definition="amount_gt:1000",
                active=True,
            )
        )

    if not db.query(models.RiskRule).filter_by(
        code="VELOCITY_ACCOUNT_3_IN_60S", version=1
    ).first():
        db.add(
            models.RiskRule(
                code="VELOCITY_ACCOUNT_3_IN_60S",
                version=1,
                name="Velocity 3 tx / 60s",
                description="Review high-velocity accounts",
                definition="velocity_count:3:60",
                active=True,
            )
        )

    db.flush()

    # Only create demo transactions once (based on external_id)
    if not db.query(models.Transaction).filter_by(external_id="demo-allow-1").first():
        _create_and_evaluate_transaction(
            db,
            external_id="demo-allow-1",
            account_id="ACC-DEMO-1",
            amount=200.0,
        )

    if not db.query(models.Transaction).filter_by(external_id="demo-review-amount").first():
        _create_and_evaluate_transaction(
            db,
            external_id="demo-review-amount",
            account_id="ACC-DEMO-1",
            amount=5000.0,
        )

    # Velocity scenario: multiple small tx in short window
    base_time = datetime.utcnow() - timedelta(seconds=30)
    for i in range(3):
        eid = f"demo-vel-pre-{i}"
        if not db.query(models.Transaction).filter_by(external_id=eid).first():
            _create_and_evaluate_transaction(
                db,
                external_id=eid,
                account_id="ACC-DEMO-VEL",
                amount=50.0,
                created_at=base_time + timedelta(seconds=i * 5),
            )

    if not db.query(models.Transaction).filter_by(external_id="demo-vel-trigger").first():
        _create_and_evaluate_transaction(
            db,
            external_id="demo-vel-trigger",
            account_id="ACC-DEMO-VEL",
            amount=60.0,
        )
    db.commit()


def _create_and_evaluate_transaction(
    db: Session,
    *,
    external_id: str,
    account_id: str,
    amount: float,
    created_at: Optional[datetime] = None,
) -> models.Transaction:
    tx = models.Transaction(
        external_id=external_id,
        account_id=account_id,
        amount=amount,
        currency="INR",
        merchant_id="M-DEMO",
        created_at=created_at or datetime.utcnow(),
    )
    db.add(tx)
    db.flush()

    evaluate_rules_for_transaction(db, tx)
    db.flush()
    return tx


