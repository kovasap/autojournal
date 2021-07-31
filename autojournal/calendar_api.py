from typing import List, Iterable, Tuple
from datetime import datetime
from googleapiclient.discovery import build
from pprint import pprint, pformat

# https://developers.google.com/calendar/v3/reference/events
CalendarEvent = dict
# https://developers.google.com/calendar/v3/reference/calendarList
CalendarList = dict

def print_event(e: CalendarEvent) -> str:
  start = datetime.fromisoformat(
      e['start']['dateTime']).strftime('%m/%d/%Y %I:%M%p')
  end = datetime.fromisoformat(
      e['end']['dateTime']).strftime('%m/%d/%Y %I:%M%p')
  print(f'{start} - {end} {e["summary"]}')

EVENT_DESCRIPTION_LENGTH_LIMIT = 8100  # characters


def get_consistant_event_timing(event: CalendarEvent) -> Tuple[str, str]:
  """Get start/end time strings that are consistant from a given event.

    Seconds can be rounded strangely by Google calendar, so we only compare up
    to the minute.
    """
  return (event['start']['dateTime'][:16], event['end']['dateTime'][:16])


def unique_event_key(event: CalendarEvent) -> str:
  """Returns a string that should uniquely identify an event."""
  return '|'.join((event['description'],) + get_consistant_event_timing(event))


def time_started_event_key(event: CalendarEvent) -> str:
  """Returns a string that should uniquely identify an event."""
  return get_consistant_event_timing(event)[0]


class CalendarApi(object):

  def __init__(self, creds):
    self.service = build('calendar', 'v3', credentials=creds)

  def get_events(self, calendar_id: str) -> List[CalendarEvent]:
    page_token = None
    events = []
    while page_token != '':
      response = self.service.events().list(calendarId=calendar_id,
                                            pageToken=page_token).execute()
      events += response.get('items', [])
      page_token = response.get('nextPageToken', '')
    return events

  def list_calendars(self) -> List[CalendarList]:
    calendars = []
    page_token = None
    while page_token != '':
      page_token = '' if not page_token else page_token
      calendar_list = self.service.calendarList().list(
          pageToken=page_token).execute()
      calendars += calendar_list['items']
      page_token = calendar_list.get('nextPageToken', '')
    return calendars

  def get_calendar_id(self, calendar_name: str) -> str:
    matches = [
        cal['id']
        for cal in self.list_calendars()
        if cal['summary'] == calendar_name
    ]
    assert len(matches) == 1
    return matches[0]

  def clear_calendar(self,
                     calendar_name: str,
                     dry_run: bool = False,
                     **filter_args):
    calendar_id = self.get_calendar_id(calendar_name)
    events = filter_events(self.get_events(calendar_id), **filter_args)
    print(f'Clearing {len(events)} events from {calendar_name}...')
    if dry_run:
      print('(DRY RUN)')
      print_events(events)
    else:
      for i, e in enumerate(events):
        self.service.events().delete(calendarId=calendar_id,
                                     eventId=e['id']).execute()
        print(i, end='\r')
      print()

  def add_events(self,
                 calendar_name: str,
                 events: Iterable[CalendarEvent],
                 dry_run: bool = False,
                 **filter_args):
    calendar_id = self.get_calendar_id(calendar_name)
    events = filter_events(events, **filter_args)
    print(f'Adding {len(events)} new events to {calendar_name}...')

    # Find all existing events.  If new events are equal to existing
    # events, skip them.  However, if new events have the same start time
    # as existing events but are otherwise not equal, overwrite the
    # existing event.
    existing_events = self.get_events(calendar_id)
    existing_keys = {unique_event_key(e) for e in existing_events}
    pre_filter_num_events = len(events)
    events = [e for e in events if unique_event_key(e) not in existing_keys]
    print(f'{pre_filter_num_events - len(events)} events were '
          'screened because they already exist on this calendar.')
    print('Removing exising events with same start time...')
    event_start_keys = {time_started_event_key(e) for e in events}
    i = 0
    for e in existing_events:
      if time_started_event_key(e) in event_start_keys:
        self.service.events().delete(calendarId=calendar_id,
                                     eventId=e['id']).execute()
        i += 1
        print(i, end='\r')

    if dry_run:
      print('(DRY RUN)')
      print_events(events)
    else:
      for event in events:
        try:
          response = self.service.events().insert(calendarId=calendar_id,
                                                  body=event).execute()
          print(f'Added event {pformat(response)}')
        except Exception as e:
          print(f'FAILED to add event {pformat(event)}')
          print(f'Failure reason: {repr(e)}')
          raise


def print_events(events):
  for e in events:
    # pprint(e)
    # print('--------------------------------------')
    print_event(e)


def filter_events(events, start_datetime=None, end_datetime=None):
  """Filters out events older than the start_datetime or newer than
    end_datetime."""

  def datetime_selector(event):
    return ((start_datetime is None or datetime.fromisoformat(
        event['start']['dateTime']) >= start_datetime) and
            (end_datetime is None or
             datetime.fromisoformat(event['end']['dateTime']) <= end_datetime))

  return [e for e in events if datetime_selector(e)]
