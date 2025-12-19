from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models


class RuleOutcome:
    def __init__(
        self,
        rule: models.RiskRule,
        passed: bool,
        decision: Optional[models.Decision],
        score_delta: float,
        details: Optional[str] = None,
    ) -> None:
        self.rule = rule
        self.passed = passed
        self.decision = decision
        self.score_delta = score_delta
        self.details = details


class EvaluatedResult:
    def __init__(
        self,
        decision: models.Decision,
        rule_outcomes: List[RuleOutcome],
        alerts: List[models.FraudAlert],
    ) -> None:
        self.decision = decision
        self.rule_outcomes = rule_outcomes
        self.alerts = alerts


def evaluate_rules_for_transaction(
    db: Session, transaction: models.Transaction
) -> EvaluatedResult:
    """
    Evaluate all active rules for a given transaction.

    For simplicity, the rule.definition is a compact string understood here.
    """
    stmt = select(models.RiskRule).where(models.RiskRule.active.is_(True))
    rules: list[models.RiskRule] = list(db.scalars(stmt))

    outcomes: list[RuleOutcome] = []
    alerts: list[models.FraudAlert] = []

    overall_decision: models.Decision = models.Decision.ALLOW

    for rule in rules:
        outcome = _evaluate_single_rule(db, rule, transaction)
        outcomes.append(outcome)

        db.add(
            models.RuleEvaluationResult(
                transaction_id=transaction.id,
                rule_id=rule.id,
                passed=outcome.passed,
                score_delta=outcome.score_delta,
                decision=outcome.decision,
                details=outcome.details,
            )
        )

        if outcome.decision == models.Decision.BLOCK:
            overall_decision = models.Decision.BLOCK
            alerts.append(
                models.FraudAlert(
                    transaction_id=transaction.id,
                    severity=models.AlertSeverity.CRITICAL,
                    title=f"Rule {rule.code} BLOCK",
                    description=outcome.details or "",
                )
            )
        elif outcome.decision == models.Decision.REVIEW and overall_decision != models.Decision.BLOCK:
            overall_decision = models.Decision.REVIEW
            alerts.append(
                models.FraudAlert(
                    transaction_id=transaction.id,
                    severity=models.AlertSeverity.HIGH,
                    title=f"Rule {rule.code} REVIEW",
                    description=outcome.details or "",
                )
            )

    for alert in alerts:
        db.add(alert)

    transaction.risk_decision = overall_decision

    return EvaluatedResult(
        decision=overall_decision,
        rule_outcomes=outcomes,
        alerts=alerts,
    )


def _evaluate_single_rule(
    db: Session, rule: models.RiskRule, transaction: models.Transaction
) -> RuleOutcome:
    definition = rule.definition or ""
    if definition.startswith("amount_gt:"):
        threshold = float(definition.split(":", 1)[1])
        if transaction.amount > threshold:
            return RuleOutcome(
                rule,
                passed=False,
                decision=models.Decision.REVIEW,
                score_delta=10.0,
                details=f"Amount {transaction.amount} > {threshold}",
            )
        return RuleOutcome(rule, passed=True, decision=None, score_delta=0.0)

    if definition.startswith("velocity_count:"):
        parts = definition.split(":")
        if len(parts) == 3:
            max_count = int(parts[1])
            window_seconds = int(parts[2])
        else:
            max_count = 3
            window_seconds = 60

        window_start = datetime.utcnow() - timedelta(seconds=window_seconds)
        count = db.scalar(
            select(func.count(models.Transaction.id)).where(
                models.Transaction.account_id == transaction.account_id,
                models.Transaction.created_at >= window_start,
            )
        )
        if count is None:
            count = 0
        # Current transaction will be added after evaluation, so we treat count >= max_count as breaching.
        if count >= max_count:
            return RuleOutcome(
                rule,
                passed=False,
                decision=models.Decision.REVIEW,
                score_delta=5.0,
                details=f"Velocity {count} tx in last {window_seconds}s for account {transaction.account_id}",
            )
        return RuleOutcome(rule, passed=True, decision=None, score_delta=0.0)

    # Default: rule not understood, treat as neutral/pass.
    return RuleOutcome(rule, passed=True, decision=None, score_delta=0.0)


