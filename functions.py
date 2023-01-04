import requests
import config
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

base_url = 'https://api.notion.com/v1/'

headers = {
    'Authorization': 'Bearer ' + config.auth_token,
    'Accept': 'application/json',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json'
}


def query_tasks(json):
    return requests.post(base_url + 'databases/' + config.database_id + '/query', json=json, headers=headers)


def update_task(id, json):
    return requests.patch(base_url + 'pages/' + id, json=json, headers=headers)


def get_recurring_finished_tasks():
    with open('jsons/done_and_recur_filter.json', 'r') as f:
        payload = json.load(f)
    return json.loads(query_tasks(payload).text)['results']


def get_recur_unit(entry):
    return entry['properties']['Recur Unit']['select']['name']


def get_recur_days(entry):
    return [day['name'] for day in entry['properties']['Recur Days']['multi_select']]


def get_recur_interval(entry):
    return entry['properties']['Recur Interval']['number']


def get_due_date(entry):
    try:
        date_string = entry['properties']['Due Date']['date']['start']
    except TypeError:
        return None

    try:
        date = datetime.strptime(date_string, '%Y-%m-%d')
    except ValueError:
        date_string = date_string[:10] + ' ' + date_string[11:19]
        date = datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
    return date


def parse_day_name(day_name):
    if day_name == 'M':
        return 0
    elif day_name == 'T':
        return 1
    elif day_name == 'W':
        return 2
    elif day_name == 'Th':
        return 3
    elif day_name == 'F':
        return 4
    elif day_name == 'Sat':
        return 5
    elif day_name == 'Sun':
        return 6
    else:
        raise ValueError


def days_to_next_day(curr, day):
    curr_day = curr.weekday()
    diff = day - curr_day
    if diff <= 0:
        diff += 7
    return diff


def calculate_next_due_date(entry):
    recur_unit = get_recur_unit(entry)
    date = get_due_date(entry)
    if recur_unit == 'Day' and get_recur_days(entry) != []:
        next_days = [parse_day_name(day) for day in get_recur_days(entry)]
        days_ahead = min([days_to_next_day(date, day) for day in next_days])
        return date + relativedelta(days=days_ahead)
    elif recur_unit == 'Last Day of Month':
        next_month = date.replace(day=1, month=(date.month % 12) + 1)
        ldom = next_month.replace(day=28) + timedelta(days=4)
        return ldom - timedelta(days=ldom.day)
    else:
        interval = get_recur_interval(entry)
        if recur_unit == 'Day':
            return date + relativedelta(days=interval)
        elif recur_unit == 'Week':
            return date + relativedelta(weeks=interval)
        elif recur_unit == 'Month':
            return date + relativedelta(months=interval)
        else:
            return ValueError


def generate_update_json(new_due_date):
    with open('jsons/update_template.json', 'r') as f:
        obj = json.load(f)
    obj["properties"]["Due Date"]["date"]["start"] = datetime.strftime(new_due_date, '%Y-%m-%dT%H:%M:%S')
    obj["properties"]["Due Date"]["date"]["time_zone"] = config.timezone
    return obj


def check_tasks(s):
    res = get_recurring_finished_tasks()
    for entry in res:
        update_task(entry['id'], generate_update_json(calculate_next_due_date(entry)))
    print("tasks checked!")
    s.enter(60, 1, check_tasks, (s,))

