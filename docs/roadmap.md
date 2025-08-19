# Implementation Roadmap — bybit-arb-bot

## Мета релізу 5.8.3 — WS Bybit MUX
Зібрати та уніфікувати стріми Bybit SPOT/LINEAR, стабільний ре-конект із backoff, мінімальний шум у логах, базові метрики потоку, інтеграція зі сповіщеннями.

Гілка: `step-5.8.3-ws-bybit-mux`

### Зроблено
- [x] Підключення двох WS: `wss://stream.bybit.com/v5/public/spot` та `.../linear`.
- [x] Нормалізація подій `tickers.*` (SPOT/LINEAR) + MUX в єдину шинку.
- [x] Дебаг-лічильники нормалізованих подій у `main.py` (лог: `SPOT/LINEAR normalized: channel=... symbol=... items=...`).
- [x] Експоненційний backoff із обмеженням (no-overshoot), легасі-сумісний.
- [x] CLI-команди `env`, `ws:run` (перевірка конфігів і запуск WS).
- [x] Конфіг через ENV: `WS_SUB_TOPICS_LINEAR/SPOT`, `WS_RECONNECT_MAX_SEC`, `RT_META_REFRESH_SEC`, `RT_LOG_PASSES`, тощо.
- [x] Pre-commit: ruff, ruff-format, isort + тести (`pytest`) інтегровані в локальний цикл.
- [x] Тестовий набір покриття `src.main`: **103 passed, 1 skipped** (остання сесія).

### У процесі / Далі по 5.8.3
- [ ] Прибрати шум **`channel=other symbol=`** із WS (системні/ack-повідомлення) — відфільтрувати до MUX або понизити рівень до TRACE.
- [ ] Throttling логів нормалізатора: агрегувати лічильники та друкувати 1 раз/сек (або `RT_LOG_PASSES`), щоб уникнути флуду.
- [ ] Перевірити дедуплікацію подій (виявити можливі повтори від провайдера/буфера) і, за потреби, додати idempotency-ключ.
- [ ] Пер-символьні метрики: подій/сек, ковзні середні, окремо для SPOT/LINEAR (готовити ґрунт для алертів).
- [ ] `AlertsSubscriber`: звʼязати MUX → калькінг спредів/дельт, повага до `ALLOW_SYMBOLS`/`DENY_SYMBOLS`, `MIN_VOL_24H_USD`, `MIN_PRICE`.
- [ ] Юніт-тести на нормалізатор MUX (фікстури фреймів Bybit SPOT/LINEAR: ticker, subscribe, pong, тощо).
- [ ] Документація по `.env` прикладу для WS-топіків (див. нижче).

### Вихідні критерії 5.8.3
- [ ] Стабільний `ws:run` ≥ 1 год без ручних втручань (0 фатальних реконектів).
- [ ] Логи без флуда (≤ 1 рядок/символ/сек на DEBUG).
- [ ] Метрики подій доступні в логах/консолі; видно навантаження по SPOT/LINEAR.
- [ ] Юніт-тести нормалізації додані та пройдені.
- [ ] `AlertsSubscriber` отримує і використовує події з MUX (мінімальний сценарій).

---

## Конфігурація (швидке нагадування)
```text
WS_PUBLIC_URL_LINEAR = wss://stream.bybit.com/v5/public/linear
WS_PUBLIC_URL_SPOT   = wss://stream.bybit.com/v5/public/spot
WS_SUB_TOPICS_LINEAR = tickers.BTCUSDT,tickers.ETHUSDT
WS_SUB_TOPICS_SPOT   = tickers.BTCUSDT,tickers.ETHUSDT
WS_RECONNECT_MAX_SEC = 30
RT_META_REFRESH_SEC  = 30
RT_LOG_PASSES        = 1
