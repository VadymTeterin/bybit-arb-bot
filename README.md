# Bybit Arbitrage Bot

Бот для моніторингу арбітражних можливостей між спотом та ф'ючерсами на біржі Bybit.

## Фази розробки

### Phase #1 — Початкове налаштування
1.1 Ініціалізація проєкту  
1.2 Налаштування логування

### Phase #2 — Підключення біржі Bybit
2.1 REST API  
2.2 WebSocket API

### Phase #3 — Логіка обчислення Basis
3.1 Формули та відбір  
3.2 Фільтрація результатів

### Phase #4 — Інтеграція Telegram
4.1 Форматування повідомлень  
4.2 Відправка повідомлень  
4.3 Команда basis:alert  
4.4 Тести форматерів  
4.5 Інтеграційні тести

### Phase #5 — Funding та WS-алерти
5.1 Funding API  
5.2 Відображення funding у CLI  
5.3 WS-алерти з Funding

## Запуск
```powershell
# Активація віртуального середовища
& .venv/Scripts/Activate.ps1

# Запуск WebSocket клієнта
python -m src.main ws:run

# Попередній перегляд алерту
python -m src.main alerts:preview --symbol BTCUSDT --spot 62850.12 --mark 62823.44 --vol 2100000000
```
