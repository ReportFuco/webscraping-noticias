import logging
from pathlib import Path


def setup_logging(log_level: str = "INFO", log_file: str | None = None) -> logging.Logger:
    root_logger = logging.getLogger()
    level = getattr(logging, log_level.upper(), logging.INFO)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if not root_logger.handlers:
        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        root_logger.addHandler(sh)

    if log_file:
        log_path = Path(log_file).resolve()
        already = any(
            isinstance(h, logging.FileHandler)
            and Path(h.baseFilename).resolve() == log_path
            for h in root_logger.handlers
        )
        if not already:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(log_path, encoding="utf-8")
            fh.setFormatter(formatter)
            root_logger.addHandler(fh)

    root_logger.setLevel(level)
    return root_logger
