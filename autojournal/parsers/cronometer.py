from collections import defaultdict
import copy
from datetime import datetime
from typing import List, Any, Union

import pytz

from ..data_model import Event


def is_numeric(v: Any) -> bool:
  """Returns True if v can be an int/float, False otherwise."""
  try:
    float(v)
  except ValueError:
    return False
  return True


def _parse_food_timing_note(note: str) -> dict:
  split_note = note['Note'].split(' ')
  data = dict(
      num_foods=int(split_note[1]),
      time=split_note[2],
  )
  if len(split_note) > 3:
    data['description'] = ' '.join(split_note[3:])
  return data


def _get_data_by_day(csv_data):
  data_by_day = defaultdict(list)
  for line in csv_data:
    data_by_day[line['Day']].append(line)
  return data_by_day


def parse_time(time: str) -> datetime:
  dt = datetime.strptime(time, '%Y-%m-%d %I:%M%p')
  return dt.astimezone(pytz.timezone('America/Los_Angeles'))


def add_food(t, d, events, cur_day_events):
  event = Event(
      summary=f'{d["Food Name"]}, {d["Amount"]}',
      description=f'{d["Food Name"]}, {d["Amount"]}',
      timestamp=t,
      data=d)
  events.append(event)
  cur_data = cur_day_events[-1].data if len(cur_day_events) else {}
  cur_day_event = copy.deepcopy(event)
  cur_day_event.data = {k: (cur_data.get(k, 0) + float(v))
                        if is_numeric(v) else v
                        for k, v in d.items()}
  cur_day_events.append(cur_day_event)


def cast_food_value_type(name: str, value: str) -> Union[float, str]:
  if is_numeric(value):
    return float(value)
  elif name in {'Category', 'Food Name', 'Amount'}:
    return value
  elif value == '':
    return 0.0
  else:
    return value


def parse_nutrition(data_by_fname, daily_cumulative: bool = True
                    ) -> List[Event]:
  foods_by_day = _get_data_by_day(data_by_fname['servings.csv'])
  notes_by_day = _get_data_by_day(data_by_fname['notes.csv'])

  events = []
  daily_cum_events = []
  for day, foods in foods_by_day.items():
    # Convert to proper types, making empty strings 0 valued
    foods = [{k: cast_food_value_type(k, v) for k, v in f.items()}
             for f in foods]
    cur_day_events = []
    foods_iter = iter(f for f in foods if f['Food Name'] != 'Tap Water')
    for note in notes_by_day[day]:
      if not note['Note'].startswith('eat'):
        continue
      note_data = _parse_food_timing_note(note)
      for _ in range(note_data['num_foods']):
        add_food(parse_time(f'{day} {note_data["time"]}'),
                 next(foods_iter), events, cur_day_events)
    # Assume the rest of the foods were eaten at midnight.
    for food in foods_iter:
      add_food(parse_time(f'{day} 12:00am'),
               food, events, cur_day_events)
    daily_cum_events += cur_day_events

  return daily_cum_events if daily_cumulative else events


def parse_biometrics(data_by_fname) -> List[Event]:
  pass
