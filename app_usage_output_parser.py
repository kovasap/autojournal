import copy
import csv
from datetime import datetime, timedelta
from dateutil import tz
from collections import defaultdict
from dataclasses import dataclass, field
from functools import reduce
from typing import Dict

from sortedcontainers import SortedSet
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

    def get_duration(self):
        return self.end_time - self.start_time

    def to_calendar_event(self):
        used_time = reduce(lambda t1, t2: t1 + t2,
                           self.summed_usages.values(),
                           timedelta(seconds=0))
        unused_time = self.get_duration() - used_time
        # Avoid off by very slight amount errors.
        if unused_time.total_seconds() < 1:
            unused_time = timedelta(seconds=0)
        if unused_time < timedelta(seconds=0):
            print(self.get_duration(), used_time, unused_time)
            print(self.end_time)
            raise Exception()
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
        used_time_str = utils.strfdelta(used_time)
        used_secs = used_time.total_seconds()
        unused_secs = unused_time.total_seconds()
        if used_secs == 0 and unused_secs == 0:
            percent_active = 100.0
        else:
            percent_active = round(
                100 * (used_secs / (unused_secs + used_secs)), 1)
        return calendar_api.Event(
            start=dict(dateTime=self.start_time.isoformat(),
                       timeZone='America/Los_Angeles'),
            end=dict(dateTime=self.end_time.isoformat(),
                     timeZone='America/Los_Angeles'),
            summary=(f'{used_time_str} ({percent_active}%), {self.checks} '
                     f'checks. {top_event_name} primarily'),
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
    # i = 0
    for row in reader:
        # i += 1
        # if i > 10:
        #     raise Exception()
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
        duration = timedelta(seconds=float(row['Duration (s)']))
        cur_usage = PhoneSession(
            start_time=use_time,
            end_time=use_time + duration,
        )
        cur_usage.summed_usages[row['\ufeff\"App name\"']] += duration
        # There is a bug with the usage_history app where events are sometimes
        # duplicated ~2 seconds after the original event.  This attempts to
        # filter those duplicates out of the final data set.
        duplicate = False
        for existing_usage in app_usages[::-1]:
            if existing_usage.summed_usages == cur_usage.summed_usages:
                duplicate = True
            if ((cur_usage.start_time - existing_usage.start_time)
                    > timedelta(seconds=4)):
                break
        if not duplicate:
            # print(cur_usage.start_time)
            # for k, v in cur_usage.summed_usages.items():
            #     print(k, v)
            app_usages.append(cur_usage)
    app_usages.sort(key=lambda usage: usage.start_time)
    return app_usages


def get_app_usages_from_phone_time_app_export_lines(csv_lines):
    """Parses export data from
    https://play.google.com/store/apps/details?id=com.smartertime.phonetime
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
        row_tuple = tuple(sorted(row.items(), key=lambda t: t[0]))
        if row_tuple in parsed_rows:
            continue
        parsed_rows.add(row_tuple)
        # Get time from row data.
        use_time = datetime.fromtimestamp(
            int(row['Start time ms']) / 1000).replace(tzinfo=tz.gettz('PST'))
        # Make sure that all times are unique, so in sorting nothing gets
        # rearranged.  This PROBABLY keeps the initial order, but might still
        # be a bit buggy.
        # if app_usages and use_time == app_usages[-1].start_time:
        #     use_time -= timedelta(seconds=1)
        cur_usage = PhoneSession(
            start_time=use_time,
            end_time=use_time + timedelta(
                seconds=float(row['Duration ms']) / 1000),
        )
        # Truncate single app sessions that have durations that bleed past the
        # next session's start time.
        if app_usages and cur_usage.start_time < app_usages[-1].end_time:
            app_usages[-1].end_time = cur_usage.start_time
            last_app = next(iter(app_usages[-1].summed_usages.keys()))
            app_usages[-1].summed_usages[
                last_app] = app_usages[-1].get_duration()
        if not row['App name'].strip():
            row['App name'] = 'Unknown'
        cur_usage.summed_usages[row['App name']] += cur_usage.get_duration()
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
    # try:
    #     unified.to_calendar_event()
    # except:
    #     for s in sessions:
    #         print(s.start_time.strftime('%M %S'))
    #         for k, v in s.summed_usages.items():
    #             print(k, utils.strfdelta(v))
    #     print(unified.to_calendar_event())
    return unified


def collapse_all_sessions(sessions, idle_mins=20):
    return [unify_sessions(s) for s in utils.split_on_gaps(
        sessions, timedelta(minutes=idle_mins),
        key=lambda s: s.start_time, last_key=lambda s: s.end_time)]


def create_events(csv_lines):
    app_usages = get_app_usages_from_usage_history_app_export_lines(csv_lines)
    # Group individual app usages into continuous usage sessions.
    sessions = collapse_all_sessions(app_usages, idle_mins=0.01)
    # Each session should count as a single phone "check".
    for s in sessions:
        s.checks = 1
    # Create new sessions representing multiple sessions happening quickly
    # after each other.
    grouped_sessions = collapse_all_sessions(sessions, idle_mins=20)
    return [ps.to_calendar_event() for ps in grouped_sessions]
