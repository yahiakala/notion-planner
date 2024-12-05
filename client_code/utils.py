import anvil
import datetime as dt
import anvil.users
from anvil_extras import routing

from . import Global


def print_timestamp(input_str):
    print(input_str, " : ", dt.datetime.now().strftime("%H:%M:%S.%f"))


def responsive_button(text, background, icon):
    """Get rid of the text and just keep the icon if it is on mobile."""
    if Global.is_mobile:
        if len(text) > 5:
            text = ''
            fsize = 32
        else:
            fsize = 12
        return Button(text=text, visible=True, background=background,
                      icon=icon, icon_align='top', align='full', width='default',
                      font_size=fsize
                     )
    else:
        return Button(text=text,
                      visible=True,
                      background=background,
                      icon=icon,
                      align='full',
                      width='default')