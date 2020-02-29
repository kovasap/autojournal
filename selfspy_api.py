import os
from dataclasses import dataclass
from typing import List
from datetime import datetime

from sortedcontainers import SortedList
from selfspy.modules import models, config as cfg
from selfspy.stats import pretty_seconds, Selfstats, create_times


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
    window_sessions = SortedList(key=lambda o: o['keypress_timings'][0])

    # Query "Keys" table for keypress_timings and basic window info.
    session = models.initialize(db_name)()
    for keys_row in session.query(models.Keys).order_by(models.Keys.id).all():
        window_sessions.add(dict(
            title=keys_row.window.title,
            program_name=keys_row.process.name,
            keypress_timings=[
                datetime.fromtimestamp(t) for t in create_times(keys_row)],
            mouse_click_timings=[],
            mouse_move_timings=[]))

    # Query "Clicks" table to fill out mouse data in window_sessions.
    for click_row in session.query(
            models.Click).order_by(models.Click.id).all():
        idx = window_sessions.bisect_left(
            dict(keypress_timings=[click_row.created_at]))
        if idx == len(window_sessions):
            idx -= 1
        session_timings_type = (
            'mouse_click_timings' if click_row.press else 'mouse_move_timings')
        window_sessions[idx][session_timings_type].append(click_row.created_at)

    for session in window_sessions[-10:]:
        print(session)


if __name__ == '__main__':
    db_name = os.path.expanduser(os.path.join(cfg.DATA_DIR, cfg.DBNAME))
    get_window_sessions(db_name)
    # stats = Selfstats(db_name, {})
    # print(stats.calc_summary())
