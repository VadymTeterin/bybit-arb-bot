#!/usr/bin/env python3
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "IRM.md"
DST = ROOT / "docs" / "IRM.view.md"


def main() -> int:
    if not SRC.exists():
        return 0
    text = SRC.read_text(encoding="utf-8")

    # прибрати <!-- IRM:BEGIN 6.x --> / <!-- IRM:END 6.x -->
    text = re.sub(r"<!--\s*IRM:(BEGIN|END)\s*[\d.]+\s*-->", "", text)

    # підчистити зайві пробіли в кінці рядків і звести 3+ порожніх рядки до 2
    text = re.sub(r"[ \t]+$", "", text, flags=re.M)
    text = re.sub(r"(?:\r?\n){3,}", "\n\n", text)

    DST.write_text(text, encoding="utf-8")
    print(f"Rendered {DST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
