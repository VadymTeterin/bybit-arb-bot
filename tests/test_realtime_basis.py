# tests/test_realtime_basis.py
import asyncio
import math

from src.core.cache import QuoteCache


def test_basis_computed_and_candidates_filters():
    cache = QuoteCache()

    async def go():
        # 1) Спочатку оновлюємо лише SPOT — basis ще невідомий (NaN)
        await cache.update("BTCUSDT", spot=50000.0)
        snap1 = await cache.snapshot_extended()
        # snap_ext tuple: (spot, linear_mark, basis_pct, ts_spot, ts_linear, ts_basis)
        assert math.isnan(snap1["BTCUSDT"][2])  # basis is NaN until both prices known

        # 2) Додаємо linear mark — basis стає > 0 (50500-50000)/50000*100 = 1%
        await cache.update("BTCUSDT", linear_mark=50500.0)
        snap2 = await cache.snapshot_extended()
        basis = snap2["BTCUSDT"][2]
        assert basis > 0

        # 3) Кандидати мають пройти поріг 0.5%
        rows = await cache.candidates(threshold_pct=0.5, min_price=1.0, min_vol24h_usd=0.0)
        assert any(sym == "BTCUSDT" for sym, _ in rows)

        # 4) Відсікаємо мінімальною ціною
        rows2 = await cache.candidates(threshold_pct=0.5, min_price=60000.0, min_vol24h_usd=0.0)
        assert not rows2

        # 5) Перевіряємо фільтр за обсягом
        await cache.update_vol24h("BTCUSDT", 1_000_000.0)
        rows3 = await cache.candidates(threshold_pct=0.5, min_price=1.0, min_vol24h_usd=2_000_000.0)
        assert not rows3

        # 6) Підвищуємо обсяг — тепер має пройти
        await cache.update_vol24h("BTCUSDT", 3_000_000.0)
        rows4 = await cache.candidates(threshold_pct=0.5, min_price=1.0, min_vol24h_usd=2_000_000.0)
        assert rows4 and rows4[0][0] == "BTCUSDT"

    asyncio.run(go())
