from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple

import geopy.distance
import geopy.geocoders

from ..data_model import Event


CLOSE_ENOUGH_DISTANCE_MILES = 0.3

STATIONARY_TIME_BETWEEN_TRIPS_SECS = 60 * 5

MODES_OF_TRAVEL_SPEEDS = dict(
    walking=(0.1. 1.0),
    biking=(1.0, 5.0),
    driving=(5.0, 25.0),
    flying=(25.0, 50.0),
)

# https://www.bbc.co.uk/bitesize/guides/zq4mfcw/revision/1
# Walking	1.5	3.4
# Running	5	11
# Cycling	7	15
# Car	13 - 30	29 - 67
# Train	56	125
# Plane	250	560


@dataclass
class Location:
  latitude: float
  longitude: float
  elevation: float
  speed: float
  name: str = 'unknown'
  mode_of_travel: str = None

  def summary(self) -> str:
    if mode_of_travel:
      return ''
    else:
      return f'At {name}'

  def as_point(self) -> Tuple[float, float]:
    return (self.latitude, self.longitude)

  def is_close_enough(self, other) -> bool:
    return (
        geopy.distance.distance(self.as_point(), other.as_point()).miles
        < CLOSE_ENOUGH_DISTANCE_MILES)


location_bank = []
nominatim = geopy.geocoders.Nominatim(user_agent='autojournal')
def get_location_name(location: Location) -> str:
  return nominatim.reverse(location.as_point()).address


def parse_gps(data_by_fname) -> List[Event]:
  cur_location = None
  events = []
  for fname, data in data_by_fname.items():
    if not fname.endswith('.zip'):
      continue
    for line in data:
      line_location = Location(
          latitude=line['lat'],
          longitude=line['long'],
          elevation=line['elevation'],
          speed=line['speed'])
      if cur_location and not cur_location.is_close_enough(line_location):
        pass
      else:
        cur_location = line_location
        for banked_location in location_bank:
          if banked_location.is_close_enough(cur_location):
            cur_location.name = banked_location.name
        else:
          cur_location.name = get_location_name(cur_location)
          location_bank.append(cur_location)
        events.append(Event(
          timestamp=datetime.fromisoformat(
            line['time'].replace('Z', '+00:00')),
          summary=cur_location.summary(),
          description='',
          data=line))
  return events
