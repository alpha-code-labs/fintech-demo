"""
News-based setup detection using Google News RSS + Gemini LLM.

P1 item 10 from pending-list.md (Steps 44-46 from databuilder.md).

Detects 3 news-driven setups:
  1. Management Change — board changes, key appointments, CEO/CFO exits
  2. Supply Disruption — factory shutdowns, trade restrictions, disasters
  3. Forced Buying/Selling — index rebalancing, large block deals, promoter issues

Flow: Google News RSS (free) → headlines → Gemini classification → structured result.
24h in-memory cache per stock.
"""
import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from html import unescape
from urllib.parse import quote

import requests

from app.llm.client import generate

logger = logging.getLogger(__name__)

_news_setup_cache: dict[str, tuple] = {}  # {symbol: (result_dict, timestamp)}
_CACHE_TTL = timedelta(hours=24)
_NEWS_TIMEOUT = 10


def detect_news_setups(symbol: str, company_name: str, sector: str) -> dict:
    """Detect news-based setups for a stock.

    Returns dict with keys: management_change, supply_disruption, forced_buying.
    Each value is either None (not detected) or a dict with 'detail' string.
    """
    now = datetime.now()
    if symbol in _news_setup_cache:
        cached, ts = _news_setup_cache[symbol]
        if now - ts < _CACHE_TTL:
            return cached

    result = {
        "management_change": None,
        "supply_disruption": None,
        "forced_buying": None,
    }

    # Fetch headlines
    headlines = _fetch_news_headlines(company_name, symbol)

    if not headlines:
        _news_setup_cache[symbol] = (result, now)
        return result

    # Ask LLM to classify
    llm_result = _classify_headlines(symbol, company_name, sector, headlines)
    if llm_result:
        result.update(llm_result)

    _news_setup_cache[symbol] = (result, now)
    return result


def _fetch_news_headlines(company_name: str, symbol: str) -> list[str]:
    """Fetch recent news headlines from Google News RSS."""
    # Clean company name for search (remove suffixes like "Limited", "Ltd")
    clean_name = company_name
    for suffix in [" Limited", " Ltd.", " Ltd", " Industries", " Corporation"]:
        clean_name = clean_name.replace(suffix, "")
    clean_name = clean_name.strip()

    query = f"{clean_name} {symbol} NSE stock"
    url = (
        f"https://news.google.com/rss/search?"
        f"q={quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"
    )

    try:
        resp = requests.get(url, timeout=_NEWS_TIMEOUT, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        })
        if resp.status_code != 200:
            logger.debug(f"Google News RSS returned {resp.status_code} for {symbol}")
            return []

        root = ET.fromstring(resp.content)
        items = root.findall(".//item")

        headlines = []
        for item in items[:15]:  # last 15 headlines
            title = item.findtext("title", "")
            if title:
                headlines.append(unescape(title.strip()))

        logger.debug(f"Fetched {len(headlines)} headlines for {symbol}")
        return headlines

    except Exception as e:
        logger.debug(f"News fetch failed for {symbol}: {e}")
        return []


def _classify_headlines(
    symbol: str, company_name: str, sector: str, headlines: list[str]
) -> dict | None:
    """Use Gemini to classify headlines into setup categories."""
    headlines_text = "\n".join(f"- {h}" for h in headlines)

    prompt = f"""You are a stock market analyst. Given recent news headlines for {company_name} ({symbol}), a {sector} company on the Indian NSE exchange, classify them into exactly 3 categories.

Headlines:
{headlines_text}

For EACH category, respond with either a brief 1-sentence finding or "none":

1. MANAGEMENT_CHANGE: Any board-level changes, CEO/CFO/MD appointments or exits, key management reshuffles, or leadership transitions. Only flag actual changes, not speculation.

2. SUPPLY_DISRUPTION: Factory shutdowns, production halts, raw material shortages, trade restrictions, sanctions, regulatory bans, natural disasters affecting operations, or supply chain disruptions. Must directly affect this company or its sector.

3. FORCED_BUYING: Index rebalancing (MSCI, Nifty, Sensex additions/removals), large institutional block deals, promoter pledge invocations, margin calls, or regulatory-forced transactions.

Respond in this exact JSON format only, no other text:
{{"management_change": "finding or null", "supply_disruption": "finding or null", "forced_buying": "finding or null"}}"""

    raw = generate(prompt, max_tokens=300)
    if not raw:
        return None

    try:
        # Extract JSON from response (LLM may wrap in markdown)
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        parsed = json.loads(text)

        result = {}
        for key in ["management_change", "supply_disruption", "forced_buying"]:
            val = parsed.get(key)
            if val and val != "null" and val.lower() != "none":
                result[key] = {"detail": str(val)}
            else:
                result[key] = None

        return result

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.debug(f"Failed to parse LLM news classification for {symbol}: {e}")
        return None
