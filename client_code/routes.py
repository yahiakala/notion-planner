import anvil.server
from routing.router import Redirect, Route
from routing.router import TemplateWithContainerRoute as BaseRoute

from .Global import Global


class EnsureUserMixin:
    def before_load(self, **loader_args):
        if not Global.user:
            raise Redirect(path="/signin")
        if Global.user and Global.get_s("tenant") is None:
            Global.tenant = anvil.server.call('get_tenant_single')
            if Global.get_s("tenant") is None:
                Global.tenant = anvil.server.call("create_tenant_single")
            try:
                Global.tenant_id = Global.tenant.get_id()
            except Exception:
                Global.tenant_id = Global.tenant["id"]
            # print(Global.permissions)
            # print(Global.tenant)
            # This executes globalcache in the server
            if "delete_members" in Global.permissions and (
                Global.tenant["name"] is None or Global.tenant["name"] == ""
            ):
                raise Redirect(path="/app/admin")


class SignRoute(BaseRoute):
    # TODO: use Global.deployment to edit route definitions
    template = "Templates.Static"
    path = "/"
    form = "Auth.Sign"
    cache_form = True


class SigninRoute(BaseRoute):
    template = "Templates.Static"
    path = "/signin"
    form = "Auth.Signin"
    cache_form = True


class SignupRoute(BaseRoute):
    template = "Templates.Static"
    path = "/signup"
    form = "Auth.Signup"
    cache_form = True


class HomeRoute(EnsureUserMixin, BaseRoute):
    template = "Templates.Router"
    path = "/app/home"
    form = "App.Home"
    cache_form = True


class SettingsRoute(EnsureUserMixin, BaseRoute):
    template = "Templates.Router"
    path = "/app/settings"
    form = "App.Settings"
    cache_form = True


class AdminRoute(EnsureUserMixin, BaseRoute):
    template = "Templates.Router"
    path = "/app/admin"
    form = "App.Admin"
    cache_form = True


class TasksRoute(EnsureUserMixin, BaseRoute):
    template = "Templates.Router"
    path = "/app/tasks"
    form = "App.Rebalance"
    cache_form = True


class NotFoundRoute(EnsureUserMixin, BaseRoute):
    template = "Templates.Router"
    form = "App.Home"
    default_not_found = True