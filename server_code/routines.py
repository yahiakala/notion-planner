"""Main server module for callables."""

import anvil.secrets
import anvil.server
import anvil.tables.query as q
import anvil.users
import anvil_squared.multi_tenant as mt
from anvil.tables import app_tables
from anvil_squared.background_tasks import proceed_or_abort, user_bk_running
from anvil_squared.helpers import print_timestamp

from . import notionyk


@anvil.server.callable(require_user=True)
def get_max_hrs(tenant_id):
    """Return the max hours defined by the user."""
    user = anvil.users.get_user(allow_remembered=True)
    tenant, usertenant, permissions = mt.authorization.validate_user(tenant_id, user)
    return usertenant["max_daily_hours"] or 6


@anvil.server.callable(require_user=True)
def get_today_tasks(tenant_id):
    """Give me all my tasks for today."""
    import datetime as dt

    import pytz

    user = anvil.users.get_user(allow_remembered=True)
    tenant, usertenant, permissions = mt.authorization.validate_user(tenant_id, user)
    if (
        not usertenant["notion_token"]
        or not usertenant["prop_mapping"]
        or not ["notion_db"]
        or not validate_props(silent=True)
    ):
        return []

    notion_token = anvil.secrets.decrypt_with_key(
        "USER_SETTING", usertenant["notion_token"]
    )

    today_str = (dt.datetime.now(pytz.timezone("US/Eastern"))).strftime("%Y-%m-%d")
    today_filter = {
        "and": [
            {
                "property": usertenant["prop_mapping"]["done"],
                "checkbox": {"equals": False},
            },
            {
                "property": usertenant["prop_mapping"]["scheduled"],
                "date": {"on_or_before": today_str},
            },
        ]
    }

    today_tasks = notionyk.read.get_all_data(
        notion_token,
        usertenant["notion_db"]["id"],
        usertenant["prop_mapping"],
        usertenant["defaults"],
        today_filter,
    )

    for i in range(len(today_tasks)):
        today_tasks[i]["deadline_next"] = next_non_weekend_day(
            today_tasks[i]["deadline"], future=True
        )

    return today_tasks


def next_non_weekend_day(input_date_dict, future=True):
    """Finds the next date that is not a weekend."""
    import datetime as dt

    if future:
        current_date = dt.date.today()
    else:
        current_date = input_date_dict["datetime"]

    day_of_week = current_date.weekday()

    if day_of_week == 4:  # Friday
        next_date = current_date + dt.timedelta(days=3)
    elif day_of_week == 5:  # Saturday
        next_date = current_date + dt.timedelta(days=2)
    else:
        next_date = current_date + dt.timedelta(days=1)

    # print(current_date, ' -- ', day_of_week)
    return {"string": next_date.strftime("%Y-%m-%d"), "datetime": next_date}


@anvil.server.callable(require_user=True)
def give_me_task(tenant_id):
    """Give me a the next available task for today."""
    import datetime as dt

    import pytz

    user = anvil.users.get_user(allow_remembered=True)
    tenant, usertenant, permissions = mt.authorization.validate_user(tenant_id, user)
    notion_token = anvil.secrets.decrypt_with_key(
        "USER_SETTING", usertenant["notion_token"]
    )

    today_str = (dt.datetime.now(pytz.timezone("US/Eastern"))).strftime("%Y-%m-%d")
    today_filter = {
        "and": [
            {
                "property": usertenant["prop_mapping"]["done"],
                "checkbox": {"equals": False},
            },
            {
                "property": usertenant["prop_mapping"]["scheduled"],
                "date": {"on_or_before": today_str},
            },
        ]
    }
    today_tasks = notionyk.read.get_response(
        usertenant["notion_db"]["id"], notion_token, queryfilter=today_filter
    )["results"]
    today_task_url = today_tasks[0]["url"]
    return today_task_url


@anvil.server.background_task
def rebalance1_single(usertenant):
    usertenant = proceed_or_abort(
        usertenant, anvil.server.context.background_task_id, "rebalance1_single"
    )
    if not usertenant:
        print_timestamp("Aborting: existing background task is running")
        return None

    notion_token = anvil.secrets.decrypt_with_key(
        "USER_SETTING", usertenant["notion_token"]
    )

    rebalanced = notionyk.rebalance0(
        notion_token,
        usertenant["notion_db"]["id"],
        usertenant["prop_mapping"],
        usertenant["defaults"],
        usertenant["max_daily_hours"],
    )
    for task in rebalanced:
        notionyk.write.prop_date_value(
            notion_token,
            task["id"],
            usertenant["prop_mapping"]["scheduled"],
            task["scheduled"]["string"],
            verbose=False,
        )
        notionyk.write.prop_date_value(
            notion_token,
            task["id"],
            usertenant["prop_mapping"]["deadline"],
            task["deadline"]["string"],
            verbose=False,
        )


@anvil.server.background_task
def rebalance1_routine(usertenants=None):
    """Run this when we rebalance."""
    # TODO: use proceed_or_abort_scheduled when this is a scheduled task.
    if not usertenants:
        usertenants = app_tables.usertenant.search(
            notion_token=q.not_(None), auto_refresh=True
        )

    for usertenant in usertenants:
        rebalance1_single(usertenant)


@anvil.server.callable(require_user=True)
def rebalance1_call(tenant_id):
    user = anvil.users.get_user(allow_remembered=True)
    tenant, usertenant, permissions = mt.authorization.validate_user(tenant_id, user)
    if validate_props(silent=True):
        return anvil.server.launch_background_task("rebalance1_single", usertenant)
    else:
        return None


@anvil.server.http_endpoint(
    "/reschedule-from-extension", cross_site_session=True, enable_cors=True
)
def reschedule_from_extension(tenant_id):
    # TODO: figure out a way to pass the tenant_id
    # headers = {
    #     "Access-Control-Allow-Origin": "chrome-extension://onfmfojkjnhaicfcaakdkcbjgcpilnde",
    #     "Access-Control-Allow-Methods": "GET",
    #     "Access-Control-Allow-Headers": "Content-Type"
    # }
    # return anvil.server.HttpResponse(200)
    user = anvil.users.get_user(allow_remembered=True)
    tenant, usertenant, permissions = mt.authorization.validate_user(tenant_id, user)
    print_timestamp("reschedule_from_extension: got usertenant")
    if validate_props(silent=True):
        print_timestamp("User is validated and logged in.")
        anvil.server.launch_background_task("rebalance1_single", usertenant)
        return anvil.server.HttpResponse(200)
    else:
        anvil.server.HttpResponse(400)


@anvil.server.callable(require_user=True)
def dt_bk_running(tenant_id, table_name, bk_name):
    user = anvil.users.get_user(allow_remembered=True)
    tenant, usertenant, permissions = mt.authorization.validate_user(tenant_id, user)
    return user_bk_running(table_name, bk_name)


@anvil.server.http_endpoint(
    "/reschedule-running", cross_site_session=True, enable_cors=True
)
def reschedule_running():
    # TODO: not used yet.
    # TODO: authorize
    is_running = user_bk_running("usertenant", "rebalance1_single")
    headers = {"Content-Type": "application/json"}
    return anvil.server.HttpResponse(
        {"is_running": is_running}, headers=headers, status=200
    )


@anvil.server.callable(require_user=True)
def remove_task_deadline(tenant_id, task):
    """Remove a task deadline."""
    user = anvil.users.get_user(allow_remembered=True)
    tenant, usertenant, permissions = mt.authorization.validate_user(tenant_id, user)
    notion_token = anvil.secrets.decrypt_with_key(
        "USER_SETTING", usertenant["notion_token"]
    )

    notionyk.write.prop_date_value(
        notion_token, task["id"], usertenant["prop_mapping"]["deadline"], ""
    )
    notionyk.write.prop_bool_value(
        notion_token, task["id"], usertenant["prop_mapping"]["hard_deadline"], False
    )
    notionyk.write.prop_date_value(
        notion_token, task["id"], usertenant["prop_mapping"]["scheduled"], ""
    )


@anvil.server.callable(require_user=True)
def remove_hard_deadline(tenant_id, task):
    """Remove a task deadline."""
    user = anvil.users.get_user(allow_remembered=True)
    tenant, usertenant, permissions = mt.authorization.validate_user(tenant_id, user)
    notion_token = anvil.secrets.decrypt_with_key(
        "USER_SETTING", usertenant["notion_token"]
    )

    notionyk.write.prop_bool_value(
        notion_token, task["id"], usertenant["prop_mapping"]["hard_deadline"], False
    )
    notionyk.write.prop_date_value(
        notion_token, task["id"], usertenant["prop_mapping"]["scheduled"], ""
    )


@anvil.server.callable(require_user=True)
def delay_deadline(tenant_id, task):
    """Delay a task deadline to the next weekday."""
    user = anvil.users.get_user(allow_remembered=True)
    tenant, usertenant, permissions = mt.authorization.validate_user(tenant_id, user)
    notion_token = anvil.secrets.decrypt_with_key(
        "USER_SETTING", usertenant["notion_token"]
    )
    # print(task['deadline_next'])
    notionyk.write.prop_date_value(
        notion_token,
        task["id"],
        usertenant["prop_mapping"]["deadline"],
        task["deadline_next"]["string"],
        verbose=False,
    )
    notionyk.write.prop_date_value(
        notion_token,
        task["id"],
        usertenant["prop_mapping"]["scheduled"],
        "",
        verbose=False,
    )


@anvil.server.callable(require_user=True)
def get_props_list(tenant_id):
    user = anvil.users.get_user(allow_remembered=True)
    tenant, usertenant, permissions = mt.authorization.validate_user(tenant_id, user)
    props_list = notionyk.props_list
    for prop in props_list:
        if usertenant["prop_mapping"] and prop["id"] in usertenant["prop_mapping"]:
            prop["alias"] = usertenant["prop_mapping"][prop["id"]]
    return props_list


def validate_props(silent=False):
    """Validate all Notion properties in the usertenant."""
    props_list = get_props_list()
    for prop in props_list:
        if silent:
            try:
                validate_prop(prop["type"], prop["alias"])
            except Exception as e:
                if "NotionError" in str(e):
                    return False
                else:
                    raise
        else:
            _ = validate_prop(prop["type"], prop["alias"])
    return True


@anvil.server.callable(require_user=True)
def validate_prop(tenant_id, prop_type, prop_alias, prop_id=None):
    if not prop_alias or prop_alias == "":
        raise Exception("NotionError: Please enter your Notion property name.")
    user = anvil.users.get_user(allow_remembered=True)
    tenant, usertenant, permissions = mt.authorization.validate_user(tenant_id, user)
    notion_token = anvil.secrets.decrypt_with_key(
        "USER_SETTING", usertenant["notion_token"]
    )
    db_props = notionyk.read.get_database(usertenant["notion_db"]["id"], notion_token)

    if prop_alias not in db_props["properties"].keys():
        raise Exception(
            f"NotionError: This property name ({prop_alias}) doesn't exist in your Notion database."
        )
    elif db_props["properties"][prop_alias]["type"] != prop_type:
        raise Exception(
            f"NotionError: This property is not of type ({prop_type}) in your Notion database."
        )

    if prop_id:
        prop_dict = usertenant["prop_mapping"].copy()
        prop_dict[prop_id] = prop_alias
        usertenant["prop_mapping"] = prop_dict
    return usertenant


@anvil.server.callable(require_user=True)
def get_databases_for_dd(tenant_id):
    user = anvil.users.get_user(allow_remembered=True)
    tenant, usertenant, permissions = mt.authorization.validate_user(tenant_id, user)
    notion_token = anvil.secrets.decrypt_with_key(
        "USER_SETTING", usertenant["notion_token"]
    )
    dbs = notionyk.read.search_databases(notion_token)
    data_list = []
    for result in dbs["results"]:
        data_dict = {}
        data_dict["id"] = result["id"]
        data_dict["title"] = "".join([j["plain_text"] for j in result["title"]])
        data_list.append(data_dict)
    return data_list


@anvil.server.callable(require_user=True)
def save_database(tenant_id, db_dict):
    user = anvil.users.get_user(allow_remembered=True)
    tenant, usertenant, permissions = mt.authorization.validate_user(tenant_id, user)
    usertenant["notion_db"] = db_dict
    return usertenant
