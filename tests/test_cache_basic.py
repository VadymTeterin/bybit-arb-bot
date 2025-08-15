# tests/test_cache_basic.py
import asyncio

from src.core.cache import QuoteCache


def test_cache_update_and_snapshot():
    cache = QuoteCache()

    async def go():
        await cache.update("BTCUSDT", spot=65000.0)
        await cache.update("BTCUSDT", linear_mark=65200.0)
        snap = await cache.snapshot()
        assert "BTCUSDT" in snap
        spot, mark, ts = snap["BTCUSDT"]
        assert abs(spot - 65000.0) < 1e-9
        assert abs(mark - 65200.0) < 1e-9
        assert ts > 0

    asyncio.run(go())
