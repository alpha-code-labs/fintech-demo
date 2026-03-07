from fastapi import APIRouter

from app.calculations.macro import get_global_pulse
from app.fetchers.world_indices import fetch_world_indices
from app.fetchers.commodities import fetch_commodities
from app.fetchers.macro_indicators import fetch_macro_indicators
from app.fetchers.market_depth import fetch_market_depth

router = APIRouter()


@router.get("/macro")
def get_macro():
    return get_global_pulse()


@router.post("/macro/refresh")
def refresh_macro():
    """Trigger a fresh fetch of all external data sources.
    Call this periodically (e.g. daily cron) or manually."""
    results = {}
    for name, fn in [
        ("world_indices", fetch_world_indices),
        ("commodities", fetch_commodities),
        ("macro_indicators", fetch_macro_indicators),
        ("market_depth", fetch_market_depth),
    ]:
        try:
            data = fn(force=True)
            results[name] = "ok"
        except Exception as e:
            results[name] = f"error: {e}"
    return {"status": "done", "results": results}
