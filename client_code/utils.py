import anvil
import anvil.users

from .Global import Global


def responsive_button(text, background, icon):
    """Get rid of the text and just keep the icon if it is on mobile."""
    if Global.is_mobile:
        if len(text) > 5:
            text = ''
            fsize = 32
        else:
            fsize = 12
        return anvil.Button(text=text, visible=True, background=background,
            icon=icon, icon_align='top', align='full', width='default',
            font_size=fsize
        )
    else:
        return anvil.Button(
            text=text,
            visible=True,
            background=background,
            icon=icon,
            align='full',
            width='default'
        )