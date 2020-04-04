# Google Photos to Calendar Syncer

When run, will make a calendar entry for every photo that exists in a given
album.

Check out https://github.com/ActivityWatch/activitywatch as a potential data
source.

## Cron

Add this command to run every day at 11am, assuming you installed this script
using the `photos_calendar_sync` virtualenv.

```
0 11 * * * cd /home/kovas/photos_calendar_sync && /home/kovas/.virtualenvs/photos_calendar_sync/bin/python photos_calendar_syncer.py --update all >> photos_calendar_sync_cron.log
```

Check out this article for ideas about other kinds of tracking on Google Calendar: https://towardsdatascience.com/andorid-activity-1ecc454c636c
