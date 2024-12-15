import anvil.server
import anvil.users
# from anvil_squared.multi_tenant import single_tenant
import anvil_squared.multi_tenant as mt
import anvil.secrets
from .helpers import role_dict
from anvil.tables import app_tables
from . import notionyk


@anvil.server.callable(require_user=True)
def create_tenant_single():
    """Create a tenant."""
    user = anvil.users.get_user(allow_remembered=True)
    _ = mt.single_tenant.create_tenant_single(user, role_dict, "Admin", ["Applicant"])
    tenant = app_tables.tenants.get()
    tenant['prop_mapping'] = notionyk.props_dict
    tenant['defaults'] = {"hours": 4}
    tenant['max_daily_hours'] = 6
    return mt.single_tenant.get_tenant_single(user, tenant)


@anvil.server.callable(require_user=True)
def save_notion_token(tenant_id, notion_token):
    user = anvil.users.get_user(allow_remembered=True)
    tenant, usertenant, permissions = mt.authorization.validate_user(tenant_id, user)
    if 'edit_integration' in permissions:
        tenant['notion_token'] = anvil.secrets.encrypt_with_key('USER_SETTING', notion_token)