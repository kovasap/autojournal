"""Gps data parsing functionality.

Parses data generated by the GPSLogger for Android app (https://gpslogger.app/).
Make sure that "gps" is the only source for data on the app (not "network").
"""

from dataclasses import dataclass
from dateutil import tz
from datetime import datetime, timedelta
from typing import List, Tuple, Sequence, Set, Optional
import statistics

import geopy.distance
import geopy.geocoders

from ..data_model import Event

# Distance between two readings for movement between them to be ignored.
STATIONARY_DISTANCE_MILES = 0.05
STATIONARY_TIME_BETWEEN_TRIPS_SECS = 60 * 5

location_bank = []
nominatim = geopy.geocoders.Nominatim(user_agent='autojournal')

def make_float(s: str) -> float:
  return float(s) if s else 0.0

@dataclass
class Location:
  """Stores location data."""

  latitude: float
  longitude: float
  elevation: float
  accuracy_miles: float
  speed: float
  name: str = 'unknown'
  mode_of_travel: str = None

  @classmethod
  def from_line(cls, line: dict) -> 'Location':
    return cls(
        latitude=make_float(line['lat']),
        longitude=make_float(line['lon']),
        elevation=make_float(line['elevation']),
        accuracy_miles=make_float(line['accuracy']) / 1609.34,  # meters -> miles
        speed=make_float(line['speed']))

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
    return (
        self.accuracy_miles + other.accuracy_miles + STATIONARY_DISTANCE_MILES
        > self.get_distance(other))

  def lookup_name(self) -> str:
    for banked_location in location_bank:
      if banked_location.is_same_place(self):
        self.name = banked_location.name
    else:
      self.name = nominatim.reverse(self.as_point()).address
      location_bank.append(self)

  def __str__(self) -> str:
    return f'{self.as_point()}, {self.name}'


def are_single_location(
    locations: Sequence[Location], fraction_required: float=0.9,
    samples: Optional[int]=None) -> bool:
  sampled_locations = locations
  if samples:
    sample_spacing = len(locations) // samples
    if sample_spacing > 0:
      sampled_locations = [locations[i*sample_spacing] for i in range(samples)]
  num_locations = len(sampled_locations)
  total_num_matching = 0
  for l1 in sampled_locations:
    num_matching_l1 = 0
    for l2 in sampled_locations:
      if l1.is_same_place(l2):
        num_matching_l1 += 1
    if num_matching_l1 / num_locations > fraction_required:
      total_num_matching += 1
  return total_num_matching / num_locations > fraction_required


def get_traveling_description(
    timestamps: Sequence[datetime], locations: Sequence[Location]) -> str:
  mph_speeds = [
      locations[i-1].get_distance(location)
      / ((timestamp - timestamps[i-1]).total_seconds() / 60 / 60)
      for i, (timestamp, location) in enumerate(zip(timestamps, locations))
      if i > 0
  ]
  if not mph_speeds:
    return 'not enough data'
  average_mph_speed = statistics.mean(mph_speeds)
  stdev_mph_speed = statistics.stdev(mph_speeds)
  max_mph_speed = max(mph_speeds)
  # https://www.bbc.co.uk/bitesize/guides/zq4mfcw/revision/1
  if average_mph_speed < 2:
    mode_of_travel = 'not travelling?'
  elif average_mph_speed < 4 and max_mph_speed < 10:
    mode_of_travel = 'walking'
  elif average_mph_speed < 13 and max_mph_speed < 16:
    mode_of_travel = 'running'
  elif average_mph_speed < 25 and max_mph_speed < 20:
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


def make_events(timestamps: List[datetime], locations: List[Location],
    window_size: timedelta=timedelta(minutes=2),
    min_points_per_window: int=3,
    ) -> List[Tuple[datetime, str]]:
  """Finds sections of input list where location is different."""

  def get_window_size(ts: List[datetime]) -> timedelta:
    if not ts:
      return timedelta(seconds=0)
    return ts[-1] - ts[0]

  # Creates windows of window_size.  If a window has less than
  # min_points_per_window, then we add more even if we go above window_size.
  timestamp_windows = [[]]
  location_windows = [[]]
  for timestamp, location in zip(timestamps, locations):
    if (get_window_size(timestamp_windows[-1]) > window_size and
        len(timestamp_windows[-1]) >= min_points_per_window):
      timestamp_windows.append([])
      location_windows.append([])
    timestamp_windows[-1].append(timestamp)
    location_windows[-1].append(location)

  events = []
  cur_event_timestamps = []
  cur_event_locations = []
  stationary = True
  for timestamp_window, location_window in zip(
      timestamp_windows, location_windows):
    print(timestamp_window[0].strftime('%m/%d/%Y %I:%M%p'))
    single_location = are_single_location(location_window)
    if cur_event_timestamps and single_location != stationary:
      events.append(make_calendar_event(
          cur_event_timestamps, cur_event_locations,
          travel_event=not stationary))
      stationary = not stationary
      cur_event_timestamps = []
      cur_event_locations = []
    cur_event_timestamps += timestamp_window
    cur_event_locations += location_window
  events.append(make_calendar_event(
      cur_event_timestamps, cur_event_locations,
      travel_event=not stationary))
  return events


def parse_gps(data_by_fname) -> List[Event]:
  # event_timestamps = []
  # event_locations = []
  events = []
  for fname, data in sorted(data_by_fname.items(), key=lambda t: t[0]):
    if not fname.endswith('.zip'):
      continue
    line_locations = []
    line_timestamps = []
    for line in data:
      line_locations.append(Location.from_line(line))
      line_timestamps.append(datetime.fromisoformat(
          line['time'].replace('Z', '+00:00')).astimezone(tz.gettz('PST')))
    events += make_events(line_timestamps, line_locations)
  return events
