"""Deadline Rebalancer."""
from ._anvil_designer import HomeTemplate
from anvil import *
import anvil.users
import anvil.server
import anvil.js

# from .. import Global
from ..Global import Global
from anvil_extras import routing
from ..utils import print_timestamp


@routing.route('', template='Router')
@routing.route('/home', template='Router')
class Home(HomeTemplate):
    def __init__(self, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)
    
        # Get the max number of hours to schedule in a day (x)
        self.usermap = Global.usermap
        

    def btn_reschedule_click(self, **event_args):
        """This method is called when the button is clicked"""
        c = confirm('Are you sure you want to reschedule all your tasks?')
        if c:
            self.btn_refresh_today.enabled = False
            self.btn_reschedule.enabled = False
            self.cp_loading.visible = True
            _ = anvil.server.call_s('rebalance1_call')
            self.ti_reschedule.interval = 2

    def ti_reschedule_tick(self, **event_args):
        """This method is called Every [interval] seconds. Does not trigger if [interval] is 0."""
        print_timestamp('ti_reschedule_tick')

        with anvil.server.no_loading_indicator:
            if not anvil.server.call('dt_bk_running', 'usermap', 'rebalance1_single'):
                print_timestamp('ti_reschedule_tick: last one')
                self.ti_reschedule.interval = 0
                self.cp_loading.visible = False
                self.btn_refresh_today.enabled = True
                self.btn_reschedule.enabled = True

    def btn_settings_click(self, **event_args):
        """This method is called when the button is clicked"""
        routing.set_url_hash('app/settings')

    def btn_refresh_today_click(self, **event_args):
        """This method is called when the button is clicked"""
        if self.usermap['notion_db']:
            print('https://notion.so/' + self.usermap['notion_db']['id'])
            anvil.js.window.location.href = (
                'https://notion.so/' + self.usermap['notion_db']['id'].replace('-', '')
            )
            