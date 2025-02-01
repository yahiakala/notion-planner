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

    def btn_reschedule_click(self, **event_args):
        """This method is called when the button is clicked"""
        if 'schedule_tasks' not in Global.usertenant['plan_permissions']:
            print(Global.usertenant['plan_permissions'])
            alert('Upgrade to access this feature')
        else:
            c = confirm("Are you sure you want to reschedule all your tasks?")
            if c:
                try:
                    _ = anvil.server.call_s("rebalance1_call", Global.tenant_id)
                    self.btn_refresh_today.enabled = False
                    self.btn_reschedule.enabled = False
                    self.cp_loading.visible = True
                    self.ti_reschedule.interval = 2
                except anvil.server.PermissionDenied:
                    alert('You do not have permission for this action. Please contact your administrator.')
                except Exception as e:
                    alert(str(e))

    def ti_reschedule_tick(self, **event_args):
        """This method is called Every [interval] seconds. Does not trigger if [interval] is 0."""
        print_timestamp("ti_reschedule_tick")

        with anvil.server.no_loading_indicator:
            if not anvil.server.call(
                "dt_bk_running", Global.tenant_id, "tenants", "rebalance1_single"
            ):
                print_timestamp("ti_reschedule_tick: last one")
                self.ti_reschedule.interval = 0
                self.cp_loading.visible = False
                self.btn_refresh_today.enabled = True
                self.btn_reschedule.enabled = True

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
