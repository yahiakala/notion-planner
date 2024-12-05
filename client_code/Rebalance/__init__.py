from ._anvil_designer import RebalanceTemplate
from anvil import *
import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from anvil_extras import routing
import webbrowser


@routing.route('/rebalance', template='Router')
class Rebalance(RebalanceTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    
    # Any code you write here will run when the form opens.

  def button_rebalance_click(self, **event_args):
    """This method is called when the button is clicked"""
    anvil.server.call('rebalance1_call')

  def button_task_click(self, **event_args):
    """This method is called when the button is clicked"""
    task_url = anvil.server.call('give_me_task')
    webbrowser.open_new_tab(task_url)
    pass


