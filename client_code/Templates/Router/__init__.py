import anvil.server
import anvil.users
from anvil import *
from routing import router

from ...Global import Global
from ._anvil_designer import RouterTemplate


class Router(RouterTemplate):
    def __init__(self, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)
        is_mobile = anvil.js.window.navigator.userAgent.lower().find("mobi") > -1
        Global.is_mobile = is_mobile

        # Any code you write here will run when the form opens.
        user = Global.user
        self.set_account_state(user)

    def on_form_load(self, url_hash, url_pattern, url_dict, form):
        """Any time a form is loaded."""
        self.set_account_state(Global.user)

    def link_logout_click(self, **event_args):
        with anvil.server.no_loading_indicator:
            anvil.users.logout()
            self.set_account_state(None)
            router.clear_cache()
            Global.clear_global_attributes()
            router.navigate(path="/signin")

    def set_account_state(self, user):
        """Control visibility of links."""
        pass

    def link_help_click(self, **event_args):
        """This method is called when the link is clicked"""
        alert("For help please email support@dreambyte.ai")
