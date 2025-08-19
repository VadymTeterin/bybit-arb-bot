# КРОК 5.8 — WS Multiplexer + інтеграція Bybit WS

Цей підкрок додає легкий мультиплексор для маршрутизації WS-подій (SPOT/LINEAR тощо) без мережевої логіки
та інтегрує його у поточну архітектуру (Bridge, Subscriber).

## Що входить
- `src/ws/multiplexer.py` — потокобезпечний роутер подій з підтримкою `*` (wildcards).
- `src/ws/bridge.py` — публікація подій Bybit в мультиплексор.
- `src/ws/subscribers/alerts_subscriber.py` — простий підписник, який генерує алерти в Telegram.
- `src/core/selector.py` — відбір пар для арбітражу (allow/deny, depth, cooldown).
- `src/main.py` — CLI та інтеграція WS/RT-режиму.

## Як перевірити
1. Встановити залежності та активувати venv.
2. Запустити тести: `pytest -q` — має бути **57 passed**.
3. Перевірити формат та хуки: `pre-commit run --all-files`.

## Швидкий старт для RT
```bash
python -m src.main rt:run
```
(потрібні змінні оточення з `.env`).

## Примітки
- Мультиплексор не залежить від `asyncio`, його легко мокати в тестах.
- `publish_bybit_ticker(...)` формує уніфіковану подію `WsEvent` для SPOT/LINEAR.
