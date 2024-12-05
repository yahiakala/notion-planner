"""Read Notion Tasks."""
import anvil.http
import anvil.server
import anvil.users
import anvil.secrets
from anvil.tables import app_tables


def isodate(iso_string):
    import datetime as dt
    iso_string2 = iso_string.replace('Z', '+00:00')
    return dt.datetime.strptime(iso_string2, "%Y-%m-%dT%H:%M:%S.%f%z")


def _read_property_checkbox(property_object):
    return property_object['checkbox']


def _read_property_title(property_object):
    return ''.join([j['plain_text'] for j in property_object['title']])


def _read_property_number(property_object):
    return property_object['number']


def _read_property_date(property_object):
    """Read date with a default value of Jan 1 2099 but null string."""
    import datetime as dt
    if property_object['date']:
        return {
            'string': property_object['date']['start'],
            'datetime': dt.datetime.strptime(property_object['date']['start'], '%Y-%m-%d')
        }
    else:
        return {'string': '', 'datetime': dt.datetime.strptime('2099-01-01', '%Y-%m-%d')}


def _read_property_lastedit(property_object):
    return {
        'string': property_object['last_edited_time'],
        'datetime': isodate(property_object['last_edited_time'])
    }


def _read_property_dummy(property_object):
    return None


prop_proc_dict = {
    'relation': _read_property_dummy,
    'date': _read_property_date,
    'formula': _read_property_dummy,
    'checkbox': _read_property_checkbox,
    'select': _read_property_dummy,
    'rollup': _read_property_dummy,
    'last_edited_time': _read_property_lastedit,
    'url': _read_property_dummy,
    'last_edited_by': _read_property_dummy,
    'created_time': _read_property_dummy,
    'number': _read_property_number,
    'title': _read_property_title,
    'button': _read_property_dummy
}


def get_database(database_id, notion_token):
    """Get a database by its id."""
    url = f"https://api.notion.com/v1/databases/{database_id}"
    headers = {
        "Authorization": "Bearer " + notion_token,
        "Content-Type": "application/json",
        "Notion-Version": "2022-02-22"
    }
    response = anvil.http.request(url, json=True, headers=headers)
    return response

def search_databases(notion_token):
    """Get all databases from integration."""
    url = "https://api.notion.com/v1/search"
    headers = {
        "Authorization": "Bearer " + notion_token,
        "Content-Type": "application/json",
        "Notion-Version": "2022-02-22"
    }
    payload = {
        "filter": {
            "value": "database",
            "property": "object"
        },
        "page_size": 100
    }
    response = anvil.http.request(url, method='POST', data=payload, json=True, headers=headers)
    return response


def get_response(database_id, notion_token, queryfilter=None, sorts=None,
                 starter=None):
    """
    Query the database with the provided filter.

    Returns list of dicts.
    """
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": "Bearer " + notion_token,
        "Content-Type": "application/json",
        "Notion-Version": "2022-02-22"
    }
    payload = {"page_size": 100}
    if queryfilter:
        payload['filter'] = queryfilter
    if sorts:
        payload['sorts'] = sorts
    if starter:
        payload['start_cursor'] = starter
    response = anvil.http.request(url, method='POST', data=payload, json=True, headers=headers)
    return response


def format_response(data, prop_mapping, defaults=None):
    """Turn Notion API response into a cleaner list of dicts."""
    output_list = []
    # print(data['results'])
    if len(data['results']) == 0:
        print('No results.')
        return output_list
    prop_types = get_types(data)

    
    for i in data['results']:
        data_dict = {}
        task_prop = i['properties']
        data_dict['id'] = i['id']
        data_dict['url'] = i['url']

        for property in prop_types:
            task_prop[property['name']] = prop_proc_dict[property['type']](task_prop[property['name']])

        
        for prop, user_prop in prop_mapping.items():
            data_dict[prop] = task_prop[user_prop]
        
        if defaults:
            for default_key, default_val in defaults.items():
                data_dict[default_key] = data_dict[default_key] or default_val

        output_list.append(data_dict)

    return output_list


def get_types(resp):
    return [{'name': key, 'type': val['type']}
            for key, val in resp['results'][0]['properties'].items()]


def get_all_data(notion_token, database_id, property_mapping,
                 defaults=None, queryfilter=None, sorts=None):
    """Read all the tasks from the Notion tasks database."""
    data_list = []
    resp1 = get_response(
        database_id, notion_token,
        queryfilter=queryfilter,
        sorts=sorts
    )
    more_data = resp1['has_more']
    starter = resp1['next_cursor']
    data_list += format_response(resp1, property_mapping, defaults)
    # print(data_list)
    while more_data:
        resp2 = get_response(
            database_id, notion_token,
            starter=starter, queryfilter=queryfilter,
            sorts=sorts
        )
        more_data = resp2['has_more']
        starter = resp2['next_cursor']
        data_list += format_response(resp2, property_mapping, defaults)
    return data_list