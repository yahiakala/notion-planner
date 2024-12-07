from anvil import *

from ._anvil_designer import StaticTemplate


class Static(StaticTemplate):
    def __init__(self, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)
