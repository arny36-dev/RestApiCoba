"""Nastavenie logovania aplikácie.

Logy sú jednoduché, po slovensky a hovoria presne, čo sa stalo.
Zapisujú sa do konzoly aj do rotujúceho súboru v LOG_DIR (10 MB x 5 záloh).
Technické hlášky knižníc (SQL, drivery) sú vypnuté — zapnú sa len cez LOG_SQL=true.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
DATE_FORMAT = "%d.%m.%Y %H:%M:%S"

# Slovenské názvy úrovní, nech je hneď jasné, o čo ide.
logging.addLevelName(logging.WARNING, "POZOR")
logging.addLevelName(logging.ERROR, "CHYBA")
logging.addLevelName(logging.CRITICAL, "KRITICKÁ CHYBA")

# Knižnice, ktorých technické hlášky bežného čitateľa logu nezaujímajú.
NOISY_LOGGERS = ("sqlalchemy.engine", "aiosqlite", "aiomysql", "asyncio", "httpx")


def setup_logging(*, log_dir: str = "logs", log_sql: bool = False) -> None:
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    directory = Path(log_dir)
    directory.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        directory / "app.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(console)
    root.addHandler(file_handler)

    for name in NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
    if log_sql:
        # Voliteľné: LOG_SQL=true zapne výpis každého SQL príkazu.
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
