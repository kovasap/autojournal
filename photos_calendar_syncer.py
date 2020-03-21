from functools import reduce
from datetime import timedelta, datetime
from dateutil import tz

import credentials
import photos_api
import selfspy_api
import calendar_api
import drive_api
import app_usage_output_parser
import maps_data_parser
import utils


def photos_to_event(photos: photos_api.mediaItem,
                    event_length_mins: int = 15) -> calendar_api.Event:
    return calendar_api.Event(
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


def main():
    creds = credentials.get_credentials([
        # If modifying scopes, delete the file token.pickle.
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/photoslibrary.readonly'])

    cal_api_instance = calendar_api.CalendarApi(creds)

    add_events_args = dict(
        dry_run=False,
        start_datetime=datetime(
            month=3, day=5, year=2020, tzinfo=tz.gettz('PST')),
    )

    # calendars = ['Food', 'Laptop Activity', 'Android Activity',
    #              'Locations and Travel']
    # for c in calendars:
    #     cal_api_instance.clear_calendar(c)

    # # Add food events from Google Photos
    # photos_api_instance = photos_api.PhotosApi(creds)
    # food_pictures = photos_api_instance.get_album_contents(
    #     photos_api_instance.get_album_id('Food!'))
    # # Collapse multiple food pictures taken within 30 mins to one food event.
    # grouped_photos = utils.split_on_gaps(
    #     food_pictures, threshold=timedelta(minutes=30),
    #     key=lambda photo: datetime.fromisoformat(
    #         photo['mediaMetadata']['creationTime'].rstrip('Z')))
    # food_events = [photos_to_event(photos) for photos in grouped_photos]
    # cal_api_instance.add_events('Food', food_events)

    # Add laptop activity from selfspy
    # laptop_events = selfspy_api.get_selfspy_usage_events()
    # cal_api_instance.add_events('Laptop Activity', laptop_events,
    #                             **add_events_args)

    # Add phone events from Google Drive
    drive_api_instance = drive_api.DriveApi(creds)
    android_activity_files = drive_api_instance.read_files(
        directory='android-activity-logs')
    android_events = app_usage_output_parser.create_events(
        # Combine all "Activity" csvs in directory into single datastream.
        reduce(list.__add__, [v for k, v in android_activity_files.items()
                              if 'usage_events' in k]))
    cal_api_instance.add_events('Android Activity', android_events,
                                **add_events_args)

    # Add locations and travel from Google Maps Location History.
    # Currently, we get the files with this data from Google Drive.
    # drive_api_instance = drive_api.DriveApi(creds)
    # maps_location_history_files = drive_api_instance.read_files(
    #     directory='maps-location-history')
    # location_events = maps_data_parser.parse_semantic_location_history(
    #     maps_location_history_files)
    # cal_api_instance.add_events('Locations and Travel', location_events,
    #                             **add_events_args)


if __name__ == '__main__':
    main()
