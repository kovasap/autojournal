from datetime import datetime
from typing import List

from ..data_model import Event


def parse_momentodb(data_by_fname) -> List[Event]:
  events = []
  for fname, data in data_by_fname.items():
    if not fname.startswith('n-'):
      continue
    for line in data:
      print(line)
      events.append(Event(
          summary=f'{line["value"]} {line["tracker"]}',
          description=str(line),
          timestamp=datetime.strptime(
              line['start'], '%Y-%m-%dT%H:%M:%S.%f'),
          data={line['tracker']: line['value']}))
  return events
