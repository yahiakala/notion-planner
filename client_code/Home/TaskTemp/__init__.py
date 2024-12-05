from ._anvil_designer import TaskTempTemplate
from anvil import *
import anvil.server

from ...Global import Global


class TaskTemp(TaskTempTemplate):
    def __init__(self, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)
        self.link_task.text = (
            self.item['name'] + f' ({self.item["hours"]} Hours)'
        )
        self.link_task.url = self.item['url']
        if Global.is_mobile:
            pass
        else:
            self.btn_pause.text = 'Remove Task Deadline'
            self.btn_later.text = 'Turn into soft deadline'
            self.btn_shift.text = 'Delay deadline by a day'

    def btn_pause_click(self, **event_args):
        """This method is called when the button is clicked"""
        anvil.server.call('remove_task_deadline', self.item)
        self.parent.raise_event('x-removetask', task=self.item)

    def btn_later_click(self, **event_args):
        """This method is called when the button is clicked"""
        anvil.server.call('remove_hard_deadline', self.item)
        self.parent.raise_event('x-removetask', task=self.item)

    def btn_shift_click(self, **event_args):
        """This method is called when the button is clicked"""
        anvil.server.call('delay_deadline', self.item)
        self.parent.raise_event('x-removetask', task=self.item)

