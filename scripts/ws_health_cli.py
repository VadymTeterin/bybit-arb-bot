"""
Temporary CLI to print WS health metrics as JSON.
Run:
    python -m scripts.ws_health_cli
(English-only comments per project rules)
"""

from __future__ import annotations

import json

from src.ws.health import MetricsRegistry


def main() -> None:
    reg = MetricsRegistry.get()
    data = reg.snapshot()
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
