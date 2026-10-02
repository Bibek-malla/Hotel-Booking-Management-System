"""Role-based access control helpers used by every service."""
from models.user import User
from utils.exceptions import AuthenticationError, AuthorizationError


def require_login(actor):
    """Ensure ``actor`` is a real, active, logged-in user."""
    if not isinstance(actor, User):
        raise AuthenticationError("You must be logged in to do that.")
    if not actor.is_active:
        raise AuthenticationError("This account has been deactivated.")
    return actor


def require_permission(actor, permission, action="perform this action"):
    """Ensure ``actor`` is logged in and holds ``permission``."""
    require_login(actor)
    if not actor.has_permission(permission):
        raise AuthorizationError(
            f"Access denied: the {actor.role} role cannot {action}."
        )
    return actor
