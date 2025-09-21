from src.core.risk_manager import RiskManager, RiskConfig


def test_scaffold_instantiates_and_allows():
    cfg = RiskConfig(dry_run=True, max_pos_usd=0.0, max_exposure_pct=0.0)
    rm = RiskManager(cfg)
    assert rm.check() is True
