import credentials
import photos_api
import selfspy_api
import calendar_api
import utils


def photo_to_event(photo: photos_api.mediaItem,
                   event_length_mins: int = 15) -> calendar_api.Event:
    return calendar_api.Event(
        start=utils.utc_to_timezone(photo['mediaMetadata']['creationTime']),
        end=utils.utc_to_timezone(photo['mediaMetadata']['creationTime'],
                                  additional_offset_mins=event_length_mins),
        description=f'Notes: {photo.get("description", "")}\n\n'
                    f'{photo["productUrl"]}',
        summary='Ate food',
    )


def main():
    creds = credentials.get_credentials([
        # If modifying scopes, delete the file token.pickle.
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/photoslibrary.readonly'])

    cal_api_instance = calendar_api.CalendarApi(creds)

    # Add food events from Google Photos
    photos_api_instance = photos_api.PhotosApi(creds)
    food_pictures = photos_api_instance.get_album_contents(
        photos_api_instance.get_album_id('Food!'))
    food_events = [photo_to_event(photo) for photo in food_pictures]
    food_calendar_id = cal_api_instance.get_calendar_id('Food')
    # Filter out all food items that have already been added to the calendar.
    existing_events = cal_api_instance.get_events(food_calendar_id)
    new_food_events = list(filter(
        lambda query: all(not utils.is_subset(ref, query)
                          for ref in existing_events),
        food_events))
    print(f'Adding {len(new_food_events)} new food events...')
    cal_api_instance.add_events(food_calendar_id, new_food_events)

    # Add laptop activity from selfspy
    laptop_events = selfspy_api.get_selfspy_usage_events()
    laptop_calendar_id = cal_api_instance.get_calendar_id('Laptop Activity')
    print(f'Adding {len(laptop_events)} laptop activity events...')
    cal_api_instance.add_events(laptop_calendar_id, laptop_events)


if __name__ == '__main__':
    main()
