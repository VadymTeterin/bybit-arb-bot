from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


def setup_logging(log_dir: Path, level: str = "INFO") -> None:
    """
    Налаштовує loguru для збереження логів у файл та виводу у консоль.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    logger.remove()  # прибираємо стандартний handler
    logger.add(sys.stdout, level=level)  # лог у консоль
    logger.add(
        log_file,
        level=level,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        enqueue=True,
    )

    logger.debug("Logging initialized. Level: {}", level)
