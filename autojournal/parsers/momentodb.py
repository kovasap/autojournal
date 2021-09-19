from datetime import datetime
from typing import List

from ..data_model import Event


def parse_momentodb(data_by_fname) -> List[Event]:
  events = []
  for fname, data in data_by_fname.items():
    for line in data:
      print(line)
      for key, val in line.items():
        if key in {'Creation', '__id'}:
          continue
        if val in {'', None, 'FALSE'}:
          continue
        events.append(Event(
            summary=f'{key} {val}' if val != 'TRUE' else key,
            description=str(line),
            timestamp=datetime.strptime(
                line['Creation'], '%m/%d/%Y %H:%M:%S'),
            data={key: val}))
  return events
