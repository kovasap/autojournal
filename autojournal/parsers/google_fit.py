"""Parses json data like:
{
  "fitnessActivity": "running",
  "startTime": "2021-04-19T20:57:39.686Z",
  "endTime": "2021-04-19T21:08:53.872Z",
  "duration": "674.186s",
  "segment": [{
    "fitnessActivity": "running",
    "startTime": "2021-04-19T20:57:39.686Z",
    "endTime": "2021-04-19T21:08:53.872Z"
  }],
  "aggregate": [{
    "metricName": "com.google.heart_minutes.summary",
    "floatValue": 19.0
  }, {
    "metricName": "com.google.calories.expended",
    "floatValue": 144.3837432861328
  }, {
    "metricName": "com.google.step_count.delta",
    "intValue": 1550
  }, {
    "metricName": "com.google.distance.delta",
    "floatValue": 1558.4816045761108
  }, {
    "metricName": "com.google.speed.summary",
    "floatValue": 2.381139442776954
  }, {
    "metricName": "com.google.active_minutes",
    "intValue": 10
  }]
}
"""

from datetime import datetime, timedelta
from dateutil import tz
import json
from typing import Dict, List, Any

from ..data_model import Event


METERS_IN_MILE = 1609


def get_agg_value(aggregate: dict) -> float:
  for key in ['floatValue', 'intValue']:
    if key in aggregate:
      return float(aggregate[key])
  raise Exception(f'Unknown key in aggregate {aggregate}')

def activity_json_to_event(activity_json: str) -> Event:
  data = json.loads(activity_json)
  aggregates = {
      agg['metricName']: get_agg_value(agg) for agg in data['aggregate']}
  if data['fitnessActivity'] in {'running', 'walking'}:
    calories = aggregates['com.google.calories.expended']
    speed = aggregates['com.google.speed.summary']
    distance_mi = aggregates['com.google.distance.delta'] / METERS_IN_MILE
    description = (
        f'{calories} cal burned {data["fitnessActivity"]} {distance_mi} mi '
        f'at {speed} m/s')
  else:
    calories = aggregates['com.google.calories.expended']
    description = f'{calories} cal burned doing {data["fitnessActivity"]}'
  return Event(
      timestamp=datetime.fromisoformat(
          data['startTime'].replace('Z',
              '+00:00')).astimezone(tz.gettz('PST')),
      duration=timedelta(seconds=float(data['duration'].strip('s'))),
      data=aggregates,
      summary=data['fitnessActivity'],
      description=description)


def parse_sessions(drive_api_instance, directory) -> List[Event]:
  json_files = drive_api_instance.read_files(directory)
  return [activity_json_to_event('\n'.join(lines))
          for lines in json_files.values()]

