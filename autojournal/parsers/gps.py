from datetime import datetime
from typing import Dict, List, Any

from ..data_model import Event


def parse_gps(data_by_fname) -> List[Event]:
    events = []
    for fname, data in data_by_fname.items():
        if not fname.endswith('.zip'):
            continue
        for line in data:
            events.append(Event(
                timestamp=datetime.fromisoformat(
                    line['time'].replace('Z', '+00:00')),
                data=line))
    return events
