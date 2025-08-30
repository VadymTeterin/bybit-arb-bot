# QS v1.0 (узгоджено з WA) — Quality Standards

> Узгоджено з **Working Agreements v2.0 (WA)**. Відхилення дозволені лише за політикою “Відхилення” (з причиною, сферами, таймбоксом і планом відкату) та з фіксацією в IRM.

## P0 — Обов’язково (ядро якості)
1. **One‑step flow** *(WA‑9)* — виконуємо рівно один крок/підкрок за раз. Рух далі — лише після явного підтвердження “крок завершено”.
2. **Безпека й секрети** *(WA‑10, WA‑8)* — попереджаю перед командами, що можуть вивести секрети; ключі/токени ніколи не потрапляють у код/логи/чат; `.gitignore` актуальний.
3. **SSOT + DoD** — IRM/README є єдиним джерелом істини; відхилення фіксуються як exception в IRM. **DoD**: збірка/ран компілюється, тести зелені локально, README/CHANGELOG оновлені, CI (якщо є) зелений, немає TODO/DEBUG, посилання на артефакти перевірені.
4. **Windows‑only чіткість виконання** *(WA‑6, WA‑11)* — завжди вказую, що запускається у **PowerShell / VS Code “Термінал”**, а що — копі‑паст у файли.
5. **Стиль коду (Python)** — повні type hints, коментарі англійською; відсутні “мертві” імпорти/змінні *(WA‑5)*; модулі лаконічні.
6. **Тестування** *(WA‑4)* — `pytest` + `pytest-cov`; покриття зміненого коду ≥ 85% рядків; детерміновані тести (fixed seed), без мережі/диску, якщо не потрібно.
7. **Надійність** — жодних `bare except`; таймаути на I/O; ретраї з backoff+джитер; ліміти на черги/потоки, щоб не залипало.

## P1 — Високий пріоритет (quality gate)
8. **Відтворюваність** — пінені версії (lockfile/requirements); однакові PowerShell‑команди й Windows‑шляхи; фіксуємо версії інструментів при зміні поведінки.
9. **Документація** *(WA‑3)* — кожна суттєва зміна доповнює README/CHANGELOG; короткі usage‑блоки та приклади.
10. **Конфіг і дані** — `.env.template`, відсутність реальних ключів у репо; за замовчуванням синтетичні/демо‑дані (ніяких live‑дій без окремого попередження).
11. **Логування** — DEBUG (dev), INFO (звичайно); шляхи логів задокументовані; секрети/PII у логи не потрапляють.
12. **Бекапи перед змінами стану** — перед міграціями/скриптами: timestamp‑бекап у `dev/tmp/...` (у `.gitignore`).

## P2 — Інженерна гігієна та ергономіка
13. **Структура артефактів** *(WA‑7)* — тимчасові/вивідні файли — тільки в окремих теках; корінь чистий.
14. **Гілки й коміти** — малі зміни; Conventional Commits (`feat:`, `fix:`, …) + номер кроку; гілки `step-X.Y.Z-feature`.
15. **PR‑чекліст (self‑review)** — тести/лінтери/ковередж пройдені, доки оновлені, немає випадкових файлів, TODO прибрані.
16. **Продуктивність і ліміти** — базові бюджети часу/пам’яті на “гарячих” шляхах; проста профілююча перевірка за ризику.

---

## Мінімальний набір інструментів
- **Лінтери/форматери**: `ruff` (+`ruff format`), `isort`.
- **Тести**: `pytest` + `pytest-cov`.
- **pre-commit**: запуск лінтерів/форматерів перед комітами (початково — *manual*).

## Політика відхилень
Лише для зниження ризику або прискорення навчання; завжди: причина, сфера, таймбокс, план відкату; фіксація в IRM як “Exception”, до кінця кроку — або інтегруємо у стандарт, або видаляємо.

## Рекомендовані шляхи у репозиторії
- `docs/QUALITY.md` — цей документ (QS v1.0).
- `docs/DoD.md` — визначення “готово” з анкорами для IRM.
- `.github/PULL_REQUEST_TEMPLATE.md` — чекліст PR.
- `.pre-commit-config.yaml`, `.ruff.toml`, `.isort.cfg`, `requirements-dev.txt` — конфіги якості.

## КОРИСНІ КОМАНДИ

> **Мітка:** ✅ Цей чат закрито: **2025-08-30 09:13**. Наступна перевірка QS: **2025-09-13**.

## 1) Репозиторій та файлові політики
- **.gitattributes**: LF для `*.py, *.md, *.yml, *.yaml, *.json, *.toml, *.sh`; CRLF для `*.ps1, *.cmd, *.bat`.
- **.gitignore**: `__pycache__/`, `*.py[cod]`, `*.egg-info/`, `dist/`, `build/`, `.venv/`, `.pytest_cache/`, `htmlcov/`, `.coverage*`, `.mypy_cache/`, `logs/`, `*.log`, `.audit_*`, `.env*` (окрім `!.env.example`), `/IRM.md` (захист від кореневого дубля).
- **Repo hygiene**: у репозиторії відсутні логи/бекапи/тимчасові/артефакти.


```powershell
git add --renormalize .
pre-commit run --hook-stage manual -a
# швидкий аудит найбільших файлів (tracked)
git ls-files | % { gi $_ } | sort Length -desc | select -f 20 FullName,Length
```

---

## 2) Лінт та форматування
- **Ruff** (`ruff.toml`):
  - `line-length = 120`
  - `[lint].extend-select = ["E","F","B","W","UP"]`  (правило `I` вимкнено — сортування робить isort)
- **isort** (`isort.cfg`):
  - `profile = black`, `line_length = 120`
  - `combine_as_imports = true`, `ensure_newline_before_comments = true`
- **Форматування**: `ruff format`

**Команди**
```powershell
pre-commit install
ruff check --fix .
ruff format .
isort .
```

---

## 3) IRM: SSOT та Генератор
- **SSOT**: `docs/irm.phase6.yaml` (UTF‑8 **без BOM**, єдиний канонічний файл).
- **Генератор**: `tools/irm_phase6_gen.py` → оновлює блок у `docs/IRM.md` між сентинелами
  `<!-- IRM:BEGIN 6.2 --> … ` + "<!-- IRM:END 6.2 -->" + `.`
- **CI/PR**: у PR запускається `--check` і блокує злиття, якщо `IRM.md` не синхронізований.

**Команди**
```powershell
# одноразово залежність
python -m pip install pyyaml

# перевірити: чи IRM актуальний
python .	ools\irm_phase6_gen.py --check

# згенерувати/перезаписати
python .	ools\irm_phase6_gen.py --write
```

---

## 4) CHANGELOG
- Ведеться вручну, **без автогенерації**. Кодування — UTF‑8 (LF). Не вносити кирилицю через несумісні редактори.

---

## 5) Кодування та рядки
- Усі `*.md` / `*.yaml` — **UTF‑8 без BOM**.
- VS Code: `".vscode/settings.json" → "files.encoding": "utf8"`.
- Перевірка «кракозябри»:
```powershell
$moji = 'Ð|Ñ|Â|РРІС'
Select-String -Path .\docs\IRM.md, .\docs\irm.phase6.yaml -Pattern $moji || Write-Host "OK"
```

---

## 6) pre-commit (локально)
Хуки: `trim trailing whitespace`, `end-of-file-fixer`, `mixed-line-ending`, `ruff`, `ruff-format`, `isort`.

**Команди**
```powershell
python -m pip install pre-commit
pre-commit install
pre-commit run --hook-stage manual -a
```

---

## 7) DoD для QS (перед PR)
- [x] Відсутні логи/бекапи/тимчасові файли у репо.
- [x] `.gitattributes`/`.gitignore` — коректні; `git add --renormalize .` — без дифу.
- [x] `pre-commit run --hook-stage manual -a` — **Passed**.
- [x] `python tools/irm_phase6_gen.py --check` — **IRM up-to-date**.
- [x] Жодних збігів по «кракозябрі» у `IRM.md`/`irm.phase6.yaml`.
- [x] Якщо були зміни в IRM — згенеровано `--write`, закомічено та запущені хуки.

---

## 8) Швидкий сценарій релізу IRM
```powershell
# генерація
python .	ools\irm_phase6_gen.py --write

# коміт
git add .\docs\IRM.md .\docs\irm.phase6.yaml
git commit -m "docs(IRM): regenerate from SSOT"

# пуш і PR
git push -u origin HEAD
Start-Process "https://github.com/<owner>/<repo>/pull/new/$(git rev-parse --abbrev-ref HEAD)"
```

---

### Примітка
Цей документ — стабільна версія **QS v1.0** для проєкту *bybit-arb-bot*. Якщо з’являться нові вимоги — оновлюємо цей файл і комунікуємо в PR.
