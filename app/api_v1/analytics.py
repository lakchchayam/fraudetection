from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api_v1.transactions import get_db
from app.services import analytics

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/rules", response_model=List[Dict[str, Any]])
def get_rule_stats(db: Session = Depends(get_db)):
    """
    Get statistics on which rules are triggering.
    """
    return analytics.get_rule_performance_stats(db)
