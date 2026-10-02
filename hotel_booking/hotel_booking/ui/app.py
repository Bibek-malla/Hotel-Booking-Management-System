"""Top-level console application: login, registration, dashboards."""
from ui.console import (
    CANCEL_KEYWORD, choose_option, pause, print_error, print_header,
    print_info, print_success, prompt_value, read_password, run_action,
)
from ui.customer_menu import CustomerMenu
from ui.forms import ask_new_password, email_validator, username_validator
from ui.manager_menu import ManagerMenu
from utils.constants import MAX_LOGIN_ATTEMPTS, ROLE_CUSTOMER, ROLE_MANAGER
from utils.exceptions import AuthenticationError
from utils.validators import validate_full_name, validate_phone

DASHBOARDS = {ROLE_CUSTOMER: CustomerMenu, ROLE_MANAGER: ManagerMenu}


class ConsoleApp:
    MENU = ("Login", "Register", "Exit")

    def __init__(self, ctx):
        self.ctx = ctx

    def run(self):
        while True:
            choice = choose_option(
                list(self.MENU), title="HOTEL BOOKING MANAGEMENT SYSTEM")
            if choice == 1:
                run_action(self._login)
            elif choice == 2:
                run_action(self._register)
                pause()
            else:
                print_info("Thank you for using the Hotel Booking "
                           "Management System. Goodbye!")
                return

    def _login(self):
        print_header("LOGIN")
        print_info(f"Type {CANCEL_KEYWORD} to return to the main menu.")
        user = None
        for attempt in range(1, MAX_LOGIN_ATTEMPTS + 1):
            username = prompt_value("Username")
            password = read_password("Password")
            try:
                user = self.ctx.auth.login(username, password)
                break
            except AuthenticationError as exc:
                print_error(str(exc))
                remaining = MAX_LOGIN_ATTEMPTS - attempt
                if remaining:
                    print_info(f"{remaining} attempt(s) remaining.")
        if user is None:
            print_error("Too many failed attempts. Returning to the main "
                        "menu.")
            return

        print_success(f"Login successful. Signed in as {user.role}.")
        self.ctx.bookings.refresh_statuses()
        try:
            DASHBOARDS[user.role](self.ctx, user).run()
        finally:
            self.ctx.auth.logout()
            print_success("You have been logged out.")

    def _register(self):
        print_header("CUSTOMER REGISTRATION")
        print_info(f"Type {CANCEL_KEYWORD} at any prompt to go back.")
        full_name = prompt_value("Full name", validate_full_name)
        username = prompt_value(
            "Username (3-20 letters, digits, _ or .)",
            username_validator(self.ctx))
        email = prompt_value("Email", email_validator(self.ctx))
        phone = prompt_value("Phone", validate_phone)
        password = ask_new_password()
        customer = self.ctx.auth.register_customer(
            full_name, username, email, password, phone)
        print_success(f"Account created for {customer.full_name}. "
                      "You can now log in.")
