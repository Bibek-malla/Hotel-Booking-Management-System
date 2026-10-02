"""Custom exception hierarchy for the application."""


class HotelError(Exception):
    """Base class for all expected, user-facing application errors."""


class ValidationError(HotelError, ValueError):
    """Raised when user-supplied data is invalid."""


class AuthenticationError(HotelError):
    """Raised when login fails or no user is logged in."""


class AuthorizationError(HotelError):
    """Raised when a user lacks permission for an operation."""


class NotFoundError(HotelError):
    """Raised when a requested record does not exist."""


class BookingError(HotelError):
    """Raised when a booking rule is violated."""


class DataStoreError(HotelError):
    """Raised when the JSON data files cannot be read or written."""
