from ._anvil_designer import RouterTemplate
from anvil import *
import anvil.users
import anvil.server

from anvil_extras import routing

from ..Home import Home
from ..Rebalance import Rebalance
from ..Settings import Settings
# from .. import Global
from ..Global import Global


@routing.template(path='app', priority=1, condition=None)
class Router(RouterTemplate):
    def __init__(self, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)
        is_mobile = anvil.js.window.navigator.userAgent.lower().find("mobi") > -1
        Global.is_mobile = is_mobile

        self.link_home.tag.url_hash = 'app/home'
        self.link_account.tag.url_hash = 'app/account'
        self.link_settings.tag.url_hash = 'app/settings'
        self.link_tasks.tag.url_hash = 'app/rebalance'
        self.link_logout.tag.url_hash = 'dummy'
    
        # Any code you write here will run when the form opens.
        user = Global.user
        self.set_account_state(user)
        self.nav_click(self.link_home)

    def nav_click(self, sender, **event_args):
        if sender.tag.url_hash == '':
            if Global.user:
                self.set_account_state(Global.user)
                routing.set_url_hash('app/home')
            else:
                routing.set_url_hash('signin')
        else:
            routing.set_url_hash(sender.tag.url_hash)

    def on_navigation(self, url_hash, url_pattern, url_dict, unload_form):
        """Whenever a new route is loaded."""
        for link in self.cp_sidebar.get_components():
            if type(link) == Link:
                link.role = 'selected' if link.tag.url_hash == url_hash else None
        if url_hash in ['app', '']:
            self.link_home.role = 'selected'

    def on_form_load(self, url_hash, url_pattern, url_dict, form):
        """Any time a form is loaded."""
        self.set_account_state(Global.user)

    def link_logout_click(self, **event_args):
        """This method is called when the link is clicked"""
        Global.clear_global_attributes()
        anvil.users.logout()
        self.set_account_state(None)
        routing.set_url_hash('signin')
        routing.clear_cache()

    def set_account_state(self, user):
        """Control visibility of links."""
        # self.link_account.visible = user is not None
        self.link_logout.visible = user is not None
        # self.link_dash.visible = user is not None
        # self.link_tasks.visible = user is not None
        self.link_settings.visible = user is not None

    def btn_help_click(self, **event_args):
        """This method is called when the button is clicked"""
        alert('For help please email support@dreambyte.ai')
