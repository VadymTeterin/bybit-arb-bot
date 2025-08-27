from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

try:
    from loguru import logger  # type: ignore
except Exception:  # pragma: no cover
    import logging

    logger = logging.getLogger(__name__)

from src.core.alerts_gate import AlertGate
from src.infra.config import get_settings
from src.infra.notify_telegram import send_telegram
from src.telegram.formatters import format_arbitrage_alert

_SETTINGS = get_settings()
_GATE = AlertGate.from_settings(_SETTINGS)


def _to_float(value: Any, default: float = 0.0) -> float:
    """Safe float conversion with default."""
    try:
        if value is None:
            return default
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _to_str(value: Any, default: str = "") -> str:
    """Safe str conversion with default."""
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default


def send_arbitrage_alert(signal: Any, enabled: bool = True) -> bool:
    """
    Build message and send it to Telegram through adapter, guarded by AlertGate.
    Returns False if disabled/missing fields or suppressed by cooldown/near-duplicate rules.
    """
    if not enabled or signal is None:
        return False

    # Gather expected fields for formatter (robust to legacy names)
    symbol_spot = (
        getattr(signal, "symbol_spot", None)
        or getattr(signal, "symbol_a", None)
        or getattr(signal, "base", None)
        or ""
    )
    symbol_linear = (
        getattr(signal, "symbol_linear", None)
        or getattr(signal, "symbol_b", None)
        or getattr(signal, "quote", None)
        or ""
    )

    spread_pct = _to_float(getattr(signal, "spread_pct", 0.0), 0.0)
    vol_24h = _to_float(getattr(signal, "vol_24h", getattr(signal, "vol24h", 0.0)), 0.0)
    basis = _to_float(getattr(signal, "basis", getattr(signal, "basis_pct", 0.0)), 0.0)

    # Choose a per-symbol key for gate (prefer futures/linear, fallback to spot)
    symbol_key = (str(symbol_linear) or str(symbol_spot)).upper().strip()
    if not symbol_key:
        # Without a symbol id there's nothing to rate-limit
        logger.info("Suppressed alert: missing symbol key")
        return False

    # Cooldown + near-duplicate suppression
    now = datetime.now(timezone.utc)
    allow, reason = _GATE.should_send(symbol_key, basis, now)
    if not allow:
        logger.info("Suppressed %s: %s", symbol_key, reason)
        return False

    # Build final text and send
    params: Dict[str, Any] = {
        "symbol_spot": _to_str(symbol_spot),
        "symbol_linear": _to_str(symbol_linear),
        "spread_pct": spread_pct,
        "vol_24h": vol_24h,
        "basis": basis,
    }
    text = format_arbitrage_alert(**params)  # type: ignore[call-arg]

    ok = send_telegram(text, enabled=True)
    if ok:
        _GATE.commit(symbol_key, basis, now)
    else:
        logger.warning("Telegram send failed for %s (no commit)", symbol_key)
    return ok
