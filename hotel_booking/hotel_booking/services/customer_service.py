"""Customer management (manager) and profile management (customer)."""
from services.authorization import require_permission
from utils.constants import (
    ACTIVE_BOOKING_STATUSES, BOOKING_COMPLETED, BOOKING_CONFIRMED,
    PERM_EDIT_OWN_PROFILE, PERM_MANAGE_CUSTOMERS, ROLE_CUSTOMER,
)
from utils.exceptions import (
    AuthenticationError, NotFoundError, ValidationError,
)
from utils.validators import (
    require_text, validate_email, validate_full_name, validate_id,
    validate_password, validate_phone,
)


class CustomerService:
    def __init__(self, user_repository, booking_store):
        self._users = user_repository
        self._bookings = booking_store

    # ------------------------------------------------------------------
    # Manager operations
    # ------------------------------------------------------------------
    def _require_customer(self, customer_id):
        user = self._users.get_by_id(validate_id(customer_id, "Customer ID"))
        if user is None or user.role != ROLE_CUSTOMER:
            raise NotFoundError("Customer not found.")
        return user

    def list_customers(self, actor):
        require_permission(actor, PERM_MANAGE_CUSTOMERS, "view customers")
        return [c.to_public_dict() for c in self._users.customers()]

    def search_customers(self, actor, keyword=None, active=None):
        """Case-insensitive search on name, username, email, phone, id."""
        require_permission(actor, PERM_MANAGE_CUSTOMERS, "search customers")
        customers = self._users.customers()
        if keyword:
            needle = require_text(keyword, "Keyword").lower()
            customers = [
                c for c in customers
                if needle in c.full_name.lower()
                or needle in c.username.lower()
                or needle in c.email.lower()
                or needle in c.phone.lower()
                or needle == str(c.user_id)
            ]
        if active is not None:
            customers = [c for c in customers if c.is_active == active]
        return [c.to_public_dict() for c in customers]

    def get_customer(self, actor, customer_id):
        """Customer details plus booking statistics (no password hash)."""
        require_permission(actor, PERM_MANAGE_CUSTOMERS, "view customers")
        customer = self._require_customer(customer_id)
        records = [r for r in self._bookings.read_all()
                   if r.get("customer_id") == customer.user_id]
        details = customer.to_public_dict()
        details["total_bookings"] = len(records)
        details["active_bookings"] = sum(
            1 for r in records
            if r.get("booking_status") in ACTIVE_BOOKING_STATUSES)
        details["total_spent"] = round(sum(
            float(r.get("total_price", 0)) for r in records
            if r.get("booking_status") in (BOOKING_CONFIRMED,
                                           BOOKING_COMPLETED)), 2)
        return details

    def update_customer(self, actor, customer_id, full_name=None, email=None,
                        phone=None):
        require_permission(actor, PERM_MANAGE_CUSTOMERS, "update customers")
        customer = self._require_customer(customer_id)
        self._apply_details(customer, full_name, email, phone)
        return customer.to_public_dict()

    def set_customer_active(self, actor, customer_id, active):
        """Activate/deactivate an account (deactivated users cannot log in)."""
        require_permission(actor, PERM_MANAGE_CUSTOMERS,
                           "change account status")
        customer = self._require_customer(customer_id)
        customer.is_active = bool(active)
        self._users.save(customer)
        return customer.to_public_dict()

    # ------------------------------------------------------------------
    # Own profile (any logged-in user with the profile permission)
    # ------------------------------------------------------------------
    def _load_self(self, actor):
        require_permission(actor, PERM_EDIT_OWN_PROFILE, "edit a profile")
        fresh = self._users.get_by_id(actor.user_id)
        if fresh is None:
            raise NotFoundError("Your account could not be found.")
        return fresh

    def get_profile(self, actor):
        return self._load_self(actor).to_public_dict()

    def update_profile(self, actor, full_name=None, email=None, phone=None):
        fresh = self._load_self(actor)
        self._apply_details(fresh, full_name, email, phone)
        actor.sync_from(fresh)
        return fresh.to_public_dict()

    def change_password(self, actor, current_password, new_password):
        fresh = self._load_self(actor)
        if not fresh.verify_password(current_password):
            raise AuthenticationError("Current password is incorrect.")
        new_password = validate_password(new_password)
        if new_password == current_password:
            raise ValidationError(
                "The new password must be different from the current one.")
        fresh.set_password(new_password)
        self._users.save(fresh)
        actor.sync_from(fresh)

    # ------------------------------------------------------------------
    def _apply_details(self, user, full_name, email, phone):
        """Validate and save the provided (non-None) profile fields."""
        new_name = validate_full_name(full_name) if full_name is not None \
            else None
        new_email = validate_email(email) if email is not None else None
        new_phone = validate_phone(phone) if phone is not None else None
        if new_email is not None:
            self._users.ensure_unique(email=new_email,
                                      exclude_user_id=user.user_id)
        user.update_details(new_name, new_email, new_phone)
        self._users.save(user)
