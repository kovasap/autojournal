from __future__ import print_function
import datetime
import pprint
import pickle
import os.path
from httplib2 import Http
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly',
          'https://www.googleapis.com/auth/photoslibrary.readonly']


def main():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Get credentials from
            # https://developers.google.com/calendar/quickstart/python#step_1_turn_on_the
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # pprint.pprint(creds.__dict__)
    photo_service = build('photoslibrary', 'v1', credentials=creds)
    cal_service = build('calendar', 'v3', credentials=creds)

    # Call the Photos API
    results = photo_service.albums().list(
        pageSize=10, fields="nextPageToken,albums(id,title)").execute()
    items = results.get('albums', [])
    if not items:
        print('No albums found.')
    else:
        print('Albums:')
        for item in items:
            print('{0} ({1})'.format(item['title'].encode('utf8'), item['id']))

    # Call the Calendar API
    print('Getting the upcoming 10 events')
    events_result = cal_service.events().list(
        calendarId='mgf5ho48h2a65185npg79tuvqc@group.calendar.google.com',
        timeMin=(datetime.datetime.utcnow() - datetime.timedelta(days=7)
                 ).isoformat() + 'Z',  # 'Z' indicates UTC time
        maxResults=10, singleEvents=True,
        orderBy='startTime').execute()
    events = events_result.get('items', [])
    # pprint.pprint(cal_service.calendarList().list().execute())
    if not events:
        print('No upcoming events found.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(start, event['summary'])


if __name__ == '__main__':
    main()
