"""Low-level console helpers: output, prompts, menus, error handling."""
import getpass
import logging
import sys

from utils.exceptions import HotelError, ValidationError
from utils.helpers import format_table
from utils.validators import require_text

logger = logging.getLogger(__name__)

WIDTH = 60
CANCEL_KEYWORD = "/cancel"


class OperationCancelled(Exception):
    """Raised when the user types /cancel at a prompt."""


# ----------------------------------------------------------------------
# Output
# ----------------------------------------------------------------------
def _can_print(text):
    encoding = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        text.encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return False
    return True


def print_header(title):
    print()
    print("=" * WIDTH)
    print(title.center(WIDTH))
    print("=" * WIDTH)


def print_divider(char="-"):
    print(char * WIDTH)


def print_success(message):
    mark = "\u2713" if _can_print("\u2713") else "OK"
    print(f"[{mark}] {message}")


def print_error(message):
    print(f"[ERROR] {message}")


def print_warning(message):
    print(f"[WARNING] {message}")


def print_info(message):
    print(f"[INFO] {message}")


def pause():
    input("\nPress Enter to continue...")


def show_table(headers, rows, empty_message="Nothing to display."):
    if not rows:
        print_info(empty_message)
        return
    print()
    for line in format_table(headers, rows):
        print(line)
    print(f"\n{len(rows)} record(s).")


def show_key_values(pairs, indent=2):
    width = max(len(label) for label, _ in pairs)
    for label, value in pairs:
        print(f"{' ' * indent}{label.ljust(width)} : {value}")


# ----------------------------------------------------------------------
# Input
# ----------------------------------------------------------------------
def prompt_value(label, validator=None, allow_blank=False):
    """Ask until the validator accepts the input.

    Returns None for blank input when ``allow_blank`` is True.
    Typing /cancel aborts the current operation.
    """
    while True:
        raw = input(f"{label}: ").strip()
        if raw.lower() == CANCEL_KEYWORD:
            raise OperationCancelled()
        if raw == "" and allow_blank:
            return None
        try:
            if validator is None:
                return require_text(raw, "This field")
            return validator(raw)
        except ValidationError as exc:
            print_error(str(exc))


def read_password(label="Password"):
    raw = getpass.getpass(f"{label}: ")
    if raw.strip().lower() == CANCEL_KEYWORD:
        raise OperationCancelled()
    return raw


def confirm(question):
    while True:
        answer = input(f"{question} (Y/N): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print_error("Please answer Y or N.")


def choose_option(options, title=None, welcome=None):
    """Show a numbered menu and return the chosen 1-based number."""
    if title:
        print_header(title)
    if welcome:
        print(f"\n{welcome}")
    print()
    for number, label in enumerate(options, start=1):
        print(f"{number}. {label}")
    print()
    while True:
        raw = input("Choose an option: ").strip()
        try:
            choice = int(raw)
        except ValueError:
            print_error("Invalid input. Please enter a valid number.")
            continue
        if 1 <= choice <= len(options):
            return choice
        print_error(f"Invalid option. Choose a number from 1 to "
                    f"{len(options)}.")


def run_action(action, *args, **kwargs):
    """Run a UI action; show friendly errors instead of crashing."""
    try:
        return action(*args, **kwargs)
    except OperationCancelled:
        print_info("Operation cancelled.")
    except HotelError as exc:
        print_error(str(exc))
    except EOFError:
        raise
    except Exception as exc:  # last-resort guard, always logged
        logger.exception("Unexpected error in %s", getattr(
            action, "__name__", action))
        print_error(f"Unexpected error: {exc}. Details were written to the "
                    "error log.")
    return None


def run_submenu(title, entries, back_label="Back"):
    """Loop over a menu of (label, handler, pause_afterwards) entries."""
    labels = [label for label, _, _ in entries] + [back_label]
    while True:
        choice = choose_option(labels, title=title)
        if choice == len(labels):
            return
        _, handler, should_pause = entries[choice - 1]
        run_action(handler)
        if should_pause:
            pause()
