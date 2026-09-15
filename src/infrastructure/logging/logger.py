import logging
from pathlib import Path


class Logger:
    """Centralized logging configuration"""

    _configured = False

    @staticmethod
    def setup():
        """
            Purpose: This function configures the logging.
            Args:
                :none
            Created at: 2026-01-23 | Ehg
        """
        if Logger._configured:
            return

        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "data_monitoring_extraction.log"

        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(message)s"
        )

        Logger._configured = True

    @staticmethod
    def log_task(level: str, message: str, task: str = "EXTRACTION"):
        """Log message with task context"""
        logger = logging.getLogger(__name__)
        log_func = getattr(logger, level.lower())
        log_func(message)