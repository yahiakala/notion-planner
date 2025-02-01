from routing.router import launch

from .Global import Global
from . import routes  # noqa

if __name__ == "__main__":
    Global.deployment = 'oss'
    launch()
