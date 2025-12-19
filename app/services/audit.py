import json
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app import models


def record_audit_event(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    event_type: str,
    payload: Dict[str, Any],
    actor: Optional[str] = None,
    case_id: Optional[int] = None,
) -> models.AuditLog:
    entry = models.AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        payload=json.dumps(payload, sort_keys=True),
        actor=actor,
        case_id=case_id,
    )
    db.add(entry)
    return entry



