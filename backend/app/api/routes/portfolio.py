from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.calculations.portfolio import (
    get_portfolio, add_holding, remove_holding,
    sell_holding, hold_decision, add_more_shares, get_trade_history,
    add_to_watchlist, remove_from_watchlist, get_watchlist,
    create_alert, delete_alert, get_alerts,
)

router = APIRouter()


class HoldingIn(BaseModel):
    symbol: str
    buy_price: float
    buy_date: str          # YYYY-MM-DD
    quantity: int = 1
    notes: str | None = None
    buy_thesis: str | None = None


class WatchlistIn(BaseModel):
    symbol: str
    notes: str | None = None


@router.get("/portfolio")
def portfolio():
    return get_portfolio()


@router.post("/portfolio/holdings")
def create_holding(body: HoldingIn):
    try:
        row = add_holding(
            symbol=body.symbol,
            buy_price=body.buy_price,
            buy_date=body.buy_date,
            quantity=body.quantity,
            notes=body.notes,
            buy_thesis=body.buy_thesis,
        )
        return {"status": "ok", "holding": row}
    except Exception as e:
        if "UNIQUE" in str(e):
            raise HTTPException(400, f"{body.symbol} is already in your portfolio")
        raise HTTPException(400, str(e))


@router.delete("/portfolio/holdings/{symbol}")
def delete_holding(symbol: str):
    deleted = remove_holding(symbol)
    if not deleted:
        raise HTTPException(404, f"{symbol} not found in portfolio")
    return {"status": "ok", "symbol": symbol}


class SellIn(BaseModel):
    symbol: str
    sell_price: float
    reason: str | None = None


class HoldIn(BaseModel):
    symbol: str
    reason: str | None = None


@router.post("/portfolio/sell")
def sell(body: SellIn):
    result = sell_holding(body.symbol, body.sell_price, body.reason)
    if not result:
        raise HTTPException(404, f"{body.symbol} not found in portfolio")
    return {"status": "ok", "trade": result}


class AddMoreIn(BaseModel):
    symbol: str
    quantity: int
    buy_price: float


@router.post("/portfolio/add-more")
def add_more(body: AddMoreIn):
    result = add_more_shares(body.symbol, body.quantity, body.buy_price)
    if not result:
        raise HTTPException(404, f"{body.symbol} not found in portfolio")
    return {"status": "ok", "result": result}


@router.post("/portfolio/hold")
def hold(body: HoldIn):
    result = hold_decision(body.symbol, body.reason)
    if not result:
        raise HTTPException(404, f"{body.symbol} not found in portfolio")
    return {"status": "ok", "decision": result}


@router.get("/portfolio/history")
def trade_history():
    return get_trade_history()


@router.get("/watchlist")
def watchlist():
    return get_watchlist()


@router.post("/watchlist")
def create_watchlist_item(body: WatchlistIn):
    try:
        row = add_to_watchlist(symbol=body.symbol, notes=body.notes)
        return {"status": "ok", "item": row}
    except Exception as e:
        if "UNIQUE" in str(e):
            raise HTTPException(400, f"{body.symbol} is already in your watchlist")
        raise HTTPException(400, str(e))


@router.delete("/watchlist/{symbol}")
def delete_watchlist_item(symbol: str):
    deleted = remove_from_watchlist(symbol)
    if not deleted:
        raise HTTPException(404, f"{symbol} not found in watchlist")
    return {"status": "ok", "symbol": symbol}


class AlertIn(BaseModel):
    symbol: str
    alert_type: str        # 'above' or 'below'
    target_price: float
    notes: str | None = None


@router.get("/alerts")
def list_alerts():
    return get_alerts()


@router.post("/alerts")
def create_price_alert(body: AlertIn):
    if body.alert_type not in ("above", "below"):
        raise HTTPException(400, "alert_type must be 'above' or 'below'")
    row = create_alert(
        symbol=body.symbol,
        alert_type=body.alert_type,
        target_price=body.target_price,
        notes=body.notes,
    )
    return {"status": "ok", "alert": row}


@router.delete("/alerts/{alert_id}")
def remove_alert(alert_id: int):
    deleted = delete_alert(alert_id)
    if not deleted:
        raise HTTPException(404, "Alert not found")
    return {"status": "ok", "id": alert_id}
