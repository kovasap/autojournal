from typing import Dict
from datetime import datetime, timezone, timedelta
from dateutil import tz
from pprint import pprint

import credentials
import photos_api
import calendar_api


def utc_to_timezone(utc_time: str,
                    timezone_name: str='America/Los_Angeles',
                    additional_offset_mins: int=0,
                    round_seconds: bool=False,
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


def photo_to_event(photo: photos_api.mediaItem,
                   event_length_mins: int=15) -> calendar_api.Event:
    return calendar_api.Event(
        start=utc_to_timezone(photo['mediaMetadata']['creationTime']),
        end=utc_to_timezone(photo['mediaMetadata']['creationTime'],
                            additional_offset_mins=event_length_mins),
        description=f'Notes: {photo.get("description", "")}\n\n'
                    f'{photo["productUrl"]}',
        summary='Ate food',
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


def main():
    creds = credentials.get_credentials([
        # If modifying scopes, delete the file token.pickle.
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/photoslibrary.readonly'])

    photos_api_instance = photos_api.PhotosApi(creds)
    food_pictures = photos_api_instance.get_album_contents(
        photos_api_instance.get_album_id('Food!'))

    # pprint(food_pictures)
    food_events = [photo_to_event(photo) for photo in food_pictures]

    food_events = [photo_to_event(food_pictures[-1])]

    cal_api_instance = calendar_api.CalendarApi(creds)
    food_calendar_id = cal_api_instance.get_calendar_id('Food')
    # Filter out all food items that have already been added to the calendar.
    existing_events = cal_api_instance.get_events(food_calendar_id)

    pprint(existing_events)
    print()
    pprint(food_events)

    new_food_events = list(filter(
        lambda query: all(not is_subset(ref, query) for ref in existing_events),
        food_events))

    print(f'Adding {len(new_food_events)} new food events...')

    # cal_api_instance.add_events(food_calendar_id, new_food_events)

    # pprint(cal_api_instance.get_latest_events(
    #     'mgf5ho48h2a65185npg79tuvqc@group.calendar.google.com', 10))


if __name__ == '__main__':
    main()
