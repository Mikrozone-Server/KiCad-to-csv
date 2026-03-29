"""Logging configuration.

Usage:
    from src.core.logger import get_logger
    logger = get_logger(__name__)
"""

from datetime import datetime
import logging
import os
from pathlib import Path
import sys

LOGGER_LOGFILE_NAME_TEMPLATE = "kicad-csv_{timestamp}.log"
LOGGER_MESSAGE_FORMAT = "[%(levelname)-7s] %(message)s"

# (tag_name, hex_colour, ANSI_colour_code)
LOGGER_LEVEL_STYLES: dict[int, tuple[str, str, str]] = {
    logging.DEBUG:    ("debug",    "#858585", "\033[90m"),
    logging.INFO:     ("info",     "#d4d4d4", "\033[97m"),
    logging.WARNING:  ("warning",  "#dcdcaa", "\033[93m"),
    logging.ERROR:    ("error",    "#f44747", "\033[91m"),
    logging.CRITICAL: ("critical", "#ff0000", "\033[31;1m"),
}
_ANSI_RESET = "\033[0m"


class _ColourFormatter(logging.Formatter):
    """Formatter that prepends ANSI colour codes when writing to a TTY."""

    def format(self, record: logging.LogRecord) -> str:
        text = super().format(record)
        _, _, ansi = LOGGER_LEVEL_STYLES.get(record.levelno, ("info", "", ""))
        return f"{ansi}{text}{_ANSI_RESET}" if ansi else text


def _ansi_supported(stream) -> bool:
    """Return True if the stream supports ANSI escape codes.

    On Windows, attempts to enable Virtual Terminal Processing for the
    underlying console handle. Falls back to False on any failure.
    """
    if not stream.isatty():
        return False
    if os.name != "nt":
        return True
    try:
        import ctypes
        import ctypes.wintypes
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-12)  # STD_ERROR_HANDLE
        mode = ctypes.wintypes.DWORD()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        if mode.value & ENABLE_VIRTUAL_TERMINAL_PROCESSING:
            return True
        return bool(kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING))
    except Exception:
        return False

def resolve_log_file() -> Path:
    """Return a timestamped log file path in the current working directory."""
    return Path.cwd() / LOGGER_LOGFILE_NAME_TEMPLATE.format(timestamp=datetime.now().strftime('%Y%m%d-%H%M%S'))


def setup_logging(level: int = logging.INFO, log_to_file: bool = False) -> None:
    if log_to_file:
        handler: logging.Handler = logging.FileHandler(resolve_log_file(), mode="w")
        handler.setFormatter(logging.Formatter(LOGGER_MESSAGE_FORMAT))
    else:
        handler = logging.StreamHandler(sys.stderr)
        fmt_cls = _ColourFormatter if _ansi_supported(sys.stderr) else logging.Formatter
        handler.setFormatter(fmt_cls(LOGGER_MESSAGE_FORMAT))

    logging.basicConfig(
        level=level,
        handlers=[handler],
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


# Initialize default logging configuration
setup_logging()
