from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.storage import persistence


def get_top_signals(last_hours: int = 24, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Забирає сигнали за останні last_hours годин і повертає top N
    за спаданням basis_pct (це вже робить persistence.get_signals).
    """
    limit = int(limit) if limit is not None else None
    return persistence.get_signals(last_hours=last_hours, limit=limit)


def format_report(signals: List[Dict[str, Any]], now: Optional[datetime] = None) -> str:
    """
    Повертає готовий багаторядковий текст для відправки в Telegram або для CLI.
    """
    if not signals:
        return "No signals for selected period."

    if now is None:
        now = datetime.utcnow()

    lines = [f"📊 Arbitrage Report • {now:%Y-%m-%d %H:%M:%S} UTC", ""]
    for i, s in enumerate(signals, 1):
        sym = s.get("symbol", "-")
        sp = s.get("spot_price", "-")
        fu = s.get("futures_price", "-")
        b = s.get("basis_pct", 0.0)
        vol = s.get("volume_24h_usd", 0.0)
        ts = s.get("timestamp")
        sign = "+" if float(b) >= 0 else ""
        lines.append(
            f"{i}. {sym}  spot={sp:g}  fut={fu:g}  basis={sign}{float(b):.2f}%  24hVol=${float(vol):,.0f}  ts={ts}"
        )
    return "\n".join(lines)
