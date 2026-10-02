"""Booking model with date-overlap logic."""
from datetime import datetime

from utils.constants import (
    ACTIVE_BOOKING_STATUSES, BOOKING_CANCELLED, BOOKING_PENDING, DATE_FORMAT,
)
from utils.helpers import current_timestamp


class Booking:
    def __init__(self, booking_id, customer_id, room_id, check_in, check_out,
                 number_of_guests, total_price,
                 booking_status=BOOKING_PENDING, created_at=None):
        self.booking_id = booking_id
        self.customer_id = customer_id
        self.room_id = room_id
        self.check_in = check_in          # datetime.date
        self.check_out = check_out        # datetime.date
        self.number_of_guests = number_of_guests
        self.total_price = total_price
        self.booking_status = booking_status
        self.created_at = created_at or current_timestamp()

    @property
    def number_of_nights(self):
        return (self.check_out - self.check_in).days

    @property
    def blocks_availability(self):
        """Cancelled bookings never block a room."""
        return self.booking_status != BOOKING_CANCELLED

    @property
    def is_active(self):
        return self.booking_status in ACTIVE_BOOKING_STATUSES

    def overlaps(self, new_check_in, new_check_out):
        """True when the date ranges overlap (check-out day is free)."""
        return new_check_in < self.check_out and new_check_out > self.check_in

    def to_dict(self):
        return {
            "booking_id": self.booking_id,
            "customer_id": self.customer_id,
            "room_id": self.room_id,
            "check_in": self.check_in.strftime(DATE_FORMAT),
            "check_out": self.check_out.strftime(DATE_FORMAT),
            "number_of_guests": self.number_of_guests,
            "number_of_nights": self.number_of_nights,
            "total_price": self.total_price,
            "booking_status": self.booking_status,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            booking_id=int(data["booking_id"]),
            customer_id=int(data["customer_id"]),
            room_id=int(data["room_id"]),
            check_in=datetime.strptime(data["check_in"], DATE_FORMAT).date(),
            check_out=datetime.strptime(data["check_out"], DATE_FORMAT).date(),
            number_of_guests=int(data["number_of_guests"]),
            total_price=float(data["total_price"]),
            booking_status=str(data["booking_status"]),
            created_at=data.get("created_at"),
        )
