import anvil.server
from routing.router import Redirect
from routing.router import TemplateWithContainerRoute as BaseRoute

from .Global import Global


class EnsureUserMixin:
    def before_load(self, **loader_args):
        if not Global.user:
            raise Redirect(path="/signin")
        if Global.user and Global.get_s("tenant") is None:
            Global.tenant = anvil.server.call("get_tenant_single_squared")
            if Global.get_s("tenant") is None:
                Global.tenant = anvil.server.call("create_tenant_single")
            try:
                Global.tenant_id = Global.tenant.get_id()
            except Exception:
                Global.tenant_id = Global.tenant["id"]
            print(Global.permissions)
            print(Global.tenant)
            if "delete_members" in Global.permissions and (
                Global.tenant["name"] is None or Global.tenant["name"] == ""
            ):
                raise Redirect(path="/app/admin")


class LandingRoute(BaseRoute):
    template = "Templates.Website"
    path = "/"
    form = "Website.Landing"
    cache_form = True


class SignRoute(BaseRoute):
    template = "Templates.Static"
    path = "/sign"
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


class TestsRoute(EnsureUserMixin, BaseRoute):
    template = "Templates.Router"
    path = "/app/tests"
    form = "App.Tests"
    cache_form = True
