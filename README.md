
# Bybit Arbitrage Bot (MVP)

## Опис
Бот для моніторингу цін на Bybit (SPOT та ф'ючерси) та пошуку можливостей арбітражу.  
Реалізовані функції:
- Перевірка з'єднання з API Bybit
- Отримання топових торгових пар за різницею SPOT / Futures
- Сканування та збереження сигналів у SQLite
- Надсилання алертів у Telegram
- Формування та відправка звітів
- Фільтрація торгових пар через allow/deny списки
- CLI-команда `price:pair` для перегляду цін по символах

**Нові параметри підкроку 3.4 (depth-фільтр):**
MIN_DEPTH_USD=1000000        # мінімальна глибина стакану в $
DEPTH_WINDOW_PCT=0.5         # вікно для розрахунку глибини у %
MIN_DEPTH_LEVELS=30          # мінімальна кількість рівнів у вікні

---

## Швидкий старт (Windows 11)

1. **Створити віртуальне середовище**
   ```powershell
   py -3.11 -m venv .venv

2. **Активувати середовище**   
.\.venv\Scripts\Activate.ps1

3. **Оновити pip**
pip install --upgrade pip

4. **Встановити залежності**
pip install -r requirements.txt

5. **Налаштувати .env**
-Скопіювати:
    copy .env.example .env

-Заповнити ключі API, токен Telegram, параметри фільтрів.

6. **Перевірити код**
pytest -q
ruff .
black .
isort .

`Приклади CLI-команд`
**Перевірка з'єднання з Bybit**
python -m src.main bybit:ping
python3 -m src.main bybit:ping

**Отримати топ-5 пар за різницею SPOT/Futures**
python -m src.main bybit:top --limit 5
python3 -m src.main bybit:top --limit 5

**Сканування сигналів і збереження в базу**
python -m src.main basis:scan
python3 -m src.main basis:scan

**Надіслати звіт у Telegram (за останні 24 години)**
python -m src.main report:send --hours 24
python3 -m src.main report:send --hours 24

**Перегляд цін по одній парі**
python -m src.main price:pair --symbol ETHUSDT
python3 -m src.main price:pair --symbol ETHUSDT

**Перегляд цін по кількох парах**
python -m src.main price:pair --symbol ETHUSDT --symbol BTCUSDT

**Структура проєкту**
src/            # Основний код бота
tests/          # Тести Pytest
logs/           # Логи виконання
requirements.txt# Залежності
.env            # Конфігурація середовища

**Тести**
**Запустити всі тести:**
pytest -q
**Запустити тести з виводом:**
pytest -v

**Ліцензія** MIT License