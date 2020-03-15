import json
from pprint import pprint

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
