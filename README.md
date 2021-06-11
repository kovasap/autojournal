# AutoJournal

Overarching goal is to provide a system that summarizes life events
automatically, to augment your memory and allow for further analysis if
desired.

## Getting Started

Run:

```
poetry install
```

Then, run:

```
source $(poetry env info --path)/bin/activate
```

to get into the poetry virtualenv to run scripts.

## Frontend Idea

Create a histogram-timeline using
[d3js](https://www.d3-graph-gallery.com/graph/density_basic.html) that all data
gets plotted on.  Have checkboxes to turn on/off data series.  Idea here is to
plot lots of stuff (keystrokes, temperature, heartrate, stock market, etc.) and
have a each way to check on whatever.  Could use [Joy
plot](http://datavizcatalogue.com/blog/area-graphs/) for this.

Some ideas to explore in this space:

 - [patternfly-timeline](https://github.com/patternfly/patternfly-timeline)
 - [d3 line chart with zoom](https://www.d3-graph-gallery.com/graph/line_brushZoom.html)
 - **[plotly stacked range slider chart](https://plotly.com/python/range-slider/)**
 - [d3 ridgeline/joy plot](https://www.d3-graph-gallery.com/graph/ridgeline_basic.html)
 - [d3 pannable chart](https://observablehq.com/@d3/pannable-chart)

For plotting GPS logs:

 - [Google maps python API](https://github.com/googlemaps/google-maps-services-python)
 - [QGIS open source mapping project](https://qgis.org/en/site/about/index.html)
 - **[folium](https://github.com/python-visualization/folium)**

## Google Photos to Calendar Syncer

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

Add this command to run every hour, assuming you installed this script
using the `photos_calendar_sync` virtualenv.

```
0 * * * * cd /home/kovas/photos_calendar_sync && /home/kovas/.virtualenvs/photos_calendar_sync/bin/python photos_calendar_syncer.py --update all >> photos_calendar_sync_cron.log
```

Check out this article for ideas about other kinds of tracking on Google Calendar: https://towardsdatascience.com/andorid-activity-1ecc454c636c

## Google Cloud

Set up a free tier compute engine instance.  Then do
https://cloud.google.com/compute/docs/gcloud-compute#default-properties and you
should be able to ssh into the instance with:

```
gcloud compute ssh kovas
```

## Other Inspiration

https://karpathy.github.io/2014/08/03/quantifying-productivity/
