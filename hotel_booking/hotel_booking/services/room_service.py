"""Room management and room search."""
from datetime import date

from models.booking import Booking
from models.room import Room
from services.authorization import require_permission
from utils.constants import (
    ACTIVE_BOOKING_STATUSES, PERM_MANAGE_ROOMS, PERM_VIEW_ROOMS,
    ROOM_STATUS_AVAILABLE, ROOM_STATUS_INACTIVE, ROOM_STATUS_MAINTENANCE,
    ROOM_STATUSES, ROOM_TYPES, SAMPLE_ROOMS,
)
from utils.exceptions import (
    BookingError, DataStoreError, NotFoundError, ValidationError,
)
from utils.helpers import build_models, natural_sort_key
from utils.validators import (
    require_text, validate_capacity, validate_choice, validate_description,
    validate_floor, validate_id, validate_positive_float, validate_price,
    validate_room_number,
)


class RoomService:
    def __init__(self, room_store, booking_store, today_provider=date.today):
        self._rooms = room_store
        self._bookings = booking_store
        self._today = today_provider

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_rooms(self):
        return build_models(self._rooms.read_all(), Room.from_dict, "room")

    def _require_room(self, room_id):
        record = self._rooms.get(validate_id(room_id, "Room ID"))
        if record is None:
            raise NotFoundError("Room not found.")
        try:
            return Room.from_dict(record)
        except (KeyError, TypeError, ValueError) as exc:
            raise DataStoreError(f"Room record is corrupted: {exc}") from exc

    def _upcoming_active_bookings(self, room_id):
        """Pending/confirmed bookings of a room that have not ended yet."""
        today = self._today()
        bookings = build_models(
            self._bookings.read_all(), Booking.from_dict, "booking"
        )
        return [
            b for b in bookings
            if b.room_id == room_id
            and b.booking_status in ACTIVE_BOOKING_STATUSES
            and b.check_out > today
        ]

    def _check_update_allowed(self, room, updates):
        upcoming = self._upcoming_active_bookings(room.room_id)
        if not upcoming:
            return
        new_status = updates.get("status")
        if (new_status in (ROOM_STATUS_MAINTENANCE, ROOM_STATUS_INACTIVE)
                and new_status != room.status):
            raise BookingError(
                f"Cannot set room {room.room_number} to {new_status}: it has "
                f"{len(upcoming)} upcoming booking(s). Cancel or complete "
                "them first."
            )
        new_capacity = updates.get("capacity")
        if new_capacity is not None and any(
                b.number_of_guests > new_capacity for b in upcoming):
            raise BookingError(
                "Cannot reduce the capacity below the guest count of an "
                "upcoming booking."
            )

    # ------------------------------------------------------------------
    # Setup / validation helpers (no authorization needed)
    # ------------------------------------------------------------------
    def seed_sample_rooms_if_empty(self):
        """Create demo rooms when rooms.json is empty. Returns count."""
        if self._rooms.read_all():
            return 0
        for sample in SAMPLE_ROOMS:
            room = Room(None, status=ROOM_STATUS_AVAILABLE, **sample)
            self._rooms.add(room.to_dict())
        return len(SAMPLE_ROOMS)

    def ensure_room_number_available(self, room_number, exclude_room_id=None):
        """Validate a room number and make sure it is unique."""
        number = validate_room_number(room_number)
        for room in self._load_rooms():
            if (room.room_id != exclude_room_id
                    and room.room_number.lower() == number.lower()):
                raise ValidationError(f"Room number {number} already exists.")
        return number

    # ------------------------------------------------------------------
    # Manager operations
    # ------------------------------------------------------------------
    def add_room(self, actor, room_number, room_type, price_per_night,
                 capacity, floor, description="",
                 status=ROOM_STATUS_AVAILABLE):
        require_permission(actor, PERM_MANAGE_ROOMS, "add rooms")
        room = Room(
            room_id=None,
            room_number=self.ensure_room_number_available(room_number),
            room_type=validate_choice(room_type, ROOM_TYPES, "room type"),
            price_per_night=validate_price(price_per_night),
            capacity=validate_capacity(capacity),
            floor=validate_floor(floor),
            status=validate_choice(status, ROOM_STATUSES, "room status"),
            description=validate_description(description),
        )
        stored = self._rooms.add(room.to_dict())
        room.room_id = stored["room_id"]
        return room

    def get_all_rooms(self, actor):
        require_permission(actor, PERM_MANAGE_ROOMS, "list all rooms")
        return sorted(self._load_rooms(),
                      key=lambda r: natural_sort_key(r.room_number))

    def update_room(self, actor, room_id, room_number=None, room_type=None,
                    price_per_night=None, capacity=None, floor=None,
                    status=None, description=None):
        """Update only the fields that are not None."""
        require_permission(actor, PERM_MANAGE_ROOMS, "update rooms")
        room = self._require_room(room_id)
        updates = {}
        if room_number is not None:
            updates["room_number"] = self.ensure_room_number_available(
                room_number, room.room_id)
        if room_type is not None:
            updates["room_type"] = validate_choice(
                room_type, ROOM_TYPES, "room type")
        if price_per_night is not None:
            updates["price_per_night"] = validate_price(price_per_night)
        if capacity is not None:
            updates["capacity"] = validate_capacity(capacity)
        if floor is not None:
            updates["floor"] = validate_floor(floor)
        if status is not None:
            updates["status"] = validate_choice(
                status, ROOM_STATUSES, "room status")
        if description is not None:
            updates["description"] = validate_description(description)

        self._check_update_allowed(room, updates)
        for field, value in updates.items():
            setattr(room, field, value)
        self._rooms.update(room.room_id, room.to_dict())
        return room

    def change_status(self, actor, room_id, status):
        return self.update_room(actor, room_id, status=status)

    def delete_room(self, actor, room_id):
        """Delete a room, or deactivate it if bookings reference it.

        Returns "deleted" or "deactivated".
        """
        require_permission(actor, PERM_MANAGE_ROOMS, "delete rooms")
        room = self._require_room(room_id)
        upcoming = self._upcoming_active_bookings(room.room_id)
        if upcoming:
            raise BookingError(
                f"Cannot remove room {room.room_number}: it has "
                f"{len(upcoming)} upcoming booking(s). Cancel or complete "
                "them first."
            )
        has_history = any(r.get("room_id") == room.room_id
                          for r in self._bookings.read_all())
        if has_history:
            room.status = ROOM_STATUS_INACTIVE
            self._rooms.update(room.room_id, room.to_dict())
            return "deactivated"
        self._rooms.delete(room.room_id)
        return "deleted"

    # ------------------------------------------------------------------
    # Operations for any logged-in user
    # ------------------------------------------------------------------
    def get_room(self, actor, room_id):
        require_permission(actor, PERM_VIEW_ROOMS, "view rooms")
        room = self._require_room(room_id)
        if (not actor.has_permission(PERM_MANAGE_ROOMS)
                and not room.is_available):
            raise NotFoundError("Room not found.")
        return room

    def search_rooms(self, actor, room_number=None, room_type=None,
                     min_price=None, max_price=None, min_capacity=None,
                     status=None, keyword=None):
        """Filter rooms. Customers only ever see Available rooms."""
        require_permission(actor, PERM_VIEW_ROOMS, "view rooms")
        is_manager = actor.has_permission(PERM_MANAGE_ROOMS)
        rooms = self._load_rooms()

        if not is_manager:
            rooms = [r for r in rooms if r.is_available]
        elif status:
            wanted = validate_choice(status, ROOM_STATUSES, "room status")
            rooms = [r for r in rooms if r.status == wanted]

        if room_number:
            needle = require_text(room_number, "Room number").lower()
            rooms = [r for r in rooms if needle in r.room_number.lower()]
        if room_type:
            wanted = validate_choice(room_type, ROOM_TYPES, "room type")
            rooms = [r for r in rooms if r.room_type == wanted]
        if min_price is not None:
            low = validate_positive_float(min_price, "Minimum price")
            rooms = [r for r in rooms if r.price_per_night >= low]
        if max_price is not None:
            high = validate_positive_float(max_price, "Maximum price")
            rooms = [r for r in rooms if r.price_per_night <= high]
        if min_capacity is not None:
            capacity = validate_capacity(min_capacity)
            rooms = [r for r in rooms if r.capacity >= capacity]
        if keyword:
            needle = require_text(keyword, "Keyword").lower()
            rooms = [
                r for r in rooms
                if needle in " ".join(
                    (r.room_number, r.room_type, r.status, r.description)
                ).lower()
            ]
        return sorted(rooms, key=lambda r: natural_sort_key(r.room_number))

    def get_available_rooms(self, actor):
        return self.search_rooms(actor, status=ROOM_STATUS_AVAILABLE)
