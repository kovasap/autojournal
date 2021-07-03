"""Gps data parsing functionality."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple, Sequence
import statistics

import geopy.distance
import geopy.geocoders

from ..data_model import Event

# Distance between two readings for movement between them to be ignored.
STATIONARY_DISTANCE_MILES = 0.05
STATIONARY_TIME_BETWEEN_TRIPS_SECS = 60 * 5

location_bank = []
nominatim = geopy.geocoders.Nominatim(user_agent='autojournal')

@dataclass
class Location:
  """Stores location data."""

  latitude: float
  longitude: float
  elevation: float
  speed: float
  name: str = 'unknown'
  mode_of_travel: str = None

  @classmethod
  def from_line(cls, line: dict) -> 'Location':
    return cls(
        latitude=line['lat'],
        longitude=line['lon'],
        elevation=line['elevation'],
        speed=line['speed'])

  def summary(self) -> str:
    if self.mode_of_travel:
      return ''
    else:
      if self.name == 'unknown':
        self.lookup_name()
      return f'At {self.name}'

  def as_point(self) -> Tuple[float, float]:
    return (self.latitude, self.longitude)

  def get_distance(self, other):
    return geopy.distance.distance(
        self.as_point(), other.as_point()).miles

  def is_same_place(self, other) -> bool:
    return self.get_distance(other) < STATIONARY_DISTANCE_MILES

  def lookup_name(self) -> str:
    for banked_location in location_bank:
      if banked_location.is_same_place(self):
        self.name = banked_location.name
    else:
      self.name = nominatim.reverse(self.as_point()).address
      location_bank.append(self)

  def __str__(self) -> str:
    return f'{self.as_point()}, {self.name}'


def get_traveling_description(
    timestamps: Sequence[datetime], locations: Sequence[Location]) -> str:
  mph_speeds = [
      locations[i-1].get_distance(location)
      / ((timestamp - timestamps[i-1]).total_seconds() / 60 / 60)
      for i, (timestamp, location) in enumerate(zip(timestamps, locations))
      if i > 0
  ]
  average_mph_speed = statistics.mean(mph_speeds)
  stdev_mph_speed = statistics.stdev(mph_speeds)
  max_mph_speed = max(mph_speeds)
  # https://www.bbc.co.uk/bitesize/guides/zq4mfcw/revision/1
  if average_mph_speed < 5 and max_mph_speed < 7:
    mode_of_travel = 'walking'
  elif average_mph_speed < 13 and max_mph_speed < 16:
    mode_of_travel = 'running'
  elif average_mph_speed < 25:
    mode_of_travel = 'biking'
  elif average_mph_speed < 100:
    mode_of_travel = 'driving'
  elif average_mph_speed < 300:
    mode_of_travel = 'on the train'
  else:
    mode_of_travel = 'flying'
  return (f'{mode_of_travel} at {average_mph_speed:.2f}±{stdev_mph_speed:.2f} '
          f'mph (max of {max_mph_speed:.2f} mph)')


def make_calendar_event(
    timestamps: Sequence[datetime], locations: Sequence[Location],
    travel_event: bool) -> Event:
  return Event(
      timestamp=timestamps[0],
      duration=timestamps[-1] - timestamps[0],
      summary=(get_traveling_description(timestamps, locations)
               if travel_event else locations[-1].summary()),
      description='')



def parse_gps(data_by_fname) -> List[Event]:
  last_location = None
  pending_event_is_travel = False
  event_timestamps = []
  event_locations = []
  events = []
  for fname, data in data_by_fname.items():
    if not fname.endswith('.zip'):
      continue
    for line in data:
      line_location = Location.from_line(line)
      print(str(line_location))
      line_timestamp = datetime.fromisoformat(
          line['time'].replace('Z', '+00:00'))
      if not last_location:
        last_location = line_location
        continue
      currently_traveling = last_location.is_same_place(line_location)
      # If we were traveling, and now are not (or vice versa), we create a new
      # event and reset our event lists.
      if (currently_traveling != pending_event_is_travel
          and len(event_timestamps) > 2 and len(event_locations) > 2):
        events.append(make_calendar_event(
            event_timestamps, event_locations, pending_event_is_travel))
        event_timestamps = []
        event_locations = []
        pending_event_is_travel = currently_traveling
      event_timestamps.append(line_timestamp)
      event_locations.append(line_location)
      last_location = line_location
  return events
