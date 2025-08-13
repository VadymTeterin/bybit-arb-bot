from src.main import preview_message

def test_alerts_preview_basic():
    txt = preview_message("BTCUSDT", 50000.0, 50500.0, vol=2_000_000.0, threshold=0.5)
    # Повідомлення має містити символ та якусь %-метрику (точне форматування може відрізнятися)
    assert "BTCUSDT" in txt
    assert "%" in txt
    assert len(txt.strip()) > 0
