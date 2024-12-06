import anvil.server
import anvil.users
from anvil_squared.multi_tenant import single_tenant

from .helpers import role_dict


@anvil.server.callable(require_user=True)
def create_tenant_single():
    """Create a tenant."""
    user = anvil.users.get_user(allow_remembered=True)
    return single_tenant.create_tenant_single(user, role_dict, "Admin", ["Member"])
