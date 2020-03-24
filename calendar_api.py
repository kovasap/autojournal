from typing import List, Iterable
from datetime import datetime
from googleapiclient.discovery import build
from pprint import pprint, pformat
import json

import utils

# https://developers.google.com/calendar/v3/reference/events
Event = dict
# https://developers.google.com/calendar/v3/reference/calendarList
CalendarList = dict


class CalendarApi(object):

    def __init__(self, creds):
        self.service = build('calendar', 'v3', credentials=creds)

    def get_events(self, calendar_id: str) -> List[Event]:
        page_token = None
        events = []
        while page_token != '':
            response = self.service.events().list(
                calendarId=calendar_id, pageToken=page_token).execute()
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
        matches = [cal['id'] for cal in self.list_calendars()
                   if cal['summary'] == calendar_name]
        assert len(matches) == 1
        return matches[0]

    def clear_calendar(self, calendar_name: str):
        calendar_id = self.get_calendar_id(calendar_name)
        events = self.get_events(calendar_id)
        print(f'Clearing {len(events)} events from {calendar_name}...')
        for i, e in enumerate(events):
            self.service.events().delete(calendarId=calendar_id,
                                         eventId=e['id']).execute()
            print(i, end='\r')
        print()

    def add_events(self, calendar_name: str,
                   events: Iterable[Event],
                   skip_existing_events: bool = True,
                   dry_run: bool = False,
                   start_datetime: datetime = None):
        if dry_run:
            print('DRY RUN')

        # Filter out events older than the start_datetime.
        events = [e for e in events if (
            start_datetime is None or
            datetime.fromisoformat(e['start']['dateTime']) >= start_datetime)]

        print(f'Adding {len(events)} new events to {calendar_name}...')
        calendar_id = self.get_calendar_id(calendar_name)
        if skip_existing_events:
            def event_key(e):
                return '|'.join([
                    e['description'],
                    # Seconds can be rounded strangely by Google calendar, so
                    # we only compare up to the minute.
                    e['start']['dateTime'][:16], e['end']['dateTime'][:16]])
            existing = {event_key(e) for e in self.get_events(calendar_id)}
            pre_filter_num_events = len(events)
            events = [e for e in events if event_key(e) not in existing]
            print(f'{pre_filter_num_events - len(events)} events were '
                  'screened because they already exist on this calendar.')

        for event in events:
            if dry_run:
                pprint(event)
                print('------------------------------------')
            else:
                response = self.service.events().insert(
                    calendarId=calendar_id, body=event).execute()
                print(f'Added event {pformat(response)}')
