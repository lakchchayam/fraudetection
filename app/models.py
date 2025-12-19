from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Decision(str, PyEnum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class AlertSeverity(str, PyEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    external_id = Column(String(64), nullable=False, unique=True)
    account_id = Column(String(64), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False)
    merchant_id = Column(String(64), nullable=False, index=True)
    merchant_category = Column(String(64), nullable=True)
    ip_address = Column(String(45), nullable=True)
    country = Column(String(2), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Pro Feature: Mock ML Score (0.0 to 100.0) indicating fraud probability
    ml_score = Column(Float, nullable=True)

    risk_decision = Column(Enum(Decision), nullable=True)

    alerts = relationship("FraudAlert", back_populates="transaction")


class RiskRule(Base):
    __tablename__ = "risk_rules"
    __table_args__ = (
        UniqueConstraint("code", "version", name="uq_risk_rules_code_version"),
    )

    id = Column(Integer, primary_key=True)
    code = Column(String(64), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    # Simple JSON-like expression or configuration string; interpreted by rules engine.
    definition = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    rule_results = relationship("RuleEvaluationResult", back_populates="rule")


class RuleEvaluationResult(Base):
    __tablename__ = "rule_evaluation_results"
    __table_args__ = (
        UniqueConstraint(
            "transaction_id",
            "rule_id",
            name="uq_rule_eval_tx_rule",
        ),
    )

    id = Column(Integer, primary_key=True)
    transaction_id = Column(
        Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )
    rule_id = Column(
        Integer, ForeignKey("risk_rules.id", ondelete="RESTRICT"), nullable=False
    )
    passed = Column(Boolean, nullable=False)
    score_delta = Column(Float, nullable=False, default=0.0)
    decision = Column(Enum(Decision), nullable=True)
    details = Column(Text, nullable=True)
    evaluated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    transaction = relationship("Transaction")
    rule = relationship("RiskRule", back_populates="rule_results")


class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    id = Column(Integer, primary_key=True)
    transaction_id = Column(
        Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )
    severity = Column(Enum(AlertSeverity), nullable=False)
    title = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    status = Column(String(32), nullable=False, default="OPEN")

    transaction = relationship("Transaction", back_populates="alerts")
    case = relationship("Case", back_populates="alert", uselist=False)


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True)
    alert_id = Column(
        Integer, ForeignKey("fraud_alerts.id", ondelete="RESTRICT"), nullable=False
    )
    assignee = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False, default="OPEN")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    resolution = Column(Text, nullable=True)

    alert = relationship("FraudAlert", back_populates="case")
    audit_logs = relationship("AuditLog", back_populates="case")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(Integer, nullable=False)
    event_type = Column(String(64), nullable=False)
    payload = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    actor = Column(String(64), nullable=True)

    case_id = Column(Integer, ForeignKey("cases.id", ondelete="SET NULL"), nullable=True)

    case = relationship("Case", back_populates="audit_logs")

    __table_args__ = (
        CheckConstraint("payload IS NOT NULL", name="ck_audit_logs_payload_not_null"),
    )



