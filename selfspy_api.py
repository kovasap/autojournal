import os
import copy
from typing import List, Any
from datetime import datetime, timedelta
from pprint import pprint
from dateutil import tz
from collections import namedtuple
from dataclasses import dataclass
from functools import reduce

from sortedcontainers import SortedList
from selfspy.modules import models, config as cfg
from selfspy.stats import create_times

import calendar_api


ActionTiming = namedtuple('ActionTiming', [
    'time',    # type datetime
    'num_moves',  # type int, zero if this is a keystroke, nonzero if is a
                  # click selfspy stores amount of mouse movement before a
                  # click in the same row, so we carry through that infomation
                  # here.
])


@dataclass
class WindowSession:
    """Describes the time spent in a single window.

    Every time a window is switched to, another instance of this is created.
    """
    # Title of the window.
    title: str = None
    # Name of the program that this window is an instance of.
    program_name: str = None
    # Timestamp for each action that happened while in this window.  There is
    # always one "action" when the window is moved to.  It's safe to say that
    # the time in a window is the last time in this list minus the first time.
    action_timings: 'Any' = None  # SortedList[ActionTiming]

    def get_total_time(self):
        return self.action_timings[-1].time - self.action_timings[0].time

    def get_total_actions_by_type(self):
        return dict(
            keystrokes=len([a for a in self.action_timings
                            if a.num_moves == 0]),
            clicks=len([a for a in self.action_timings if a.num_moves != 0]),
            mouse_moves=sum([a.num_moves for a in self.action_timings]),
        )

    def summarize(self):
        actions = ', '.join([
            f'{v} {k}' for k, v in self.get_total_actions_by_type().items()])
        total_mins = round(self.get_total_time().total_seconds() / 60, 2)
        return f'{total_mins}m : {self.title} --- {actions}'


def get_session_group_description(sessions: List[WindowSession], long=True):
    unique_sessions = combine_sessions(sessions)
    total_actions = reduce(
        lambda d1, d2: {k: d1[k] + d2[k] for k in d1.keys()},
        [s.get_total_actions_by_type() for s in sessions])
    action_summary = ''
    for k, v in total_actions.items():
        action_summary += f'{v} {k} ({round(v / 60, 2)} {k} per minute)\n'
    total_mins = round(sum([s.get_total_time().total_seconds()
                            for s in unique_sessions]) / 60, 2)
    if long:
        return f"""Session lasted {total_mins} minutes.

{action_summary}
Windows used ({len(sessions)} total switches):

""" + '\n'.join([s.summarize() for s in unique_sessions])
    else:
        # Get events that make up majority of time in session
        top_session_titles = []
        percent_left = 100
        for s in unique_sessions:
            top_session_titles.append(s.title)
            percent_left -= ((s.get_total_time().total_seconds() / 60)
                             / total_mins) * 100
            if percent_left < 25:
                break
        kpm = round(total_actions['keystrokes'] / 60, 2)
        cpm = round(total_actions['clicks'] / 60, 2)
        return f'{kpm}kpm, {cpm}cpm. {" | ".join(top_session_titles)}'


def make_cal_event_from_session_group(sessions: List[WindowSession]):
    return calendar_api.Event(
        start=dict(
            dateTime=sessions[0].action_timings[0].time.replace(
                tzinfo=tz.gettz('PST')).isoformat(),
            timeZone='America/Los_Angeles'),
        end=dict(
            dateTime=sessions[-1].action_timings[-1].time.replace(
                tzinfo=tz.gettz('PST')).isoformat(),
            timeZone='America/Los_Angeles'),
        summary=get_session_group_description(sessions, long=False),
        description=get_session_group_description(sessions, long=True),
    )


def get_window_sessions(db_name):
    # Sessions sorted by the first action that occured in them.
    window_sessions = SortedList(key=lambda ws: ws.action_timings[0])

    # Query "Keys" table for action_timings and basic window info.
    session = models.initialize(db_name)()
    for keys_row in session.query(models.Keys).order_by(models.Keys.id).all():
        window_sessions.add(WindowSession(
            title=keys_row.window.title,
            program_name=keys_row.process.name,
            action_timings=SortedList(
                [ActionTiming(time=datetime.fromtimestamp(t),
                              num_moves=0)
                 for t in create_times(keys_row)])))

    # Query "Clicks" table to fill out mouse data in window_sessions.
    for click_row in session.query(
            models.Click).order_by(models.Click.id).all():
        click_row_tuple = ActionTiming(
            time=click_row.created_at,
            num_moves=click_row.nrmoves)
        idx = window_sessions.bisect_left(
            WindowSession(action_timings=[click_row_tuple])) - 1
        window_sessions[idx].action_timings.add(click_row_tuple)

    return window_sessions


def split_on_gaps(values, threshold, key=lambda o: o, last_key=None):
    """

    >>> split_on_gaps([1,2,3,4,8,9,10], 2)
    [[1, 2, 3, 4], [8, 9, 10]]
    """
    if last_key is None:
        last_key = key
    last_val = None
    split_points = []
    for i, orig_value in enumerate(values):
        value = key(orig_value)
        if last_val is not None and (value - last_val) > threshold:
            split_points.append(i)
        last_val = last_key(orig_value)
    if split_points:
        split_points.insert(0, 0)
        split_points.append(len(values))
        return [values[split_points[i]:split_points[i+1]]
                for i in range(len(split_points) - 1)]
    else:
        return [values]


def combine_sessions(window_sessions):
    """Takes all window sessions in input with same title and merges them into a
    new session with all their action_timings.

    Output is sorted by the total time spent in the combined session.
    """
    title_to_merged_sessions = {}
    for session in window_sessions:
        if session.title not in title_to_merged_sessions:
            title_to_merged_sessions[session.title] = copy.deepcopy(session)
        else:
            title_to_merged_sessions[session.title].action_timings.update(
                session.action_timings)
    return sorted(title_to_merged_sessions.values(),
                  # longest sessions first
                  key=WindowSession.get_total_time)[::-1]


def get_events_from_sessions(window_sessions, idle_time):
    # Split up long window sessions with inactive periods into several
    # sessions, each containing activity (clicks/keystrokes).
    active_sessions = []
    for window_session in window_sessions:
        new_timings = split_on_gaps(
            window_session.action_timings, idle_time, key=lambda t: t.time)
        for timings in new_timings:
            active_sessions.append(WindowSession(
                title=window_session.title,
                program_name=window_session.program_name,
                action_timings=SortedList(timings, key=lambda t: t.time)))

    # Group window sessions into chunks, where each chunk contains a continuous
    # period of activity, with no inactivity longer than idle_time.
    grouped_sessions = split_on_gaps(
        active_sessions, idle_time,
        key=lambda s: s.action_timings[0].time,
        last_key=lambda s: s.action_timings[-1].time)

    for sessions in grouped_sessions:
        print(get_session_group_description(sessions, long=False))
        print(get_session_group_description(sessions))
        print('------------------------------------------------------')

    return [make_cal_event_from_session_group(sessions)
            for sessions in grouped_sessions]


def get_selfspy_usage_events(session_limit=None,
                             idle_seconds=120) -> List[calendar_api.Event]:
    db_name = os.path.expanduser(os.path.join(cfg.DATA_DIR, cfg.DBNAME))
    window_sessions = get_window_sessions(db_name)
    if session_limit:
        window_sessions = window_sessions[-session_limit:]
    return get_events_from_sessions(window_sessions,
                                    timedelta(seconds=idle_seconds))
