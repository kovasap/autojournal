import os
import copy
from typing import List
from datetime import datetime, timedelta
from enum import Enum
from pprint import pprint

from sortedcontainers import SortedList
from selfspy.modules import models, config as cfg
from selfspy.stats import pretty_seconds, Selfstats, create_times


def print_session(session):
    print(session['title'])
    for t in session['action_timings']:
        print(t[0].isoformat(' '), t[1])
    print()


def get_window_sessions(db_name):
    # List where each element describes the activity in a single window.
    # Switching windows creates a new element, even if window switched to was
    # visited previously. Elements are dicts with these keys:
    #     title (str): Title of the window.
    #     program_name (str): Name of the program that this window is an
    #         instance of.
    #     keypress_timings (sorted list of datetimes): Timestamp for each
    #         keypress that happened while in this window.  There is always one
    #         "keypress" when the window is moved to.  It's safe to say that the
    #         time in a window is the last time in this list minus the first
    #         time.  This list is sorted.
    #     mouse_click_timings: Like keypress_timings, but for mouse clicks.
    #     mouse_move_timings: Like keypress_timings, but for mouse moves.
    window_sessions = SortedList(key=lambda o: o['action_timings'][0])

    class Action(Enum):
        KEYPRESS = 1
        MOUSE_MOVE = 2
        MOUSE_CLICK = 3

    # Query "Keys" table for keypress_timings and basic window info.
    session = models.initialize(db_name)()
    for keys_row in session.query(models.Keys).order_by(models.Keys.id).all():
        window_sessions.add(dict(
            title=keys_row.window.title,
            program_name=keys_row.process.name,
            action_timings=SortedList(
                [(datetime.fromtimestamp(t), Action.KEYPRESS)
                 for t in create_times(keys_row)])))

    # Query "Clicks" table to fill out mouse data in window_sessions.
    for click_row in session.query(
            models.Click).order_by(models.Click.id).all():
        click_row_tuple = (
            click_row.created_at,
            Action.MOUSE_CLICK if click_row.press else Action.MOUSE_MOVE)
        idx = window_sessions.bisect_left(
            dict(action_timings=[click_row_tuple])) - 1
        window_sessions[idx]['action_timings'].add(click_row_tuple)

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


def get_events_from_sessions(window_sessions, idle_time):
    active_sessions = []
    last_time = None
    for window_session in window_sessions:
        new_timings = split_on_gaps(
            window_session['action_timings'], idle_time, key=lambda t: t[0])
        session_no_timings = copy.deepcopy(window_session)
        session_no_timings.pop('action_timings')
        for timings in new_timings:
            active_sessions.append(
                dict(action_timings=timings, **session_no_timings))

    # pprint(active_sessions)
    grouped_sessions = split_on_gaps(
        active_sessions, idle_time,
        key=lambda s: s['action_timings'][0][0],
        last_key=lambda s: s['action_timings'][-1][0])
    for sessions in grouped_sessions:
        # print([session['title'] for session in sessions])
        for s in sessions:
            print_session(s)
        # print(sessions[0]['action_timings'][0][0].isoformat(' '))
        # print(sessions[-1]['action_timings'][-1][0].isoformat(' '))
        # print(len(sessions))
        print('-----------------------------------')


if __name__ == '__main__':
    db_name = os.path.expanduser(os.path.join(cfg.DATA_DIR, cfg.DBNAME))
    window_sessions = get_window_sessions(db_name)[-7:]
    get_events_from_sessions(window_sessions, timedelta(seconds=60))
    # for session in window_sessions:
    #     print(session['title'], len(session['action_timings']))
    # stats = Selfstats(db_name, {})
    # print(stats.calc_summary())
