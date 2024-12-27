import anvil.tables.query as q
from anvil.tables import app_tables
from anvil_squared.helpers import print_timestamp
from anvil_squared.multi_tenant import authorization, tasks
import anvil.users
import anvil_squared.multi_tenant as mt
from . import notionyk


role_dict = {
    "Member": ["schedule_tasks"],
    "Admin": [
        "schedule_tasks",
        "see_members",
        "edit_members",
        "delete_members",
        "delete_admin",
        "edit_roles",
        "edit_integration"
    ],
}


def populate_roles(tenant):
    """Some basic roles."""
    print_timestamp("populate_roles")
    return tasks.populate_roles(tenant, role_dict)


# --------------------
# Return rows as dicts
# --------------------
def usertenant_row_to_dict(row):
    row_dict = {
        "email": row["user"]["email"],
        "last_login": row["user"]["last_login"],
        "signed_up": row["user"]["signed_up"],
        "permissions": authorization.get_permissions(
            None, row["user"], tenant=row["tenant"], usertenant=row
        ),
        "roles": authorization.get_user_roles(None, None, row, row["tenant"]),
        # "prop_mapping": row["prop_mapping"],
        # "max_daily_hours": row["max_daily_hours"],
        # "defaults": row["defaults"],
        # "notion_token": row["notion_token"],
        # "notion_db": row["notion_db"]
    }
    return row_dict


def role_row_to_dict(role):
    if role["permissions"]:
        role_perm = [j["name"] for j in role["permissions"]]
    else:
        role_perm = []
    return {
        "name": role["name"],
        "last_update": role["last_update"],
        "guides": app_tables.rolefiles.search(role=role),
        "permissions": role_perm,
        "can_edit": role["can_edit"],
    }

# -------
# Tenants
# -------
@anvil.server.callable(require_user=True)
def get_tenant_single(user=None, tenant=None):
    """Get the tenant in this instance."""
    user = user or anvil.users.get_user(allow_remembered=True)
    tenant = tenant or app_tables.tenants.get()

    if not tenant:
        return None

    # Eventually deprecate
    tenant['prop_mapping'] = tenant['prop_mapping'] or notionyk.props_dict
    tenant['max_daily_hours'] = tenant['max_daily_hours'] or 6
    tenant['defaults'] = tenant['defaults'] or {'hours': 4}
    
    tenant_dict = {
        "id": tenant.get_id(),
        "name": tenant["name"],
        "prop_mapping": tenant["prop_mapping"],
        "max_daily_hours": tenant["max_daily_hours"],
        "defaults": tenant["defaults"],
        "notion_token": tenant["notion_token"],
        "notion_db": tenant["notion_db"]
    }
    if user:
        tenant, usertenant, permissions = mt.authorization.validate_user(
            tenant.get_id(), user, tenant=tenant
        )
        if "delete_members" in permissions:
            # TODO: do not return client writable
            return app_tables.tenants.client_writable().get()

    return tenant_dict


@anvil.server.callable(require_user=True)
def create_tenant_single():
    """Create a tenant."""
    user = anvil.users.get_user(allow_remembered=True)
    _ = mt.single_tenant.create_tenant_single(user, role_dict, "Admin", ["Member"])
    tenant = app_tables.tenants.get()
    tenant['prop_mapping'] = notionyk.props_dict
    tenant['defaults'] = {"hours": 4}
    tenant['max_daily_hours'] = 6
    return mt.single_tenant.get_tenant_single(user, tenant)


def get_deployment():
    try:
        _ = anvil.secrets.get_secret("NOTION_OAUTH_CLIENT_ID")
        return "saas"
    except anvil.secrets.SecretError:
        return "oss"