"""
Weekly Briefing Calculation Engine (M7).

Compiles real data from macro, scanner, and portfolio into the briefing
response shape. LLM generates narrative text for world/india sections.
Works without API key — falls back to data-only summaries.
"""
from app.calculations.macro import get_global_pulse
from app.calculations.scanner import run_scanner
from app.calculations.portfolio import get_portfolio
from app.llm.summaries import generate_briefing_narratives

# Map yfinance sector names → heatmap display names (matching macro.py SECTOR_INDICES)
_YFINANCE_TO_HEATMAP = {
    "Technology": "IT",
    "Healthcare": "Pharma",
    "Consumer Cyclical": "Auto",
    "Consumer Defensive": "FMCG",
    "Basic Materials": "Metal",
    "Real Estate": "Realty",
    "Energy": "Energy",
    "Communication Services": "Media",
    "Utilities": "PSU",
    "Industrials": "Infra",
    "Financial Services": "Bank Nifty",
}


def get_weekly_briefing() -> dict:
    """Build the weekly briefing from real data + optional LLM narratives."""

    # ── Gather real data ──────────────────────────────────────
    macro = get_global_pulse()
    scanner = run_scanner()
    portfolio = get_portfolio()

    # ── Week ending ───────────────────────────────────────────
    week_ending = scanner.get("week_ending", macro.get("date", ""))

    # ── Market phase ──────────────────────────────────────────
    phase = macro.get("market_phase", {})
    market_phase = phase.get("label", "N/A")

    # ── LLM narratives (or data-only fallback) ────────────────
    narratives = generate_briefing_narratives({
        "world_indices": macro.get("world_indices", []),
        "commodities": macro.get("commodities", []),
        "macro_indicators": macro.get("macro_indicators", {}),
        "indian_indices": macro.get("indian_indices", []),
        "market_depth": macro.get("market_depth", {}),
        "sector_heatmap": macro.get("sector_heatmap", []),
        "market_phase": phase,
    })

    # ── Top signals from scanner ──────────────────────────────
    signals = scanner.get("signals", [])
    new_signals_count = scanner.get("stocks_triggered", 0)
    top_signals = _build_top_signals(signals[:3])

    # ── Sectors from heatmap + scanner trigger counts ─────────
    sectors = _build_sector_notes(macro.get("sector_heatmap", []), signals)

    # ── Portfolio alerts ──────────────────────────────────────
    portfolio_alerts = _build_portfolio_alerts(portfolio)

    return {
        "week_ending": week_ending,
        "market_phase": market_phase,
        "market_phase_change": phase.get("reason", ""),
        "world": narratives["world"],
        "india": narratives["india"],
        "sectors": sectors,
        "new_signals_count": new_signals_count,
        "top_signals": top_signals,
        "portfolio_alerts": portfolio_alerts,
    }


def _build_sector_notes(heatmap: list[dict], signals: list[dict] | None = None) -> list[dict]:
    """Build sector notes from heatmap data + scanner trigger counts per sector."""
    if not heatmap:
        return []

    # Count triggered stocks per sector from scanner signals
    # Map yfinance sector names to heatmap display names
    sector_trigger_counts: dict[str, int] = {}
    if signals:
        for sig in signals:
            yf_sector = sig.get("sector", "Unknown")
            display_name = _YFINANCE_TO_HEATMAP.get(yf_sector, yf_sector)
            sector_trigger_counts[display_name] = sector_trigger_counts.get(display_name, 0) + 1

    sectors = []
    for i, s in enumerate(heatmap):
        name = s.get("name", "?")
        change = s.get("change_pct")
        rs = s.get("rs_vs_nifty_4w")
        triggered = sector_trigger_counts.get(name, 0)

        triggered_text = f" {triggered} stock{'s' if triggered != 1 else ''} triggered." if triggered > 0 else ""

        if change is None:
            note = "Data unavailable"
        elif i == 0:
            note = (f"Strongest. RS {rs:+.1f}% vs Nifty." if rs is not None else f"Leading ({change:+.1f}% this week).") + triggered_text
        elif i == len(heatmap) - 1:
            note = (f"Weakest. RS {rs:+.1f}% vs Nifty." if rs is not None else f"Lagging ({change:+.1f}% this week).") + triggered_text
        elif rs is not None and rs > 2:
            note = f"Emerging strength. RS {rs:+.1f}% vs Nifty." + triggered_text
        elif rs is not None and rs < -2:
            note = f"Weakening. RS {rs:+.1f}% vs Nifty." + triggered_text
        else:
            note = f"{change:+.1f}% this week." + triggered_text

        sectors.append({"name": name, "note": note, "triggered": triggered})

    # Return top 3 most interesting: strongest, weakest, and one emerging
    if len(sectors) <= 3:
        return sectors

    result = [sectors[0]]  # strongest
    # Find an emerging one (middle with notable RS or triggered stocks)
    for s in sectors[1:-1]:
        if "Emerging" in s["note"] or "Weakening" in s["note"] or s["triggered"] > 0:
            result.append(s)
            break
    else:
        if len(sectors) > 2:
            result.append(sectors[1])
    result.append(sectors[-1])  # weakest
    return result


def _build_top_signals(signals: list[dict]) -> list[dict]:
    """Format top scanner signals for briefing."""
    result = []
    for s in signals:
        sigs = s.get("signals", {})
        note_parts = []
        if sigs.get("consolidation_months", 0) > 0:
            note_parts.append(f"{sigs['consolidation_months']}-month breakout")
        if sigs.get("golden_cross"):
            note_parts.append("golden cross")
        if sigs.get("sector_index_outperforming"):
            note_parts.append("sector momentum")
        if sigs.get("rs_vs_nifty_4w", 0) > 5:
            note_parts.append(f"RS +{sigs['rs_vs_nifty_4w']:.0f}%")
        if not note_parts:
            note_parts.append(f"score {s.get('score', 0)}/8")

        result.append({
            "symbol": s["symbol"],
            "name": s.get("name", s["symbol"]),
            "sector": s.get("sector", "Unknown"),
            "score": s.get("score", 0),
            "note": ", ".join(note_parts),
        })
    return result


def _build_portfolio_alerts(portfolio: dict) -> list[dict]:
    """Extract portfolio warnings and alerts for briefing."""
    alerts = []
    holdings = portfolio.get("holdings", {})

    for h in holdings.get("alert", []):
        sig_count = len(h.get("signals", []))
        alerts.append({
            "symbol": h["symbol"],
            "name": h.get("name", h["symbol"]),
            "level": "alert",
            "note": f"{sig_count} exit signal{'s' if sig_count != 1 else ''}. Review immediately.",
        })

    for h in holdings.get("warning", []):
        sig_count = len(h.get("signals", []))
        alerts.append({
            "symbol": h["symbol"],
            "name": h.get("name", h["symbol"]),
            "level": "warning",
            "note": f"{sig_count} early signal{'s' if sig_count != 1 else ''}. Watch closely.",
        })

    return alerts
