# Google Photos to Calendar Syncer

When run, will make a calendar entry for every photo that exists in a given
album.

## Cron

Add this command to run every day at 11am, assuming you installed this script
using the `photos_calendar_sync` virtualenv.

```
0 11 * * * /home/kovas/.virtualenvs/photos_calendar_sync/bin/python /home/kovas/photos_calendar_sync/photos_calendar_syncer.py >> /home/kovas/photos_calendar_sync/photos_calendar_sync_cron.log
```
