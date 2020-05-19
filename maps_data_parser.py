import json
from pprint import pprint
import pandas as pd
from datetime import datetime, timedelta

from maps_location_history.process_location import get_kml_file, full_df

import calendar_api
import utils


def _get_coord_str(d):
    return f"{d['latitudeE7']}, {d['longitudeE7']}"


def parse_semantic_location_history(lines_by_filename):
    events = []
    for lines in lines_by_filename.values():
        data = json.loads('\n'.join(lines))
        for o in data['timelineObjects']:
            # These dicts should have a single key
            obj_type = next(iter(o.keys()))
            obj = o[obj_type]
            events.append(calendar_api.Event(
                start=utils.timestamp_ms_to_event_time(
                    int(obj['duration']['startTimestampMs'])),
                end=utils.timestamp_ms_to_event_time(
                    int(obj['duration']['endTimestampMs'])),
            ))
            date = events[-1]['start']['dateTime'][:11]
            if obj_type == 'placeVisit':
                events[-1]['summary'] = f"At {obj['location']['name']}"
                events[-1]['description'] = f"""Details:
Coordinates: {_get_coord_str(obj['location'])}
Address: {obj['location']['address']}
See https://www.google.com/maps/timeline?pb=!1m2!1m1!1s{date} for more.
"""
            elif obj_type == 'activitySegment':
                speed = round(obj['distance'] / ((
                    int(obj['duration']['endTimestampMs'])
                    - int(obj['duration']['startTimestampMs'])) / 1000), 2)
                travel_mode = obj['activityType'].lower().replace('_', ' ')
                events[-1][
                    'summary'] = f"{speed} m/s {travel_mode}"
                events[-1]['description'] = f"""Details:
Start Coordinates: {_get_coord_str(obj['startLocation'])}
End Coordinates: {_get_coord_str(obj['endLocation'])}
See https://www.google.com/maps/timeline?pb=!1m2!1m1!1s{date} for more.
"""
            else:
                raise Exception(o)
    return events


COOKIE_FILE = '/home/kovas/photos_calendar_sync/timeline_cookie.txt'
KML_OUTPUT_DIRECTORY = '/home/kovas/photos_calendar_sync/location_data/'


def make_events_from_kml_data(start_date, end_date,
                              timezone_name='America/Los_Angeles'):
    with open(COOKIE_FILE, 'r') as f:
        cookie_content = f.read().strip()
    kml_files = []
    for date in pd.date_range(start=start_date, end=end_date):
        kml_files.append(
            get_kml_file(date.year, date.month, date.day, cookie_content,
                         KML_OUTPUT_DIRECTORY))
    df = full_df(kml_files).sort_values('RawBeginTime')
    events = []
    last_name_id = None
    for _, row in df.iterrows():
        name_id = str(row.Name) + str(row.Address)
        # Collapse events where both places are the same into a single event.
        if last_name_id == name_id:
            events[-1]['end'] = utils.utc_to_timezone(row.RawEndTime,
                                                      timezone_name)
        else:
            events.append(calendar_api.Event(
                start=utils.utc_to_timezone(row.RawBeginTime, timezone_name),
                end=utils.utc_to_timezone(row.RawEndTime, timezone_name),
                summary=(
                    f'{round(row.Distance / row.TotalSecs, 1)} m/s {row.Category}'
                    if row.Category else
                    f'At {row.Name} {row.Address}'
                ),
                description=f'See https://www.google.com/maps/timeline?pb=!1m2!1m1!1s{row.BeginDate} for details.'
            ))
        last_name_id = name_id
    return events


if __name__ == '__main__':
    make_events_from_kml_data('2019-09-01', '2019-10-10')
