import os
from datetime import datetime
from dateutil import tz
import pickle
from typing import Union, Iterable, List

import click
import plotly.graph_objects as go
import plotly.express as px

from . import credentials
from . import drive_api
from . import calendar_api
from .parsers import cronometer
from .parsers import cgm
from .parsers import nomie
from .parsers import gps
from .parsers import activitywatch
from .parsers import google_fit
from .data_model import Event

METRIC_COLORS = px.colors.sequential.Plasma

# Map from metric names to other metric names that should be used as labels.
LABEL_METRICS = {
    'Energy (kcal)': ('Food Name', 'Amount'),
    'Fiber (g)': ('Food Name', 'Amount'),
    'asleep': ('description',),
}


# Based on https://plotly.com/python/range-slider/.
def create_plot(data: Iterable[Event], metrics_to_plot: List[str], html_name: str) -> str:
  # Create figure
  fig = go.Figure()

  def get_metric_data(m):
    return [p for p in data if m in p.data]

  metrics_to_data = {
      m: get_metric_data(m) for m in metrics_to_plot if get_metric_data(m)
  }

  # If sleep data is included, display it as colored backgrounds
  if 'asleep' in metrics_to_data:
    asleep_periods = []
    for i, event in enumerate(metrics_to_data['asleep']):
      if event.data['asleep']:
        asleep_periods.append((event.timestamp, ))
      else:
        assert len(asleep_periods[-1]) == 1
        asleep_periods[-1] += (event.timestamp, )
    if len(asleep_periods[-1]) == 1:
      asleep_periods.pop(-1)
    fig.update_layout(
        shapes=[
            dict(
                fillcolor="rgba(63, 81, 181, 0.2)",
                line={"width": 0},
                type="rect",
                x0=x0,
                x1=x1,
                xref="x",
                y0=0,
                y1=1.0,
                yref="paper"
            )
            for x0, x1 in asleep_periods
        ]
    )
    del metrics_to_data['asleep']

  axis_domain_size = 1.0 / len(metrics_to_data)
  y_axes = {}
  for i, (m, pts) in enumerate(metrics_to_data.items()):
    print(m)
    print(pts[0])
    y_data = [p.data[m] for p in pts]
    y_str = '' if i == 0 else str(i + 1)
    fig.add_trace(
        go.Scatter(
            x=[p.timestamp for p in pts],
            y=y_data,
            name=m,
            text=[
                ', '.join(p.data.get(lm, '') for lm in LABEL_METRICS[m])
                if m in LABEL_METRICS else str(p.data[m]) for p in pts
            ],
            yaxis=f'y{y_str}',
        ))
    y_axes[f'yaxis{y_str}'] = dict(
        anchor='x',
        autorange=True,
        domain=[axis_domain_size * i, axis_domain_size * (i + 1)],
        linecolor=METRIC_COLORS[i],
        mirror=True,
        range=[min(y_data), max(y_data)],
        showline=True,
        side='right',
        tickfont={'color': METRIC_COLORS[i]},
        tickmode='auto',
        ticks='',
        title=m,
        titlefont={'color': METRIC_COLORS[i]},
        type='linear',
        zeroline=False)

  # style all the traces
  fig.update_traces(
      hoverinfo='name+x+text',
      # https://plotly.com/python/line-charts/
      line=dict(width=1.5, shape='hv'),
      marker={'size': 8},
      mode='lines+markers',
      showlegend=False)

  # Update axes
  fig.update_layout(xaxis=dict(
      autorange=True,
      range=[data[0].timestamp, data[-1].timestamp],
      rangeslider=dict(
          autorange=True,
          range=[data[0].timestamp, data[-1].timestamp],
      ),
      type='date'),
      **y_axes)

  # Update layout
  fig.update_layout(
      title='Time',
      legend_title='Legend',
      dragmode='zoom',
      hovermode='closest',
      legend=dict(traceorder='reversed'),
      height=1100,
      template='plotly_white',
      margin=dict(t=50, b=50),
  )

  fig.write_html(html_name)


def parse_date(s: Union[str, datetime]) -> datetime:
  if isinstance(s, datetime):
    return s
  for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%m/%d/%Y'):
    try:
      return datetime.strptime(s, fmt).replace(tzinfo=DEFAULT_TIMEZONE)
    except ValueError:
      pass
  raise ValueError('no valid date format found')


DEFAULT_TIMEZONE = tz.gettz('PST')


@click.command()
@click.option('--start_date', default='2000-01-01')
@click.option('--end_date',
              default=datetime.now().replace(tzinfo=DEFAULT_TIMEZONE))
@click.option('--use_cache/--no_cache', default=False)
def main(start_date: str, end_date: str, use_cache: bool):
  start_date, end_date = parse_date(start_date), parse_date(end_date)

  if use_cache:
    with open('report_data_cache.pickle', 'rb') as f:
      event_data = pickle.load(f)
  else:
    creds = credentials.get_credentials([
        # If modifying scopes, delete the file token.pickle.
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/photoslibrary.readonly'
    ])
    drive_api_instance = drive_api.DriveApi(creds)
    cal_api_instance = calendar_api.CalendarApi(creds)

    event_data = []
    spreadsheet_data = {}
    sleep_data = cal_api_instance.get_events(
        cal_api_instance.get_calendar_id('Sleep'))
    for e in sleep_data:
        event_data.append(Event(
            summary='',
            description='',
            timestamp=datetime.fromisoformat(e['start']['dateTime']),
            data={'description': e.get('description', ''), 'asleep': 1},
        ))
        event_data.append(Event(
            summary='',
            description='',
            timestamp=datetime.fromisoformat(e['end']['dateTime']),
            data={'description': e.get('description', ''), 'asleep': 0},
        ))
    spreadsheet_data.update(drive_api_instance.read_all_spreadsheet_data(
        'cronometer'))
    event_data += cronometer.parse_nutrition(
        spreadsheet_data, daily_cumulative=True)
    spreadsheet_data.update(drive_api_instance.read_all_spreadsheet_data(
        'medical-records'))
    event_data += cgm.parse_cgm(spreadsheet_data)
    event_data += google_fit.parse_sessions(
        drive_api_instance, 'google-fit-sessions')
    # event_data += nomie.parse_nomie(spreadsheet_data)
    # spreadsheet_data.update(drive_api_instance.read_all_spreadsheet_data(
    #     'GPSLogger for Android'))
    # event_data += gps.parse_gps(spreadsheet_data)
    # event_data += activitywatch.get_events(
    #     os.path.expanduser(
    #         '~/.local/share/activitywatch/aw-server/peewee-sqlite.v2.db'))
    # for file_lines in drive_api_instance.read_files(
    #     'activitywatch-phone-data').values():
    #   event_data += activitywatch.get_events_from_json('\n'.join(file_lines))

    # If events don't have a timezone, assume DEFAULT_TIMEZONE.
    # Then, shift all times to the DEFAULT_TIMEZONE.
    for e in event_data:
      if e.timestamp.tzinfo is None:
        e.timestamp = e.timestamp.replace(tzinfo=DEFAULT_TIMEZONE)
      e.timestamp = e.timestamp.astimezone(tz=DEFAULT_TIMEZONE)

  with open('report_data_cache.pickle', 'wb') as f:
    pickle.dump(event_data, f)

  # Filter events by date
  event_data = [e for e in event_data if start_date < e.timestamp < end_date]
  event_data = sorted(event_data, key=lambda e: e.timestamp)

  create_plot(event_data, [
      'Energy (kcal)', 'Fiber (g)', 'asleep', 'Historic Glucose mg/dL',
      'weight', 'speed', 'using_laptop', 'using_phone',
      'com.google.calories.expended'
  ], 'out.html')

  # TODO Rank activities by time spent in them here.


if __name__ == '__main__':
  main()
