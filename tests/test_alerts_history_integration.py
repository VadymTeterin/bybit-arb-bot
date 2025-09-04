# tests/test_alerts_history_integration.py
import time
from pathlib import Path

import pytest

from src.core.alerts import RealtimeAlerter, AlerterConfig
from src.infra.alerts_repo import SqliteAlertGateRepo
from src.core import alerts_hook


@pytest.mark.asyncio
async def test_alerts_history_written_after_successful_send(tmp_path: Path):
    # 1) ізолюємо репозиторій історії на тимчасовий файл
    db_path = tmp_path / "alerts.db"
    alerts_hook._repo = SqliteAlertGateRepo.from_settings(str(db_path))  # type: ignore[attr-defined]

    # 2) готуємо алертер і фейковий sender
    symbol = "BTCUSDT"
    ts_epoch = time.time()
    sent = {"ok": False}

    async def dummy_sender(text: str) -> None:
        sent["ok"] = True

    alerter = RealtimeAlerter(
        AlerterConfig(enable_alerts=True, cooldown_sec=0),
        sender=dummy_sender,
    )

    # 3) шлемо — має спрацювати
    ok = await alerter.maybe_send(
        symbol=symbol,
        spot_price=100.0,
        mark_price=101.0,
        basis_pct=1.0,
        vol24h_usd=10_000_000.0,
        ts=ts_epoch,
    )
    assert ok and sent["ok"]

    # 4) перевіряємо, що історія поповнилася
    recent = alerts_hook._repo.get_recent(symbol=symbol, limit=5)
    assert len(recent) >= 1
    assert recent[0].symbol == symbol
    assert abs(recent[0].basis_pct - 1.0) < 1e-9
