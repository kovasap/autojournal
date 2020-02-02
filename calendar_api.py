import datetime
from typing import List, Iterable
import functools
from googleapiclient.discovery import build

# https://developers.google.com/calendar/v3/reference/events
Event = dict
# https://developers.google.com/calendar/v3/reference/calendarList
CalendarList = dict


class CalendarApi(object):

    def __init__(self, creds):
        self.service = build('calendar', 'v3', credentials=creds)

    def get_events(self, calendar_id: str) -> List[Event]:
        response = self.service.events().list(calendarId=calendar_id).execute()
        return response.get('items', [])

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

    def add_events(self, calendar_id: str, events: Iterable[Event]):
        for event in events:
            response = self.service.events().insert(
                calendarId=calendar_id, body=event).execute()
            print(f'Added event {response}')
