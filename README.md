# Google Photos to Calendar Syncer

When run, will make a calendar entry for every photo that exists in a given
album.

Check out https://github.com/ActivityWatch/activitywatch as a potential data
source.

For long events (e.g. whole day), think about making the event name long with
newlines, so that you get a "graph" in the calendar UI.  For example:

```
Temperature event:
68
68
68
68
68
68
69
70
70
70
70
...
```

For complex events (e.g. selfspy activity tracking), try using a word cloud
type program to extract out representative words to put into the calendar event
summary.

## Analysis TODOs

Calculate total daily calories vs time of first meal.

## Additional Things to Track

Try https://blog.luap.info/how-i-track-my-life.html.

Also try using nomie.app to track activity.

## Cron

Add this command to run every day at 11am, assuming you installed this script
using the `photos_calendar_sync` virtualenv.

```
0 11 * * * cd /home/kovas/photos_calendar_sync && /home/kovas/.virtualenvs/photos_calendar_sync/bin/python photos_calendar_syncer.py --update all >> photos_calendar_sync_cron.log
```

Check out this article for ideas about other kinds of tracking on Google Calendar: https://towardsdatascience.com/andorid-activity-1ecc454c636c
