"""Deadline Rebalancer."""

import anvil.js
import anvil.server
import anvil.users
from anvil import *
from anvil_squared.utils import print_timestamp
from routing import router

from ...Global import Global
from ._anvil_designer import HomeTemplate


class Home(HomeTemplate):
    def __init__(self, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)

        # Get the max number of hours to schedule in a day (x)
        self.tenant = Global.tenant

    def _set_loading_state(self, is_loading: bool) -> None:
        """Helper to manage loading state of components"""
        self.btn_refresh_today.enabled = not is_loading
        self.btn_reschedule.enabled = not is_loading
        self.cp_loading.visible = is_loading
        self.ti_reschedule.interval = 2 if is_loading else 0

    def btn_reschedule_click(self, **event_args):
        """Handle rescheduling of all tasks"""
        if "schedule_tasks" not in Global.usertenant["plan_permissions"]:
            alert("Upgrade to access this feature")
            return

        if not confirm("Are you sure you want to reschedule all your tasks?"):
            return

        try:
            _ = anvil.server.call_s("rebalance1_call", Global.tenant_id)
            self._set_loading_state(True)
        except anvil.server.PermissionDenied:
            alert(
                "You do not have permission for this action. Please contact your administrator."
            )

    def ti_reschedule_tick(self, **event_args):
        """Check rebalancing status every interval"""
        print_timestamp("ti_reschedule_tick")

        with anvil.server.no_loading_indicator:
            if not anvil.server.call(
                "dt_bk_running", Global.tenant_id, "tenants", "rebalance1_single"
            ):
                print_timestamp("ti_reschedule_tick: last one")
                self._set_loading_state(False)

    def btn_settings_click(self, **event_args):
        """This method is called when the button is clicked"""
        router.navigate("/app/settings")

    def btn_refresh_today_click(self, **event_args):
        """This method is called when the button is clicked"""
        if self.tenant["notion_db"]:
            print("https://notion.so/" + self.tenant["notion_db"]["id"])
            anvil.js.window.location.href = "https://notion.so/" + self.tenant[
                "notion_db"
            ]["id"].replace("-", "")
