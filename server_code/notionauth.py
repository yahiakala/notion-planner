"""Public Auth Code."""
import anvil.users
import anvil.secrets
from anvil.tables import app_tables
import anvil.server
import anvil.http


@anvil.server.callable(require_user=True)
def get_auth_code():
    """Get authorization URL."""
    import urllib.parse
    CLIENT_ID = anvil.secrets.get_secret('NOTION_OAUTH_CLIENT_ID')
    # TODO: I think you need to send tenant id in this auth URL redirect param
    auth_url = (
        f"https://api.notion.com/v1/oauth/authorize?client_id={CLIENT_ID}" +
        "&response_type=code&owner=user&redirect_uri=" +
        urllib.parse.quote(anvil.server.get_api_origin() + "/notion_redirect", safe='')
    )
    return auth_url


@anvil.server.http_endpoint('/notion_redirect', cross_site_session=True)
def get_auth_token(**params):
    """Get a user's authentication token using access code."""
    import base64
    CLIENT_ID = anvil.secrets.get_secret('NOTION_OAUTH_CLIENT_ID')
    CLIENT_SECRET = anvil.secrets.get_secret('NOTION_OAUTH_SECRET')

    # check for query param code=this
    # check for query param error=access_denied
    if 'error' in params:
        pass
    else:
        url = 'https://api.notion.com/v1/oauth/token'
        # payload = anvil.server.request.body.get_bytes()
        # payload_dict = json.loads(payload.decode('utf-8'))
        # header_signature = anvil.server.request.headers.get('x-discourse-event-signature')
        # print(payload)
        data = {
            'grant_type': 'authorization_code',
            'code': params['code'],
            'redirect_uri': anvil.server.get_api_origin() + '/notion_redirect'
        }
        client_credentials = CLIENT_ID + ":" + CLIENT_SECRET
        encoded_credentials = base64.b64encode(client_credentials.encode()).decode()
        
        headers = {
            'Authorization': 'Basic ' + encoded_credentials,
            'Content-Type': 'application/json'
        }
        try:
            response = anvil.http.request(url, method='POST', data=data, json=True, headers=headers)
        except anvil.http.HttpError as e:
            print(e.content)
            print(f"Error {e.status}")

        user = anvil.users.get_user(allow_remembered=True)
        # TODO: fix to explicitly get tenant
        userrow = app_tables.usertenant.get(user=user)
        print(response)
        access_token = response["access_token"] # also store bot_id, workspace_id, workspace_name, workspace_icon
        userrow['notion_token'] = anvil.secrets.encrypt_with_key('USER_SETTING', access_token)
    return anvil.server.HttpResponse(302, headers={"Location": anvil.server.get_app_origin() + '/#app/settings'})
