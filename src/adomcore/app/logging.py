"""Loguru logging setup."""

import sys
from datetime import datetime
from pathlib import Path

from loguru import logger


def setup_logging(log_dir: Path, level: str = "INFO") -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    logger.remove()
    logger.add(sys.stderr, level=level, serialize=False)
    logger.add(log_dir / f"{stamp}.log", level=level, serialize=False, rotation=None)
    logger.add(
        log_dir / f"{stamp}-errors.log", level="ERROR", serialize=False, rotation=None
    )
