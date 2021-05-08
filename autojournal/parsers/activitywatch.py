from datetime import datetime, timedelta
import sqlite3
from typing import Dict, List, Any

from ..data_model import Event


def get_events(db_file: str) -> List[Event]:
    con = sqlite3.connect(db_file)
    cur = con.cursor()

    buckets_by_id = {}
    hostnames_by_id = {}
    for bid, name, hostname in cur.execute(
            'SELECT key, id, hostname FROM bucketmodel'):
        buckets_by_id[bid] = name
        hostnames_by_id[bid] = hostname


    events = []
    for bid, timestamp, duration, datastr in cur.execute(
            'SELECT bucket_id, timestamp, duration, datastr FROM eventmodel'):
        parsed_time = datetime.fromisoformat(timestamp)
        data = eval(datastr)
        start_event = Event(
            timestamp=parsed_time,
            data=dict(device=hostnames_by_id[bid]),
        )
        end_event = Event(
            timestamp=parsed_time + timedelta(seconds=duration),
            data=dict(device=hostnames_by_id[bid]),
        )
        if buckets_by_id[bid].startswith('aw-watcher-afk'):
            # Ignore all statuses other than "not-afk"
            if data['status'] != 'not-afk':
                continue
            start_event.data['using'] = 1
            end_event.data['using'] = 0
        elif buckets_by_id[bid].startswith('aw-watcher-window'):
            start_event.data.update(data)
            end_event.data.update(data)
        events.append(start_event)
        events.append(end_event)

    return events
