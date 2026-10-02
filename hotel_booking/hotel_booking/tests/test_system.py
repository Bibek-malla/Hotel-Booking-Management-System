"""End-to-end tests of the service layer.  Run:  python -m unittest discover -s tests -v"""
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.context import ServiceContext  # noqa: E402
from utils.exceptions import (  # noqa: E402
    AuthenticationError, AuthorizationError, BookingError, NotFoundError,
    ValidationError,
)


class Clock:
    """Controllable replacement for date.today."""

    def __init__(self, today):
        self.today = today

    def __call__(self):
        return self.today


class BaseCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.clock = Clock(date(2026, 10, 2))
        self.ctx = ServiceContext(self._tmp.name, self.clock)
        self.ctx.initialize()
        self.admin = self.ctx.auth.login("admin", "admin123")
        self.alice = self.new_customer("alice")
        self.bob = self.new_customer("bob")
        self.room = {r.room_number: r for r in
                     self.ctx.rooms.get_all_rooms(self.admin)}

    def new_customer(self, username):
        self.ctx.auth.register_customer(
            f"{username.title()} Tester", username, f"{username}@mail.com",
            "secret12", "5551234567")
        return self.ctx.auth.login(username, "secret12")

    def book(self, user, room_number, check_in, check_out, guests=1):
        return self.ctx.bookings.create_booking(
            user, self.room[room_number].room_id, check_in, check_out, guests)


class AuthTests(BaseCase):
    def test_default_manager_and_sample_rooms(self):
        self.assertEqual(self.admin.role, "Manager")
        self.assertEqual(len(self.room), 5)

    def test_password_is_hashed(self):
        text = (Path(self._tmp.name) / "users.json").read_text()
        self.assertNotIn("admin123", text)
        self.assertNotIn("secret12", text)
        self.assertIn("pbkdf2_sha256", text)

    def test_duplicate_username_and_email(self):
        with self.assertRaises(ValidationError):
            self.ctx.auth.register_customer(
                "Other Person", "ALICE", "other@mail.com", "secret12",
                "5551234567")
        with self.assertRaises(ValidationError):
            self.ctx.auth.register_customer(
                "Other Person", "other", "Alice@Mail.com", "secret12",
                "5551234567")

    def test_wrong_password_and_unknown_user(self):
        for name, pw in (("alice", "wrong123"), ("nobody", "secret12"),
                         ("", "x")):
            with self.assertRaises(AuthenticationError):
                self.ctx.auth.login(name, pw)

    def test_logout(self):
        self.ctx.auth.logout()
        self.assertIsNone(self.ctx.auth.current_user)

    def test_weak_registration_input_rejected(self):
        bad = [("A", "validuser", "a@b.com", "secret12", "5551234567"),
               ("Valid Name", "x", "a@b.com", "secret12", "5551234567"),
               ("Valid Name", "validuser", "not-an-email", "secret12",
                "5551234567"),
               ("Valid Name", "validuser", "a@b.com", "short", "5551234567"),
               ("Valid Name", "validuser", "a@b.com", "onlyletters", "5551234567"),
               ("Valid Name", "validuser", "a@b.com", "secret12", "abc")]
        for args in bad:
            with self.assertRaises(ValidationError, msg=args):
                self.ctx.auth.register_customer(*args)

    def test_deactivated_customer_cannot_login(self):
        customer = self.ctx.customers.search_customers(
            self.admin, keyword="alice")[0]
        self.ctx.customers.set_customer_active(
            self.admin, customer["user_id"], False)
        with self.assertRaises(AuthenticationError):
            self.ctx.auth.login("alice", "secret12")


class RoleAccessTests(BaseCase):
    def test_customer_cannot_use_manager_functions(self):
        rid = self.room["101"].room_id
        calls = [
            lambda: self.ctx.rooms.add_room(
                self.alice, "999", "Single", 50, 1, 1),
            lambda: self.ctx.rooms.get_all_rooms(self.alice),
            lambda: self.ctx.rooms.update_room(self.alice, rid, price_per_night=1),
            lambda: self.ctx.rooms.delete_room(self.alice, rid),
            lambda: self.ctx.customers.list_customers(self.alice),
            lambda: self.ctx.customers.get_customer(self.alice, 1),
            lambda: self.ctx.reports.generate_report(self.alice),
            lambda: self.ctx.bookings.get_all_bookings(self.alice),
            lambda: self.ctx.bookings.confirm_booking(self.alice, 1),
            lambda: self.ctx.bookings.complete_booking(self.alice, 1),
        ]
        for call in calls:
            with self.assertRaises(AuthorizationError):
                call()

    def test_manager_cannot_book_and_anonymous_is_rejected(self):
        with self.assertRaises(AuthorizationError):
            self.ctx.bookings.create_booking(
                self.admin, self.room["101"].room_id, "2026-10-10",
                "2026-10-12", 1)
        with self.assertRaises(AuthenticationError):
            self.ctx.rooms.search_rooms(None)

    def test_customer_cannot_touch_other_customers_bookings(self):
        booking = self.book(self.alice, "101", "2026-10-10", "2026-10-12")
        with self.assertRaises(AuthorizationError):
            self.ctx.bookings.cancel_booking(self.bob, booking["booking_id"])
        with self.assertRaises(AuthorizationError):
            self.ctx.bookings.get_booking_details(
                self.bob, booking["booking_id"])
        self.assertEqual(self.ctx.bookings.search_bookings(self.bob), [])

    def test_customer_sees_only_available_rooms(self):
        self.ctx.rooms.change_status(
            self.admin, self.room["101"].room_id, "Maintenance")
        numbers = [r.room_number
                   for r in self.ctx.rooms.search_rooms(self.alice)]
        self.assertNotIn("101", numbers)
        with self.assertRaises(NotFoundError):
            self.ctx.rooms.get_room(self.alice, self.room["101"].room_id)


class RoomTests(BaseCase):
    def test_add_update_search_filter(self):
        room = self.ctx.rooms.add_room(
            self.admin, "401", "suite", "250.5", "5", "4", "Penthouse")
        self.assertEqual(room.room_type, "Suite")
        self.assertEqual(room.price_per_night, 250.5)
        self.ctx.rooms.update_room(
            self.admin, room.room_id, price_per_night=260, description="New")
        found = self.ctx.rooms.search_rooms(self.admin, room_number="40")
        self.assertEqual(found[0].price_per_night, 260.0)
        types = self.ctx.rooms.search_rooms(self.alice, room_type="Deluxe")
        self.assertEqual({r.room_number for r in types}, {"201", "202"})
        cheap = self.ctx.rooms.search_rooms(self.alice, max_price=70)
        self.assertEqual({r.room_number for r in cheap}, {"101", "102"})
        big = self.ctx.rooms.search_rooms(self.alice, min_capacity=4)
        self.assertEqual({r.room_number for r in big}, {"301", "401"})

    def test_room_validation(self):
        add = self.ctx.rooms.add_room
        bad = [("101", "Single", 50, 1, 1), ("500", "Castle", 50, 1, 1),
               ("500", "Single", -5, 1, 1), ("500", "Single", "abc", 1, 1),
               ("500", "Single", 50, 0, 1), ("500", "Single", 50, 1, -1),
               ("", "Single", 50, 1, 1)]
        for args in bad:
            with self.assertRaises(ValidationError, msg=args):
                add(self.admin, *args)
        with self.assertRaises(ValidationError):
            add(self.admin, "500", "Single", 50, 1, 1, status="Broken")

    def test_delete_vs_deactivate(self):
        fresh = self.ctx.rooms.add_room(
            self.admin, "900", "Single", 40, 1, 9)
        self.assertEqual(
            self.ctx.rooms.delete_room(self.admin, fresh.room_id), "deleted")
        booking = self.book(self.alice, "101", "2026-10-10", "2026-10-12")
        with self.assertRaises(BookingError):
            self.ctx.rooms.delete_room(self.admin, self.room["101"].room_id)
        self.ctx.bookings.cancel_booking(self.alice, booking["booking_id"])
        self.assertEqual(self.ctx.rooms.delete_room(
            self.admin, self.room["101"].room_id), "deactivated")
        self.assertEqual(self.ctx.rooms.get_room(
            self.admin, self.room["101"].room_id).status, "Inactive")

    def test_cannot_put_booked_room_in_maintenance(self):
        self.book(self.alice, "101", "2026-10-10", "2026-10-12")
        with self.assertRaises(BookingError):
            self.ctx.rooms.change_status(
                self.admin, self.room["101"].room_id, "Maintenance")


class BookingTests(BaseCase):
    def test_booking_price_and_pending_status(self):
        booking = self.book(self.alice, "201", "2026-10-10", "2026-10-13", 2)
        self.assertEqual(booking["number_of_nights"], 3)
        self.assertEqual(booking["total_price"], 285.0)
        self.assertEqual(booking["booking_status"], "Pending")

    def test_invalid_dates_and_guests(self):
        rid = self.room["201"].room_id
        create = self.ctx.bookings.create_booking
        cases = [("2026-13-40", "2026-10-12", 1), ("abc", "2026-10-12", 1),
                 ("2026-10-12", "2026-10-12", 1),
                 ("2026-10-12", "2026-10-10", 1),
                 ("2026-10-01", "2026-10-05", 1),
                 ("2026-10-10", "2026-10-12", 0),
                 ("2026-10-10", "2026-10-12", -2),
                 ("2026-10-10", "2026-10-12", "abc")]
        for check_in, check_out, guests in cases:
            with self.assertRaises(ValidationError, msg=(check_in, guests)):
                create(self.alice, rid, check_in, check_out, guests)

    def test_capacity_violation_and_missing_room(self):
        with self.assertRaises(BookingError):
            self.book(self.alice, "101", "2026-10-10", "2026-10-12", 2)
        with self.assertRaises(NotFoundError):
            self.ctx.bookings.create_booking(
                self.alice, 9999, "2026-10-10", "2026-10-12", 1)

    def test_inactive_and_maintenance_rooms_not_bookable(self):
        for status in ("Maintenance", "Inactive"):
            self.ctx.rooms.change_status(
                self.admin, self.room["102"].room_id, status)
            with self.assertRaises(BookingError):
                self.book(self.alice, "102", "2026-10-10", "2026-10-12")

    def test_double_booking_prevented(self):
        self.book(self.alice, "101", "2026-10-10", "2026-10-15")
        overlaps = [("2026-10-10", "2026-10-15"), ("2026-10-12", "2026-10-13"),
                    ("2026-10-08", "2026-10-11"), ("2026-10-14", "2026-10-18"),
                    ("2026-10-05", "2026-10-20")]
        for check_in, check_out in overlaps:
            with self.assertRaises(BookingError, msg=(check_in, check_out)):
                self.book(self.bob, "101", check_in, check_out)

    def test_back_to_back_stays_allowed(self):
        self.book(self.alice, "101", "2026-10-10", "2026-10-15")
        self.book(self.bob, "101", "2026-10-15", "2026-10-17")
        self.book(self.bob, "101", "2026-10-05", "2026-10-10")

    def test_cancelled_booking_frees_the_room(self):
        booking = self.book(self.alice, "101", "2026-10-10", "2026-10-15")
        self.ctx.bookings.cancel_booking(self.alice, booking["booking_id"])
        self.book(self.bob, "101", "2026-10-10", "2026-10-15")

    def test_availability_search_by_dates(self):
        self.book(self.alice, "101", "2026-10-10", "2026-10-15")
        rooms = self.ctx.bookings.find_available_rooms(
            self.bob, "2026-10-11", "2026-10-12", 1)
        numbers = {r.room_number for r in rooms}
        self.assertNotIn("101", numbers)
        self.assertIn("102", numbers)

    def test_cancel_rules(self):
        booking = self.book(self.alice, "101", "2026-10-10", "2026-10-12")
        bid = booking["booking_id"]
        self.ctx.bookings.cancel_booking(self.alice, bid)
        with self.assertRaises(BookingError):
            self.ctx.bookings.cancel_booking(self.alice, bid)
        with self.assertRaises(NotFoundError):
            self.ctx.bookings.cancel_booking(self.alice, 4242)
        with self.assertRaises(ValidationError):
            self.ctx.bookings.cancel_booking(self.alice, "abc")

    def test_customer_cannot_cancel_started_stay(self):
        booking = self.book(self.alice, "101", "2026-10-02", "2026-10-05")
        with self.assertRaises(BookingError):
            self.ctx.bookings.cancel_booking(self.alice, booking["booking_id"])
        cancelled = self.ctx.bookings.cancel_booking(
            self.admin, booking["booking_id"])
        self.assertEqual(cancelled["booking_status"], "Cancelled")

    def test_manager_confirm_and_complete(self):
        booking = self.book(self.alice, "101", "2026-10-02", "2026-10-05")
        bid = booking["booking_id"]
        with self.assertRaises(BookingError):
            self.ctx.bookings.complete_booking(self.admin, bid)  # pending
        confirmed = self.ctx.bookings.confirm_booking(self.admin, bid)
        self.assertEqual(confirmed["booking_status"], "Confirmed")
        with self.assertRaises(BookingError):
            self.ctx.bookings.confirm_booking(self.admin, bid)
        done = self.ctx.bookings.complete_booking(self.admin, bid)
        self.assertEqual(done["booking_status"], "Completed")

    def test_cannot_complete_future_stay(self):
        booking = self.book(self.alice, "101", "2026-10-20", "2026-10-22")
        self.ctx.bookings.confirm_booking(self.admin, booking["booking_id"])
        with self.assertRaises(BookingError):
            self.ctx.bookings.complete_booking(
                self.admin, booking["booking_id"])

    def test_auto_completion_after_checkout(self):
        confirmed = self.book(self.alice, "101", "2026-10-05", "2026-10-08")
        cancelled = self.book(self.bob, "102", "2026-10-05", "2026-10-08")
        pending = self.book(self.bob, "201", "2026-10-05", "2026-10-08")
        self.ctx.bookings.confirm_booking(self.admin, confirmed["booking_id"])
        self.ctx.bookings.cancel_booking(self.bob, cancelled["booking_id"])
        self.clock.today = date(2026, 10, 9)

        def status(booking):
            return self.ctx.bookings.get_booking_details(
                self.admin, booking["booking_id"])["booking_status"]

        self.assertEqual(status(confirmed), "Completed")
        self.assertEqual(status(cancelled), "Cancelled")
        self.assertEqual(status(pending), "Pending")
        history = self.ctx.bookings.get_booking_history(self.alice)
        self.assertEqual([h["booking_id"] for h in history],
                         [confirmed["booking_id"]])

    def test_my_bookings_history_and_search(self):
        first = self.book(self.alice, "101", "2026-10-10", "2026-10-12")
        second = self.book(self.alice, "102", "2026-11-01", "2026-11-03", 2)
        self.ctx.bookings.cancel_booking(self.alice, first["booking_id"])
        active = self.ctx.bookings.get_my_bookings(self.alice)
        self.assertEqual([b["booking_id"] for b in active],
                         [second["booking_id"]])
        history = self.ctx.bookings.get_booking_history(self.alice)
        self.assertEqual(history[0]["booking_status"], "Cancelled")
        mine = self.ctx.bookings.search_bookings(self.alice, room="102")
        self.assertEqual(len(mine), 1)
        by_date = self.ctx.bookings.search_bookings(
            self.admin, on_date="2026-11-02")
        self.assertEqual(len(by_date), 1)
        by_customer = self.ctx.bookings.search_bookings(
            self.admin, customer="ALICE")
        self.assertEqual(len(by_customer), 2)
        by_status = self.ctx.bookings.search_bookings(
            self.admin, status="cancelled")
        self.assertEqual(len(by_status), 1)
        with self.assertRaises(ValidationError):
            self.ctx.bookings.search_bookings(self.admin, status="Bogus")


class CustomerAndProfileTests(BaseCase):
    def test_profile_update_and_duplicates(self):
        self.ctx.customers.update_profile(
            self.alice, full_name="Alice Cooper", email="ac@mail.com",
            phone="+1 555 000 1111")
        profile = self.ctx.customers.get_profile(self.alice)
        self.assertEqual(profile["full_name"], "Alice Cooper")
        self.assertNotIn("password_hash", profile)
        with self.assertRaises(ValidationError):
            self.ctx.customers.update_profile(
                self.alice, email="bob@mail.com")
        with self.assertRaises(ValidationError):
            self.ctx.customers.update_profile(self.alice, phone="12")

    def test_change_password(self):
        with self.assertRaises(AuthenticationError):
            self.ctx.customers.change_password(
                self.alice, "wrongpass1", "newsecret1")
        with self.assertRaises(ValidationError):
            self.ctx.customers.change_password(
                self.alice, "secret12", "weak")
        self.ctx.customers.change_password(
            self.alice, "secret12", "newsecret1")
        with self.assertRaises(AuthenticationError):
            self.ctx.auth.login("alice", "secret12")
        self.assertEqual(
            self.ctx.auth.login("alice", "newsecret1").username, "alice")

    def test_manager_customer_management(self):
        customers = self.ctx.customers.list_customers(self.admin)
        self.assertEqual(len(customers), 2)
        self.assertTrue(all("password_hash" not in c for c in customers))
        cid = customers[0]["user_id"]
        updated = self.ctx.customers.update_customer(
            self.admin, cid, full_name="Renamed Person")
        self.assertEqual(updated["full_name"], "Renamed Person")
        details = self.ctx.customers.get_customer(self.admin, cid)
        self.assertEqual(details["total_bookings"], 0)
        with self.assertRaises(NotFoundError):
            self.ctx.customers.get_customer(
                self.admin, self.admin.user_id)  # managers are not customers
        found = self.ctx.customers.search_customers(
            self.admin, keyword="BOB@MAIL")
        self.assertEqual(len(found), 1)


class ReportTests(BaseCase):
    def test_report_numbers(self):
        a = self.book(self.alice, "101", "2026-10-02", "2026-10-05")   # 3n
        b = self.book(self.bob, "201", "2026-10-10", "2026-10-12", 2)  # 2n
        c = self.book(self.bob, "102", "2026-10-10", "2026-10-12", 2)
        self.ctx.bookings.confirm_booking(self.admin, a["booking_id"])
        self.ctx.bookings.confirm_booking(self.admin, b["booking_id"])
        self.ctx.bookings.cancel_booking(self.bob, c["booking_id"])
        self.ctx.rooms.change_status(
            self.admin, self.room["301"].room_id, "Maintenance")
        report = self.ctx.reports.generate_report(self.admin)
        self.assertEqual(report["total_rooms"], 5)
        self.assertEqual(report["available_rooms"], 4)
        self.assertEqual(report["maintenance_rooms"], 1)
        self.assertEqual(report["total_customers"], 2)
        self.assertEqual(report["total_bookings"], 3)
        self.assertEqual(report["confirmed_bookings"], 2)
        self.assertEqual(report["cancelled_bookings"], 1)
        self.assertEqual(report["total_revenue"], 3 * 45 + 2 * 95)
        self.assertEqual(report["currently_occupied_rooms"], 1)
        self.assertEqual(report["most_common_room_type"]["names"], ["Deluxe"])
        self.assertEqual(report["occupancy_rate"], 25.0)


class StorageTests(BaseCase):
    def test_data_persists_across_restart(self):
        self.book(self.alice, "101", "2026-10-10", "2026-10-12")
        again = ServiceContext(self._tmp.name, self.clock)
        again.initialize()
        admin = again.auth.login("admin", "admin123")
        self.assertEqual(len(again.bookings.get_all_bookings(admin)), 1)
        self.assertEqual(len(again.rooms.get_all_rooms(admin)), 5)

    def test_corrupted_json_is_recovered(self):
        path = Path(self._tmp.name) / "rooms.json"
        path.write_text("{ this is not json", encoding="utf-8")
        again = ServiceContext(self._tmp.name, self.clock)
        again.initialize()  # re-seeds sample rooms
        self.assertEqual(json.loads(path.read_text())[0]["room_number"], "101")
        self.assertTrue(list(Path(self._tmp.name).glob("rooms.corrupt-*")))

    def test_missing_files_are_recreated(self):
        for name in ("users.json", "rooms.json", "bookings.json"):
            (Path(self._tmp.name) / name).unlink()
        again = ServiceContext(self._tmp.name, self.clock)
        again.initialize()
        self.assertEqual(again.auth.login("admin", "admin123").role, "Manager")

    def test_ids_are_never_reused(self):
        first = self.book(self.alice, "101", "2026-10-10", "2026-10-11")
        self.ctx.bookings.cancel_booking(self.alice, first["booking_id"])
        second = self.book(self.alice, "101", "2026-10-10", "2026-10-11")
        self.assertEqual(second["booking_id"], first["booking_id"] + 1)


if __name__ == "__main__":
    unittest.main()
