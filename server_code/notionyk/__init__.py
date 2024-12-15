from . import write  # noqa
from . import read

props_list = [
    {
        "id": "name",
        "type": "title",
        "name": "Title",
        "alias": None,
        "tooltip": 'Title of the task. Usually just "Name"',
    },
    {
        "id": "done",
        "type": "checkbox",
        "name": "Done (Yes/No)",
        "alias": None,
        "tooltip": "A checkbox that indicates whether the task is completed.",
    },
    {
        "id": "hours",
        "type": "number",
        "name": "Estimated Workload (Hours)",
        "alias": None,
        "tooltip": "The number of hours of workload estimated for a task.",
    },
    {
        "id": "deadline",
        "type": "date",
        "name": "Deadline (date)",
        "alias": None,
        "tooltip": "A date property that indicates the deadline.",
    },
    {
        "id": "hard_deadline",
        "type": "checkbox",
        "name": "Hard Deadline (Yes/No)",
        "alias": None,
        "tooltip": "A checkbox property that indicates whether it is a 'hard' deadline.",
    },
    {
        "id": "last_edit",
        "type": "last_edited_time",
        "name": "Last Edited Time",
        "alias": None,
        "tooltip": "A date property that indicates when the task was last edited.",
    },
    {
        "id": "scheduled",
        "type": "date",
        "name": "Scheduled (date)",
        "alias": None,
        "tooltip": "A date property that indicates when the task is scheduled.",
    },
]
props_dict = {d["id"]: None for d in props_list}


def rebalance1(notion_token, database_id, property_mappings, defaults, max_hrs=6):
    """Rebalance tasks based on deadlines and workload."""
    import datetime as dt

    import pytz

    today = dt.datetime.now(pytz.timezone("US/Eastern"))
    today2 = dt.datetime(today.year, today.month, today.day)
    today2_str = dt.datetime.strftime(today2, "%Y-%m-%d")

    # All not-done tasks.
    # TODO: Add more precise filters to speed it up.
    # You want: scheduled in next 7 days + not done, or deadline in next 7 days + not done,
    # What if there are not enough tasks to fill up the week in those criteria?
    # This whole thing has to be iterative then. API call, rebalance, another API call.
    # Use the built in pagination.
    taskfilter = {"property": property_mappings["done"], "checkbox": {"equals": False}}

    # Get hard deadline tasks first.
    # Null values go to the end in sorting rules.
    sorts = [
        {"property": property_mappings["hard_deadline"], "direction": "descending"},
        {"property": property_mappings["deadline"], "direction": "ascending"},
    ]
    input_data = read.get_all_data(
        notion_token,
        database_id,
        property_mappings,
        defaults,
        queryfilter=taskfilter,
        sorts=sorts,
    )

    # Initialize current workload by day.
    days_df = get_days_df(max_hrs=max_hrs)

    rescheduled = input_data.copy()

    for task, task_old in zip(rescheduled, input_data):
        first_before_deadline = get_first_day_available(task, days_df)
        lightest_before_deadline = get_lightest_day_available(task, days_df)
        first_after_deadline = get_first_day_after(task, days_df)

        if first_before_deadline:  # Fit this task into your schedule!
            task["scheduled"] = first_before_deadline
        elif (
            task["hard_deadline"] and lightest_before_deadline
        ):  # Squeeze in hard deadline
            task["scheduled"] = lightest_before_deadline
        elif (
            task["hard_deadline"]
            and task["deadline"]["datetime"] > days_df["day"].max()
        ):
            # Hard deadline is past planning window, which doesn't have enough avail anyway
            task["scheduled"] = {"datetime": None, "string": ""}
        elif task["hard_deadline"]:  # Overdue hard deadline
            task["scheduled"] = {"datetime": today2, "string": today2_str}
        elif first_after_deadline:  # Soft deadline push inside window
            task["scheduled"] = first_after_deadline
            task["deadline"] = first_after_deadline
        elif task["deadline"]["string"] != "":  # Soft deadline push outside window
            task["scheduled"] = {"datetime": None, "string": ""}
            task["deadline"] = {
                "datetime": days_df.iloc[-1, 0],
                "string": days_df.index[-1],
            }
        else:  # No deadline and no avail.
            task["scheduled"] = {"datetime": None, "string": ""}

        # Add this task's workload to the right day.
        right_day = days_df["day"] == task["scheduled"]["datetime"]
        days_df.loc[right_day, "curr_load"] += task["hours"]
        days_df.loc[right_day, "curr_avail"] -= task["hours"]

        if (
            task["scheduled"] != task_old["scheduled"]
            or task["deadline"] != task_old["deadline"]
        ):
            task["changed"] = True
        else:
            task["changed"] = False
    return [i for i in rescheduled if i["changed"]]


def get_first_day_available(task, availability):
    """
    Get the first day with enough availability before the task deadline.

    Return a dict with two keys: 'datetime' and 'string'.
    If there is no day with enough availability, return None.
    """
    first_day = availability[
        (availability["day"] < task["deadline"]["datetime"])
        & (availability["curr_avail"] >= task["hours"])
    ].sort_values(by="day", ascending=True)
    if len(first_day) > 0:
        return {"datetime": first_day.iloc[0, 0], "string": first_day.index[0]}
    else:
        return None


def get_lightest_day_available(task, availability):
    """
    Find a day before the deadline that has the least workload.

    Return a dict with two keys: 'datetime' and 'string'.
    If there's no day before the deadline (overdue), return None.
    """
    lightest_day = availability[
        availability["day"] < task["deadline"]["datetime"]
    ].sort_values(by=["curr_load", "day"])
    if len(lightest_day) > 0:
        return {"datetime": lightest_day.iloc[0, 0], "string": lightest_day.index[0]}
    return None


def get_first_day_after(task, availability):
    """
    Get the first day in the time window with enough availability.

    Return a dict with two keys: 'datetime' and 'string'.
    If there's no day available in the time window, return None.
    """
    first_day = availability[availability["curr_avail"] >= task["hours"]].sort_values(
        by=["day"]
    )
    if len(first_day) > 0:
        return {"datetime": first_day.iloc[0, 0], "string": first_day.index[0]}
    else:
        return None


def get_days_df(curr_load={"hours": 0}, days_ahead=7, max_hrs=6):
    """Get a sequential days dataframe."""
    import datetime as dt

    import pandas as pd
    import pytz

    today = dt.datetime.now(pytz.timezone("US/Eastern"))
    today2 = dt.datetime(today.year, today.month, today.day)

    # Create a days df between today and the next x days
    days_list = [today2 + dt.timedelta(days=i) for i in range(days_ahead)]
    days_df = pd.DataFrame(columns=["day"], data=days_list)
    days_df["day_str"] = days_df["day"].dt.strftime("%Y-%m-%d")
    days_df.set_index("day_str", inplace=True)
    # Join them
    days_df["curr_load"] = curr_load["hours"]
    days_df["curr_load"].fillna(0.0, inplace=True)
    # Filter out the weekends, don't want to allocate tasks then.
    days_df["weekday"] = days_df["day"].dt.weekday
    days_df = days_df[days_df["weekday"] <= 4]
    # calculate available time
    days_df["curr_avail"] = max_hrs - days_df["curr_load"]
    return days_df


def rebalance0(notion_token, database_id, property_mappings, defaults, max_hrs=6):
    """
    Rebalance today's tasks with soft deadlines.
    """
    import datetime as dt

    import numpy as np
    import pandas as pd
    import pytz

    today = dt.datetime.now(pytz.timezone("US/Eastern"))
    today2 = dt.datetime(today.year, today.month, today.day)
    today2_str = dt.datetime.strftime(today2, "%Y-%m-%d")

    taskfilter = {"property": property_mappings["done"], "checkbox": {"equals": False}}

    input_data0 = read.get_all_data(
        notion_token, database_id, property_mappings, defaults, queryfilter=taskfilter
    )
    print(input_data0[:2])
    input_data = pd.DataFrame(input_data0)
    input_data["deadline_str"] = None
    input_data["last_edit_str"] = None
    input_data["scheduled_str"] = None
    for i in range(len(input_data0)):
        input_data.loc[i, "deadline"] = input_data0[i]["deadline"]["datetime"]
        input_data.loc[i, "deadline_str"] = input_data0[i]["deadline"]["string"]
        input_data.loc[i, "last_edit"] = input_data0[i]["last_edit"]["datetime"]
        input_data.loc[i, "last_edit_str"] = input_data0[i]["last_edit"]["string"]
        input_data.loc[i, "scheduled"] = input_data0[i]["scheduled"]["datetime"]
        input_data.loc[i, "scheduled_str"] = input_data0[i]["scheduled"]["string"]

    # TODO: not elegant, refactor
    curr_load = {"hours": 0}
    days_dfi = get_days_df(curr_load)

    # Prep for the loop
    # Sorting algorithm is here. Sorting by schedule creates inconsistent
    # results. Sort by evergreen values.
    input_data["scheduled"].fillna(np.datetime64("2099-12-31"), inplace=True)
    input_data["deadline"].fillna(np.datetime64("2099-12-31"), inplace=True)
    # This'll prioritize ANY deadline (even a year from now) over none.
    # Also sort by hard deadline first, in case deadlines are same.
    input_data.sort_values(
        by=["hard_deadline", "deadline"], ascending=[False, True], inplace=True
    )

    rescheduled = input_data.copy()
    # Schedule all behind-schedule tasks for today.
    rescheduled["scheduled"] = rescheduled["scheduled"].clip(lower=today2)
    rescheduled.loc[rescheduled["scheduled"] == today2, "scheduled_str"] = today2_str
    days_df = days_dfi.copy()

    for ind, row in rescheduled.iterrows():
        # print(row['title'])
        if (
            all(days_df["curr_avail"] < row["hours"])
            and row["deadline"] > days_df["day"].max()
        ):
            # Break loop if no available time AND
            # deadline is past our planning window
            rescheduled.loc[ind, "scheduled_str"] = ""
            rescheduled.loc[ind, "scheduled"] = np.datetime64("nat")
        else:
            # First, find a day before deadline with avail
            day_assignment_1 = days_df[
                (days_df["day"] < row["deadline"])
                & (days_df["curr_avail"] >= row["hours"])
            ].sort_values(by="day", ascending=False)
            # Second, find the lightest day before deadline
            day_assignment_2 = days_df[days_df["day"] < row["deadline"]].sort_values(
                by=["curr_load", "day"]
            )
            # Third, find the first available day after deadline
            day_assignment_3 = days_df[
                days_df["curr_avail"] >= row["hours"]
            ].sort_values(by=["day"])
            # Find the first decently available day
            if len(day_assignment_1) > 0:
                dayass = day_assignment_1.copy()
                # print('--There is time')
            elif (
                len(day_assignment_3) > 0 and not rescheduled.loc[ind, "hard_deadline"]
            ):
                # Not enough avail before soft deadline, so push deadline back
                dayass = day_assignment_3.copy()
                rescheduled.loc[ind, "deadline"] = dayass.iloc[0, 0]
                rescheduled.loc[ind, "deadline_str"] = dayass.index[0]
                # print('--There is no time but no worries')
            elif not rescheduled.loc[ind, "hard_deadline"]:
                # Planning period is full, push back soft deadline to last day
                dayass = days_df.sort_values(by="day", ascending=False).copy()
                rescheduled.loc[ind, "deadline"] = dayass.iloc[0, 0]
                rescheduled.loc[ind, "deadline_str"] = dayass.index[0]
                rescheduled.loc[ind, "scheduled_str"] = ""
                rescheduled.loc[ind, "scheduled"] = np.datetime64("nat")
                # print('--There is no time so push to end')
            elif len(day_assignment_2) > 0:
                # Hard deadline so add it to the least busy day before that
                dayass = day_assignment_2.copy()
                # print('--There is no time and hard')
            else:  # Overdue hard deadline
                dayass = days_df.copy()
                # print('--There is no time and overdue')

            rescheduled.loc[ind, "scheduled_str"] = dayass.index[0]
            rescheduled.loc[ind, "scheduled"] = dayass.iloc[0, 0]

            days_df.loc[dayass.index[0], "curr_load"] += row["hours"]
            days_df.loc[dayass.index[0], "curr_avail"] = (
                max_hrs - days_df.loc[dayass.index[0], "curr_load"]
            )
    # Only return the values where the data was changed.
    rescheduled = rescheduled[
        (input_data["scheduled_str"] != rescheduled["scheduled_str"])
        | (input_data["deadline_str"] != rescheduled["deadline_str"])
    ]

    print(rescheduled[["name", "deadline_str", "scheduled_str"]])
    print(len(rescheduled))
    # Convert to dict and return
    rescheduled_dict = rescheduled.to_dict("records")
    for i in range(len(rescheduled_dict)):
        rescheduled_dict[i]["deadline"] = {
            "string": rescheduled_dict[i]["deadline_str"],
            "datetime": rescheduled_dict[i]["deadline"],
        }
        rescheduled_dict[i]["scheduled"] = {
            "string": rescheduled_dict[i]["scheduled_str"],
            "datetime": rescheduled_dict[i]["scheduled"],
        }
    return rescheduled_dict
