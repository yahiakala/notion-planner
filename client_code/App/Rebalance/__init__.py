from ._anvil_designer import RebalanceTemplate
from anvil import *
import anvil.users
import anvil.server
import webbrowser
from ...Global import Global


class Rebalance(RebalanceTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    
  def button_rebalance_click(self, **event_args):
    """This method is called when the button is clicked"""
    anvil.server.call('rebalance1_call', Global.tenant_id)

  def button_task_click(self, **event_args):
    """This method is called when the button is clicked"""
    task_url = anvil.server.call('give_me_task', Global.tenant_id)
    webbrowser.open_new_tab(task_url)
