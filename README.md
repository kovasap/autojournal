# AutoJournal

Overarching goal is to provide a system that summarizes life events
automatically, to augment your memory and allow for further analysis if
desired.

## Examples

Autojournal fundamentally moves personal data around between different services.
The most supported place for data to end up is Google calendar.
Here are some examples of what that looks like.
Each block on the calendar corresponds to a single "event" that I've tracked. For
sleep, this would be time asleep. For location, this would be time at a specific
location, or time travelling. For computer usage, this would be active time interacting
with a computer (not AFK).

An excellent example of someone else doing exactly what autojournal is trying to do
can be found at https://miguelrochefort.com/blog/calendar/.

Just the location events from a trip I went on:

![travelling](example_location_calendar.png?raw=true "Locations")

All events before the trip, showing usage of multiple different computers, and
sleep:

![computer usage](example_computer_usage_calendar.png?raw=true "All Events")

These were generated with the help of [this blurring
script](https://gist.github.com/IceCreamYou/4f085b180a1608b99cb2).

## Getting Started

Run:

```
# Required for selfspy dependency.
sudo apt-get install python-tk
poetry install
```

Then, run:

```
source $(poetry env info --path)/bin/activate
```

to get into the poetry virtualenv to run scripts.

To run once a day at 10pm, run `crontab -e` and add this snippet (assuming you
cloned autojournal into your home directory ~/):

```
0 22 * * * (cd ~/autojournal; nohup poetry run gcal_aggregator --update all &> ~/autojournal.log &)
```

### Raspberry Pi

Requires additional installs before poetry install:

```
sudo apt-get install python-dev libatlas-base-dev
```

## Nomie with Couchdb

1. Setup couchdb on your machine (for me it's a raspberry pi:
   https://andyfelong.com/2019/07/couchdb-2-1-on-raspberry-pi-raspbian-stretch/,
   https://github.com/jguillod/couchdb-on-raspberry-pi#5-script-for-running-couchdb-on-boot).
1. Follow
   https://github.com/happydata/nomie-docs/blob/master/development/couchdb-setup.md

Checkout this for coding help:
https://colab.research.google.com/drive/1vKOHtu1cLgky6I_4W-aFBqq6e6Hb4qBA

## TODOs

### Better Location Data

Could use ML to judge mode of travel better like these guys:
https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5620731/.

### Emailed Report

Generate a report with the timeline that is already implemented, plus something like https://stackoverflow.com/questions/21604997/how-to-find-significant-correlations-in-a-large-dataset.  Email this regularly.

### Frontend Idea

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

This could generate an HTML report that would be automatically emailed to me
every week.

## GPS Logging

Uses https://gpslogger.app/.  Note to make this work consistently, refer to
https://gpslogger.app/#sometimestheappwillnotlogforlongperiodsoftime.

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

## Cron

Add this command to run every other hour, assuming you cloned this project to `~/autojournal`.

```
0 */2 * * * ~/autojournal/run_gcal_aggregator.bash
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

https://vimeo.com/99571921

https://karpathy.github.io/2014/08/03/quantifying-productivity/
