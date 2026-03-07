"""
LLM prompt builders and generators for stock summaries and briefing narratives.
"""
from app.llm.client import generate


# ── Stock AI Summary (Deep Dive, Screen 3) ────────────────────

def generate_stock_summary(stock_data: dict) -> str | None:
    """
    Generate a 2-3 sentence factual summary for a stock.
    Input: the full dict returned by get_stock_deep_dive().
    Returns None if LLM is unavailable.
    """
    prompt = _build_stock_prompt(stock_data)
    return generate(prompt, max_tokens=256)


def _build_stock_prompt(d: dict) -> str:
    symbol = d.get("symbol", "?")
    name = d.get("name", symbol)
    sector = d.get("sector", "?")
    price = d.get("price")

    t = d.get("technical", {})
    f = d.get("fundamentals", {})
    setups_data = d.get("setups", {})
    sc = d.get("sector_context", {})

    # Technical summary
    tech_points = []
    if t.get("above_30w_ma"):
        tech_points.append("above 30W MA")
    else:
        tech_points.append("below 30W MA")
    if t.get("above_52w_ma"):
        tech_points.append("above 52W MA")
    else:
        tech_points.append("below 52W MA")
    if t.get("golden_cross"):
        tech_points.append(f"golden cross ({t['golden_cross']})")
    rs = t.get("rs_vs_nifty_4w")
    if rs is not None:
        tech_points.append(f"RS vs Nifty {rs:+.1f}%")
    vol = t.get("vol_vs_avg")
    if vol is not None:
        tech_points.append(f"volume {vol:.1f}x avg")
    consol = t.get("consolidation_months", 0)
    if consol > 0:
        tech_points.append(f"{consol}-month consolidation breakout")

    # Fundamentals summary
    fund_points = []
    quarters = f.get("quarters", [])
    if quarters:
        latest_q = quarters[0]
        rev = latest_q.get("revenue_cr")
        pat = latest_q.get("net_profit_cr")
        margin = latest_q.get("operating_margin_pct")
        if rev is not None:
            fund_points.append(f"revenue ₹{rev:,.0f} Cr")
        if pat is not None:
            fund_points.append(f"PAT ₹{pat:,.0f} Cr")
        if margin is not None:
            fund_points.append(f"margin {margin:.1f}%")

    pe = f.get("pe")
    if pe is not None:
        fund_points.append(f"P/E {pe:.1f}")

    promoter = f.get("promoter_holding", [])
    if promoter:
        latest_prom = promoter[0]
        pct = latest_prom.get("promoter_pct")
        if pct is not None:
            fund_points.append(f"promoter {pct:.1f}%")

    # Setups
    setup_names = [s.get("setup", "") for s in setups_data.get("detected", [])]

    return f"""You are a factual investment research assistant. Write exactly 2-3 sentences summarizing this stock.
Be factual and specific — mention actual numbers. No opinions, no recommendations, no "buy/sell".

Stock: {name} ({symbol})
Sector: {sector}
Price: ₹{price:,.2f}

Technicals: {', '.join(tech_points)}
Fundamentals: {', '.join(fund_points) if fund_points else 'limited data'}
Setups detected: {', '.join(setup_names) if setup_names else 'none'}
Sector context: RS vs Nifty {sc.get('sector_rs_vs_nifty_4w', 'N/A')}%, {len(sc.get('peers_triggered', []))} peers triggered

Write the summary now. 2-3 sentences only. Factual. No disclaimer."""


# ── Weekly Briefing Narratives (Screen 5) ─────────────────────

def generate_briefing_narratives(context: dict) -> dict:
    """
    Generate world + india narrative paragraphs for the weekly briefing.
    Input: dict with world_indices, commodities, macro_indicators,
           indian_indices, market_depth, sector_heatmap, market_phase.
    Returns {"world": str, "india": str} or fallback strings if LLM unavailable.
    """
    world_text = _generate_world_narrative(context)
    india_text = _generate_india_narrative(context)

    return {
        "world": world_text or _fallback_world(context),
        "india": india_text or _fallback_india(context),
    }


def _generate_world_narrative(ctx: dict) -> str | None:
    world = ctx.get("world_indices", [])
    commod = ctx.get("commodities", [])
    macro = ctx.get("macro_indicators", {})

    lines = []
    for w in world:
        if w.get("value") is not None:
            chg = w.get("change_pct")
            chg_str = f" ({chg:+.1f}%)" if chg is not None else ""
            lines.append(f"{w['name']}: {w['value']:,.1f}{chg_str}")

    for c in commod:
        if c.get("value") is not None:
            chg = c.get("change_pct")
            chg_str = f" ({chg:+.1f}%)" if chg is not None else ""
            lines.append(f"{c['name']}: {c.get('unit','')}{c['value']:,.2f}{chg_str}")

    dxy = macro.get("dxy", {})
    if dxy.get("value"):
        lines.append(f"DXY: {dxy['value']} ({dxy.get('change_pct', 0):+.1f}%)")
    us10y = macro.get("us_10y", {})
    if us10y.get("value"):
        lines.append(f"US 10Y: {us10y['value']}%")

    if not lines:
        return None

    prompt = f"""You are a financial market analyst writing a weekly briefing. Write 2-3 sentences summarizing global markets this week.
Be concise and factual. Mention key moves and what drove them.

Data:
{chr(10).join(lines)}

Write the summary now. 2-3 sentences only. No disclaimer."""

    return generate(prompt, max_tokens=200)


def _generate_india_narrative(ctx: dict) -> str | None:
    indices = ctx.get("indian_indices", [])
    macro = ctx.get("macro_indicators", {})
    depth = ctx.get("market_depth", {})
    phase = ctx.get("market_phase", {})

    lines = []
    for idx in indices:
        chg = idx.get("change_pct")
        if chg is not None:
            lines.append(f"{idx['name']}: {idx.get('value', 0):,.0f} ({chg:+.1f}%)")

    ad = depth.get("ad_ratio") if depth else None
    if ad is not None:
        lines.append(f"A/D ratio: {ad:.1f}")

    fii = macro.get("fii_flow_mtd")
    dii = macro.get("dii_flow_mtd")
    if fii is not None:
        lines.append(f"FII flow: ₹{fii:,.0f} Cr")
    if dii is not None:
        lines.append(f"DII flow: ₹{dii:,.0f} Cr")

    india_10y = macro.get("india_10y", {})
    if india_10y.get("value"):
        lines.append(f"India 10Y: {india_10y['value']}%")

    if phase:
        lines.append(f"Market phase: {phase.get('label', 'N/A')}")

    if not lines:
        return None

    prompt = f"""You are a financial market analyst writing a weekly briefing for Indian markets. Write 2-3 sentences summarizing the week.
Be concise and factual. Mention Nifty movement, breadth, and key flows.

Data:
{chr(10).join(lines)}

Write the summary now. 2-3 sentences only. No disclaimer."""

    return generate(prompt, max_tokens=200)


# ── Fallback text (no LLM) ───────────────────────────────────

def _fallback_world(ctx: dict) -> str:
    """Build a data-only world summary when LLM is unavailable."""
    parts = []
    for w in ctx.get("world_indices", []):
        if w.get("value") is not None:
            chg = w.get("change_pct")
            chg_str = f" ({chg:+.1f}%)" if chg is not None else ""
            parts.append(f"{w['name']} at {w['value']:,.0f}{chg_str}")

    dxy = ctx.get("macro_indicators", {}).get("dxy", {})
    if dxy.get("value"):
        parts.append(f"DXY at {dxy['value']}")

    if not parts:
        return "Global market data unavailable."
    return ". ".join(parts) + "."


def _fallback_india(ctx: dict) -> str:
    """Build a data-only India summary when LLM is unavailable."""
    parts = []
    for idx in ctx.get("indian_indices", []):
        chg = idx.get("change_pct")
        if chg is not None:
            parts.append(f"{idx['name']} {chg:+.1f}%")

    macro = ctx.get("macro_indicators", {})
    fii = macro.get("fii_flow_mtd")
    dii = macro.get("dii_flow_mtd")
    if fii is not None:
        parts.append(f"FII ₹{fii:,.0f} Cr")
    if dii is not None:
        parts.append(f"DII ₹{dii:,.0f} Cr")

    phase = ctx.get("market_phase", {})
    if phase.get("label"):
        parts.append(f"Market phase: {phase['label']}")

    if not parts:
        return "Indian market data unavailable."
    return ". ".join(parts) + "."
