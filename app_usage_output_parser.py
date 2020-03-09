import csv
from datetime import date, time, datetime, timedelta
from dateutil import tz
from collections import defaultdict
from functools import reduce

import calendar_api
import utils


def create_events(csv_lines):
    reader = csv.DictReader(csv_lines)
    # Convert times to datetime and get rid of non-data lines.  Also skip
    # repeated lines.
    existing = set()
    app_usages = []
    last_time = None
    for row in reader:
        # Ignore lines with no data, lines indicating the end of a session, or
        # repeated lines.
        hashable_row = tuple(sorted(row.items()))
        if None in row.values() or hashable_row in existing:
            continue
        existing.add(hashable_row)
        app_usages.append({})
        app_usages[-1]['start_time'] = datetime.strptime(
            f"{row['Date']} {row['Time']}", '%m/%d/%y %I:%M:%S %p')
        # Make sure that all times are unique, so in sorting nothing gets
        # rearranged.  This PROBABLY keeps the initial order, but might still
        # be a bit buggy.
        if app_usages[-1]['start_time'] == last_time:
            app_usages[-1]['start_time'] -= timedelta(seconds=1)
        app_usages[-1]['duration'] = (
            datetime.strptime(row['Duration'], '%H:%M:%S')
            - datetime.strptime('00:00:00', '%H:%M:%S'))
        app_usages[-1]['app_name'] = row['App name']
        last_time = app_usages[-1]['start_time']
    app_usages.sort(key=lambda usage: usage['start_time'])

    # Create a calendar event for every period between unlocking and locking
    # the phone.
    events = []
    cur_event = None
    for usage in app_usages:
        print(usage)
        if cur_event is None:
            cur_event = calendar_api.Event(
                start=dict(dateTime=usage['start_time'].replace(
                    tzinfo=tz.gettz('PST')).isoformat(),
                           timeZone='America/Los_Angeles'),
                # Dict mapping app name to total time it was used.
                summed_usages=defaultdict(lambda: timedelta(seconds=0)),
            )
        elif (cur_event is not None
              and usage['app_name'] == 'Screen off (locked)'):
            print(cur_event)
            if cur_event['summed_usages']:
                sorted_summed_usages = list(reversed(sorted(
                    cur_event['summed_usages'].items(), key=lambda i: i[1])))
                if not sorted_summed_usages:
                    sorted_summed_usages = [('No app', timedelta(seconds=1))]
            else:
                sorted_summed_usages = [('No app', timedelta(seconds=1))]
            cur_event['summary'] = sorted_summed_usages[0][0]
            cur_event['description'] = reduce(
                str.__add__,
                [f'{u[0]} -- {round(u[1].total_seconds() / 60, 2)} mins\n'
                 for u in sorted_summed_usages])
            cur_event['end'] = dict(
                dateTime=usage['start_time'].replace(
                    tzinfo=tz.gettz('PST')).isoformat(),
                timeZone='America/Los_Angeles')
            events.append(cur_event)
            cur_event = None
        else:
            cur_event['summed_usages'][usage['app_name']] += usage['duration']
    return events
