from datetime import datetime
from typing import Dict, List, Any

from ..data_model import Event


def parse_nomie(data_by_fname) -> List[Event]:
    events = []
    for fname, data in data_by_fname.items():
        if not fname.startswith('n-'):
            continue
        for line in data:
            events.append(Event(
                timestamp=datetime.strptime(
                    line['start'], '%Y-%m-%dT%H:%M:%S.%f'),
                data={line['tracker']: line['value']}))
    return events
