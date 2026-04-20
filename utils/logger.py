import logging
import logging.handlers
import os
import re

_KEY_PATTERN = re.compile(r'[A-Za-z0-9_\-]{20,}')


class _SanitizingFilter(logging.Filter):
    """Masks potential API keys in log records."""

    def filter(self, record):
        record.msg = _KEY_PATTERN.sub("***REDACTED***", str(record.msg))
        return True


def setup_logger(app_dir: str) -> logging.Logger:
    log_dir = os.path.join(app_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "yapclean.log")

    logger = logging.getLogger("yapclean")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        # File handler with rotation
        fh = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        fh.addFilter(_SanitizingFilter())

        # Console handler (INFO and above)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        ch.addFilter(_SanitizingFilter())

        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger


def get_logger(name: str = "yapclean") -> logging.Logger:
    return logging.getLogger(name)
