# AUDIT_CHECKLIST — Проєкт «БОТ АРБІТРАЖНИЙ BYBIT»
**Крок 6.3.12 — Audit & Inspection (0 → 6.3.11)**  
Ролі: Senior Dev, QA, PM, DevOps, Repo Maintainer.  
Ціль: повний аудит від нульового кроку до стану 6.3.11, впорядкування репозиторію, перевірка синхронізації IRM ↔ IRM.view ↔ YAML, прибирання зайвого без поломок, робота в цільовій гілці зі зеленими тестами/гвардами/CI.

**Звіт сформовано:** 2025-09-20 18:28:38Z
---

## 0) Правила
- Працюємо у гілці `step-6.3.12-audit`. `main` не чіпаємо до merge.
- Маленькі атомарні коміти з чіткими меседжами.
- Видалення — спочатку список кандидатів, потім окремий коміт.
- Після кожного підкроку: `pre-commit run -a` → `pytest -q` → (за потреби) регенерація IRM.

---

## 1) Підготовка
```powershell
git checkout -B step-6.3.12-audit
& .\.venv\Scripts\Activate.ps1
pre-commit install
```

---

## 2) Снімок стану
```powershell
git --no-pager log --oneline -n 10
git status
git tag --list
python tools/irm_phase6_gen.py --check --phase 6.3
python tools/render_irm_view.py --check
pre-commit run -a
pytest -q
```

---

## 3) IRM-рев’ю — підсумок
- SSOT — `docs/irm.phase6.yaml`; `docs/IRM.md` генерується; guard-и локальні та CI є.
- README містить локальні результати тестів; Releases відмічають 6.1.0/6.1.1 та v6.3.7b (IRM guards).

**Кроки (0 → 6.3.11) за репозиторієм:**  
6.2.0 WS Resilience; 6.3.4 cooldown de-dup; 6.3.5 AlertGate state → SQLite; 6.3.6 SQLite maintenance scripts; 6.3.7 docs; 6.3.7b IRM guards; 6.3.8 coverage badge (перевірити); 6.3.9 YAML→IRM gen; 6.3.10 IRM.view + CI; 6.3.11 pre-commit guard.

**Що доповнити:**  
- Перевірити/уточнити статуси 6.0.x–6.2.x в YAML.  
- Зафіксувати 6.3.8 (badge) — done/wip.  
- Узгодити назви 6.3.4–6.3.6 з файлами.

**Дії:** мінімальні правки в YAML → regenerate `IRM.md` + `IRM.view.md` → коміт разом з YAML.

---

## 4) Репогігієна
### Пошук сміття
```powershell
git ls-files | ForEach-Object { $_, (Get-Item $_).Length } | ? { $_[1] -gt 5MB }
git ls-files | Select-String -Pattern '\.pyc$|__pycache__|\.pytest_cache|\.coverage|\.DS_Store|Thumbs\.db|^dev/|^tmp/|^\.vscode/'
git check-ignore -v -- * | Sort-Object
ls -r -fo | ? { $_.Name -match '\.log$|\.tmp$|\.bak$|\.swp$|\.old$|\.orig$|^~|^#|\.ipynb_checkpoints' } | % FullName
```

### Кандидати на видалення (план)
- Папки: `__pycache__/`, `.pytest_cache/`, `.vscode/`, `dev/tmp/`, `logs/`, `run/` (якщо відстежуються).
- Файли: `*.log`, `*.tmp`, `*.bak`, `*.old`, `*.orig`, `*.swp`, `Thumbs.db`, `.DS_Store`, локальні БД/артефакти (`data/**/*.db`, `data/**/*.parquet`), `coverage.xml`, `.coverage*`.
- Оновити `.gitignore`/`.gitattributes` (EOL LF для текстових, text=auto).

---

## 5) Залежності/безпека
```powershell
pip list --format=columns
python -m pip install pipdeptree pip-audit safety --quiet
pipdeptree
pip-audit
safety check
```
Рекомендації: зафіксувати верхні межі dev-інструментів у `requirements-dev.txt` (reproducibility).

---

## 6) CI/Workflows огляд
- `irm-check.yml`, `irm_phase6_sync.yml`, `irm-view-check.yml` — актуальні, зелені.
- Digest smoke/notify — без дублів.
- Перевірити останні раннери у Actions — усі green.

---

## 7) Гварди/тести
```powershell
pre-commit run -a
pytest -q
```
Очікування: зелено; coverage ≥ 67% (ціль 6.3.8 — badge).

---

## 8) План малих PR
- PR-1: `.gitignore`/`.gitattributes` (ігнори, EOL).
- PR-2: YAML статуси → regenerate IRM/IRM.view.
- PR-3: README (посилання на IRM.view, how-to).
- PR-4 (опц.): публікація IRM.view на GH Pages.
- PR-5 (опц.): coverage badge, якщо ще не закрито.

---

## 9) Артефакти для PR
- Оновлений `AUDIT_CHECKLIST.md` (цей файл).
- Список кандидатів на видалення з ризиками.
- Виводи guardів/тестів (логи/скріни).

---

## 10) DoD
- Гілка `step-6.3.12-audit`, відкритий PR.
- IRM ↔ IRM.view ↔ YAML синхронні.
- Чисті ігнори/атрибути, без сміття у треку.
- Всі guard-и/тести green локально та в CI.
- Мердж у `main` після зеленого CI.

---

## Додатки
**Ролі:** PM, Senior Dev, QA, DevOps, Repo Maintainer.  
**Знахідки → Рішення → Дія:** (1) артефакти в треку → оновити `.gitignore` (PR-1); (2) EOL різнобій → `.gitattributes` (PR-1); (3) IRM розсинхрон → правки YAML + regenerate (PR-2); (4) badge → PR-5.

---

### Контрольний прогін перед PR
```powershell
pre-commit run -a
pytest -q
python tools/irm_phase6_gen.py --check --phase 6.3
python tools/render_irm_view.py --check

git add AUDIT_CHECKLIST.md
git commit -m "audit(6.3.12): finalize audit checklist (IRM sync, hygiene plan, CI/tests)"
git push -u origin step-6.3.12-audit
```
## 6.3.12 � Audit (final)
- Tests: 155 passed, 1 skipped; coverage 67.81% (67%).
- Phase-4 subset: 28 passed; module coverage (selector/liquidity/alerts_gate): 67% / 89% / 85% (phase4-only).
- IRM guards: Passed; IRM 6.3 up-to-date; IRM.view rendered OK.
- EOL: normalized; hooks no longer rewrite IRM.view.md.
- Note: Phase 4 changes kept local in IRM.md (manual), not committed (SSOT for Phase 4 is a follow-up).
