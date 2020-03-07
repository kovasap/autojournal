from typing import Dict
from datetime import datetime, timedelta
from dateutil import tz


def utc_to_timezone(utc_time: str,
                    timezone_name: str = 'America/Los_Angeles',
                    additional_offset_mins: int = 0,
                    round_seconds: bool = False,
                    ) -> Dict[str, str]:
    """Converts utc time string (e.g. from Google Photos timestamp) to pst
    string with timezone name (e.g. for Google Calendar event).

    >>> utc_to_timezone('2020-01-29T01:57:06Z', 'America/Los_Angeles', \
                        round_seconds=False)
    {'dateTime': '2020-01-28T17:57:06-08:00', 'timeZone': 'America/Los_Angeles'}
    >>> utc_to_timezone('2020-01-29T01:57:06Z', 'America/Los_Angeles', 4, \
                        round_seconds=False)
    {'dateTime': '2020-01-28T18:01:06-08:00', 'timeZone': 'America/Los_Angeles'}
    >>> utc_to_timezone('2020-01-29T01:57:06Z', 'America/Los_Angeles', \
                        round_seconds=True)
    {'dateTime': '2020-01-28T17:57:00-08:00', 'timeZone': 'America/Los_Angeles'}
    """
    utc = datetime.fromisoformat(utc_time.rstrip('Z')).replace(
        tzinfo=tz.gettz('UTC'))
    pst = utc.astimezone(tz.gettz(timezone_name))
    pst += timedelta(minutes=additional_offset_mins)
    if round_seconds:
        pst = pst.replace(second=0)
    return dict(
        dateTime=pst.isoformat(),
        timeZone=timezone_name,
    )


def is_subset(ref: dict, query: dict) -> bool:
    """Checks to see if the query dict is a subset of the ref dict.

    Taken from
    https://stackoverflow.com/questions/49419486/recursive-function-to-check-dictionary-is-a-subset-of-another-dictionary

    """
    for key, value in query.items():
        if key not in ref:
            return False
        if isinstance(value, dict):
            if not is_subset(ref[key], value):
                return False
        elif isinstance(value, list):
            if not set(value) <= set(ref[key]):
                return False
        elif isinstance(value, set):
            if not value <= ref[key]:
                return False
        else:
            if not value == ref[key]:
                return False
    return True
