from anvil_squared.globals import GlobalCache

_global_dict = {
    "user": None,
    "is_mobile": None,
    "customer_portal": None,
    "tenant": None,
    "tenant_id": None,
}

_tenanted_dict = {
    'last_week': None,
    'last_week_plot': None,
    'max_hrs': None,
    'today_tasks': None,
    'usermap': None,
    'props_list': None
}

Global = GlobalCache(_global_dict, _tenanted_dict)

AppName = "Notion Planner"