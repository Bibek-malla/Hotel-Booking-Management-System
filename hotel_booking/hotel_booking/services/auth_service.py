"""Registration, login and logout."""
import logging

from models.user import Customer, Manager
from utils.constants import (
    DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_FULL_NAME, DEFAULT_ADMIN_PASSWORD,
    DEFAULT_ADMIN_PHONE, DEFAULT_ADMIN_USERNAME, ROLE_MANAGER,
)
from utils.exceptions import AuthenticationError
from utils.helpers import hash_password
from utils.validators import (
    validate_email, validate_full_name, validate_password, validate_phone,
    validate_username,
)

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, user_repository):
        self._users = user_repository
        self._current_user = None

    @property
    def current_user(self):
        return self._current_user

    def ensure_default_manager(self):
        """Create the default admin account when no manager exists."""
        if any(u.role == ROLE_MANAGER for u in self._users.all_users()):
            return None
        if (self._users.get_by_username(DEFAULT_ADMIN_USERNAME)
                or self._users.get_by_email(DEFAULT_ADMIN_EMAIL)):
            logger.warning("Default admin username/email already in use; "
                           "no default manager was created.")
            return None
        manager = Manager(
            user_id=None,
            full_name=DEFAULT_ADMIN_FULL_NAME,
            username=DEFAULT_ADMIN_USERNAME,
            email=DEFAULT_ADMIN_EMAIL,
            password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
            phone=DEFAULT_ADMIN_PHONE,
        )
        return self._users.add(manager)

    def register_customer(self, full_name, username, email, password, phone):
        """Create a new Customer account (managers are never self-created)."""
        full_name = validate_full_name(full_name)
        username = validate_username(username)
        email = validate_email(email)
        phone = validate_phone(phone)
        password = validate_password(password)
        self._users.ensure_unique(username=username, email=email)
        customer = Customer(
            user_id=None,
            full_name=full_name,
            username=username,
            email=email,
            password_hash=hash_password(password),
            phone=phone,
        )
        return self._users.add(customer)

    def login(self, username, password):
        user = self._users.get_by_username(username) if username else None
        if user is None or not user.verify_password(password):
            raise AuthenticationError("Invalid username or password.")
        if not user.is_active:
            raise AuthenticationError(
                "This account has been deactivated. Please contact the manager."
            )
        self._current_user = user
        return user

    def logout(self):
        self._current_user = None
