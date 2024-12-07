import time

import anvil.users
from anvil import *
from routing import router

from ...Global import AppName, Global  # noqa
from ._anvil_designer import SignTemplate


class Sign(SignTemplate):
    def __init__(self, routing_context: router.RoutingContext, **properties):
        self.init_components(**properties)
        self.url_dict = routing_context.query
        self.user = Global.user
        if self.user:
            router.navigate(path="/app/home")

        is_mobile = anvil.js.window.navigator.userAgent.lower().find("mobi") > -1
        if is_mobile:
            self.spacer_1.visible = False
            self.cp_login.role = ["narrow-col", "narrow-col-mobile"]

    def btn_signin_click(self, **event_args):
        """This method is called when the button is clicked"""
        router.navigate(path="/signin", query=self.url_dict)

    def btn_signup_click(self, **event_args):
        """This method is called when the button is clicked"""
        router.navigate(path="/signup", query=self.url_dict)

    def form_show(self, **event_args):
        """Skip expansion animation with cp inside of fp."""
        time.sleep(0.3)
        self.fp_outer.visible = True
