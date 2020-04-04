import os
import copy
import re
from typing import List, Any
from datetime import datetime, timedelta
from dateutil import tz
from collections import namedtuple
from dataclasses import dataclass
from collections import defaultdict
from functools import reduce

from sortedcontainers import SortedList
from selfspy.modules import models, config as cfg
from selfspy.stats import create_times

import calendar_api
import utils


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
    # TODO might be a bug here where the actions do not quite give the time in
    # the window accurately.  For instance, if a key is pressed to go to a
    # window, then no actions are taken for a while, it might be that the
    # window session for the window "starts" when the first key is pressed,
    # which is inaccurate.
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


def get_total_time_of_sessions(sessions: List[WindowSession]):
    return sum([s.get_total_time().total_seconds() for s in sessions])


def get_total_time_of_sessions_str(sessions: List[WindowSession]):
    return utils.strfdelta(
        timedelta(seconds=get_total_time_of_sessions(sessions)))


def remove_urls(s):
    return re.sub(r'http\S+', '', s)


def remove_redundancy(string):
    redundants = [
        ' - Google Chrome',
        '/google/src/cloud/kovas/chamber_regression_replication/',
    ]
    return reduce(lambda s, r: s.replace(r, ''), redundants, string)


def get_session_group_description(sessions: List[WindowSession], long=True):
    unique_sessions = defaultdict(list)
    for s in sessions:
        unique_sessions[s.title].append(s)
    # Sort unique_sessions by the total time of each group of sessions, longest
    # first.
    unique_sessions = sorted(
        unique_sessions.items(),
        key=lambda t: get_total_time_of_sessions(t[1]))[::-1]

    total_actions = reduce(
        lambda d1, d2: {k: d1[k] + d2[k] for k in d1.keys()},
        [s.get_total_actions_by_type() for s in sessions])
    action_summary = ''
    for k, v in total_actions.items():
        action_summary += f'{v} {k} ({round(v / 60, 2)} {k} per minute)\n'
    # TODO rank windows both by time used AND by keystrokes/mouse actions
    # within.
    if long:
        desc = f"""Used computer for {get_total_time_of_sessions_str(sessions)}.

{action_summary}
Windows used ({len(sessions)} total switches):

"""
        for title, ss in unique_sessions:
            title = remove_redundancy(title)
            actions = reduce(
                lambda d1, d2: {k: d1[k] + d2[k] for k in d1.keys()},
                [s.get_total_actions_by_type() for s in ss])
            actions_str = ', '.join(
                [f'{v} {k}' for k, v in actions.items()]
            ).replace('keystrokes', 'k').replace('clicks', 'c').replace(
                'mouse_moves', 'm')  # Save some characters
            row = (f'{get_total_time_of_sessions_str(ss)} : {title} '
                   f'--- {actions_str}\n')
            if (len(desc) + len(row)
                    > calendar_api.EVENT_DESCRIPTION_LENGTH_LIMIT):
                break
            desc += row
        return desc
    else:
        # Get events that make up majority of time in session
        top_session_titles = []
        percent_left = 100
        total_secs = get_total_time_of_sessions(sessions)
        # Round up to at least 0.01 to avoid div by zero errors.
        if total_secs == 0:
            total_secs = 0.01
        for title, ss in unique_sessions:
            top_session_titles.append(remove_urls(remove_redundancy(
                title.replace('\n', ' '))))
            percent_left -= (get_total_time_of_sessions(ss) / total_secs) * 100
            if percent_left < 25:
                break
        kpm = round(total_actions['keystrokes'] / 60, 2)
        cpm = round(total_actions['clicks'] / 60, 2)
        percent_active = round(
            100 * total_secs / (
                sessions[-1].action_timings[-1].time
                - sessions[0].action_timings[0].time).total_seconds(),
            1)
        return f"""{get_total_time_of_sessions_str(sessions)} Active
 ({percent_active}%)
 -- {' | '.join(top_session_titles)[:50]}
 -- {kpm}kpm, {cpm}cpm.""".replace('\n', '')


def get_window_sessions(db_name):
    # Sessions sorted by the first action that occured in them.
    window_sessions = SortedList(key=lambda ws: ws.action_timings[0])

    # Query "Keys" table for action_timings and basic window info.
    session = models.initialize(db_name)()
    for keys_row in session.query(models.Keys).order_by(models.Keys.id).all():
        window_sessions.add(
            WindowSession(
                title=keys_row.window.title,
                program_name=keys_row.process.name,
                action_timings=SortedList(
                    [ActionTiming(
                        time=datetime.fromtimestamp(t),
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


def get_events_from_sessions(window_sessions, idle_time,
                             group_separation_time):
    # Split up long window sessions with inactive periods into several
    # sessions, each containing activity (clicks/keystrokes).
    active_sessions = []
    for window_session in window_sessions:
        new_timings = utils.split_on_gaps(
            window_session.action_timings, idle_time, key=lambda t: t.time)
        for timings in new_timings:
            active_sessions.append(
                WindowSession(
                    title=window_session.title,
                    program_name=window_session.program_name,
                    action_timings=SortedList(timings, key=lambda t: t.time)))

    # Group window sessions into chunks, where each chunk contains a continuous
    # period of activity, with no inactivity longer than idle_time.
    grouped_sessions = utils.split_on_gaps(
        active_sessions, group_separation_time,
        key=lambda s: s.action_timings[0].time,
        last_key=lambda s: s.action_timings[-1].time)

    # for sessions in grouped_sessions:
    #     print(get_session_group_description(sessions, long=False))
    #     print(get_session_group_description(sessions))
    #     print('------------------------------------------------------')

    return [make_cal_event_from_session_group(sessions)
            for sessions in grouped_sessions]


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


def get_selfspy_usage_events(session_limit=None,
                             idle_seconds=60 * 3,
                             event_separation_seconds=60 * 20,
                             ) -> List[calendar_api.Event]:
    db_name = os.path.expanduser(os.path.join(cfg.DATA_DIR, cfg.DBNAME))
    # db_name = 'test_selfspy_db/selfspy.sqlite'
    window_sessions = get_window_sessions(db_name)
    if session_limit:
        window_sessions = window_sessions[-session_limit:]
    return get_events_from_sessions(
        window_sessions, timedelta(seconds=idle_seconds),
        timedelta(seconds=event_separation_seconds))
