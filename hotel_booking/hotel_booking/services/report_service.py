"""Statistics calculated from the stored data (nothing is hard-coded)."""
from collections import Counter
from datetime import date

from models.booking import Booking
from models.room import Room
from services.authorization import require_permission
from utils.constants import (
    BOOKING_CANCELLED, BOOKING_COMPLETED, BOOKING_CONFIRMED, BOOKING_PENDING,
    PERM_VIEW_REPORTS, REVENUE_BOOKING_STATUSES, ROOM_STATUS_AVAILABLE,
    ROOM_STATUS_INACTIVE, ROOM_STATUS_MAINTENANCE,
)
from utils.helpers import build_models


def _top_entries(counter):
    """Most common keys with their count (ties included), or None."""
    if not counter:
        return None
    highest = max(counter.values())
    names = sorted(name for name, count in counter.items()
                   if count == highest)
    return {"names": names, "count": highest}


class ReportService:
    def __init__(self, room_store, booking_store, user_repository,
                 booking_service, today_provider=date.today):
        self._room_store = room_store
        self._booking_store = booking_store
        self._users = user_repository
        self._booking_service = booking_service
        self._today = today_provider

    def generate_report(self, actor):
        require_permission(actor, PERM_VIEW_REPORTS, "view reports")
        self._booking_service.refresh_statuses()
        today = self._today()

        rooms = build_models(self._room_store.read_all(), Room.from_dict,
                             "room")
        bookings = build_models(self._booking_store.read_all(),
                                Booking.from_dict, "booking")
        customers = self._users.customers()

        room_by_id = {r.room_id: r for r in rooms}
        room_status = Counter(r.status for r in rooms)
        booking_status = Counter(b.booking_status for b in bookings)

        counted = [b for b in bookings
                   if b.blocks_availability and b.room_id in room_by_id]
        per_room = Counter(room_by_id[b.room_id].room_number
                           for b in counted)
        per_type = Counter(room_by_id[b.room_id].room_type for b in counted)
        inventory_types = Counter(r.room_type for r in rooms)

        revenue_bookings = [b for b in bookings
                            if b.booking_status in REVENUE_BOOKING_STATUSES]
        pending_bookings = [b for b in bookings
                            if b.booking_status == BOOKING_PENDING]
        in_house = [b for b in bookings
                    if b.booking_status == BOOKING_CONFIRMED
                    and b.check_in <= today < b.check_out]
        occupied_rooms = {b.room_id for b in in_house}
        sellable = room_status.get(ROOM_STATUS_AVAILABLE, 0)
        occupancy = (min(len(occupied_rooms), sellable) / sellable * 100
                     if sellable else 0.0)

        return {
            "generated_for": today.isoformat(),
            "total_rooms": len(rooms),
            "available_rooms": room_status.get(ROOM_STATUS_AVAILABLE, 0),
            "maintenance_rooms": room_status.get(ROOM_STATUS_MAINTENANCE, 0),
            "inactive_rooms": room_status.get(ROOM_STATUS_INACTIVE, 0),
            "total_customers": len(customers),
            "active_customers": sum(1 for c in customers if c.is_active),
            "total_bookings": len(bookings),
            "confirmed_bookings": booking_status.get(BOOKING_CONFIRMED, 0),
            "pending_bookings": booking_status.get(BOOKING_PENDING, 0),
            "cancelled_bookings": booking_status.get(BOOKING_CANCELLED, 0),
            "completed_bookings": booking_status.get(BOOKING_COMPLETED, 0),
            "total_revenue": round(
                sum(b.total_price for b in revenue_bookings), 2),
            "pending_revenue": round(
                sum(b.total_price for b in pending_bookings), 2),
            "most_booked_room": _top_entries(per_room),
            "most_booked_room_type": _top_entries(per_type),
            "most_common_room_type": _top_entries(inventory_types),
            "currently_occupied_rooms": len(occupied_rooms),
            "guests_in_house": sum(b.number_of_guests for b in in_house),
            "occupancy_rate": round(occupancy, 1),
            "upcoming_bookings": sum(
                1 for b in bookings
                if b.booking_status in (BOOKING_PENDING, BOOKING_CONFIRMED)
                and b.check_in > today),
        }
