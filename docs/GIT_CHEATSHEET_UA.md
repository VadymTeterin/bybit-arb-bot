# Git & GitHub Cheat Sheet (Windows/VS Code, PowerShell)

> Оновлено: 2025-09-21 04:08 UTC
> Ціль: короткі **покрокові рецепти** для щоденної роботи (rebase, конфлікти в VS Code, amend, відкат, force-with-lease тощо) у репозиторії *bybit-arb-bot*.

---

## 0) Разове налаштування

```powershell
# Редактор — VS Code у блокуючому режимі
git config --global core.editor "code --wait"

# Безпечний fetch (прибирати віддалено видалені гілки)
git config --global fetch.prune true

# Рекомендовано для Windows: контроль переносів рядків
git config --global core.autocrlf false
git config --global core.safecrlf warn
# у репо: .gitattributes має правила типу "text eol=lf"
```

Перевірити налаштування:
```powershell
git config --show-origin --get core.editor
git config --get fetch.prune
git config --get core.autocrlf
```

---

## 1) Базовий робочий цикл (feature → PR → main)

```powershell
# оновити main
git switch main
git pull

# відгалузитися
git switch -c step-xyz-description

# робота, коміти
git add .
git commit -m "feat: ..."

# пуш гілки
git push -u origin step-xyz-description

# створити PR (на GitHub UI)
# після мерджа локально:
git switch main
git pull
git branch -d step-xyz-description
git push origin --delete step-xyz-description   # опціонально
```

---

## 2) Rebase на свіжий main (без переписування чужої історії)

> Коли твоя гілка відстає від `main`.

```powershell
git fetch origin
git switch step-xyz-description
git rebase origin/main
# (вирішити конфлікти → git add <file> → git rebase --continue)
```

### Типові команди під час rebase
```powershell
git rebase --continue    # завершити поточний крок
git rebase --skip        # пропустити конфліктний коміт
git rebase --abort       # повністю скасувати rebase
```

### Інтерактивний rebase (squash/fixup/rename)
```powershell
git rebase -i origin/main
# позначити коміти як "s" (squash) або "f" (fixup), зберегти
```

### Безпечний пуш після rebase
```powershell
# зробити бекап-тег (рекомендовано перед force-пушем)
$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
git tag "backup-pre-force-$ts" HEAD
git push origin "backup-pre-force-$ts"

# безпечний force
git push --force-with-lease
```

---

## 3) Розв’язання конфліктів у **VS Code** (Merge Editor)

1. Відкрити репо у VS Code.  
2. Файл з конфліктом має «Conflict» маркери:  
   ```
   <<<<<<< ours
   ...твоя версія...
   =======
   ...версія з main...
   >>>>>>> theirs
   ```
3. Відкрити **Merge Editor** (клік по статус-рядку «Resolve in Merge Editor» або по самому файлу).  
4. По кожному блоку: **Accept Current / Accept Incoming / Accept Both / Manual**.  
5. Прибрати всі маркери (`<<<<<<<`, `=======`, `>>>>>>>`).  
6. Зберегти файл → `git add <file>` → продовжити rebase:
   ```powershell
   git add path/to/file
   git rebase --continue
   ```

> Порада: для `.gitignore` часто треба **залишити правило** `coverage_phase4.xml` (один раз), а інші маркери прибрати.

---

## 4) Amend останнього коміту

- **Змінити лише повідомлення:**
  ```powershell
  git commit --amend
  ```
- **Додати ще файли у той же коміт:**
  ```powershell
  git add <files>
  git commit --amend --no-edit
  ```
- Якщо коміт уже на віддаленій гілці — **переписує історію**, пуш:
  ```powershell
  git push --force-with-lease
  ```

---

## 5) Відкат / відновлення

```powershell
# Відновити файл із індексу/HEAD
git restore path/to/file

# "М’який" відкат до коміту (зберегти зміни у staging)
git reset --soft <commit>

# Відкотити індекс (зміни лишаться у робочій теці)
git reset <commit>

# Жорсткий відкат (уважно! видаляє зміни)
git reset --hard <commit>

# Рятувальний круг: перегляд історії дій
git reflog
```

---

## 6) Stash (тимчасово відкласти зміни)

```powershell
git stash push -m "wip: опис"          # з індексом і неіндексом
git stash list
git stash show -p stash@0
git stash pop                           # застосувати і видалити
git stash apply stash@1               # застосувати і залишити запис
git stash push -u                       # включити untracked
```

---

## 7) Cherry-pick (перенести коміт)

```powershell
git cherry-pick <commit>                # один
git cherry-pick A^..B                   # діапазон A..B включно
# якщо конфлікти: вирішити → git add → git cherry-pick --continue
```

---

## 8) Теги (release/backup)

```powershell
git tag v6.3.12 -m "Release 6.3.12"
git push origin v6.3.12

git tag -d v6.3.12
git push origin :refs/tags/v6.3.12
```

---

## 9) Чистка локальних артефактів / ігнори

```powershell
# Подивитися, що не під контролем
git status --ignored

# Видалити сміття, що не відслідковується (уважно!)
git clean -fdx      # -n для dry-run
```

`.gitignore` — правило для локального coverage підмножини:
```
coverage_phase4.xml
```

---

## 10) Переноси рядків (CRLF/LF), «M» на файлах без змін

### Швидкі рецепти
```powershell
# показати EOL у файлах
git ls-files --eol docs/IRM.view.md

# масово нормалізувати перенос рядків по .gitattributes
git add --renormalize .
git commit -m "chore(eol): renormalize per .gitattributes"
```

> Попередження `CRLF will be replaced by LF` — нормальне, якщо `.gitattributes` примушує `eol=lf`.

---

## 11) Pre-commit / тести / IRM-гварди

```powershell
pre-commit run -a

pytest -q

python tools/irm_phase6_gen.py --check --phase 6.3
python tools/render_irm_view.py --check
```

Якщо хук **автоматично змінює** файл (наприклад, `IRM.view.md`) — просто **додай** файл і зроби коміт.

---

## 12) «Detached HEAD» — що це і як вийти

- Ти стоїш на конкретному коміті, а не гілці.  
Виправлення:
```powershell
git switch main              # повернутися на гілку
# або створити гілку від поточного місця
git switch -c fix-from-here
```

---

## 13) Часті перевірки перед пушем/мерджем

```powershell
git status
git --no-pager diff --name-status origin/main..HEAD
git --no-pager log --oneline -n 5
pre-commit run -a
pytest -q
```

---

## 14) Рекомендовані alias’и (зберігаються у глобальному конфігу)

```powershell
git config --global alias.co "checkout"
git config --global alias.br "branch"
git config --global alias.st "status -sb"
git config --global alias.lg "log --oneline --graph --decorate"
git config --global alias.df "diff --word-diff"
```

Використання: `git lg`, `git st`, `git df` …

---

## 15) Швидкі сценарії «як у нас було»

### A. Перед force-push робимо бекап-тег
```powershell
$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
git tag "backup-pre-force-$ts" HEAD
git push origin "backup-pre-force-$ts"
git push --force-with-lease
```

### B. Конфлікт у `.gitignore` лише через локальний coverage файл
- Вирішити в Merge Editor: прибрати маркери, залишити **один** рядок `coverage_phase4.xml`.
- Зберегти → `git add .gitignore` → продовжити rebase/merge.

### C. «M» на `docs/IRM.view.md` через EOL
```powershell
python tools/render_irm_view.py --check
git add docs/IRM.view.md
git commit -m "docs(IRM.view): normalize EOL & sync with SSOT"
```

---

## 16) Коли щось пішло не так

- **Скасувати rebase/merge**: `git rebase --abort` або `git merge --abort`  
- **Знайти втрачений коміт**: `git reflog` → `git show <hash>` → `git cherry-pick <hash>`  
- **Створити підтримку**: надайте в чаті
  - точні команди, які виконувались,
  - `git status`,
  - `git --no-pager log --oneline -n 20`,
  - скрін(и) конфліктів.

---

*Усе вище узгоджено з нашим робочим процесом (pre-commit гварди IRM, pytest ≥ 67% coverage, EOL через .gitattributes).*
