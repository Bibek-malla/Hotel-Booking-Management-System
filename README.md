# Hotel Booking Management System

## 1. Project name
**Hotel Booking Management System** - a standalone, console-based Python application.

## 2. Description
A complete hotel booking system with two roles (Manager and Customer), real
role-based access control, JSON file persistence, double-booking prevention,
automatic price calculation, reports and search. No web framework, no external
database and no third-party packages are used.

## 3. Features
- Customer registration, login, logout, password hashing (PBKDF2-SHA256 + salt)
- Role-based access control enforced **inside the service layer**
- Room management (add, view, search/filter, update, change status, delete/deactivate)
- Customer room search by number, type, maximum price, minimum capacity, or free dates
- Booking creation with summary and Y/N confirmation, cancellation, history
- Overlap check: `new_check_in < existing_check_out AND new_check_out > existing_check_in`
  (cancelled bookings never block a room; same-day check-out/check-in is allowed)
- Automatic price: `nights x price_per_night`
- Manager tools: confirm / cancel / complete bookings, customer management, reports
- Confirmed bookings whose check-out date has passed become **Completed** automatically
- Crash-proof input handling, corrupted/missing JSON recovery, error log

## 4. Technologies used
Python 3.8+ (standard library only): `json`, `hashlib`, `hmac`, `datetime`,
`pathlib`, `logging`, `getpass`, `unittest`.

## 5. Project structure
```
hotel_booking/
├── main.py                  # entry point
├── README.md
├── data/                    # created automatically on first run
│   ├── users.json
│   ├── rooms.json
│   ├── bookings.json
│   └── error.log            # unexpected errors / skipped bad records
├── models/
│   ├── user.py              # User -> Customer, Manager (roles + permissions)
│   ├── room.py
│   └── booking.py           # includes overlap logic
├── services/
│   ├── authorization.py     # require_login / require_permission
│   ├── user_repository.py
│   ├── auth_service.py
│   ├── room_service.py
│   ├── booking_service.py
│   ├── customer_service.py
│   ├── report_service.py
│   └── context.py           # wires everything together
├── ui/                      # console screens (no business rules here)
│   ├── console.py  forms.py  views.py  search.py
│   ├── menu_base.py  customer_menu.py  manager_menu.py  app.py
├── utils/
│   ├── constants.py  exceptions.py  file_handler.py
│   ├── validators.py  helpers.py
└── tests/test_system.py
```

## 6. How to install
1. Install Python 3.8 or newer (https://www.python.org/downloads/).
2. Copy the `hotel_booking` folder anywhere and open it in VS Code.
3. No `pip install` is needed.

## 7. How to run
```
cd hotel_booking
python main.py
```
(use `python3 main.py` on macOS/Linux). The program works regardless of the
folder you launch it from, e.g. `python path/to/hotel_booking/main.py`.

Run the automated tests:
```
python -m unittest discover -s tests -v
```

## 8. Default manager credentials
| Username | Password |
|----------|----------|
| `admin`  | `admin123` |

Created automatically on first run. Change the password in `utils/constants.py`
**before** the first run, or create another manager by editing `users.json`
(role `"Manager"`) if you need to. Customers register themselves from the main menu.

## 9. How data storage works
All data lives in `data/*.json` (lists of records). `utils/file_handler.py`
(`JsonStore`) is the only code that touches files. It:
- creates the folder and files when missing,
- writes atomically (temp file + replace) so a crash cannot corrupt data,
- renames an unreadable file to `*.corrupt-<timestamp>.json` and starts fresh,
- generates ids as `max(existing id) + 1` (never reused, because bookings/users
  are never deleted and rooms with booking history are deactivated, not deleted).

Set the environment variable `HOTEL_DATA_DIR` to use a different data folder.

## 10. User roles
| Capability | Customer | Manager |
|---|---|---|
| Search / view available rooms | yes (Available rooms only) | yes (all rooms) |
| Create / cancel own bookings, view own history | yes | no |
| Manage rooms, customers, all bookings, reports | **no** | yes |
| Edit own profile / change password | yes | - |

Each service method checks the caller's permission (`require_permission`).
Typing a manager menu number as a customer is impossible, and calling a
manager service with a customer object raises `AuthorizationError`.

## 11. Main functionalities
- **Customer dashboard:** view/search rooms, book a room, my bookings (active),
  booking history (completed/cancelled), cancel booking, profile, logout.
- **Manager dashboard:** room management, customer management, booking
  management (confirm/cancel/complete/history), reports & statistics, search, logout.
- New bookings start as **Pending**; the manager confirms them. Customers may
  cancel Pending/Confirmed bookings until the day the stay starts.
- Rooms with upcoming Pending/Confirmed bookings cannot be set to
  Maintenance/Inactive or deleted until those bookings are cancelled/completed.
- Reports: room counts by status, customers, bookings by status, revenue
  (Confirmed + Completed; pending shown separately), most booked room / room
  type, most common room type, current occupancy - all calculated from the JSON data.

## 12. Validation rules
- Username: 3-20 letters/digits/`_`/`.`; unique, case-insensitive. Email: valid format, unique.
- Password: at least 6 characters with letters and digits. Phone: 7-15 digits.
- Room number: unique, 1-10 chars. Price > 0. Capacity 1-20. Floor 0-100.
- Room type: Single / Double / Deluxe / Suite. Status: Available / Maintenance / Inactive.
- Dates: `YYYY-MM-DD`, real calendar dates, check-in not in the past,
  check-out after check-in, stay at most 90 nights.
- Guests: positive and not above room capacity.
- Room must exist, be Available (not Maintenance/Inactive) and free for the dates.
- All IDs must be positive numbers and must exist.
- Type `/cancel` at most prompts to abort the current operation.

## 13. Example usage
```
1. Login  ->  admin / admin123  ->  Manager dashboard
2. Register (as a customer) -> log in
3. Book a Room -> check-in 2026-10-10, check-out 2026-10-13, guests 2
   -> pick a room ID from the list of rooms free on those dates
   ------------------------------
   BOOKING SUMMARY
   ------------------------------
   Room: 201 ... Nights: 3 ... Total: $285.00
   Confirm booking? (Y/N): y
   [✓] Booking created successfully.
4. Log in as admin -> Booking Management -> Confirm Pending Booking
```

## 14. Future improvements
- Booking modification (change dates), payment records, invoices/PDF receipts
- Pagination for long tables, CSV export of reports
- Account lockout after repeated failed logins, password reset
- Switch the `JsonStore` layer for SQLite without touching the services
- Seasonal / weekend pricing and room amenities
