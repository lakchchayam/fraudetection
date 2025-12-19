from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.api_v1.transactions import get_db
from app.schemas import AlertOut


router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
) -> list[AlertOut]:
    stmt = select(models.FraudAlert).order_by(models.FraudAlert.created_at.desc())
    if status:
        stmt = stmt.where(models.FraudAlert.status == status)
    if severity:
        stmt = stmt.where(models.FraudAlert.severity == severity)
    stmt = stmt.limit(limit).offset(offset)
    alerts = list(db.scalars(stmt))
    return [AlertOut.model_validate(a) for a in alerts]


