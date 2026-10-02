"""Access to stored users (shared by auth and customer services)."""
from models.user import User
from utils.constants import ROLE_CUSTOMER
from utils.exceptions import ValidationError
from utils.helpers import build_models


class UserRepository:
    def __init__(self, store):
        self._store = store

    def all_users(self):
        return build_models(self._store.read_all(), User.from_dict, "user")

    def customers(self):
        return [u for u in self.all_users() if u.role == ROLE_CUSTOMER]

    def get_by_id(self, user_id):
        record = self._store.get(user_id)
        if record is None:
            return None
        users = build_models([record], User.from_dict, "user")
        return users[0] if users else None

    def get_by_username(self, username):
        wanted = str(username).strip().lower()
        for user in self.all_users():
            if user.username.lower() == wanted:
                return user
        return None

    def get_by_email(self, email):
        wanted = str(email).strip().lower()
        for user in self.all_users():
            if user.email.lower() == wanted:
                return user
        return None

    def add(self, user):
        stored = self._store.add(user.to_dict())
        user.user_id = stored[self._store.id_field]
        return user

    def save(self, user):
        self._store.update(user.user_id, user.to_dict())

    def ensure_unique(self, username=None, email=None, exclude_user_id=None):
        """Raise ValidationError if the username/email is already used."""
        if username is not None:
            owner = self.get_by_username(username)
            if owner and owner.user_id != exclude_user_id:
                raise ValidationError(
                    f"The username '{username}' is already taken."
                )
        if email is not None:
            owner = self.get_by_email(email)
            if owner and owner.user_id != exclude_user_id:
                raise ValidationError(
                    f"The email '{email}' is already registered."
                )
