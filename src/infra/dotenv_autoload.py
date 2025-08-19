# src/infra/dotenv_autoload.py
from __future__ import annotations

import os
import re
from typing import Optional

__all__ = ["autoload_env", "find_env_file"]


def _strip_inline_comment(s: str) -> str:
    out: list[str] = []
    in_single = False
    in_double = False
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            break
        out.append(ch)
        i += 1
    return "".join(out).strip()


def _parse_dotenv_line(line: str) -> tuple[str, str] | None:
    # Trim whitespace and drop a potential UTF-8 BOM
    s = line.lstrip("\ufeff").strip()
    s = _strip_inline_comment(s)
    if not s or "=" not in s:
        return None

    # Allow optional leading 'export ' (case-insensitive), with or without extra spaces/BOM
    s = re.sub(r"^\ufeff?\s*export\s+", "", s, flags=re.IGNORECASE)

    key, val = s.split("=", 1)
    key = key.strip()

    # Only allow [A-Za-z0-9_] in keys (underscore allowed)
    if not key or not key.replace("_", "").isalnum() or key[0].isdigit():
        return None

    val = val.strip()
    if val.startswith("'") and val.endswith("'") and len(val) >= 2:
        raw = val[1:-1]
    elif val.startswith('"') and val.endswith('"') and len(val) >= 2:
        tmp = val[1:-1]
        tmp = (
            tmp.replace(r"\n", "\n")
            .replace(r"\r", "\r")
            .replace(r"\t", "\t")
            .replace(r"\\\"", '"')
            .replace(r"\\", r"\\")
        )
        raw = tmp
    else:
        raw = val.strip()

    return key, raw


_VAR_PATTERN = re.compile(r"\$(\w+)|\$\{(\w+)\}")


def _expand_vars(value: str, env: dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        key = match.group(1) or match.group(2)
        return env.get(key, os.environ.get(key, match.group(0)))

    previous = None
    current = value
    for _ in range(5):
        if current == previous:
            break
        previous = current
        current = _VAR_PATTERN.sub(repl, current)
    return current


def find_env_file() -> Optional[str]:
    path = os.getenv("ENV_FILE")
    if path and os.path.isfile(path):
        return path

    cwd_env = os.path.join(os.getcwd(), ".env")
    if os.path.isfile(cwd_env):
        return cwd_env

    here = os.path.abspath(__file__)
    candidate = os.path.abspath(os.path.join(os.path.dirname(here), "..", "..", ".env"))
    if os.path.isfile(candidate):
        return candidate

    candidate2 = os.path.abspath(os.path.join(os.path.dirname(here), "..", ".env"))
    if os.path.isfile(candidate2):
        return candidate2

    return None


def autoload_env(override: bool = False) -> Optional[str]:
    """Load .env into os.environ without external packages.

    - override=False keeps existing os.environ values (safe for CI/secrets)
    - supports: export KEY=..., quotes, inline # comments, $VAR/${VAR} expansion
    - search order: ENV_FILE -> ./.env -> project-root .env
    """
    path = find_env_file()
    if not path:
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return None

    entries: list[tuple[str, str]] = []
    for ln in lines:
        parsed = _parse_dotenv_line(ln)
        if parsed:
            entries.append(parsed)

    local: dict[str, str] = {}
    for key, value in entries:
        expanded = _expand_vars(value, {**local, **os.environ})
        if override or key not in os.environ:
            os.environ[key] = expanded
        local[key] = expanded

    return path
