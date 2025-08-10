# tests/test_price_pair.py
import types
import src.main as app


class FakeRest:
    """Мінімальний двійник BybitRest для price:pair."""
    def __init__(self, spot_prices: dict[str, float], fut_prices: dict[str, float]):
        # будуємо мапи у форматі, який очікує команда (з ключем 'price')
        self._spot_map = {s: {"price": p} for s, p in spot_prices.items()}
        self._lin_map = {s: {"price": p} for s, p in fut_prices.items()}

    def get_spot_map(self):
        return self._spot_map

    def get_linear_map(self):
        return self._lin_map


def test_price_pair_single_symbol(monkeypatch, capsys):
    # ETH є і на SPOT, і на LINEAR
    monkeypatch.setattr(
        app,
        "BybitRest",
        lambda: FakeRest({"ETHUSDT": 3000.0}, {"ETHUSDT": 3010.0}),
    )

    ns = types.SimpleNamespace(symbol=["ETHUSDT"])
    rc = app.cmd_price_pair(ns)
    assert rc == 0

    out, _ = capsys.readouterr()
    assert "ETHUSDT" in out
    assert "spot=3000" in out
    assert "fut=3010" in out
    assert "basis=" in out


def test_price_pair_multiple_symbols(monkeypatch, capsys):
    # ETH/BTC є, XRP відсутній — має з’явитися повідомлення "not found"
    monkeypatch.setattr(
        app,
        "BybitRest",
        lambda: FakeRest(
            {"ETHUSDT": 3000.0, "BTCUSDT": 65000.0},
            {"ETHUSDT": 3010.0, "BTCUSDT": 65300.0},
        ),
    )

    ns = types.SimpleNamespace(symbol=["ETHUSDT", "BTCUSDT", "XRPUSDT"])
    rc = app.cmd_price_pair(ns)
    assert rc == 0

    out, _ = capsys.readouterr()
    assert "ETHUSDT  spot=3000" in out
    assert "BTCUSDT  spot=65000" in out
    assert "XRPUSDT: not found on SPOT or LINEAR" in out


def test_price_pair_default_symbols(monkeypatch, capsys):
    # символи не задані — мають використатися дефолтні ETH/BTC
    monkeypatch.setattr(
        app,
        "BybitRest",
        lambda: FakeRest(
            {"ETHUSDT": 3000.0, "BTCUSDT": 65000.0},
            {"ETHUSDT": 3010.0, "BTCUSDT": 65300.0},
        ),
    )

    ns = types.SimpleNamespace(symbol=None)
    rc = app.cmd_price_pair(ns)
    assert rc == 0

    out, _ = capsys.readouterr()
    assert "ETHUSDT" in out
    assert "BTCUSDT" in out


def test_price_pair_no_data_anywhere(monkeypatch, capsys):
    # Повна відсутність даних на SPOT та LINEAR -> для кожного символу "not found"
    monkeypatch.setattr(app, "BybitRest", lambda: FakeRest({}, {}))

    ns = types.SimpleNamespace(symbol=["ETHUSDT", "BTCUSDT"])
    rc = app.cmd_price_pair(ns)
    assert rc == 0

    out, _ = capsys.readouterr()
    assert "ETHUSDT: not found on SPOT or LINEAR" in out
    assert "BTCUSDT: not found on SPOT or LINEAR" in out
