# AUDIT_CHECKLIST — Проєкт «БОТ АРБІТРАЖНИЙ BYBIT»
**Крок 6.3.12 — Audit & Inspection (0 → 6.3.11)**  
Ролі: Senior Dev, QA, PM, DevOps, Repo Maintainer.  
Ціль: виконати повний аудит від нульового кроку до поточного стану (6.3.11), навести лад у репозиторії, перевірити синхронізацію IRM ↔ IRM.view ↔ YAML, прибрати зайве без поломок, і все це — у цільовій гілці з зеленими тестами/гвардами/CI.

**Звіт сформовано:** 2025-09-20 17:46:10Z
---

## 0) Правила виконання аудиту
- Працюємо **у цільовій гілці**: `step-6.3.12-audit` (main не чіпаємо до успішного PR).
- Кожна зміна — **малим комітом з чітким меседжем**.
- Будь-яке вилучення файлів — **спершу у список кандидатів, потім окремий коміт**.
- Після кожного логічного підкроку: `pre-commit run -a` → `pytest -q` →, за потреби, оновлення IRM.

---

## 1) Підготовка середовища (DevOps/Senior Dev)
- [ ] Перейти на main та підтягнути оновлення:
```powershell
git checkout main
git pull --ff-only
git checkout -b step-6.3.12-audit
python --version
pip --version
```
- [ ] Активувати venv (Windows 11):
```powershell
& .\.venv\Scripts\Activate.ps1
pre-commit install
```

---

## 2) Зняття «снімку» поточного стану (Repo Maintainer/PM)
- [ ] Зафіксувати ключові артефакти у лог (для історії PR):
```powershell
git --no-pager log --oneline -n 10
git status
git tag --list
```
- [ ] Перевірити, що **IRM синхронний** (Phase 6.3):
```powershell
python tools/irm_phase6_gen.py --check --phase 6.3
python tools/render_irm_view.py --check
```
- [ ] Прогнати локальні гварди/тести:
```powershell
pre-commit run -a
pytest -q
```

---

## 3) IRM-рев’ю (PM/Senior Dev) — **заповнено**
Мета: звірити дорожню карту, знайти пропуски, скласти «глобальний» трек.

### 3.1 Що підтверджено за README/релізами
- README описує **IRM workflow**: SSOT — `docs/irm.phase6.yaml`; `docs/IRM.md` генерується тільки зі скрипта; є локальний pre-commit guard та CI-перевірка синхронності (посилання/фрагменти в README).  
- У README зазначено локальні результати тестів: *144 passed, 1 skipped* (локально).  
- На сторінці Releases наявні теги 6.1.0 / 6.1.1 (Config Hardening/Env precedence), також на головній сторінці репозиторію відображено реліз **v6.3.7b IRM guards + README note** (актуалізація guard-ів для IRM).

### 3.2 Перелік кроків 0 → 6.3.11 за даними репозиторію
> Узагальнення (буде уточнене при прогоні генератора IRM):
- 6.2.0 — WS Resilience (описані покращення парсерів та MUX у README).
- 6.3.4 — Приглушення майже-дублікатів під час cooldown (Alerts).
- 6.3.5 — Персист стану гейта у SQLite (Alerts).
- 6.3.6 — SQLite Maintenance (retention & compaction) — наявні скрипти у `scripts/`.
- 6.3.7 — Documentation update (за історією чатів/README).
- 6.3.7b — IRM guards + README note.
- 6.3.8 — Coverage & Badge у CI — **потребує перевірки статусу в IRM**.
- 6.3.9 — Генерація секції з YAML — **done**.
- 6.3.10 — IRM View (read-only) + CI guard — **done**.
- 6.3.11 — Локальний pre-commit guard (IRM.view) — **done**.

### 3.3 Глобальні пропуски (заповнено)
- [ ] Переконатися, що **всі підкроки 6.0.x–6.2.x** присутні в `docs/irm.phase6.yaml` і мають коректні статуси (особливо 6.0.1–6.0.6 по Digest/notify).
- [ ] Актуалізувати статус **6.3.7–6.3.8** (за фактом CI-badge): якщо badge/coverage вже увімкнено — проставити `done`; якщо ні — `todo/wip` та додати підкроки.
- [ ] Узгодити в YAML точні назви підкроків **6.3.4–6.3.6** з фактичними файлами (SQLite maint scripts, AlertGate persistence).

### 3.4 Дії по IRM
- [ ] Внести мінімальні правки у `docs/irm.phase6.yaml` (тільки статуси/пункти), **без масового переформатування**.
- [ ] Згенерувати `docs/IRM.md` та `docs/IRM.view.md` і закомітити разом з YAML.
- [ ] Повторити guard-и/тести.

---

## 4) Репозиторна гігієна та «сміття» (Repo Maintainer/DevOps)
Мета: виявити зайві файли/папки/артефакти і зробити план чистки без ризику.

### 4.1 Пошук «сміття» (команди)
```powershell
# великі файли (>5 МБ) у відстежених
git ls-files | ForEach-Object { $_, (Get-Item $_).Length } |
  Where-Object { $_[1] -gt 5MB } | Format-Table -AutoSize

# кеші/артефакти у відстежених (підозрілі)
git ls-files | Select-String -Pattern '\.pyc$|__pycache__|\.pytest_cache|\.coverage|\.DS_Store|Thumbs\.db|^dev/|^tmp/|^\.vscode/'

# що ігнорується, але випадково могло потрапити
git check-ignore -v -- * | Sort-Object

# що НЕ ігнорується, але, ймовірно, має бути ігнорованим
ls -r -fo |
  ? { $_.Name -match '\.log$|\.tmp$|\.bak$|\.swp$|\.old$|\.orig$|^~|^#|\.ipynb_checkpoints' } |
  % FullName
```

### 4.2 Список кандидатів на видалення — **первинний план**
> **ВАЖЛИВО:** поки лише план. Видалення — окремим комітом після погодження.
- [ ] Папки (якщо потрапили під відстеження випадково):
  - [ ] `__pycache__/`, `.pytest_cache/`, `.vscode/`, `dev/tmp/`, `logs/`, `run/`
- [ ] Файли (якщо відстежуються):
  - [ ] `*.log`, `*.tmp`, `*.bak`, `*.old`, `*.orig`, `*.swp`, `Thumbs.db`, `.DS_Store`
  - [ ] Локальні БД/артефакти: `data/**/*.db`, `data/**/*.parquet`, `coverage.xml`, `.coverage*`
- [ ] Ігнор/атрибути (оновити `.gitignore`/`.gitattributes`):
  - [ ] Додати правила для вищенаведених шаблонів + EOL-норми (LF для `*.py`, `*.yml`, `*.yaml`, `*.sh`; `text=auto` для решти).

---

## 5) Аналіз залежностей та безпеки (Senior Dev/DevOps/QA)
- [ ] Перевірити «хвости» у `requirements*.txt`:
```powershell
pip list --format=columns
python -m pip install pipdeptree --quiet
pipdeptree
```
- [ ] Security-скани (локально):
```powershell
python -m pip install pip-audit safety --quiet
pip-audit
safety check
```
- [ ] Знахідки/рекомендації (шаблон — оновити після реального прогону)
  - [ ] На даний момент **критичних вразливостей не зафіксовано** (підтвердити сканами).
  - [ ] Рекомендовано зафіксувати верхні межі версій Dev-інструментів у `requirements-dev.txt` (reproducibility).

---

## 6) CI/Workflows огляд (DevOps)
- [ ] Перевірити `.github/workflows`:
  - `irm-check.yml` — працює і потрібен.
  - `irm_phase6_sync.yml` — актуальний.
  - `irm-view-check.yml` — є і зелений.
  - Digest E2E Smoke / notify workflow — актуальні, без дублікатів.
  - Висновок: дублювань не виявлено/потребує уточнення за історією PR.
- [ ] Додатково: перевірити останні раннери у вкладці Actions, що всі джоби **green**.

---

## 7) Гварди та тести (QA/Senior Dev)
- [ ] Локальні гварди:
```powershell
pre-commit run -a
```
Очікування:  
  - `IRM Phase 6 sync check` — **Passed**  
  - `Forbid manual commits of docs/IRM.md without YAML` — **Passed**  
  - `IRM.view must match YAML (render_irm_view.py --check)` — **Passed**

- [ ] Тести:
```powershell
pytest -q
```
Очікування: **green**; Coverage ≥ 67% (ціль 6.3.8 — badge у CI).

---

## 8) План змін (малими PR, без ризику поломок) — **заповнено**
- [ ] **PR-1: Ігнори та атрибути** — оновити `.gitignore`/`.gitattributes` (EOL, лог-/tmp-/db-артефакти).
- [ ] **PR-2: IRM-синхронізація** — точкові правки YAML + регенерація IRM/IRM.view.
- [ ] **PR-3: Документація** — README: посилання на IRM.view (SSOT), короткий how-to по генерації.
- [ ] **PR-4 (опційно)**: Автопублікація `IRM.view.md` на GitHub Pages.
- [ ] **PR-5 (опційно)**: Coverage badge у README (якщо 6.3.8 ще не закритий).

---

## 9) Підсумкові артефакти цього аудиту (обов’язково в PR)
- [ ] Оновлений **`AUDIT_CHECKLIST.md`** (цей файл) — заповнені розділи 3/4/5/8.
- [ ] Лист «кандидатів на видалення» з ризиками/обґрунтуванням.
- [ ] Виводи гвардів/тестів (скріни або копіпасти з консолі у PR-коментар).

---

## 10) Definition of Done (DoD)
- [ ] Створена гілка `step-6.3.12-audit`, відкритий PR.
- [ ] IRM ↔ IRM.view ↔ YAML синхронні; 6.3.9/6.3.10/6.3.11 — **done**.
- [ ] У репо немає явно «сміттєвих» файлів; `.gitignore`/`.gitattributes` актуальні.
- [ ] Усі гварди/тести **green** локально та в CI.
- [ ] Узгоджений план наступних PR для чистки/поліпшень.
- [ ] Мердж у `main` після зеленого CI.

---

## Додаток A — Ролі та майндсет
- **PM**: узгодження обсягу, пріоритизація мікрокроків, фіксація DoD.
- **Senior Dev**: технічний аудит, рішення по SSOT/генерації/хуках.
- **QA**: невидимі для продакшна зміни не повинні ламати тести/покриття.
- **DevOps**: робочість CI, відсутність flaky, чисті артефакти.
- **Repo Maintainer**: єдина стилістика комітів, чистота дерева.

---

## Додаток B — Шаблон «Знахідки → Рішення → Дія» — **первинне заповнення**
| ID | Знахідка | Вплив/Ризик | Рішення | Дія/PR |
|----|----------|-------------|---------|--------|
| 1  | Потенційні артефакти у відстежених (logs/tmp/db) | Шум у дифах, ризик секретів | Оновити `.gitignore`/прибрати з треку | PR-1 |
| 2  | EOL/CRLF різнобій між файлами | Flaky-дифи, попередження Git | Встановити правила в `.gitattributes` | PR-1 |
| 3  | Розсинхрон IRM ↔ IRM.view в окремих підкроках | Червоні гварди/CI | Виправити YAML і регенерувати | PR-2 |
| 4  | Coverage badge відсутній/застарілий | Менша прозорість якості | Додати/осучаснити badge | PR-5 |
| 5  | Подвійні або застарілі GHA-джоби (підозра) | Довший CI/ризик плутанини | Провести рев’ю і об’єднати | PR-4/окремий |

---

## Додаток C — Короткий підсумок виконаних кроків (0 → 6.3.11)
- ✅ 6.2.0 — WS Resilience (парсери `tickers`, MUX-поведінка, health-метрики).
- ✅ 6.3.4 — Alerts: приглушення повторів під час cooldown.
- ✅ 6.3.5 — Alerts: персист стану гейта у SQLite.
- ✅ 6.3.6 — SQLite Maintenance (retention & compaction) — скрипти в `scripts/`.
- ✅ 6.3.7 — Documentation update (деталі в README/CHANGELOG).
- ✅ 6.3.7b — IRM guards + README note.
- ⏳ 6.3.8 — Coverage & badge у CI — **перевірити й зафіксувати статус у YAML**.
- ✅ 6.3.9 — Генерація секції з YAML — **done**.
- ✅ 6.3.10 — IRM View (read-only) + CI guard — **done**.
- ✅ 6.3.11 — Локальний pre-commit guard (IRM.view) — **done**.

---

## Порада (щоб мінімізувати дифи у YAML)
- При точкових змінах статусу в YAML — **правити вручну один рядок** у блоці `id: X.Y.Z` (без автоматичних «переформатувальників»), щоб уникати суцільного переформатування.

---

### Контрольний запуск перед PR
```powershell
pre-commit run -a
pytest -q
python tools/irm_phase6_gen.py --check --phase 6.3
python tools/render_irm_view.py --check

git add AUDIT_CHECKLIST.md
git commit -m "audit(6.3.12): resolve checklist conflicts; finalize audit notes"
git push -u origin step-6.3.12-audit
```
