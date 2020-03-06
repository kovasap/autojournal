import os
import copy
from typing import List
from datetime import datetime, timedelta
from enum import Enum
from pprint import pprint
from collections import namedtuple
from dataclasses import dataclass
from functools import reduce

from sortedcontainers import SortedList
from selfspy.modules import models, config as cfg
from selfspy.stats import pretty_seconds, Selfstats, create_times


def print_session(session):
    actions = ' - '.join([f'{k}={v}' for k, v in
                          session.get_total_actions_by_type().items()])
    print(f'{session.title} --- {actions}')
    # print(session['title'])
    # for t in session['action_timings']:
    #     print(t[0].isoformat(' '), t[1])
    # print()

ActionTiming = namedtuple('ActionTiming', [
    'time',    # type datetime
    'num_moves',  # type int, zero if this is a keypress, nonzero if is a click
                  # selfspy stores amount of mouse movement before a click in
                  # the same row, so we carry through that infomation here
])

@dataclass
class WindowSession:
    """Describes the time spent in a single window.

    Every time a window is switched to, another instance of this is created.
    """
    # Title of the window.
    title: str=None
    # Name of the program that this window is an instance of.
    program_name: str=None
    # Timestamp for each action that happened while in this window.  There is
    # always one "action" when the window is moved to.  It's safe to say that
    # the time in a window is the last time in this list minus the first time.
    action_timings: 'typing.Any'=None #  SortedList[ActionTiming]

    def get_total_time(self):
        return self.action_timings[-1].time - self.action_timings[0].time

    def get_total_actions_by_type(self):
        return dict(
            keypress=len([a for a in self.action_timings if a.num_moves == 0]),
            click=len([a for a in self.action_timings if a.num_moves != 0]),
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
    """
    title_to_merged_sessions = {}
    for session in window_sessions:
        if session.title not in title_to_merged_sessions:
            title_to_merged_sessions[session.title] = copy.deepcopy(session)
        else:
            title_to_merged_sessions[session.title].action_timings.update(
                session.action_timings)
    return sorted(title_to_merged_sessions.values(),
                  key=WindowSession.get_total_time)

def get_events_from_sessions(window_sessions, idle_time):
    # Split up long window sessions with inactive periods into several sessions,
    # each containing activity (clicks/keypresses).
    active_sessions = []
    last_time = None
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
        start = sessions[0].action_timings[0].time
        end = sessions[-1].action_timings[-1].time
        switches = len(sessions)
        unique_sessions = combine_sessions(sessions)
        total_actions = {
            action_type: sum([s.get_total_actions_by_type()[action_type]
                              for s in unique_sessions])
            for action_type in ['click', 'keypress']}
        print(start)
        print(end)
        print(switches)
        pprint(total_actions)
        for s in unique_sessions:
            print_session(s)
        # print(sessions[0]['action_timings'][0][0].isoformat(' '))
        # print(sessions[-1]['action_timings'][-1][0].isoformat(' '))
        # print(len(sessions))
        print('-----------------------------------')


if __name__ == '__main__':
    db_name = os.path.expanduser(os.path.join(cfg.DATA_DIR, cfg.DBNAME))
    window_sessions = get_window_sessions(db_name)[-10:]
    get_events_from_sessions(window_sessions, timedelta(seconds=120))
    # for session in window_sessions:
    #     print(session['title'], len(session['action_timings']))
    # stats = Selfstats(db_name, {})
    # print(stats.calc_summary())
