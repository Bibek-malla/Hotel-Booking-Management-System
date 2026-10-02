"""User models. Customer and Manager differ in role and permissions."""
from utils.constants import (
    PERM_CANCEL_OWN_BOOKING, PERM_CREATE_BOOKING, PERM_EDIT_OWN_PROFILE,
    PERM_MANAGE_BOOKINGS, PERM_MANAGE_CUSTOMERS, PERM_MANAGE_ROOMS,
    PERM_VIEW_OWN_BOOKINGS, PERM_VIEW_REPORTS, PERM_VIEW_ROOMS,
    ROLE_CUSTOMER, ROLE_MANAGER,
)
from utils.helpers import (
    current_timestamp, hash_password, verify_password,
)


class User:
    """Base user. The password hash is kept private to the object."""

    ROLE = ""
    PERMISSIONS = frozenset()

    def __init__(self, user_id, full_name, username, email, password_hash,
                 phone="", created_at=None, is_active=True):
        self.user_id = user_id
        self.full_name = full_name
        self.username = username
        self.email = email
        self._password_hash = password_hash
        self.phone = phone
        self.created_at = created_at or current_timestamp()
        self.is_active = is_active

    @property
    def role(self):
        return self.ROLE

    @property
    def password_hash(self):
        return self._password_hash

    @property
    def greeting_name(self):
        """Name shown on the dashboard (polymorphic)."""
        return self.full_name

    def has_permission(self, permission):
        return permission in self.PERMISSIONS

    def verify_password(self, plain_password):
        return verify_password(plain_password, self._password_hash)

    def set_password(self, plain_password):
        self._password_hash = hash_password(plain_password)

    def update_details(self, full_name=None, email=None, phone=None):
        if full_name is not None:
            self.full_name = full_name
        if email is not None:
            self.email = email
        if phone is not None:
            self.phone = phone

    def sync_from(self, other):
        """Copy mutable fields from a freshly loaded copy of this user."""
        self.full_name = other.full_name
        self.email = other.email
        self.phone = other.phone
        self.is_active = other.is_active
        self._password_hash = other.password_hash

    def to_dict(self):
        """Full record for storage (includes the password hash)."""
        return {
            "user_id": self.user_id,
            "full_name": self.full_name,
            "username": self.username,
            "email": self.email,
            "password_hash": self._password_hash,
            "role": self.role,
            "phone": self.phone,
            "created_at": self.created_at,
            "is_active": self.is_active,
        }

    def to_public_dict(self):
        """Record safe to display: never contains the password hash."""
        data = self.to_dict()
        del data["password_hash"]
        return data

    @classmethod
    def from_dict(cls, data):
        """Build the right subclass for the stored role."""
        role_class = _ROLE_CLASSES.get(data.get("role"))
        if role_class is None:
            raise ValueError(f"Unknown role: {data.get('role')!r}")
        return role_class(
            user_id=int(data["user_id"]),
            full_name=str(data["full_name"]),
            username=str(data["username"]),
            email=str(data["email"]),
            password_hash=str(data["password_hash"]),
            phone=str(data.get("phone", "")),
            created_at=data.get("created_at"),
            is_active=bool(data.get("is_active", True)),
        )


class Customer(User):
    ROLE = ROLE_CUSTOMER
    PERMISSIONS = frozenset({
        PERM_VIEW_ROOMS, PERM_CREATE_BOOKING, PERM_VIEW_OWN_BOOKINGS,
        PERM_CANCEL_OWN_BOOKING, PERM_EDIT_OWN_PROFILE,
    })


class Manager(User):
    ROLE = ROLE_MANAGER
    PERMISSIONS = frozenset({
        PERM_VIEW_ROOMS, PERM_MANAGE_ROOMS, PERM_MANAGE_CUSTOMERS,
        PERM_MANAGE_BOOKINGS, PERM_VIEW_REPORTS, PERM_EDIT_OWN_PROFILE,
    })

    @property
    def greeting_name(self):
        return "Manager"


_ROLE_CLASSES = {ROLE_CUSTOMER: Customer, ROLE_MANAGER: Manager}
