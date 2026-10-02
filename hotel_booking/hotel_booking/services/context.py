"""Wires stores and services together (one place, no globals)."""
from datetime import date
from pathlib import Path

from services.auth_service import AuthService
from services.booking_service import BookingService
from services.customer_service import CustomerService
from services.report_service import ReportService
from services.room_service import RoomService
from services.user_repository import UserRepository
from utils.constants import (
    BOOKINGS_FILE_NAME, DATA_DIR, ROOMS_FILE_NAME, USERS_FILE_NAME,
)
from utils.file_handler import JsonStore


class ServiceContext:
    """Holds every service. ``today_provider`` is injectable for tests."""

    def __init__(self, data_dir=DATA_DIR, today_provider=date.today):
        directory = Path(data_dir)
        self.today = today_provider

        user_store = JsonStore(directory / USERS_FILE_NAME, "user_id")
        room_store = JsonStore(directory / ROOMS_FILE_NAME, "room_id")
        booking_store = JsonStore(directory / BOOKINGS_FILE_NAME,
                                  "booking_id")

        self.users = UserRepository(user_store)
        self.auth = AuthService(self.users)
        self.rooms = RoomService(room_store, booking_store, today_provider)
        self.bookings = BookingService(booking_store, room_store, self.users,
                                       today_provider)
        self.customers = CustomerService(self.users, booking_store)
        self.reports = ReportService(room_store, booking_store, self.users,
                                     self.bookings, today_provider)

    def initialize(self):
        """First-run setup: default manager, sample rooms, status refresh."""
        self.auth.ensure_default_manager()
        self.rooms.seed_sample_rooms_if_empty()
        self.bookings.refresh_statuses()
