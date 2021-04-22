from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any

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


def _get_data_for_day(csv_data):
    data_by_day = defaultdict(list)
    for line in csv_data:
        data_by_day[line['Day']].append(line)
    return data_by_day


def parse_time(time: str) -> datetime:
    dt = datetime.strptime(time, '%Y-%m-%d %I:%M%p')
    return dt.astimezone(pytz.timezone('America/Los_Angeles'))


def parse_nutrition(data_by_fname, daily_cumulative: bool=True
                    ) -> List[Event]:
    foods_by_day = _get_data_for_day(data_by_fname['servings.csv'])
    notes_by_day = _get_data_for_day(data_by_fname['notes.csv'])

    events = []
    daily_cum_events = []
    for day, foods in foods_by_day.items():
        cur_day_events = []
        foods_iter = iter(f for f in foods if f['Food Name'] != 'Tap Water')
        for note in notes_by_day[day]:
            if not note['Note'].startswith('eat'):
                continue
            note_data = _parse_food_timing_note(note)
            for _ in range(note_data['num_foods']):
                food = next(foods_iter)
                events.append(Event(
                    timestamp=parse_time(f'{day} {note_data["time"]}'),
                    # duration=10 * 60,  # In seconds
                    data=food))
                cur_day_events.append(Event(
                    timestamp=events[-1].timestamp,
                    data={k: sum(e.data.get(k, 0) for e in cur_day_events) + float(v)
                          for k, v in food.items() if is_numeric(v)},
                ))
        # Assume the rest of the foods were eaten at midnight.
        for food in foods_iter:
            events.append(Event(
                timestamp=parse_time(f'{day} 12:00am'),
                # duration=10 * 60,  # In seconds
                data=food))
            cur_day_events.append(Event(
                timestamp=events[-1].timestamp,
                data={k: sum(e.data.get(k, 0) for e in cur_day_events) + float(v)
                      for k, v in food.items() if is_numeric(v)},
            ))
        daily_cum_events += cur_day_events

    return daily_cum_events if daily_cumulative else events


def parse_biometrics(data_by_fname) -> List[Event]:
    pass
