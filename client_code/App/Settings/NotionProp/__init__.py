import anvil.server
from anvil import *

from ....Global import Global
from ._anvil_designer import NotionPropTemplate


class NotionProp(NotionPropTemplate):
    def __init__(self, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)
        # self.tb_prop_change()

    def tb_prop_change(self, **event_args):
        """Validate the property name against the database."""
        self.lbl_error.visible = False
        self.icon_err.visible = False
        self.icon_ok.visible = False
        try:
            Global.usertenant = anvil.server.call(
                "validate_prop",
                Global.tenant_id,
                self.item["type"],
                self.tb_prop.text,
                self.item["id"],
            )
            self.icon_ok.visible = True
            Global.today_tasks = None
            Global.props_list = None
        except Exception as e:
            if "NotionError" in str(e):
                self.lbl_error.text = str(e.args[0]).replace("NotionError:", "").strip()
                self.lbl_error.visible = True
                self.icon_err.visible = True
            else:
                raise
