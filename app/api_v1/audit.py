from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api_v1.transactions import get_db
from app.schemas import AuditLogOut
from app.services.cases import list_audit_for_entity


router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
def list_audit(
    request: Request,
    entity_type: str = Query(...),
    entity_id: int = Query(...),
    db: Session = Depends(get_db),
) -> list[AuditLogOut]:
    logs = list_audit_for_entity(db, entity_type=entity_type, entity_id=entity_id)
    return [AuditLogOut.model_validate(a) for a in logs]



