from typing import List, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app import models

def get_rule_performance_stats(db: Session) -> List[Dict[str, Any]]:
    """
    Returns aggregated stats on which rules are triggering.
    Example: [{"code": "VELOCITY", "count": 12}, ...]
    """
    # Group by rule_id and count
    results = (
        db.query(
            models.RiskRule.code,
            func.count(models.RuleEvaluationResult.id).label("hit_count")
        )
        .join(models.RuleEvaluationResult, models.RiskRule.id == models.RuleEvaluationResult.rule_id)
        .filter(models.RuleEvaluationResult.passed == False)  # Only count failures (hits)
        .group_by(models.RiskRule.id, models.RiskRule.code)
        .order_by(func.count(models.RuleEvaluationResult.id).desc())
        .all()
    )

    return [
        {"code": row.code, "count": row.hit_count}
        for row in results
    ]
