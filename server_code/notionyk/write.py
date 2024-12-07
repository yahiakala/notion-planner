"""Write Notion Tasks."""

import anvil.http
import anvil.server


def patch_page(notion_token, page_id, payload_dict):
    NOTION_URL_PAGE = "https://api.notion.com/v1/pages/"
    url = NOTION_URL_PAGE + page_id
    headers = {
        "Authorization": "Bearer " + notion_token,
        "Accept": "application/json",
        "Notion-Version": "2022-02-22",
        "Content-Type": "application/json",
    }
    response = anvil.http.request(
        url, method="PATCH", data=payload_dict, json=True, headers=headers
    )
    return response


def prop_date_value(notion_token, page_id, prop_name, date_val, verbose=True):
    """Change a date property value in a database-type page."""
    # date_val should be YYYY-MM-DD
    date_obj = {"date": {"start": date_val, "end": None, "time_zone": None}}
    if date_val == "" or date_val == None:  # noqa
        date_obj = {"date": None}
    payload = {"properties": {prop_name: date_obj}}
    response = patch_page(notion_token, page_id, payload)
    if verbose:
        print(response)
    return None


def prop_bool_value(notion_token, page_id, prop_name, val, verbose=True):
    """Change a checkbox value."""
    bool_obj = {"checkbox": val}
    payload = {"properties": {prop_name: bool_obj}}
    response = patch_page(notion_token, page_id, payload)
    if verbose:
        print(response)
    return None
