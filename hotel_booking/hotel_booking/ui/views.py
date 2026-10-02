"""Formatting of rooms, bookings and customers for display."""
from ui.console import (
    print_divider, print_header, show_key_values, show_table,
)
from utils.helpers import format_money


def show_rooms(rooms, empty_message="No rooms found."):
    rows = [
        [r.room_id, r.room_number, r.room_type,
         format_money(r.price_per_night), r.capacity, r.floor, r.status]
        for r in rooms
    ]
    show_table(["ID", "Room", "Type", "Price/Night", "Capacity", "Floor",
                "Status"], rows, empty_message)


def show_room_details(room):
    print_header("ROOM DETAILS")
    show_key_values([
        ("Room ID", room.room_id),
        ("Room number", room.room_number),
        ("Type", room.room_type),
        ("Price per night", format_money(room.price_per_night)),
        ("Capacity", f"{room.capacity} guest(s)"),
        ("Floor", room.floor),
        ("Status", room.status),
        ("Description", room.description or "-"),
    ])


def show_bookings(bookings, show_customer=False,
                  empty_message="No bookings found."):
    headers = ["Booking ID"]
    if show_customer:
        headers.append("Customer")
    headers += ["Room", "Check-in", "Check-out", "Guests", "Nights",
                "Total", "Status"]
    rows = []
    for b in bookings:
        row = [b["booking_id"]]
        if show_customer:
            row.append(b["customer_name"])
        row += [b["room_number"], b["check_in"], b["check_out"],
                b["number_of_guests"], b["number_of_nights"],
                format_money(b["total_price"]), b["booking_status"]]
        rows.append(row)
    show_table(headers, rows, empty_message)


def show_booking_details(booking, show_customer=False):
    print_header("BOOKING DETAILS")
    pairs = [("Booking ID", booking["booking_id"])]
    if show_customer:
        pairs.append(("Customer", f"{booking['customer_name']} "
                      f"(@{booking['customer_username']})"))
    pairs += [
        ("Room", f"{booking['room_number']} ({booking['room_type']})"),
        ("Check-in", booking["check_in"]),
        ("Check-out", booking["check_out"]),
        ("Nights", booking["number_of_nights"]),
        ("Guests", booking["number_of_guests"]),
        ("Price/Night", format_money(booking["price_per_night"])),
        ("Total", format_money(booking["total_price"])),
        ("Status", booking["booking_status"]),
        ("Booked on", booking["created_at"]),
    ]
    show_key_values(pairs)


def show_booking_summary(booking):
    line = "-" * 30
    print()
    print(line)
    print("BOOKING SUMMARY")
    print(line)
    print(f"Room: {booking['room_number']}")
    print(f"Type: {booking['room_type']}")
    print(f"Price/Night: {format_money(booking['price_per_night'])}")
    print(f"Check-in: {booking['check_in']}")
    print(f"Check-out: {booking['check_out']}")
    print(f"Nights: {booking['number_of_nights']}")
    print(f"Guests: {booking['number_of_guests']}")
    print(f"Total: {format_money(booking['total_price'])}")
    print(line)


def show_customers(customers, empty_message="No customers found."):
    rows = [
        [c["user_id"], c["full_name"], c["username"], c["email"],
         c["phone"], "Active" if c["is_active"] else "Deactivated",
         c["created_at"][:10]]
        for c in customers
    ]
    show_table(["ID", "Name", "Username", "Email", "Phone", "Status",
                "Joined"], rows, empty_message)


def show_customer_details(customer):
    print_header("CUSTOMER DETAILS")
    pairs = [
        ("Customer ID", customer["user_id"]),
        ("Full name", customer["full_name"]),
        ("Username", customer["username"]),
        ("Email", customer["email"]),
        ("Phone", customer["phone"]),
        ("Account", "Active" if customer["is_active"] else "Deactivated"),
        ("Member since", customer["created_at"]),
    ]
    if "total_bookings" in customer:
        pairs += [
            ("Total bookings", customer["total_bookings"]),
            ("Active bookings", customer["active_bookings"]),
            ("Total spent", format_money(customer["total_spent"])),
        ]
    show_key_values(pairs)
    print_divider()
