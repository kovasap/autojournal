from datetime import datetime
from typing import Dict, List, Any

from ..data_model import Event


def parse_cgm(data_by_fname) -> List[Event]:
    events = []
    for fname, data in data_by_fname.items():
        if 'glucose' not in fname:
            continue
        for line in data:
            events.append(Event(
                timestamp=datetime.strptime(
                    line['Device Timestamp'], '%m-%d-%Y %I:%M %p'),
                data=line))
    return events
