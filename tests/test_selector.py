from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from importlib import reload

from src.core import selector
from src.storage import persistence


class _FakeBybitRest:
    """
    Мінімальний фейк клієнта BybitRest для тестів селектора.
    Повертає SPOT/LINEAR мапи у форматі, який споживає selector._basis_candidates().
    """

    def __init__(self, spot_map, linear_map):
        self._spot = spot_map
        self._lin = linear_map

    def get_spot_map(self):
        return self._spot

    def get_linear_map(self):
        return self._lin


def _reset_db(db_path: str):
    os.environ["DB_PATH"] = db_path
    reload(persistence)  # щоб persistence «побачив» новий шлях
    persistence.init_db()


def test_selector_basic_saves_and_respects_limit(tmp_path):
    db = tmp_path / "sel1.db"
    _reset_db(str(db))

    # Дані: 3 символи — один неліківідний, 2 валідні з різним basis
    spot = {
        "AAAUSDT": {"price": 2.0, "turnover_usd": 12_000_000},
        "BBBUSDT": {"price": 3.0, "turnover_usd": 25_000_000},
        "PENNYUSDT": {
            "price": 0.0001,
            "turnover_usd": 100_000,
        },  # має відсіктись за ціною/обігом
    }
    linear = {
        "AAAUSDT": {"price": 2.04, "turnover_usd": 11_000_000},  # basis ~ 2%
        "BBBUSDT": {"price": 3.09, "turnover_usd": 30_000_000},  # basis ~ 3%
        "PENNYUSDT": {"price": 0.00011, "turnover_usd": 200_000},
    }

    fake = _FakeBybitRest(spot, linear)

    saved = selector.run_selection(
        min_vol=10_000_000,
        min_price=0.001,
        threshold=1.0,
        limit=1,  # має зберегти лише ТОП-1 за |basis|
        cooldown_sec=0,  # щоб не вплинув
        client=fake,
    )

    # Перевірка: збережено рівно 1 запис — BBBUSDT (вищий basis)
    assert len(saved) == 1
    assert saved[0]["symbol"] == "BBBUSDT"

    rows = persistence.get_signals(last_hours=24, limit=10)
    assert len(rows) == 1
    assert rows[0]["symbol"] == "BBBUSDT"


def test_selector_respects_cooldown(tmp_path):
    db = tmp_path / "sel2.db"
    _reset_db(str(db))

    # Початково збережемо свіжий сигнал для AAAUSDT
    now = datetime.now(timezone.utc)
    persistence.save_signal(
        "AAAUSDT", 2.0, 2.02, 1.0, 12_000_000, now - timedelta(seconds=30)
    )

    # Ті ж дані, AAA знов проходить пороги — але має відсіятись кулдауном
    spot = {
        "AAAUSDT": {"price": 2.0, "turnover_usd": 12_000_000},
        "BBBUSDT": {"price": 3.0, "turnover_usd": 25_000_000},
    }
    linear = {
        "AAAUSDT": {"price": 2.04, "turnover_usd": 11_000_000},  # basis ~ 2%
        "BBBUSDT": {
            "price": 3.00,
            "turnover_usd": 26_000_000,
        },  # basis ~ 0% (не пройде threshold 1.0)
    }
    fake = _FakeBybitRest(spot, linear)

    saved = selector.run_selection(
        min_vol=10_000_000,
        min_price=0.001,
        threshold=1.0,
        limit=5,
        cooldown_sec=300,  # 5 хвилин
        client=fake,
    )

    # AAAUSDT підходить за метриками, але був сигнал 30 сек тому — новий НЕ збережеться
    assert saved == [] or all(row["symbol"] != "AAAUSDT" for row in saved)

    rows = persistence.get_signals(last_hours=24, limit=10)
    # Лише той попередній (seed) запис
    assert len(rows) == 1
    assert rows[0]["symbol"] == "AAAUSDT"


def test_selector_threshold_filters_out(tmp_path):
    db = tmp_path / "sel3.db"
    _reset_db(str(db))

    # basis у всіх < 1.0% => ніхто не повинен зберегтись
    spot = {
        "XUSDT": {"price": 10.0, "turnover_usd": 20_000_000},
        "YUSDT": {"price": 5.0, "turnover_usd": 15_000_000},
    }
    linear = {
        "XUSDT": {"price": 10.05, "turnover_usd": 22_000_000},  # ~0.5%
        "YUSDT": {"price": 5.04, "turnover_usd": 16_000_000},  # ~0.8%
    }
    fake = _FakeBybitRest(spot, linear)

    saved = selector.run_selection(
        min_vol=10_000_000,
        min_price=0.001,
        threshold=1.0,  # поріг 1%
        limit=5,
        cooldown_sec=0,
        client=fake,
    )
    assert saved == []

    rows = persistence.get_signals(last_hours=24, limit=10)
    assert rows == []
