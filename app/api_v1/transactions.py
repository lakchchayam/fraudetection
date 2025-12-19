from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.db import SessionLocal
from app.schemas import PaginatedTransactions, TransactionIn, TransactionOut, TransactionWithRiskResponse
from app.services.rules_engine import evaluate_rules_for_transaction


router = APIRouter(prefix="/transactions", tags=["transactions"])


def get_db(request: Request):
    """
    Dependency that yields a DB session.

    - In tests, uses the pre-injected `app.state._test_session`.
    - In normal runs, creates and closes a new SessionLocal.
    """
    test_session = getattr(request.app.state, "_test_session", None)
    if test_session is not None:
        # In tests we hand FastAPI an existing session and do not manage its lifecycle here.
        yield test_session
        return

    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "",
    response_model=TransactionWithRiskResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_transaction(
    payload: TransactionIn,
    request: Request,
    db: Session = Depends(get_db),
) -> TransactionWithRiskResponse:
    # Idempotent ingestion based on external_id.
    existing = db.scalar(
        select(models.Transaction).where(
            models.Transaction.external_id == payload.external_id
        )
    )
    if existing:
        decision = existing.risk_decision or models.Decision.ALLOW
        # Collect alerts and rule results.
        alerts = list(
            db.scalars(
                select(models.FraudAlert).where(
                    models.FraudAlert.transaction_id == existing.id
                )
            )
        )
        rule_results = list(
            db.scalars(
                select(models.RuleEvaluationResult)
                .join(models.RiskRule)
                .where(models.RuleEvaluationResult.transaction_id == existing.id)
            )
        )
        return TransactionWithRiskResponse(
            transaction=TransactionOut.model_validate(existing),
            decision=decision,  # type: ignore[arg-type]
            alerts=[a for a in alerts],
            rules_fired=[
                {
                    "id": rr.rule.id,
                    "code": rr.rule.code,
                    "version": rr.rule.version,
                    "decision": rr.decision,
                    "details": rr.details,
                }
                for rr in rule_results
            ],
        )

    tx = models.Transaction(
        external_id=payload.external_id,
        account_id=payload.account_id,
        amount=payload.amount,
        currency=payload.currency,
        merchant_id=payload.merchant_id,
        merchant_category=payload.merchant_category,
        ip_address=payload.ip_address,
        country=payload.country,
    )

    # Pro Feature: Calculate Mock ML Score
    # Simple logic: higher amount = higher risk, plus random noise
    import random
    base_score = min(payload.amount / 1000.0 * 10.0, 50.0)  # Max 50 points from amount
    random_noise = random.uniform(0, 40)
    # If high velocity (simulated), add more risk.
    # real model would query feature store.
    ml_score = base_score + random_noise
    if payload.amount > 5000:
        ml_score += 20
    
    tx.ml_score = round(min(max(ml_score, 0.0), 100.0), 2)

    db.add(tx)
    db.flush()

    result = evaluate_rules_for_transaction(db, tx)
    db.flush()
    db.commit()

    return TransactionWithRiskResponse(
        transaction=TransactionOut.model_validate(tx),
        decision=result.decision,
        alerts=[a for a in result.alerts],
        rules_fired=[
            {
                "id": outcome.rule.id,
                "code": outcome.rule.code,
                "version": outcome.rule.version,
                "decision": outcome.decision,
                "details": outcome.details,
            }
            for outcome in result.rule_outcomes
        ],
    )


@router.get("", response_model=PaginatedTransactions)
def list_transactions(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> PaginatedTransactions:
    total = db.scalar(select(func.count(models.Transaction.id))) or 0
    stmt = (
        select(models.Transaction)
        .order_by(models.Transaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = list(db.scalars(stmt))
    return PaginatedTransactions(
        total=total,
        items=[TransactionOut.model_validate(t) for t in items],
    )


@router.get(
    "/{transaction_id}",
    response_model=TransactionWithRiskResponse,
    responses={404: {"description": "Transaction not found"}},
)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
) -> TransactionWithRiskResponse:
    tx = db.get(models.Transaction, transaction_id)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )

    decision = tx.risk_decision or models.Decision.ALLOW
    
    # Collect alerts and rules
    alerts = list(
        db.scalars(
            select(models.FraudAlert).where(models.FraudAlert.transaction_id == tx.id)
        )
    )
    rule_results = list(
        db.scalars(
            select(models.RuleEvaluationResult)
            .join(models.RiskRule)
            .where(models.RuleEvaluationResult.transaction_id == tx.id)
        )
    )

    return TransactionWithRiskResponse(
        transaction=TransactionOut.model_validate(tx),
        decision=decision,  # type: ignore[arg-type]
        alerts=[a for a in alerts],
        rules_fired=[
            {
                "id": rr.rule.id,
                "code": rr.rule.code,
                "version": rr.rule.version,
                "decision": rr.decision,
                "details": rr.details,
            }
            for rr in rule_results
        ],
    )


