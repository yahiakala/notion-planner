"""Public Auth Code."""

import base64
import json

import anvil.http
import anvil.secrets
import anvil.server
import anvil.users
from anvil.tables import app_tables


@anvil.server.callable(require_user=True)
def get_auth_code(tenant_id):
    """Get authorization URL."""
    import urllib.parse

    CLIENT_ID = anvil.secrets.get_secret("NOTION_OAUTH_CLIENT_ID")
    # Encode tenant_id in state parameter
    state = base64.urlsafe_b64encode(
        json.dumps({"tenant_id": tenant_id}).encode()
    ).decode()

    auth_url = (
        f"https://api.notion.com/v1/oauth/authorize?client_id={CLIENT_ID}"
        + "&response_type=code&owner=user"
        + f"&state={state}"
        + "&redirect_uri="
        + urllib.parse.quote(
            anvil.server.get_api_origin() + "/notion_redirect", safe=""
        )
    )
    return auth_url


@anvil.server.http_endpoint("/notion_redirect", cross_site_session=True)
def get_auth_token(**params):
    """Get a user's authentication token using access code."""
    import base64

    CLIENT_ID = anvil.secrets.get_secret("NOTION_OAUTH_CLIENT_ID")
    CLIENT_SECRET = anvil.secrets.get_secret("NOTION_OAUTH_SECRET")

    # check for query param code=this
    # check for query param error=access_denied
    if "error" in params:
        pass
    else:
        # Decode state parameter to get tenant_id
        state_data = json.loads(base64.urlsafe_b64decode(params["state"]).decode())
        tenant_id = state_data["tenant_id"]
        print(tenant_id)

        url = "https://api.notion.com/v1/oauth/token"
        data = {
            "grant_type": "authorization_code",
            "code": params["code"],
            "redirect_uri": anvil.server.get_api_origin() + "/notion_redirect",
        }
        client_credentials = CLIENT_ID + ":" + CLIENT_SECRET
        encoded_credentials = base64.b64encode(client_credentials.encode()).decode()

        headers = {
            "Authorization": "Basic " + encoded_credentials,
            "Content-Type": "application/json",
        }
        try:
            response = anvil.http.request(
                url, method="POST", data=data, json=True, headers=headers
            )
        except anvil.http.HttpError as e:
            print(e.content)
            print(f"Error {e.status}")

        user = anvil.users.get_user(allow_remembered=True)
        # Use both user and tenant_id to get the correct row
        userrow = app_tables.usertenant.get(user=user, tenant_id=tenant_id)
        print(response)
        access_token = response["access_token"]
        userrow["notion_token"] = anvil.secrets.encrypt_with_key(
            "USER_SETTING", access_token
        )
    return anvil.server.HttpResponse(
        302, headers={"Location": anvil.server.get_app_origin() + "/#app/settings"}
    )
