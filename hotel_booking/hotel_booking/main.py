"""Hotel Booking Management System - run with:  python main.py"""
import logging
import sys

from services.context import ServiceContext
from ui.app import ConsoleApp
from utils.constants import DATA_DIR, ERROR_LOG_NAME
from utils.exceptions import DataStoreError

logger = logging.getLogger(__name__)


def configure_console_encoding():
    """Use UTF-8 so symbols such as the check mark print on any terminal."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError) as exc:
            logger.debug("Could not reconfigure console encoding: %s", exc)


def configure_logging():
    """Send warnings/errors to data/error.log (stderr if not writable)."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(DATA_DIR / ERROR_LOG_NAME,
                                      encoding="utf-8")
    except OSError:
        handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.WARNING, handlers=[handler])


def main():
    configure_console_encoding()
    configure_logging()
    try:
        context = ServiceContext()
        context.initialize()
    except DataStoreError as exc:
        print(f"[ERROR] The application could not start: {exc}")
        return 1

    try:
        ConsoleApp(context).run()
    except (KeyboardInterrupt, EOFError):
        print("\n\nInput closed. Goodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
