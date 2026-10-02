"""Search/filter menus shared by customer and manager dashboards."""
from ui.console import prompt_value, run_submenu
from ui.forms import ask_stay_dates, choice_validator
from ui.views import (
    show_booking_details, show_bookings, show_customer_details,
    show_customers, show_room_details, show_rooms,
)
from utils.constants import (
    BOOKING_STATUSES, PERM_MANAGE_BOOKINGS, PERM_MANAGE_ROOMS, ROOM_STATUSES,
    ROOM_TYPES,
)
from utils.validators import (
    validate_capacity, validate_date, validate_guests, validate_id,
    validate_price,
)


# ----------------------------------------------------------------------
# Rooms
# ----------------------------------------------------------------------
def search_rooms_menu(ctx, user):
    is_manager = user.has_permission(PERM_MANAGE_ROOMS)

    def show(rooms):
        show_rooms(rooms, "No rooms match your search.")
        if not rooms:
            return
        room_id = prompt_value(
            "Enter a Room ID to view details (Enter to skip)",
            validate_id, allow_blank=True)
        if room_id is not None:
            show_room_details(ctx.rooms.get_room(user, room_id))

    def by_number():
        value = prompt_value("Room number (full or partial)")
        show(ctx.rooms.search_rooms(user, room_number=value))

    def by_type():
        value = prompt_value(f"Room type ({'/'.join(ROOM_TYPES)})",
                             choice_validator(ROOM_TYPES, "room type"))
        show(ctx.rooms.search_rooms(user, room_type=value))

    def by_max_price():
        value = prompt_value("Maximum price per night", validate_price)
        show(ctx.rooms.search_rooms(user, max_price=value))

    def by_capacity():
        value = prompt_value("Minimum capacity (guests)", validate_capacity)
        show(ctx.rooms.search_rooms(user, min_capacity=value))

    def by_status():
        value = prompt_value(f"Status ({'/'.join(ROOM_STATUSES)})",
                             choice_validator(ROOM_STATUSES, "room status"))
        show(ctx.rooms.search_rooms(user, status=value))

    def by_dates():
        check_in, check_out = ask_stay_dates(ctx)
        guests = prompt_value("Number of guests", validate_guests)
        show(ctx.bookings.find_available_rooms(
            user, check_in, check_out, guests))

    def show_all():
        if is_manager:
            show(ctx.rooms.get_all_rooms(user))
        else:
            show(ctx.rooms.get_available_rooms(user))

    entries = [
        ("Room Number", by_number, True),
        ("Room Type", by_type, True),
        ("Maximum Price", by_max_price, True),
        ("Minimum Capacity", by_capacity, True),
    ]
    if is_manager:
        entries.append(("Room Status", by_status, True))
    entries += [("Available for Dates", by_dates, True),
                ("Show All", show_all, True)]
    run_submenu("SEARCH ROOMS", entries)


# ----------------------------------------------------------------------
# Bookings
# ----------------------------------------------------------------------
def search_bookings_menu(ctx, user):
    is_manager = user.has_permission(PERM_MANAGE_BOOKINGS)

    def show(bookings):
        show_bookings(bookings, show_customer=is_manager,
                      empty_message="No bookings match your search.")
        if not bookings:
            return
        booking_id = prompt_value(
            "Enter a Booking ID to view details (Enter to skip)",
            validate_id, allow_blank=True)
        if booking_id is not None:
            show_booking_details(
                ctx.bookings.get_booking_details(user, booking_id),
                show_customer=is_manager)

    def by_id():
        value = prompt_value("Booking ID", validate_id)
        show(ctx.bookings.search_bookings(user, booking_id=value))

    def by_customer():
        value = prompt_value("Customer (name, username, email or ID)")
        show(ctx.bookings.search_bookings(user, customer=value))

    def by_room():
        value = prompt_value("Room number or type")
        show(ctx.bookings.search_bookings(user, room=value))

    def by_status():
        value = prompt_value(
            f"Status ({'/'.join(BOOKING_STATUSES)})",
            choice_validator(BOOKING_STATUSES, "booking status"))
        show(ctx.bookings.search_bookings(user, status=value))

    def by_date():
        value = prompt_value(
            "Date (YYYY-MM-DD) - stays that include this day",
            lambda v: validate_date(v, "Date"))
        show(ctx.bookings.search_bookings(user, on_date=value))

    def show_all():
        show(ctx.bookings.search_bookings(user))

    entries = [("Booking ID", by_id, True)]
    if is_manager:
        entries.append(("Customer", by_customer, True))
    entries += [("Room", by_room, True), ("Status", by_status, True),
                ("Date", by_date, True), ("Show All", show_all, True)]
    run_submenu("SEARCH BOOKINGS", entries)


# ----------------------------------------------------------------------
# Customers (manager only; the service enforces the role)
# ----------------------------------------------------------------------
def search_customers_menu(ctx, user):
    def show(customers):
        show_customers(customers, "No customers match your search.")
        if not customers:
            return
        customer_id = prompt_value(
            "Enter a Customer ID to view details (Enter to skip)",
            validate_id, allow_blank=True)
        if customer_id is not None:
            show_customer_details(
                ctx.customers.get_customer(user, customer_id))

    def by_keyword():
        value = prompt_value("Name, username, email, phone or ID")
        show(ctx.customers.search_customers(user, keyword=value))

    def by_active():
        show(ctx.customers.search_customers(user, active=True))

    def by_inactive():
        show(ctx.customers.search_customers(user, active=False))

    def show_all():
        show(ctx.customers.list_customers(user))

    run_submenu("SEARCH CUSTOMERS", [
        ("Keyword", by_keyword, True),
        ("Active Accounts", by_active, True),
        ("Deactivated Accounts", by_inactive, True),
        ("Show All", show_all, True),
    ])
