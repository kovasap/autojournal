#!/bin/python3

from functools import reduce
from datetime import timedelta, datetime, date
from dateutil import tz
import argparse

from . import credentials
from . import photos_api
from . import selfspy_api
from . import calendar_api
from . import drive_api
from . import app_usage_output_parser
from . import maps_data_parser
from . import utils
from .parsers import gps, nomie, momentodb


def photos_to_event(
    photos: photos_api.mediaItem,
    event_length_mins: int = 15) -> calendar_api.CalendarEvent:
  return calendar_api.CalendarEvent(
      start=utils.utc_to_timezone(
          photos[0]['mediaMetadata']['creationTime']),
      end=utils.utc_to_timezone(photos[-1]['mediaMetadata']['creationTime'],
                                additional_offset_mins=event_length_mins),
      description=reduce(
          lambda s1, s2: s1 + s2,
          [f'Notes: {photo.get("description", "")}\n\n'
           f'{photo["productUrl"]}\n\n\n' for photo in photos]),
      summary='Ate food',
  )


calendars = {
    'laptop': 'Laptop Activity',
    'desktop': 'Desktop Activity',
    'phone': 'Android Activity',
    'maps': 'Locations and Travel',
    'food': 'Food',
    'nomie': 'Nomie',
    'momento': 'Momento',
}


argparser = argparse.ArgumentParser(
    description='Upload data from multiple sources to Google Calendar')
argparser.add_argument(
    '--clear', nargs='*', choices=list(calendars.keys()) + ['all'],
    default=[],
    help='Calendars to REMOVE ALL EVENTS from.')
argparser.add_argument(
    '--update', nargs='*', choices=list(calendars.keys()) + ['all'],
    default=[],
    help='Calendars to update.')
argparser.add_argument(
    '--dry_run', action='store_true', default=False,
    help='Will print what would be added to the calendar(s) without actually '
         'updating them.')
argparser.add_argument(
    '--start_date', type=str,
    help='Date (inclusive) at which to start modifying the calendar(s) in '
         'format mm/dd/yyyy.')
argparser.add_argument(
    '--end_date', type=str,
    help='Date (inclusive) at which to stop modifying the calendar(s) in '
         'format mm/dd/yyyy.')
args = argparser.parse_args()


def main():
  creds = credentials.get_credentials([
      # If modifying scopes, delete the file token.pickle.
      'https://www.googleapis.com/auth/drive.readonly',
      'https://www.googleapis.com/auth/calendar',
      'https://www.googleapis.com/auth/photoslibrary.readonly'])

  cal_api_instance = calendar_api.CalendarApi(creds)
  drive_api_instance = drive_api.DriveApi(creds)

  cal_mod_args = dict(dry_run=args.dry_run)
  if args.start_date:
    cal_mod_args['start_datetime'] = datetime.strptime(
        args.start_date, '%m/%d/%Y').replace(tzinfo=tz.gettz('PST'))
  if args.end_date:
    cal_mod_args['end_datetime'] = datetime.strptime(
        args.end_date, '%m/%d/%Y').replace(tzinfo=tz.gettz('PST'))

  # Clear events from calendars.
  if 'all' in args.clear:
    args.clear = list(calendars.keys())
  for c in args.clear:
    cal_api_instance.clear_calendar(calendars[c], **cal_mod_args)

  # Add food events from Google Photos.
  if 'all' in args.update or 'food' in args.update:
    photos_api_instance = photos_api.PhotosApi(creds)
    food_pictures = photos_api_instance.get_album_contents(
        photos_api_instance.get_album_id('Food!'))
    # Collapse multiple food pictures taken within 30 mins to one food
    # event.
    grouped_photos = utils.split_on_gaps(
        food_pictures, threshold=timedelta(minutes=30),
        key=lambda photo: datetime.fromisoformat(
            photo['mediaMetadata']['creationTime'].rstrip('Z')))
    food_events = [photos_to_event(photos) for photos in grouped_photos]
    cal_api_instance.add_events(
        calendars['food'], food_events, **cal_mod_args)

  # Add laptop activity from selfspy
  if 'all' in args.update or 'laptop' in args.update:
    drive_api_instance.download_file_to_disk(
        'selfspy-laptop', 'selfspy.sqlite', 'laptop_selfspy.sqlite')
    laptop_events = selfspy_api.get_selfspy_usage_events(
        db_name='laptop_selfspy.sqlite')
    cal_api_instance.add_events(
        calendars['laptop'], laptop_events,
        **cal_mod_args)

  # Add desktop activity from selfspy db stored in Google Drive
  if 'all' in args.update or 'desktop' in args.update:
    drive_api_instance.download_file_to_disk(
        'selfspy', 'selfspy.sqlite', 'desktop_selfspy.sqlite')
    desktop_events = selfspy_api.get_selfspy_usage_events(
        db_name='desktop_selfspy.sqlite')
    cal_api_instance.add_events(calendars['desktop'], desktop_events,
                                **cal_mod_args)

  # Add phone events from phone usage csvs stored in Google Drive
  if 'all' in args.update or 'phone' in args.update:
    android_activity_files = drive_api_instance.read_files(
        directory='android-activity-logs')
    android_events = app_usage_output_parser.create_events(
        # Combine all "Activity" csvs in directory into single datastream.
        reduce(list.__add__, [v for k, v in android_activity_files.items()
                              if 'usage_events' in k]))
    cal_api_instance.add_events(calendars['phone'], android_events,
                                **cal_mod_args)

  # Add locations and travel.
  if 'all' in args.update or 'maps' in args.update:
    # From Google Takeout files stored in Google Drive.
    # drive_api_instance = drive_api.DriveApi(creds)
    # maps_location_history_files = drive_api_instance.read_files(
    #   directory='maps-location-history')
    # location_events = maps_data_parser.parse_semantic_location_history(
    #   maps_location_history_files)

    # Directly from timeline web "API"
    # location_events = maps_data_parser.make_events_from_kml_data(
    #   '2019-09-01',
    #   # Get data from yesterday only so that the data from today is fully
    #   # populated before we send it off to the calendar.
    #   date.today() - timedelta(days=1))
    # cal_api_instance.add_events(calendars['maps'], location_events,
    #               **cal_mod_args)

    # From GPSLogger files in Google Drive
    spreadsheet_data = drive_api_instance.read_all_spreadsheet_data(
        'GPSLogger for Android')
        # 'GPS TESTING')
    location_events = [
        e.to_calendar_event() for e in gps.parse_gps(spreadsheet_data)]
    cal_api_instance.add_events(calendars['maps'], location_events,
                                **cal_mod_args)

  # Add manually tracked event from Nomie
  if 'all' in args.update or 'nomie' in args.update:
    nomie_data = drive_api_instance.read_all_spreadsheet_data('Nomie')
    nomie_events = [
        e.to_calendar_event() for e in nomie.parse_nomie(nomie_data)]
    cal_api_instance.add_events(calendars['nomie'], nomie_events,
                                **cal_mod_args)

  if 'all' in args.update or 'momento' in args.update:
    momento_data = drive_api_instance.read_all_spreadsheet_data('momentodb')
    momento_events = [
        e.to_calendar_event() for e in momentodb.parse_momentodb(momento_data)]
    cal_api_instance.add_events(calendars['momento'], momento_events,
                                **cal_mod_args)

  # TODO add journal entries

  # TODO add github commits

  # TODO add sleep


if __name__ == '__main__':
  main()
