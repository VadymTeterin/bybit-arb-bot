# TESTING.md

## Як запускати тести (Windows PowerShell / VS Code “Термінал”)
```powershell
# (опц.) активуй venv
# .\.venv\Scripts\Activate.ps1

# встанови dev-залежності
pip install -r requirements-dev.txt

# швидкий прогін
pytest -q

# з ковереджем (звіт у термінал)
pytest --cov=src --cov-report=term-missing

# повний HTML-звіт ковереджу
pytest --cov=src --cov-report=html:.\dev\tmp\htmlcov
Start-Process .\dev\tmp\htmlcov\index.html
```

## Практики
- Не робимо мережевих викликів за замовчуванням; використовуємо фіктивні дані/моки.
- Тести детерміновані: фіксовані random seeds, контроль часу та I/O.
- Повільні/мережеві тести позначаємо маркерами й відокремлюємо від smoke.
