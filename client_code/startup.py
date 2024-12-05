from anvil_extras import routing

from .Router import Router  # noqa
from .BlankTemplate import BlankTemplate  # noqa
from .Static import Static  # noqa
# from . import Global
from .Global import Global


@routing.redirect(path="app", priority=20, condition=lambda: Global.user is None)
def redirect_no_user():
    return "sign"

hash, pattern, dict = routing.get_url_components()

routing.set_url_hash(hash)

routing.launch()