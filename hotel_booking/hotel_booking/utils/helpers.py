"""General-purpose helpers: password hashing, formatting, model building."""
import hashlib
import hmac
import logging
import os
import re
from datetime import datetime

from utils.constants import (
    CURRENCY_SYMBOL, DATETIME_FORMAT, PBKDF2_ITERATIONS,
)

logger = logging.getLogger(__name__)
_HASH_SCHEME = "pbkdf2_sha256"


# ----------------------------------------------------------------------
# Password hashing (standard library only)
# ----------------------------------------------------------------------
def _derive_key(password, salt, iterations):
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )


def hash_password(password):
    """Return a salted PBKDF2-SHA256 hash string for ``password``."""
    salt = os.urandom(16)
    digest = _derive_key(password, salt, PBKDF2_ITERATIONS)
    return f"{_HASH_SCHEME}${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password, stored_hash):
    """Check ``password`` against a hash made by ``hash_password``."""
    if not isinstance(password, str) or not isinstance(stored_hash, str):
        return False
    parts = stored_hash.split("$")
    if len(parts) != 4 or parts[0] != _HASH_SCHEME:
        return False
    try:
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected = bytes.fromhex(parts[3])
    except ValueError:
        return False
    return hmac.compare_digest(
        _derive_key(password, salt, iterations), expected
    )


# ----------------------------------------------------------------------
# Formatting
# ----------------------------------------------------------------------
def current_timestamp():
    return datetime.now().strftime(DATETIME_FORMAT)


def format_money(amount):
    if amount is None:
        return "N/A"
    return f"{CURRENCY_SYMBOL}{amount:,.2f}"


def truncate(text, width):
    return text if len(text) <= width else text[: width - 3] + "..."


def natural_sort_key(text):
    """Sort 'room2' before 'room10'."""
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", str(text))]


def format_table(headers, rows, max_col_width=28):
    """Return table lines (header, rule, rows) with aligned columns."""
    text_rows = [[truncate(str(cell), max_col_width) for cell in row]
                 for row in rows]
    widths = [len(header) for header in headers]
    for row in text_rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def render(cells):
        return "  ".join(
            cell.ljust(widths[i]) for i, cell in enumerate(cells)
        ).rstrip()

    lines = [render(headers), "  ".join("-" * width for width in widths)]
    lines.extend(render(row) for row in text_rows)
    return lines


# ----------------------------------------------------------------------
# Record -> model conversion
# ----------------------------------------------------------------------
def build_models(records, builder, label="record"):
    """Convert records to models, logging (not hiding) invalid ones."""
    models = []
    for record in records:
        try:
            models.append(builder(record))
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Skipping invalid %s %r: %s", label, record, exc)
    return models
