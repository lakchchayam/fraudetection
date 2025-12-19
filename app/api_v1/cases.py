from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.api_v1.transactions import get_db
from app.schemas import CaseCreate, CaseOut, CaseUpdate
from app.services import cases as case_service


router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
def create_case_endpoint(
    request: Request,
    payload: CaseCreate,
    db: Session = Depends(get_db),
) -> CaseOut:
    try:
        case = case_service.create_case(
            db, alert_id=payload.alert_id, assignee=payload.assignee, actor="system"
        )
    except ValueError as exc:  # alert not found
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CaseOut.model_validate(case)


@router.patch("/{case_id}", response_model=CaseOut)
def update_case_endpoint(
    request: Request,
    case_id: int,
    payload: CaseUpdate,
    db: Session = Depends(get_db),
) -> CaseOut:
    try:
        case = case_service.update_case(
            db,
            case_id=case_id,
            assignee=payload.assignee,
            status=payload.status,
            resolution=payload.resolution,
            actor="system",
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CaseOut.model_validate(case)


@router.get("", response_model=list[CaseOut])
def list_cases(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    assignee: Optional[str] = Query(None),
) -> list[CaseOut]:
    stmt = select(models.Case).order_by(models.Case.updated_at.desc())
    if status:
        stmt = stmt.where(models.Case.status == status)
    if assignee:
        stmt = stmt.where(models.Case.assignee == assignee)
    stmt = stmt.limit(limit).offset(offset)
    cases = list(db.scalars(stmt))
    return [CaseOut.model_validate(c) for c in cases]

