"""Booking creation, availability, search and status changes."""
from datetime import date

from models.booking import Booking
from models.room import Room
from services.authorization import require_login, require_permission
from utils.constants import (
    ACTIVE_BOOKING_STATUSES, BOOKING_CANCELLED, BOOKING_COMPLETED,
    BOOKING_CONFIRMED, BOOKING_PENDING, BOOKING_STATUSES,
    HISTORY_BOOKING_STATUSES, PERM_CANCEL_OWN_BOOKING, PERM_CREATE_BOOKING,
    PERM_MANAGE_BOOKINGS, PERM_VIEW_OWN_BOOKINGS, PERM_VIEW_ROOMS,
    ROOM_STATUS_AVAILABLE, ROOM_STATUS_INACTIVE, ROOM_STATUS_MAINTENANCE,
)
from utils.exceptions import (
    AuthorizationError, BookingError, DataStoreError, NotFoundError,
)
from utils.helpers import build_models, natural_sort_key
from utils.validators import (
    require_text, validate_choice, validate_date, validate_guests,
    validate_id, validate_stay_dates,
)


class BookingService:
    def __init__(self, booking_store, room_store, user_repository,
                 today_provider=date.today):
        self._bookings = booking_store
        self._rooms = room_store
        self._users = user_repository
        self._today = today_provider

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _read_bookings(self):
        return build_models(
            self._bookings.read_all(), Booking.from_dict, "booking"
        )

    def _load_bookings(self):
        self.refresh_statuses()
        return self._read_bookings()

    def _load_rooms(self):
        return build_models(self._rooms.read_all(), Room.from_dict, "room")

    def _get_room(self, room_id):
        record = self._rooms.get(validate_id(room_id, "Room ID"))
        if record is None:
            raise NotFoundError("Room not found.")
        try:
            return Room.from_dict(record)
        except (KeyError, TypeError, ValueError) as exc:
            raise DataStoreError(f"Room record is corrupted: {exc}") from exc

    def _require_booking(self, booking_id):
        wanted = validate_id(booking_id, "Booking ID")
        for booking in self._load_bookings():
            if booking.booking_id == wanted:
                return booking
        raise NotFoundError("Booking not found.")

    def _authorize_access(self, actor, booking):
        """Managers see everything; customers only their own bookings."""
        require_login(actor)
        if actor.has_permission(PERM_MANAGE_BOOKINGS):
            return
        if (actor.has_permission(PERM_VIEW_OWN_BOOKINGS)
                and booking.customer_id == actor.user_id):
            return
        raise AuthorizationError("Access denied: you can only access your "
                                 "own bookings.")

    def _scope(self, actor, bookings):
        require_login(actor)
        if actor.has_permission(PERM_MANAGE_BOOKINGS):
            return bookings
        if actor.has_permission(PERM_VIEW_OWN_BOOKINGS):
            return [b for b in bookings if b.customer_id == actor.user_id]
        raise AuthorizationError("Access denied: your role cannot view "
                                 "bookings.")

    def _views(self, bookings):
        rooms = {r.room_id: r for r in self._load_rooms()}
        users = {u.user_id: u for u in self._users.all_users()}
        return [self._to_view(b, rooms, users) for b in bookings]

    @staticmethod
    def _to_view(booking, rooms, users):
        """Booking record plus room/customer details for display."""
        room = rooms.get(booking.room_id)
        customer = users.get(booking.customer_id)
        view = booking.to_dict()
        view.update(
            room_number=room.room_number if room else "?",
            room_type=room.room_type if room else "?",
            price_per_night=room.price_per_night if room else None,
            customer_name=customer.full_name if customer else "Unknown",
            customer_username=customer.username if customer else "?",
        )
        return view

    def _single_view(self, booking):
        return self._views([booking])[0]

    @staticmethod
    def _sort(bookings):
        return sorted(bookings, key=lambda b: (b.check_in, b.booking_id or 0))

    # ------------------------------------------------------------------
    # Automatic status handling and availability
    # ------------------------------------------------------------------
    def refresh_statuses(self):
        """Mark confirmed bookings whose check-out has passed as Completed.

        Cancelled (and pending) bookings are never touched.
        """
        today = self._today()
        updated = 0
        for booking in self._read_bookings():
            if (booking.booking_status == BOOKING_CONFIRMED
                    and booking.check_out < today):
                self._bookings.update(
                    booking.booking_id, {"booking_status": BOOKING_COMPLETED}
                )
                updated += 1
        return updated

    def is_room_available(self, room_id, check_in, check_out,
                          exclude_booking_id=None):
        """True when no non-cancelled booking overlaps the given dates."""
        for booking in self._read_bookings():
            if booking.room_id != room_id:
                continue
            if booking.booking_id == exclude_booking_id:
                continue
            if booking.blocks_availability and booking.overlaps(
                    check_in, check_out):
                return False
        return True

    def find_available_rooms(self, actor, check_in, check_out, guests=1):
        """Rooms that can be booked for the dates and number of guests."""
        require_permission(actor, PERM_VIEW_ROOMS, "view rooms")
        check_in, check_out, _ = validate_stay_dates(
            check_in, check_out, self._today())
        guests = validate_guests(guests)
        blocked = {
            b.room_id for b in self._read_bookings()
            if b.blocks_availability and b.overlaps(check_in, check_out)
        }
        rooms = [
            r for r in self._load_rooms()
            if r.status == ROOM_STATUS_AVAILABLE
            and r.capacity >= guests and r.room_id not in blocked
        ]
        return sorted(rooms, key=lambda r: natural_sort_key(r.room_number))

    # ------------------------------------------------------------------
    # Creating bookings (customers)
    # ------------------------------------------------------------------
    def _build_booking(self, actor, room_id, check_in, check_out, guests):
        require_permission(actor, PERM_CREATE_BOOKING, "create bookings")
        check_in, check_out, nights = validate_stay_dates(
            check_in, check_out, self._today())
        guests = validate_guests(guests)
        room = self._get_room(room_id)

        if room.status == ROOM_STATUS_INACTIVE:
            raise BookingError("This room is inactive and cannot be booked.")
        if room.status == ROOM_STATUS_MAINTENANCE:
            raise BookingError("This room is under maintenance and cannot "
                               "be booked.")
        if guests > room.capacity:
            raise BookingError(
                f"Room {room.room_number} holds at most {room.capacity} "
                f"guest(s)."
            )
        if not self.is_room_available(room.room_id, check_in, check_out):
            raise BookingError("Room is already booked for the selected "
                               "dates.")
        return Booking(
            booking_id=None,
            customer_id=actor.user_id,
            room_id=room.room_id,
            check_in=check_in,
            check_out=check_out,
            number_of_guests=guests,
            total_price=round(nights * room.price_per_night, 2),
            booking_status=BOOKING_PENDING,
        )

    def preview_booking(self, actor, room_id, check_in, check_out, guests):
        """Validate and price a booking without saving it."""
        booking = self._build_booking(
            actor, room_id, check_in, check_out, guests)
        return self._single_view(booking)

    def create_booking(self, actor, room_id, check_in, check_out, guests):
        """Validate again and save a new Pending booking."""
        booking = self._build_booking(
            actor, room_id, check_in, check_out, guests)
        stored = self._bookings.add(booking.to_dict())
        booking.booking_id = stored["booking_id"]
        return self._single_view(booking)

    # ------------------------------------------------------------------
    # Viewing and searching
    # ------------------------------------------------------------------
    def get_my_bookings(self, actor):
        """The customer's Pending/Confirmed bookings."""
        require_permission(actor, PERM_VIEW_OWN_BOOKINGS, "view own bookings")
        mine = [b for b in self._load_bookings()
                if b.customer_id == actor.user_id
                and b.booking_status in ACTIVE_BOOKING_STATUSES]
        return self._views(self._sort(mine))

    def get_booking_history(self, actor):
        """Completed and cancelled bookings (all for managers)."""
        bookings = self._scope(actor, self._load_bookings())
        past = [b for b in bookings
                if b.booking_status in HISTORY_BOOKING_STATUSES]
        return self._views(sorted(
            past, key=lambda b: (b.check_in, b.booking_id), reverse=True))

    def get_booking_details(self, actor, booking_id):
        booking = self._require_booking(booking_id)
        self._authorize_access(actor, booking)
        return self._single_view(booking)

    def search_bookings(self, actor, booking_id=None, customer=None,
                        room=None, status=None, on_date=None):
        """Filter bookings. Customers are always limited to their own."""
        bookings = self._scope(actor, self._load_bookings())
        is_manager = actor.has_permission(PERM_MANAGE_BOOKINGS)
        rooms = {r.room_id: r for r in self._load_rooms()}

        if booking_id is not None:
            wanted_id = validate_id(booking_id, "Booking ID")
            bookings = [b for b in bookings if b.booking_id == wanted_id]
        if customer and is_manager:
            needle = require_text(customer, "Customer").lower()
            matching = {
                u.user_id for u in self._users.all_users()
                if needle in u.full_name.lower()
                or needle in u.username.lower()
                or needle in u.email.lower()
                or needle == str(u.user_id)
            }
            bookings = [b for b in bookings if b.customer_id in matching]
        if room:
            needle = require_text(room, "Room").lower()
            bookings = [
                b for b in bookings
                if b.room_id in rooms and (
                    needle in rooms[b.room_id].room_number.lower()
                    or needle in rooms[b.room_id].room_type.lower())
            ]
        if status:
            wanted = validate_choice(status, BOOKING_STATUSES,
                                     "booking status")
            bookings = [b for b in bookings if b.booking_status == wanted]
        if on_date is not None:
            day = validate_date(on_date, "Date")
            bookings = [b for b in bookings
                        if b.check_in <= day <= b.check_out]
        return self._views(self._sort(bookings))

    def get_all_bookings(self, actor):
        require_permission(actor, PERM_MANAGE_BOOKINGS, "view all bookings")
        return self.search_bookings(actor)

    # ------------------------------------------------------------------
    # Changing booking status
    # ------------------------------------------------------------------
    def _set_status(self, booking, status):
        self._bookings.update(booking.booking_id, {"booking_status": status})
        booking.booking_status = status
        return self._single_view(booking)

    def cancel_booking(self, actor, booking_id):
        """Customers cancel their own bookings; managers can cancel any."""
        require_login(actor)
        booking = self._require_booking(booking_id)
        self._authorize_access(actor, booking)
        is_manager = actor.has_permission(PERM_MANAGE_BOOKINGS)
        if not is_manager and not actor.has_permission(
                PERM_CANCEL_OWN_BOOKING):
            raise AuthorizationError(
                f"Access denied: the {actor.role} role cannot cancel "
                "bookings.")
        if booking.booking_status not in ACTIVE_BOOKING_STATUSES:
            raise BookingError(
                f"A {booking.booking_status.lower()} booking cannot be "
                "cancelled.")
        if not is_manager and booking.check_in <= self._today():
            raise BookingError(
                "This stay has already started and can no longer be "
                "cancelled online. Please contact the hotel.")
        return self._set_status(booking, BOOKING_CANCELLED)

    def confirm_booking(self, actor, booking_id):
        require_permission(actor, PERM_MANAGE_BOOKINGS, "confirm bookings")
        booking = self._require_booking(booking_id)
        if booking.booking_status != BOOKING_PENDING:
            raise BookingError("Only pending bookings can be confirmed "
                               f"(this one is {booking.booking_status}).")
        if booking.check_out < self._today():
            raise BookingError("The dates of this booking have already "
                               "passed; it cannot be confirmed.")
        return self._set_status(booking, BOOKING_CONFIRMED)

    def complete_booking(self, actor, booking_id):
        require_permission(actor, PERM_MANAGE_BOOKINGS, "complete bookings")
        booking = self._require_booking(booking_id)
        if booking.booking_status != BOOKING_CONFIRMED:
            raise BookingError("Only confirmed bookings can be marked "
                               f"completed (this one is "
                               f"{booking.booking_status}).")
        if booking.check_in > self._today():
            raise BookingError("This stay has not started yet; it cannot "
                               "be marked completed.")
        return self._set_status(booking, BOOKING_COMPLETED)
