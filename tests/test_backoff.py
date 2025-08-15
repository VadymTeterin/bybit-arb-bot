# tests/test_backoff.py
from src.exchanges.bybit.ws import exp_backoff_with_jitter


def test_backoff_monotonic_and_cap():
    # Перевіряємо, що значення в межах очікуваних діапазонів (з урахуванням jitter)
    base = 1.0
    cap = 8.0
    targets = [1.0, 2.0, 4.0, 8.0, 8.0]  # 1,2,4,8,8 (cap)
    vals = [exp_backoff_with_jitter(i, base=base, cap=cap) for i in range(1, 6)]
    for v, t in zip(vals, targets):
        # з jitter значення у [t/2, t]
        assert (t * 0.5) <= v <= t
