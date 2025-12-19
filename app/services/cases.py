from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.services.audit import record_audit_event


def create_case(
    db: Session, *, alert_id: int, assignee: Optional[str] = None, actor: Optional[str] = None
) -> models.Case:
    alert = db.get(models.FraudAlert, alert_id)
    if alert is None:
        raise ValueError("Alert not found")
    case = models.Case(alert_id=alert_id, assignee=assignee)
    db.add(case)
    db.flush()
    record_audit_event(
        db,
        entity_type="Case",
        entity_id=case.id,
        event_type="CASE_CREATED",
        payload={"alert_id": alert_id, "assignee": assignee},
        actor=actor,
        case_id=case.id,
    )
    return case


def update_case(
    db: Session,
    case_id: int,
    *,
    assignee: Optional[str] = None,
    status: Optional[str] = None,
    resolution: Optional[str] = None,
    actor: Optional[str] = None,
) -> models.Case:
    case = db.get(models.Case, case_id)
    if case is None:
        raise ValueError("Case not found")
    if assignee is not None:
        case.assignee = assignee
    if status is not None:
        case.status = status
    if resolution is not None:
        case.resolution = resolution

    record_audit_event(
        db,
        entity_type="Case",
        entity_id=case.id,
        event_type="CASE_UPDATED",
        payload={
            "assignee": assignee,
            "status": status,
            "resolution": resolution,
        },
        actor=actor,
        case_id=case.id,
    )
    return case


def list_audit_for_entity(
    db: Session, *, entity_type: str, entity_id: int
) -> list[models.AuditLog]:
    stmt = select(models.AuditLog).where(
        models.AuditLog.entity_type == entity_type,
        models.AuditLog.entity_id == entity_id,
    )
    return list(db.scalars(stmt))


