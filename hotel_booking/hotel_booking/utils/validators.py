"""Reusable input validation functions.

Every validator takes a raw value, returns the cleaned value and raises
``ValidationError`` with a friendly message when the value is invalid.
"""
import math
import re
from datetime import date, datetime

from utils.constants import (
    DATE_FORMAT, MAX_FLOOR, MAX_GUESTS, MAX_PRICE_PER_NIGHT,
    MAX_ROOM_CAPACITY, MAX_STAY_NIGHTS, MIN_PASSWORD_LENGTH,
)
from utils.exceptions import ValidationError

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.]{3,20}$")
PHONE_CHARS_PATTERN = re.compile(r"^[+0-9()\-\s]+$")
ROOM_NUMBER_PATTERN = re.compile(r"^[A-Za-z0-9\-]{1,10}$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
INVALID_NUMBER_MESSAGE = "Invalid input. Please enter a valid number."


# ----------------------------------------------------------------------
# Generic validators
# ----------------------------------------------------------------------
def require_text(value, field_name="Value", min_length=1, max_length=100):
    text = "" if value is None else str(value).strip()
    if not text:
        raise ValidationError(f"{field_name} cannot be empty.")
    if len(text) < min_length:
        raise ValidationError(
            f"{field_name} must be at least {min_length} characters long."
        )
    if len(text) > max_length:
        raise ValidationError(
            f"{field_name} cannot be longer than {max_length} characters."
        )
    return text


def validate_integer(value, field_name="Value", minimum=None, maximum=None):
    text = require_text(value, field_name)
    try:
        number = int(text)
    except ValueError:
        raise ValidationError(INVALID_NUMBER_MESSAGE) from None
    if minimum is not None and number < minimum:
        raise ValidationError(f"{field_name} must be at least {minimum}.")
    if maximum is not None and number > maximum:
        raise ValidationError(f"{field_name} cannot be greater than {maximum}.")
    return number


def validate_positive_int(value, field_name="Value", maximum=None):
    number = validate_integer(value, field_name, maximum=maximum)
    if number <= 0:
        raise ValidationError(f"{field_name} must be a positive number.")
    return number


def validate_positive_float(value, field_name="Value", maximum=None):
    text = require_text(value, field_name)
    try:
        number = float(text)
    except ValueError:
        raise ValidationError(INVALID_NUMBER_MESSAGE) from None
    if not math.isfinite(number):
        raise ValidationError(INVALID_NUMBER_MESSAGE)
    if number <= 0:
        raise ValidationError(f"{field_name} must be a positive number.")
    if maximum is not None and number > maximum:
        raise ValidationError(f"{field_name} cannot be greater than {maximum}.")
    return round(number, 2)


def validate_choice(value, choices, field_name="Option"):
    """Case-insensitive choice check; returns the canonical spelling."""
    text = require_text(value, field_name)
    lookup = {choice.lower(): choice for choice in choices}
    if text.lower() not in lookup:
        raise ValidationError(
            f"Invalid {field_name}. Choose one of: {', '.join(choices)}."
        )
    return lookup[text.lower()]


def validate_id(value, field_name="ID"):
    try:
        return validate_positive_int(value, field_name)
    except ValidationError:
        raise ValidationError(
            f"{field_name} must be a valid positive number."
        ) from None


# ----------------------------------------------------------------------
# Dates
# ----------------------------------------------------------------------
def validate_date(value, field_name="Date"):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = require_text(value, field_name)
    label = field_name.lower()
    if not DATE_PATTERN.match(text):
        raise ValidationError(
            f"Invalid {label}. Use the format YYYY-MM-DD (e.g. 2026-10-10)."
        )
    try:
        return datetime.strptime(text, DATE_FORMAT).date()
    except ValueError:
        raise ValidationError(
            f"Invalid {label}: that calendar date does not exist."
        ) from None


def validate_check_in(value, today):
    check_in = validate_date(value, "Check-in date")
    if check_in < today:
        raise ValidationError("Check-in date cannot be in the past.")
    return check_in


def validate_stay_dates(check_in, check_out, today):
    """Validate a stay and return (check_in, check_out, nights)."""
    check_in_date = validate_check_in(check_in, today)
    check_out_date = validate_date(check_out, "Check-out date")
    if check_out_date <= check_in_date:
        raise ValidationError("Check-out date must be after the check-in date.")
    nights = (check_out_date - check_in_date).days
    if nights > MAX_STAY_NIGHTS:
        raise ValidationError(
            f"A single stay cannot exceed {MAX_STAY_NIGHTS} nights."
        )
    return check_in_date, check_out_date, nights


# ----------------------------------------------------------------------
# User fields
# ----------------------------------------------------------------------
def validate_full_name(value):
    name = " ".join(require_text(value, "Full name", 2, 60).split())
    if not any(char.isalpha() for char in name):
        raise ValidationError("Full name must contain letters.")
    return name


def validate_username(value):
    text = require_text(value, "Username")
    if not USERNAME_PATTERN.match(text):
        raise ValidationError(
            "Username must be 3-20 characters: letters, digits, '_' or '.'."
        )
    return text.lower()


def validate_email(value):
    text = require_text(value, "Email", max_length=100)
    if not EMAIL_PATTERN.match(text):
        raise ValidationError("Invalid email address (example: name@mail.com).")
    return text.lower()


def validate_phone(value):
    text = require_text(value, "Phone", max_length=25)
    digits = re.sub(r"\D", "", text)
    if not PHONE_CHARS_PATTERN.match(text) or not 7 <= len(digits) <= 15:
        raise ValidationError(
            "Invalid phone number. Use 7-15 digits (spaces, '+', '-' allowed)."
        )
    return text


def validate_password(value):
    if value is None or not isinstance(value, str) or not value:
        raise ValidationError("Password cannot be empty.")
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValidationError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
        )
    has_letter = any(char.isalpha() for char in value)
    has_digit = any(char.isdigit() for char in value)
    if not (has_letter and has_digit):
        raise ValidationError("Password must contain both letters and digits.")
    return value


# ----------------------------------------------------------------------
# Room fields
# ----------------------------------------------------------------------
def validate_room_number(value):
    text = require_text(value, "Room number")
    if not ROOM_NUMBER_PATTERN.match(text):
        raise ValidationError(
            "Room number must be 1-10 characters: letters, digits or '-'."
        )
    return text.upper()


def validate_price(value):
    return validate_positive_float(value, "Price", MAX_PRICE_PER_NIGHT)


def validate_capacity(value):
    return validate_positive_int(value, "Capacity", MAX_ROOM_CAPACITY)


def validate_floor(value):
    return validate_integer(value, "Floor", minimum=0, maximum=MAX_FLOOR)


def validate_guests(value):
    return validate_positive_int(value, "Number of guests", MAX_GUESTS)


def validate_description(value):
    text = "" if value is None else str(value).strip()
    if len(text) > 200:
        raise ValidationError("Description cannot exceed 200 characters.")
    return text
