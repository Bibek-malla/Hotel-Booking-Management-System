"""Reusable prompt validators and small input forms."""
from ui.console import (
    print_error, prompt_value, read_password,
)
from utils.exceptions import ValidationError
from utils.validators import (
    validate_check_in, validate_choice, validate_email, validate_password,
    validate_stay_dates, validate_username,
)


def username_validator(ctx):
    def _validate(value):
        username = validate_username(value)
        ctx.users.ensure_unique(username=username)
        return username
    return _validate


def email_validator(ctx, exclude_user_id=None):
    def _validate(value):
        email = validate_email(value)
        ctx.users.ensure_unique(email=email, exclude_user_id=exclude_user_id)
        return email
    return _validate


def room_number_validator(ctx, exclude_room_id=None):
    def _validate(value):
        return ctx.rooms.ensure_room_number_available(
            value, exclude_room_id)
    return _validate


def choice_validator(choices, field_name):
    return lambda value: validate_choice(value, choices, field_name)


def ask_new_password(label="Password"):
    """Prompt for a new password twice until valid and matching."""
    while True:
        password = read_password(f"{label} (min 6 chars, letters + digits)")
        try:
            validate_password(password)
        except ValidationError as exc:
            print_error(str(exc))
            continue
        if read_password("Confirm password") != password:
            print_error("Passwords do not match. Please try again.")
            continue
        return password


def ask_stay_dates(ctx):
    """Prompt for check-in and check-out, validating each in context."""
    today = ctx.today()
    check_in = prompt_value(
        "Check-in date (YYYY-MM-DD)",
        lambda value: validate_check_in(value, today))
    check_out = prompt_value(
        "Check-out date (YYYY-MM-DD)",
        lambda value: validate_stay_dates(check_in, value, today)[1])
    return check_in, check_out
