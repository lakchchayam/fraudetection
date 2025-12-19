from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, constr

from app.models import AlertSeverity, Decision


class TransactionIn(BaseModel):
    external_id: constr(min_length=1, max_length=64)
    account_id: constr(min_length=1, max_length=64)
    amount: float = Field(ge=0)
    currency: constr(min_length=3, max_length=3)
    merchant_id: constr(min_length=1, max_length=64)
    merchant_category: Optional[str] = None
    ip_address: Optional[str] = None
    country: Optional[constr(min_length=2, max_length=2)] = None


class TransactionOut(BaseModel):
    id: int
    external_id: str
    account_id: str
    amount: float
    currency: str
    merchant_id: str
    merchant_category: Optional[str]
    ip_address: Optional[str]
    country: Optional[str]
    created_at: datetime
    ml_score: Optional[float] = None
    risk_decision: Optional[Decision]

    class Config:
        from_attributes = True


class RuleFired(BaseModel):
    id: int
    code: str
    version: int
    decision: Optional[Decision]
    details: Optional[str]


class AlertOut(BaseModel):
    id: int
    transaction_id: int
    severity: AlertSeverity
    title: str
    description: Optional[str]
    created_at: datetime
    status: str

    class Config:
        from_attributes = True


class TransactionWithRiskResponse(BaseModel):
    transaction: TransactionOut
    decision: Decision
    alerts: List[AlertOut]
    rules_fired: List[RuleFired]


class PaginatedTransactions(BaseModel):
    total: int
    items: List[TransactionOut]


class CaseCreate(BaseModel):
    alert_id: int
    assignee: Optional[str] = None


class CaseUpdate(BaseModel):
    assignee: Optional[str] = None
    status: Optional[str] = None
    resolution: Optional[str] = None


class CaseOut(BaseModel):
    id: int
    alert_id: int
    assignee: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    resolution: Optional[str]

    class Config:
        from_attributes = True


class AuditLogOut(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    event_type: str
    payload: str
    created_at: datetime
    actor: Optional[str]
    case_id: Optional[int]

    class Config:
        from_attributes = True


