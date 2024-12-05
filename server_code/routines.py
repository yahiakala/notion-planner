"""Main server module for callables."""
import anvil.users
import anvil.server
import anvil.secrets
from anvil.tables import app_tables
import anvil.tables.query as q

from . import notionyk

from anvil_extras.authorisation import authorisation_required
from anvil_extras import authorisation
from anvil_squared.helpers import print_timestamp, proceed_or_abort, user_bk_running, proceed_or_wait

authorisation.set_config(get_roles='usermap')


@anvil.server.callable(require_user=True)
def get_permissions():
    # TODO: add to anvil extras
    user = anvil.users.get_user(allow_remembered=True)
    usermap = app_tables.usermap.get(user=user)
    try:
        user_permissions = set(
            permission["name"]
            for role in usermap["roles"]
            for permission in role["permissions"]
        )
        return list(user_permissions)
    except TypeError:
        return []


@anvil.server.callable(require_user=True)
def get_max_hrs():
    """Return the max hours defined by the user."""
    usermap = get_usermap()
    return usermap['max_daily_hours'] or 6


@anvil.server.callable(require_user=True)
def get_today_tasks():
    """Give me all my tasks for today."""
    import datetime as dt
    import pytz
    usermap = get_usermap()
    if not usermap['notion_token'] or not usermap['prop_mapping'] or not ['notion_db'] or not validate_props(silent=True):
        return []
    
    notion_token = anvil.secrets.decrypt_with_key('USER_SETTING', usermap['notion_token'])
    
    today_str = (dt.datetime.now(pytz.timezone('US/Eastern'))).strftime('%Y-%m-%d')
    today_filter = {
        'and':
            [
                {
                    'property': usermap['prop_mapping']['done'],
                    'checkbox': {'equals': False}
                },
                {
                    'property': usermap['prop_mapping']['scheduled'],
                    'date': {'on_or_before': today_str}
                }
            ]
    }
    
    today_tasks = notionyk.read.get_all_data(
        notion_token,
        usermap['notion_db']['id'],
        usermap['prop_mapping'],
        usermap['defaults'],
        today_filter
    )

    for i in range(len(today_tasks)):
        today_tasks[i]['deadline_next'] = next_non_weekend_day(today_tasks[i]['deadline'], future=True)

    return today_tasks


def next_non_weekend_day(input_date_dict, future=True):
    """Finds the next date that is not a weekend."""
    import datetime as dt
    if future:
        current_date = dt.date.today()
    else:
        current_date = input_date_dict['datetime']

    day_of_week = current_date.weekday()
    
    if day_of_week == 4:  # Friday
        next_date = current_date + dt.timedelta(days=3)
    elif day_of_week == 5:  # Saturday
        next_date = current_date + dt.timedelta(days=2)
    else:
        next_date = current_date + dt.timedelta(days=1)

    # print(current_date, ' -- ', day_of_week)
    return {'string': next_date.strftime('%Y-%m-%d'), 'datetime': next_date}


@anvil.server.callable(require_user=True)
def give_me_task():
    """Give me a the next available task for today."""
    import datetime as dt
    import pytz
    user = anvil.users.get_user(allow_remembered=True)
    usermap = app_tables.usermap.get(user=user)
    notion_token = anvil.secrets.decrypt_with_key('USER_SETTING', usermap['notion_token'])
    
    today_str = (dt.datetime.now(pytz.timezone('US/Eastern'))).strftime('%Y-%m-%d')
    today_filter = {
        'and':
            [
                {
                    'property': usermap['prop_mapping']['done'],
                    'checkbox': {'equals': False}
                },
                {
                    'property': usermap['prop_mapping']['scheduled'],
                    'date': {'on_or_before': today_str}
                }
            ]
    }
    today_tasks = notionyk.read.get_response(
        usermap['notion_db']['id'],
        notion_token,
        queryfilter=today_filter
    )['results']
    today_task_url = today_tasks[0]['url']
    return today_task_url


@anvil.server.background_task
def rebalance1_single(usermap):
    usermap = proceed_or_abort(usermap, anvil.server.context.background_task_id, 'rebalance1_single')
    if not usermap:
        print_timestamp('Aborting: existing background task is running')
        return None
    
    notion_token = anvil.secrets.decrypt_with_key('USER_SETTING', usermap['notion_token'])
    
    rebalanced = notionyk.rebalance0(
        notion_token,
        usermap['notion_db']['id'],
        usermap['prop_mapping'],
        usermap['defaults'],
        usermap['max_daily_hours']
    )
    for task in rebalanced:
        notionyk.write.prop_date_value(
            notion_token,
            task['id'],
            usermap['prop_mapping']['scheduled'],
            task['scheduled']['string'],
            verbose=False
        )
        notionyk.write.prop_date_value(
            notion_token,
            task['id'],
            usermap['prop_mapping']['deadline'],
            task['deadline']['string'],
            verbose=False
        )


@anvil.server.background_task
def rebalance1_routine(usermaps=None):
    """Run this when we rebalance."""
    # TODO: use proceed_or_abort_scheduled when this is a scheduled task.
    if not usermaps:
        usermaps = app_tables.usermap.search(notion_token=q.not_(None), auto_refresh=True)

    for usermap in usermaps:
        rebalance1_single(usermap)


@anvil.server.callable(require_user=True)
def rebalance1_call():
    usermap = get_usermap()
    if validate_props(silent=True):
        return anvil.server.launch_background_task('rebalance1_single', usermap)
    else:
        return None


@anvil.server.http_endpoint('/reschedule-from-extension', cross_site_session=True, enable_cors=True)
def reschedule_from_extension():
    # headers = {
    #     "Access-Control-Allow-Origin": "chrome-extension://onfmfojkjnhaicfcaakdkcbjgcpilnde",
    #     "Access-Control-Allow-Methods": "GET",
    #     "Access-Control-Allow-Headers": "Content-Type"
    # }
    # return anvil.server.HttpResponse(200)
    user = anvil.users.get_user(allow_remembered=True)
    print(user)
    usermap = get_usermap()
    print_timestamp('reschedule_from_extension: got usermap')
    print(dict(usermap))
    if validate_props(silent=True):
        print_timestamp('User is validated and logged in.')
        anvil.server.launch_background_task('rebalance1_single', usermap)
        return anvil.server.HttpResponse(200)
    else:
        anvil.server.HttpResponse(400)


@anvil.server.callable(require_user=True)
def dt_bk_running(table_name, bk_name):
    return user_bk_running(table_name, bk_name)


@anvil.server.http_endpoint('/reschedule-running', cross_site_session=True, enable_cors=True)
def reschedule_running():
    # TODO: not used yet.
    is_running = user_bk_running('usermap', 'rebalance1_single')
    headers = {
        'Content-Type': 'application/json'
    }
    return anvil.server.HttpResponse({'is_running': is_running}, headers=headers, status=200)


@anvil.server.callable(require_user=True)
def remove_task_deadline(task):
    """Remove a task deadline."""
    user = anvil.users.get_user(allow_remembered=True)
    usermap = app_tables.usermap.get(user=user)
    notion_token = anvil.secrets.decrypt_with_key('USER_SETTING', usermap['notion_token'])

    notionyk.write.prop_date_value(notion_token, task['id'], usermap['prop_mapping']['deadline'], '')
    notionyk.write.prop_bool_value(notion_token, task['id'], usermap['prop_mapping']['hard_deadline'], False)
    notionyk.write.prop_date_value(notion_token, task['id'], usermap['prop_mapping']['scheduled'], '')


@anvil.server.callable(require_user=True)
def remove_hard_deadline(task):
    """Remove a task deadline."""
    user = anvil.users.get_user(allow_remembered=True)
    usermap = app_tables.usermap.get(user=user)
    notion_token = anvil.secrets.decrypt_with_key('USER_SETTING', usermap['notion_token'])

    notionyk.write.prop_bool_value(notion_token, task['id'], usermap['prop_mapping']['hard_deadline'], False)
    notionyk.write.prop_date_value(notion_token, task['id'], usermap['prop_mapping']['scheduled'], '')


@anvil.server.callable(require_user=True)
def delay_deadline(task):
    """Delay a task deadline to the next weekday."""
    user = anvil.users.get_user(allow_remembered=True)
    usermap = app_tables.usermap.get(user=user)
    notion_token = anvil.secrets.decrypt_with_key('USER_SETTING', usermap['notion_token'])
    # print(task['deadline_next'])
    notionyk.write.prop_date_value(notion_token, task['id'], usermap['prop_mapping']['deadline'], task['deadline_next']['string'], verbose=False)
    notionyk.write.prop_date_value(notion_token, task['id'], usermap['prop_mapping']['scheduled'], '', verbose=False)


@anvil.server.callable(require_user=True)
def get_usermap():
    user = anvil.users.get_user(allow_remembered=True)
    if not user:
        raise ValueError('User is not logged in.')
    if not app_tables.usermap.get(user=user):
        usermap = app_tables.usermap.add_row(user=user)
    else:
        usermap = app_tables.usermap.get(user=user)
    usermap['prop_mapping'] = usermap['prop_mapping'] or notionyk.props_dict
    usermap['max_daily_hours'] = usermap['max_daily_hours'] or 6
    usermap['defaults'] = usermap['defaults'] or {'hours': 4}
    return usermap


@anvil.server.callable(require_user=True)
def get_props_list():
    usermap = get_usermap()
    props_list = notionyk.props_list
    for prop in props_list:
        if usermap['prop_mapping'] and prop['id'] in usermap['prop_mapping']:
            prop['alias'] = usermap['prop_mapping'][prop['id']]
    return props_list


def validate_props(silent=False):
    """Validate all Notion properties in the usermap."""
    props_list = get_props_list()
    for prop in props_list:
        if silent:
            try:
                validate_prop(prop['type'], prop['alias'])
            except Exception as e:
                if 'NotionError' in str(e):
                    return False
                else:
                    raise
        else:
            _ = validate_prop(prop['type'], prop['alias'])
    return True


@anvil.server.callable(require_user=True)
def validate_prop(prop_type, prop_alias, prop_id=None):
    if not prop_alias or prop_alias == '':
        raise Exception('NotionError: Please enter your Notion property name.')
    usermap = get_usermap()
    notion_token = anvil.secrets.decrypt_with_key('USER_SETTING', usermap['notion_token'])
    db_props = notionyk.read.get_database(usermap['notion_db']['id'], notion_token)

    if prop_alias not in db_props['properties'].keys():
        raise Exception(f"NotionError: This property name ({prop_alias}) doesn't exist in your Notion database.")
    elif db_props['properties'][prop_alias]['type'] != prop_type:
        raise Exception(f"NotionError: This property is not of type ({prop_type}) in your Notion database.")

    if prop_id:
        prop_dict = usermap['prop_mapping'].copy()
        prop_dict[prop_id] = prop_alias
        usermap['prop_mapping'] = prop_dict
    return usermap


@anvil.server.callable(require_user=True)
def get_databases_for_dd():
    usermap = get_usermap()
    notion_token = anvil.secrets.decrypt_with_key('USER_SETTING', usermap['notion_token'])
    dbs = notionyk.read.search_databases(notion_token)
    data_list = []
    for result in dbs['results']:
        data_dict = {}
        data_dict['id'] = result['id']
        data_dict['title'] = ''.join([j['plain_text'] for j in result['title']])
        data_list.append(data_dict)
    return data_list


@anvil.server.callable(require_user=True)
def save_database(db_dict):
    usermap = get_usermap()
    usermap['notion_db'] = db_dict
    return usermap