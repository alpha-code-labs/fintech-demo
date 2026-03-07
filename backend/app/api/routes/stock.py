from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.calculations.stock import (
    get_stock_deep_dive, set_stock_flag, clear_stock_flag,
    get_chart_judgments, add_chart_judgment, delete_chart_judgment,
    get_stock_universe,
)

router = APIRouter()


class FlagRequest(BaseModel):
    detail: str = ""


class JudgmentRequest(BaseModel):
    pattern: str
    conviction: str
    notes: Optional[str] = ""


@router.get("/stock/universe")
def list_universe():
    return get_stock_universe()


@router.get("/stock/{symbol}")
def get_stock(symbol: str, week_ending: Optional[str] = None):
    result = get_stock_deep_dive(symbol, week_ending=week_ending)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Stock {symbol.upper()} not found in universe")
    return result


@router.post("/stock/{symbol}/flag/business_mix")
def flag_business_mix(symbol: str, body: FlagRequest):
    """Flag a stock as having a business mix change."""
    result = set_stock_flag(symbol, "business_mix", body.detail or "Business mix change flagged by user.")
    return result


@router.delete("/stock/{symbol}/flag/business_mix")
def unflag_business_mix(symbol: str):
    """Remove business mix change flag from a stock."""
    deleted = clear_stock_flag(symbol, "business_mix")
    if not deleted:
        raise HTTPException(status_code=404, detail="Flag not found")
    return {"status": "cleared"}


@router.get("/stock/{symbol}/judgments")
def list_judgments(symbol: str):
    return get_chart_judgments(symbol)


@router.post("/stock/{symbol}/judgments")
def create_judgment(symbol: str, body: JudgmentRequest):
    return add_chart_judgment(symbol, body.pattern, body.conviction, body.notes)


@router.delete("/stock/{symbol}/judgments/{judgment_id}")
def remove_judgment(symbol: str, judgment_id: int):
    deleted = delete_chart_judgment(judgment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Judgment not found")
    return {"status": "deleted"}
