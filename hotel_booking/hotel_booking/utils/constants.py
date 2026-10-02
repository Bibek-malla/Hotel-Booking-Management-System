"""Application-wide constants (single source of truth for business rules)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
# HOTEL_DATA_DIR lets you point the app at another folder (useful for tests).
DATA_DIR = Path(os.environ.get("HOTEL_DATA_DIR", BASE_DIR / "data"))
USERS_FILE_NAME = "users.json"
ROOMS_FILE_NAME = "rooms.json"
BOOKINGS_FILE_NAME = "bookings.json"
ERROR_LOG_NAME = "error.log"

# Roles
ROLE_MANAGER = "Manager"
ROLE_CUSTOMER = "Customer"

# Rooms
ROOM_TYPES = ("Single", "Double", "Deluxe", "Suite")
ROOM_STATUS_AVAILABLE = "Available"
ROOM_STATUS_MAINTENANCE = "Maintenance"
ROOM_STATUS_INACTIVE = "Inactive"
ROOM_STATUSES = (
    ROOM_STATUS_AVAILABLE,
    ROOM_STATUS_MAINTENANCE,
    ROOM_STATUS_INACTIVE,
)

# Bookings
BOOKING_PENDING = "Pending"
BOOKING_CONFIRMED = "Confirmed"
BOOKING_CANCELLED = "Cancelled"
BOOKING_COMPLETED = "Completed"
BOOKING_STATUSES = (
    BOOKING_PENDING,
    BOOKING_CONFIRMED,
    BOOKING_CANCELLED,
    BOOKING_COMPLETED,
)
ACTIVE_BOOKING_STATUSES = (BOOKING_PENDING, BOOKING_CONFIRMED)
HISTORY_BOOKING_STATUSES = (BOOKING_COMPLETED, BOOKING_CANCELLED)
REVENUE_BOOKING_STATUSES = (BOOKING_CONFIRMED, BOOKING_COMPLETED)

# Formats
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
CURRENCY_SYMBOL = "$"

# Limits
MIN_PASSWORD_LENGTH = 6
PBKDF2_ITERATIONS = 150_000
MAX_LOGIN_ATTEMPTS = 3
MAX_FLOOR = 100
MAX_ROOM_CAPACITY = 20
MAX_GUESTS = MAX_ROOM_CAPACITY
MAX_PRICE_PER_NIGHT = 100_000
MAX_STAY_NIGHTS = 90

# Permissions (role-based access control)
PERM_VIEW_ROOMS = "view_rooms"
PERM_MANAGE_ROOMS = "manage_rooms"
PERM_MANAGE_CUSTOMERS = "manage_customers"
PERM_MANAGE_BOOKINGS = "manage_bookings"
PERM_VIEW_REPORTS = "view_reports"
PERM_CREATE_BOOKING = "create_booking"
PERM_VIEW_OWN_BOOKINGS = "view_own_bookings"
PERM_CANCEL_OWN_BOOKING = "cancel_own_booking"
PERM_EDIT_OWN_PROFILE = "edit_own_profile"

# Default manager account created on first start
DEFAULT_ADMIN_FULL_NAME = "System Administrator"
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
DEFAULT_ADMIN_EMAIL = "admin@hotel.local"
DEFAULT_ADMIN_PHONE = "5550100000"

# Sample rooms created when rooms.json is empty
SAMPLE_ROOMS = (
    {"room_number": "101", "room_type": "Single", "price_per_night": 45.0,
     "capacity": 1, "floor": 1,
     "description": "Cozy single room with a work desk."},
    {"room_number": "102", "room_type": "Double", "price_per_night": 70.0,
     "capacity": 2, "floor": 1,
     "description": "Double room with a queen bed and city view."},
    {"room_number": "201", "room_type": "Deluxe", "price_per_night": 95.0,
     "capacity": 3, "floor": 2,
     "description": "Spacious deluxe room with a balcony."},
    {"room_number": "202", "room_type": "Deluxe", "price_per_night": 105.0,
     "capacity": 3, "floor": 2,
     "description": "Deluxe corner room with extra natural light."},
    {"room_number": "301", "room_type": "Suite", "price_per_night": 180.0,
     "capacity": 4, "floor": 3,
     "description": "Top-floor suite with living area and minibar."},
)
