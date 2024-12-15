import anvil.tables.query as q
from anvil.tables import app_tables
from anvil_squared.helpers import print_timestamp
from anvil_squared.multi_tenant import authorization, tasks

from . import routes  # noqa

role_dict = {
    "Member": ["see_profile"],
    "Admin": [
        "see_profile",
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
