<!--
Біля назви PR використовуйте короткий двомовний заголовок.
Use a concise bilingual title near the PR name.
Example: Phase 7 (IRM): генератор та перевірки / generator & checks
-->

# 🧩 Summary / Мета
- **UA:** Коротко опишіть, що і навіщо змінюється.
- **EN:** Briefly describe what changes and why.

## 🔧 Changes / Ключові зміни
- **UA:** Маркованим списком основні пункти.
- **EN:** Bullet list of key points.

## 🗂 Files Changed / Список файлів
- path/to/file — short note
- ...

## ✅ How to Test / Як перевірити
```powershell
# UA: Локальні кроки відтворення / перевірки
# EN: Local steps to reproduce / verify
pre-commit run -a
pytest -q
python tools\render_irm_view.py --write
```
**Expected / Очікування:** опишіть очікуваний результат.

## 🔒 Risks & Rollback / Ризики та відкат
- **UA:** Потенційні ризики та як відкотити.
- **EN:** Potential risks and how to roll back.

## 🔗 Linked Issues / Пов’язані задачі
- Closes #...
- Relates to #...

## 📝 Release Notes / Ноти релізу
- **UA:** 1–2 рядки для CHANGELOG.
- **EN:** 1–2 lines for CHANGELOG.

---

### 🧪 Phase-specific checks / Перевірки для фаз (IRM)
- [ ] **UA:** `irm.phaseX.yaml` оновлено відповідно до змін.
- [ ] **EN:** `irm.phaseX.yaml` updated accordingly.
- [ ] `python tools/irm_phaseX_gen.py --check` — clean
- [ ] `python tools/render_irm_view.py --write` — synced
- [ ] `pre-commit run -a` — all hooks passed
