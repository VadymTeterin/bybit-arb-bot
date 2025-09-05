# tests/test_alerts_repo_history.py

import os
import time
from pathlib import Path

from src.infra.alerts_repo import SqliteAlertGateRepo


def _tmp_db(name: str) -> str:
    Path("dev/tmp").mkdir(parents=True, exist_ok=True)
    return f"dev/tmp/{name}-{int(time.time()*1000)}.db"


def test_history_log_and_last_kept_separately():
    db_path = _tmp_db("alerts")
    repo = SqliteAlertGateRepo.from_settings(db_path)

    # 1) last is empty at start
    assert repo.get_last("BTCUSDT") is None

    # 2) set_last does not require log
    repo.set_last("BTCUSDT", ts=time.time() - 5, basis_pct=1.23)
    last1 = repo.get_last("BTCUSDT")
    assert isinstance(last1, tuple)
    last_ts, last_basis = last1
    assert last_basis == 1.23

    # 3) log_event appends history
    rid1 = repo.log_event("BTCUSDT", ts_epoch=time.time(), basis_pct=1.25, reason="sent", tg_msg_id="42")
    rid2 = repo.log_event("BTCUSDT", ts_epoch=time.time() + 1, basis_pct=1.40, reason="sent", tg_msg_id="43")
    assert rid1 > 0 and rid2 > 0

    # 4) recent must have two rows, ordered desc
    recent = repo.get_recent(limit=10, symbol="BTCUSDT")
    assert len(recent) == 2
    assert recent[0].symbol == "BTCUSDT"
    assert recent[0].ts >= recent[1].ts

    # 5) set_last updates pointer, history remains
    repo.set_last("BTCUSDT", ts=time.time(), basis_pct=1.40)
    last2 = repo.get_last("BTCUSDT")
    assert last2 is not None and abs(last2[1] - 1.40) < 1e-9

    # sanity: sqlite file exists
    assert os.path.exists(db_path)
