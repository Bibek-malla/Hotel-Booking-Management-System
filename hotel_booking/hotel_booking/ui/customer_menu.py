"""Customer dashboard."""
from ui.console import (
    confirm, print_header, print_info, print_success, prompt_value,
    read_password, run_submenu, show_key_values,
)
from ui.forms import (
    ask_new_password, ask_stay_dates, email_validator,
)
from ui.menu_base import DashboardMenu
from ui.search import search_bookings_menu, search_rooms_menu
from ui.views import (
    show_booking_details, show_booking_summary, show_bookings,
    show_room_details, show_rooms,
)
from utils.validators import (
    validate_full_name, validate_guests, validate_id, validate_phone,
)


class CustomerMenu(DashboardMenu):
    TITLE = "CUSTOMER DASHBOARD"
    OPTIONS = (
        "View Available Rooms", "Search Rooms", "Book a Room",
        "My Bookings", "Booking History", "Cancel Booking", "My Profile",
        "Logout",
    )

    def actions(self):
        return {
            1: (self.view_available_rooms, True),
            2: (lambda: search_rooms_menu(self.ctx, self.user), False),
            3: (self.book_room, True),
            4: (self.my_bookings, False),
            5: (self.booking_history, True),
            6: (self.cancel_booking, True),
            7: (self.my_profile, False),
        }

    # ------------------------------------------------------------------
    # Rooms
    # ------------------------------------------------------------------
    def view_available_rooms(self):
        print_header("AVAILABLE ROOMS")
        rooms = self.ctx.rooms.get_available_rooms(self.user)
        show_rooms(rooms, "No rooms are available right now.")
        if not rooms:
            return
        room_id = prompt_value(
            "Enter a Room ID to view details (Enter to skip)",
            validate_id, allow_blank=True)
        if room_id is not None:
            show_room_details(self.ctx.rooms.get_room(self.user, room_id))

    # ------------------------------------------------------------------
    # Booking
    # ------------------------------------------------------------------
    def book_room(self):
        print_header("BOOK A ROOM")
        print_info("Type /cancel at any prompt to abort.")
        check_in, check_out = ask_stay_dates(self.ctx)
        guests = prompt_value("Number of guests", validate_guests)

        rooms = self.ctx.bookings.find_available_rooms(
            self.user, check_in, check_out, guests)
        show_rooms(rooms, "No rooms are available for those dates and "
                          "guest count.")
        if not rooms:
            return

        room_id = prompt_value("Enter the Room ID to book", validate_id)
        summary = self.ctx.bookings.preview_booking(
            self.user, room_id, check_in, check_out, guests)
        show_booking_summary(summary)
        if not confirm("Confirm booking?"):
            print_info("Booking not made. No changes were saved.")
            return
        booking = self.ctx.bookings.create_booking(
            self.user, room_id, check_in, check_out, guests)
        print_success(
            f"Booking created successfully. Booking ID: "
            f"{booking['booking_id']} (status: {booking['booking_status']} "
            "- awaiting manager confirmation).")

    def my_bookings(self):
        def list_active():
            show_bookings(self.ctx.bookings.get_my_bookings(self.user),
                          empty_message="You have no active bookings.")

        def details():
            booking_id = prompt_value("Booking ID", validate_id)
            show_booking_details(
                self.ctx.bookings.get_booking_details(self.user, booking_id))

        run_submenu("MY BOOKINGS", [
            ("View Active Bookings", list_active, True),
            ("View Booking Details", details, True),
            ("Search / Filter My Bookings",
             lambda: search_bookings_menu(self.ctx, self.user), False),
        ])

    def booking_history(self):
        print_header("BOOKING HISTORY")
        show_bookings(self.ctx.bookings.get_booking_history(self.user),
                      empty_message="You have no completed or cancelled "
                                    "bookings yet.")

    def cancel_booking(self):
        print_header("CANCEL BOOKING")
        bookings = self.ctx.bookings.get_my_bookings(self.user)
        show_bookings(bookings, empty_message="You have no active bookings "
                                              "to cancel.")
        if not bookings:
            return
        booking_id = prompt_value("Enter the Booking ID to cancel",
                                  validate_id)
        show_booking_details(
            self.ctx.bookings.get_booking_details(self.user, booking_id))
        if not confirm("Cancel this booking?"):
            print_info("Booking was not cancelled.")
            return
        self.ctx.bookings.cancel_booking(self.user, booking_id)
        print_success("Booking cancelled successfully.")

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------
    def my_profile(self):
        run_submenu("MY PROFILE", [
            ("View Profile", self._show_profile, True),
            ("Update Name", self._update_name, True),
            ("Update Email", self._update_email, True),
            ("Update Phone", self._update_phone, True),
            ("Change Password", self._change_password, True),
        ])

    def _show_profile(self):
        profile = self.ctx.customers.get_profile(self.user)
        print_header("MY PROFILE")
        show_key_values([
            ("Full name", profile["full_name"]),
            ("Username", profile["username"]),
            ("Email", profile["email"]),
            ("Phone", profile["phone"]),
            ("Member since", profile["created_at"]),
        ])

    def _update_name(self):
        name = prompt_value("New full name", validate_full_name)
        self.ctx.customers.update_profile(self.user, full_name=name)
        print_success("Name updated.")

    def _update_email(self):
        email = prompt_value(
            "New email",
            email_validator(self.ctx, self.user.user_id))
        self.ctx.customers.update_profile(self.user, email=email)
        print_success("Email updated.")

    def _update_phone(self):
        phone = prompt_value("New phone", validate_phone)
        self.ctx.customers.update_profile(self.user, phone=phone)
        print_success("Phone updated.")

    def _change_password(self):
        current = read_password("Current password")
        new_password = ask_new_password("New password")
        self.ctx.customers.change_password(self.user, current, new_password)
        print_success("Password changed successfully.")
