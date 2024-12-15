import anvil.server
import anvil.tables.query as q
import anvil.users
import anvil_squared.multi_tenant as mt
from anvil.tables import app_tables
from anvil_squared.helpers import print_timestamp
import anvil.secrets

from . import notionyk
from .helpers import usertenant_row_to_dict


# --------------------
# Non tenanted globals
# --------------------
@anvil.server.callable(require_user=True)
def get_data(key):
    print_timestamp(f"get_data: {key}")
    # user = anvil.users.get_user(allow_remembered=True)
    if key == "all_permissions":
        return mt.authorization.get_all_permissions()
    elif key == "deployment":
        return get_deployment()


def get_deployment():
    try:
        _ = anvil.secrets.get_secret("NOTION_OAUTH_CLIENT_ID")
        return "saas"
    except anvil.secrets.SecretError:
        return "oss"


# ----------------
# Tenanted globals
# ----------------
@anvil.server.callable(require_user=True)
def get_tenanted_data(tenant_id, key):
    print_timestamp(f"get_tenanted_data: {key}")
    user = anvil.users.get_user(allow_remembered=True)

    if key == "users":
        return get_users_iterable(tenant_id, user)
    elif key == "permissions":
        return mt.authorization.get_permissions(tenant_id, user)
    elif key == "usertenant":
        return get_usertenant_dict(tenant_id, user)
    elif key == 'notion_token':
        return get_notion_token(tenant_id, user)


def get_users_iterable(tenant_id, user):
    """Get an iterable of the users."""
    tenant, usertenant, permissions = mt.authorization.validate_user(tenant_id, user)
    if "see_members" not in permissions:
        return []
    return app_tables.usertenant.client_readable(q.only_cols("user"), tenant=tenant)


def get_usertenant_dict(tenant_id, user):
    """Get user tenant data including Notion settings"""
    tenant, usertenant, permissions = mt.authorization.validate_user(tenant_id, user)

    # usertenant["prop_mapping"] = usertenant["prop_mapping"] or notionyk.props_dict
    # usertenant["max_daily_hours"] = usertenant["max_daily_hours"] or 6
    # usertenant["defaults"] = usertenant["defaults"] or {"hours": 4}

    data = usertenant_row_to_dict(usertenant)
    return data


def get_notion_token(tenant_id, user):
    tenant, usertenant, permissions = mt.authorization.validate_user(tenant_id, user)
    if 'edit_integration' in permissions:
        try:
            return anvil.secrets.decrypt_with_key('USER_SETTING', tenant['notion_token'])
        except anvil.secrets.SecretError as e:
            if 'This is not a valid key' in str(e):
                return ''
            else:
                raise
    else:
        return ''