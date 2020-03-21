import copy
import csv
from datetime import date, time, datetime, timedelta
from dateutil import tz
from collections import defaultdict
from dataclasses import dataclass, field
from functools import reduce
from typing import Dict

import calendar_api
import utils


@dataclass
class PhoneSession:
    """Phone usage session"""
    start_time: datetime = None
    end_time: datetime = None
    # Map from app name to the total time it was used in this session.
    summed_usages: Dict[str, timedelta] = field(
        default_factory=lambda: defaultdict(lambda: timedelta(seconds=0)))
    # Number of times the phone was checked (used before locking) during this
    # period.
    checks: int = 1

    def to_calendar_event(self):
        unused_time = (
            (self.end_time - self.start_time)
            - reduce(lambda t1, t2: t1 + t2, self.summed_usages.values(),
                     timedelta(seconds=0)))
        usage_sums = list(self.summed_usages.items())
        if unused_time > timedelta(seconds=2):
            usage_sums.append(('Unused', unused_time))
        sorted_usage_sums = list(reversed(sorted(usage_sums,
                                                 key=lambda item: item[1])))
        # TODO look into using selfspy api functionality for this to pick
        # significant events to show.
        top_event_name = ''
        if sorted_usage_sums:
            top_event_name = sorted_usage_sums[0][0]
            if top_event_name == 'Unused' and len(sorted_usage_sums) > 1:
                top_event_name = sorted_usage_sums[1][0]
        return calendar_api.Event(
            start=dict(dateTime=self.start_time.isoformat(),
                       timeZone='America/Los_Angeles'),
            end=dict(dateTime=self.end_time.isoformat(),
                     timeZone='America/Los_Angeles'),
            summary=f'{self.checks} checks, {top_event_name} primarily',
            description=reduce(
                str.__add__,
                [f'{u[0]} -- {round(u[1].total_seconds() / 60, 2)} mins\n'
                 for u in sorted_usage_sums],
                ''),
        )


def get_app_usages_from_usage_history_app_export_lines(csv_lines):
    """Parses export data from
    https://play.google.com/store/apps/details?id=com.huybn.UsageHistory
    """
    reader = csv.DictReader(csv_lines)
    # Convert times to datetime and get rid of non-data lines.  Also skip
    # repeated lines.
    parsed_rows = set()
    app_usages = []
    for row in reader:
        # Ignore header lines from concatenating multiple csvs
        if list(row.keys()) == list(row.values()):
            continue
        # Ignore duplicate rows.
        row_tuple = tuple(row.values())
        if row_tuple in parsed_rows:
            continue
        parsed_rows.add(row_tuple)
        # Get time from row data.
        use_time = datetime.fromtimestamp(
            int(row['Time in ms']) / 1000).replace(tzinfo=tz.gettz('PST'))
        # Make sure that all times are unique, so in sorting nothing gets
        # rearranged.  This PROBABLY keeps the initial order, but might still
        # be a bit buggy.
        if app_usages and use_time == app_usages[-1].start_time:
            use_time -= timedelta(seconds=1)
        cur_usage = PhoneSession(
            start_time=use_time,
            end_time=use_time,
        )
        cur_usage.summed_usages[row['\ufeff\"App name\"']] += timedelta(
            seconds=float(row['Duration (s)']))
        app_usages.append(cur_usage)
    app_usages.sort(key=lambda usage: usage.start_time)
    return app_usages


def unify_sessions(sessions):
    def join_summed_usages(su1, su2):
        new = copy.deepcopy(su1)
        for app, duration in su2.items():
            new[app] += duration
        return new
    unified = PhoneSession(
        start_time=sessions[0].start_time,
        end_time=sessions[-1].end_time,
        summed_usages=reduce(join_summed_usages,
                             [s.summed_usages for s in sessions]),
        checks=sum([s.checks for s in sessions]),
    )
    return unified


def collapse_all_sessions(sessions, idle_mins=20):
    return [unify_sessions(s) for s in utils.split_on_gaps(
        sessions, timedelta(minutes=idle_mins),
        key=lambda s: s.start_time, last_key=lambda s: s.end_time)]


def create_events(csv_lines):
    app_usages = get_app_usages_from_usage_history_app_export_lines(csv_lines)
    sessions = collapse_all_sessions(app_usages, idle_mins=20)
    return [ps.to_calendar_event() for ps in sessions]
