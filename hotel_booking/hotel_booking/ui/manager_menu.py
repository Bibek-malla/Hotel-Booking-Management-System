"""Manager dashboard."""
from ui.console import (
    confirm, print_header, print_info, print_success, prompt_value,
    run_submenu, show_key_values,
)
from ui.forms import choice_validator, email_validator, room_number_validator
from ui.menu_base import DashboardMenu
from ui.search import (
    search_bookings_menu, search_customers_menu, search_rooms_menu,
)
from ui.views import (
    show_booking_details, show_bookings, show_customer_details,
    show_customers, show_room_details, show_rooms,
)
from utils.constants import (
    BOOKING_PENDING, ROOM_STATUS_AVAILABLE, ROOM_STATUSES, ROOM_TYPES,
)
from utils.helpers import format_money
from utils.validators import (
    validate_capacity, validate_description, validate_floor,
    validate_full_name, validate_id, validate_phone, validate_price,
)


class ManagerMenu(DashboardMenu):
    TITLE = "MANAGER DASHBOARD"
    OPTIONS = (
        "Room Management", "Customer Management", "Booking Management",
        "Reports & Statistics", "Search", "Logout",
    )

    def actions(self):
        return {
            1: (self.room_management, False),
            2: (self.customer_management, False),
            3: (self.booking_management, False),
            4: (self.reports, True),
            5: (self.search, False),
        }

    # ------------------------------------------------------------------
    # Rooms
    # ------------------------------------------------------------------
    def room_management(self):
        run_submenu("ROOM MANAGEMENT", [
            ("Add Room", self.add_room, True),
            ("View All Rooms", self.view_rooms, True),
            ("Search / Filter Rooms",
             lambda: search_rooms_menu(self.ctx, self.user), False),
            ("Update Room", self.update_room, True),
            ("Change Room Status", self.change_room_status, True),
            ("Delete / Deactivate Room", self.delete_room, True),
        ])

    def _ask_room(self, label="Room ID"):
        room_id = prompt_value(label, validate_id)
        return self.ctx.rooms.get_room(self.user, room_id)

    def add_room(self):
        print_header("ADD ROOM")
        print_info("Type /cancel at any prompt to abort.")
        number = prompt_value("Room number", room_number_validator(self.ctx))
        room_type = prompt_value(f"Room type ({'/'.join(ROOM_TYPES)})",
                                 choice_validator(ROOM_TYPES, "room type"))
        price = prompt_value("Price per night", validate_price)
        capacity = prompt_value("Capacity (guests)", validate_capacity)
        floor = prompt_value("Floor", validate_floor)
        description = prompt_value("Description (optional)",
                                   validate_description, allow_blank=True)
        status = prompt_value(
            f"Status ({'/'.join(ROOM_STATUSES)}) [Enter = "
            f"{ROOM_STATUS_AVAILABLE}]",
            choice_validator(ROOM_STATUSES, "room status"),
            allow_blank=True) or ROOM_STATUS_AVAILABLE
        room = self.ctx.rooms.add_room(
            self.user, number, room_type, price, capacity, floor,
            description or "", status)
        print_success(f"Room {room.room_number} added (ID {room.room_id}).")

    def view_rooms(self):
        print_header("ALL ROOMS")
        show_rooms(self.ctx.rooms.get_all_rooms(self.user),
                   "No rooms have been added yet.")

    def update_room(self):
        print_header("UPDATE ROOM")
        room = self._ask_room()
        show_room_details(room)
        print_info("Press Enter to keep the current value.")
        number = prompt_value(
            f"Room number [{room.room_number}]",
            room_number_validator(self.ctx, room.room_id), allow_blank=True)
        room_type = prompt_value(
            f"Room type [{room.room_type}]",
            choice_validator(ROOM_TYPES, "room type"), allow_blank=True)
        price = prompt_value(f"Price per night [{room.price_per_night}]",
                             validate_price, allow_blank=True)
        capacity = prompt_value(f"Capacity [{room.capacity}]",
                                validate_capacity, allow_blank=True)
        floor = prompt_value(f"Floor [{room.floor}]", validate_floor,
                             allow_blank=True)
        status = prompt_value(
            f"Status [{room.status}]",
            choice_validator(ROOM_STATUSES, "room status"),
            allow_blank=True)
        description = prompt_value("Description", validate_description,
                                   allow_blank=True)
        updated = self.ctx.rooms.update_room(
            self.user, room.room_id, room_number=number, room_type=room_type,
            price_per_night=price, capacity=capacity, floor=floor,
            status=status, description=description)
        print_success(f"Room {updated.room_number} updated.")

    def change_room_status(self):
        print_header("CHANGE ROOM STATUS")
        room = self._ask_room()
        print_info(f"Room {room.room_number} is currently {room.status}.")
        status = prompt_value(
            f"New status ({'/'.join(ROOM_STATUSES)})",
            choice_validator(ROOM_STATUSES, "room status"))
        updated = self.ctx.rooms.change_status(
            self.user, room.room_id, status)
        print_success(f"Room {updated.room_number} is now {updated.status}.")

    def delete_room(self):
        print_header("DELETE / DEACTIVATE ROOM")
        room = self._ask_room()
        show_room_details(room)
        print_info("Rooms with booking records are deactivated instead of "
                   "deleted, so history stays intact.")
        if not confirm(f"Remove room {room.room_number}?"):
            print_info("No changes were made.")
            return
        result = self.ctx.rooms.delete_room(self.user, room.room_id)
        print_success(f"Room {room.room_number} was {result}.")

    # ------------------------------------------------------------------
    # Customers
    # ------------------------------------------------------------------
    def customer_management(self):
        run_submenu("CUSTOMER MANAGEMENT", [
            ("View All Customers", self.view_customers, True),
            ("Search Customers",
             lambda: search_customers_menu(self.ctx, self.user), False),
            ("View Customer Details", self.customer_details, True),
            ("Update Customer Information", self.update_customer, True),
            ("Activate / Deactivate Account", self.toggle_customer, True),
        ])

    def view_customers(self):
        print_header("ALL CUSTOMERS")
        show_customers(self.ctx.customers.list_customers(self.user),
                       "No customers have registered yet.")

    def customer_details(self):
        customer_id = prompt_value("Customer ID", validate_id)
        show_customer_details(
            self.ctx.customers.get_customer(self.user, customer_id))

    def update_customer(self):
        print_header("UPDATE CUSTOMER")
        customer_id = prompt_value("Customer ID", validate_id)
        customer = self.ctx.customers.get_customer(self.user, customer_id)
        show_customer_details(customer)
        print_info("Press Enter to keep the current value.")
        name = prompt_value(f"Full name [{customer['full_name']}]",
                            validate_full_name, allow_blank=True)
        email = prompt_value(
            f"Email [{customer['email']}]",
            email_validator(self.ctx, customer["user_id"]),
            allow_blank=True)
        phone = prompt_value(f"Phone [{customer['phone']}]", validate_phone,
                             allow_blank=True)
        self.ctx.customers.update_customer(
            self.user, customer_id, full_name=name, email=email, phone=phone)
        print_success("Customer information updated.")

    def toggle_customer(self):
        customer_id = prompt_value("Customer ID", validate_id)
        customer = self.ctx.customers.get_customer(self.user, customer_id)
        show_customer_details(customer)
        make_active = not customer["is_active"]
        action = "Reactivate" if make_active else "Deactivate"
        if not confirm(f"{action} the account of {customer['full_name']}?"):
            print_info("No changes were made.")
            return
        self.ctx.customers.set_customer_active(
            self.user, customer_id, make_active)
        print_success(f"Account {action.lower()}d.")

    # ------------------------------------------------------------------
    # Bookings
    # ------------------------------------------------------------------
    def booking_management(self):
        run_submenu("BOOKING MANAGEMENT", [
            ("View All Bookings", self.view_bookings, True),
            ("Search / Filter Bookings",
             lambda: search_bookings_menu(self.ctx, self.user), False),
            ("View Booking Details", self.booking_details, True),
            ("Confirm Pending Booking", self.confirm_booking, True),
            ("Cancel Booking", self.cancel_booking, True),
            ("Mark Booking as Completed", self.complete_booking, True),
            ("Booking History", self.booking_history, True),
        ])

    def view_bookings(self):
        print_header("ALL BOOKINGS")
        show_bookings(self.ctx.bookings.get_all_bookings(self.user),
                      show_customer=True,
                      empty_message="No bookings have been made yet.")

    def booking_details(self):
        booking_id = prompt_value("Booking ID", validate_id)
        show_booking_details(
            self.ctx.bookings.get_booking_details(self.user, booking_id),
            show_customer=True)

    def confirm_booking(self):
        print_header("CONFIRM PENDING BOOKING")
        pending = self.ctx.bookings.search_bookings(
            self.user, status=BOOKING_PENDING)
        show_bookings(pending, show_customer=True,
                      empty_message="There are no pending bookings.")
        if not pending:
            return
        booking_id = prompt_value("Booking ID to confirm", validate_id)
        self.ctx.bookings.confirm_booking(self.user, booking_id)
        print_success(f"Booking {booking_id} confirmed.")

    def cancel_booking(self):
        print_header("CANCEL BOOKING")
        booking_id = prompt_value("Booking ID to cancel", validate_id)
        show_booking_details(
            self.ctx.bookings.get_booking_details(self.user, booking_id),
            show_customer=True)
        if not confirm("Cancel this booking?"):
            print_info("No changes were made.")
            return
        self.ctx.bookings.cancel_booking(self.user, booking_id)
        print_success(f"Booking {booking_id} cancelled.")

    def complete_booking(self):
        print_header("MARK BOOKING AS COMPLETED")
        booking_id = prompt_value("Booking ID to complete", validate_id)
        self.ctx.bookings.complete_booking(self.user, booking_id)
        print_success(f"Booking {booking_id} marked as completed.")

    def booking_history(self):
        print_header("BOOKING HISTORY")
        show_bookings(self.ctx.bookings.get_booking_history(self.user),
                      show_customer=True,
                      empty_message="No completed or cancelled bookings "
                                    "yet.")

    # ------------------------------------------------------------------
    # Reports and search
    # ------------------------------------------------------------------
    def reports(self):
        report = self.ctx.reports.generate_report(self.user)
        print_header("REPORTS & STATISTICS")
        print(f"  Report date: {report['generated_for']}")
        print("\n  ROOMS")
        show_key_values([
            ("Total rooms", report["total_rooms"]),
            ("Available", report["available_rooms"]),
            ("Maintenance", report["maintenance_rooms"]),
            ("Inactive", report["inactive_rooms"]),
        ], indent=4)
        print("\n  CUSTOMERS")
        show_key_values([
            ("Total customers", report["total_customers"]),
            ("Active accounts", report["active_customers"]),
        ], indent=4)
        print("\n  BOOKINGS")
        show_key_values([
            ("Total bookings", report["total_bookings"]),
            ("Pending", report["pending_bookings"]),
            ("Confirmed", report["confirmed_bookings"]),
            ("Completed", report["completed_bookings"]),
            ("Cancelled", report["cancelled_bookings"]),
            ("Upcoming (pending/confirmed)", report["upcoming_bookings"]),
        ], indent=4)
        print("\n  REVENUE")
        show_key_values([
            ("Revenue (confirmed + completed)",
             format_money(report["total_revenue"])),
            ("Pending (not yet confirmed)",
             format_money(report["pending_revenue"])),
        ], indent=4)
        print("\n  INSIGHTS")
        show_key_values([
            ("Most booked room", self._describe_top(
                report["most_booked_room"], "booking")),
            ("Most booked room type", self._describe_top(
                report["most_booked_room_type"], "booking")),
            ("Most common room type", self._describe_top(
                report["most_common_room_type"], "room")),
        ], indent=4)
        print("\n  CURRENT OCCUPANCY (today)")
        show_key_values([
            ("Rooms occupied", report["currently_occupied_rooms"]),
            ("Guests in house", report["guests_in_house"]),
            ("Occupancy rate", f"{report['occupancy_rate']}%"),
        ], indent=4)

    @staticmethod
    def _describe_top(entry, unit):
        if entry is None:
            return "N/A (no data yet)"
        plural = "" if entry["count"] == 1 else "s"
        return f"{', '.join(entry['names'])} ({entry['count']} {unit}{plural})"

    def search(self):
        run_submenu("SEARCH", [
            ("Rooms", lambda: search_rooms_menu(self.ctx, self.user), False),
            ("Customers",
             lambda: search_customers_menu(self.ctx, self.user), False),
            ("Bookings",
             lambda: search_bookings_menu(self.ctx, self.user), False),
        ])
