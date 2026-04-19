"""Loguru logging setup."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from loguru import logger

PACKAGE = "adomcore"

logger.disable(PACKAGE)


def setup_logging(
    log_dir: Path, level: str = "INFO", *, takeover_logging: bool = False
) -> None:
    if takeover_logging:
        log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        logger.enable(PACKAGE)
        logger.remove()
        logger.add(sys.stderr, level=level)
        logger.add(log_dir / f"{stamp}.log", level="DEBUG", rotation=None)
