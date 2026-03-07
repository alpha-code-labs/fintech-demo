from app.fetchers.world_indices import fetch_world_indices
from app.fetchers.commodities import fetch_commodities
from app.fetchers.macro_indicators import fetch_macro_indicators
from app.fetchers.market_depth import fetch_market_depth

__all__ = [
    "fetch_world_indices",
    "fetch_commodities",
    "fetch_macro_indicators",
    "fetch_market_depth",
]
