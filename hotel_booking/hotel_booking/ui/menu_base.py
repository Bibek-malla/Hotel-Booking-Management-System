"""Shared dashboard loop for the customer and manager menus."""
from ui.console import choose_option, pause, run_action


class DashboardMenu:
    """Subclasses define TITLE, OPTIONS and ``actions()``.

    The last option is always Logout. ``actions()`` maps a menu number to
    (handler, pause_afterwards).
    """

    TITLE = "DASHBOARD"
    OPTIONS = ()

    def __init__(self, ctx, user):
        self.ctx = ctx
        self.user = user

    def actions(self):
        raise NotImplementedError

    def run(self):
        actions = self.actions()
        logout_choice = len(self.OPTIONS)
        while True:
            choice = choose_option(
                list(self.OPTIONS), title=self.TITLE,
                welcome=f"Welcome, {self.user.greeting_name}")
            if choice == logout_choice:
                return
            handler, should_pause = actions[choice]
            run_action(handler)
            if should_pause:
                pause()
