# tests/test_backoff.py
from src.exchanges.bybit.ws import exp_backoff_with_jitter

def test_backoff_monotonic_cap():
    # jitter робить значення не детермінованим, але межі можемо перевірити
    vals = [exp_backoff_with_jitter(i, base=1.0, cap=8.0) for i in range(1, 6)]
    # межі по степенях двійки з урахуванням jitter [delay/2, delay]
    bounds = [1.0, 2.0, 4.0, 8.0, 8.0]
    for v, d in zip(vals, bounds):
        assert 0.5 * d <= v <= d
