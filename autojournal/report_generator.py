import os
import copy
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


def create_altair_report(
    data: Iterable[Event], metrics_to_plot: List[str], html_name: str,
):
  pass


# Based on https://plotly.com/python/range-slider/.
def create_plotly_report(
    data: Iterable[Event], metrics_to_plot: List[str], html_name: str,
    metric_colors=px.colors.cyclical.mrybm * 2,
    # metric_colors=px.colors.sequential.Electric * 2,
):
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
    # COMMENT THIS OUT TO USE BAR CHARTS TO VISUALIZE SLEEP!
    del metrics_to_data['asleep']

  axis_domain_size = 1.0 / len(metrics_to_data)
  y_axes = {}
  for i, (m, pts) in enumerate(metrics_to_data.items()):
    # print(m)
    # for pt in pts:
    #   print(pt.data['Day'], pt.data['Food Name'], pt.data['Energy (kcal)'])
    y_data = [p.data[m] for p in pts]
    y_str = '' if i == 0 else str(i + 1)

    if m == 'asleep':
      pass
      fig.add_trace(
          go.Bar(x=[p.timestamp for p in pts][:-1],
                 # base=[p.timestamp for p in pts][1:],
                 y=[1 if p.data['asleep'] else 2 for p in pts],
                 yaxis=f'y{y_str}',
                 marker=dict(color=metric_colors[i]),
                 showlegend=False,
                 name=m,
                 hovertemplate='<img src="https://kovasap.github.io/crow.png">'))
    else:
      fig.add_trace(
          go.Scatter(
              x=[p.timestamp for p in pts],
              y=y_data,
              name=m,
              text=[p.description for p in pts],
              yaxis=f'y{y_str}',
              marker=dict(color=metric_colors[i], size=8),
              hoverinfo='name+x+text',
              # https://plotly.com/python/line-charts/
              line=dict(width=1.5, shape='hv'),
              mode='lines+markers',
              showlegend=False,
          ))
    y_axes[f'yaxis{y_str}'] = dict(
        anchor='x',
        autorange=True,
        domain=[axis_domain_size * i, axis_domain_size * (i + 1)],
        linecolor=metric_colors[i],
        mirror=True,
        range=[min(y_data), max(y_data)],
        showline=True,
        side='right',
        tickfont={'color': metric_colors[i]},
        tickmode='auto',
        ticks='',
        title=m,
        titlefont={'color': metric_colors[i]},
        type='linear',
        zeroline=False)

  # style all the traces
  # fig.update_traces(
  #     hoverinfo='name+x+text',
  #     # https://plotly.com/python/line-charts/
  #     line=dict(width=1.5, shape='hv'),
  #     marker={'size': 8},
  #     mode='lines+markers',
  #     showlegend=False)

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
      title='Glucose monitoring data',
      legend_title='Legend',
      dragmode='zoom',
      hovermode='closest',
      legend=dict(traceorder='reversed'),
      height=2000,
      template='plotly_white',
      margin=dict(t=50, b=50),
  )

  with open('autojournal/image_hover.js', 'r') as f:
    fig.write_html(html_name, post_script=''.join(f.readlines()))


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
    print('Done setting up google APIs')

    event_data = []
    spreadsheet_data = {}
    print('Getting sleep data...')
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
    print('Getting Cronometer data...')
    spreadsheet_data.update(drive_api_instance.read_all_spreadsheet_data(
        'cronometer'))
    event_data += cronometer.parse_nutrition(
        spreadsheet_data, daily_cumulative=True)
    print('Getting Glucose data...')
    spreadsheet_data.update(drive_api_instance.read_all_spreadsheet_data(
        '4-21-2021-continuous-glucose-monitoring'))
    event_data += cgm.parse_cgm(spreadsheet_data)
    print('Getting workout data...')
    fit_data = google_fit.parse_sessions(
        drive_api_instance, 'google-fit-sessions')
    for e in fit_data:
      start_event = copy.deepcopy(e)
      event_data.append(start_event)
      end_event = copy.deepcopy(e)
      end_event.data['Burned Calories'] = 0.0
      end_event.timestamp = e.timestamp + e.duration
      event_data.append(end_event)
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
    print('Fixing timestamps...')
    for e in event_data:
      if e.timestamp.tzinfo is None:
        e.timestamp = e.timestamp.replace(tzinfo=DEFAULT_TIMEZONE)
      e.timestamp = e.timestamp.astimezone(tz=DEFAULT_TIMEZONE)

  print('Writing cache file...')
  with open('report_data_cache.pickle', 'wb') as f:
    pickle.dump(event_data, f)

  # Filter events by date
  print('Filtering events to specified date range...')
  event_data = [e for e in event_data if start_date < e.timestamp < end_date]
  event_data = sorted(event_data, key=lambda e: e.timestamp)

  print('Making plot...')
  create_plotly_report(event_data, [
      'Carbs (g)', 'Sugars (g)', 'Fat (g)', 'Fiber (g)',
      'Monounsaturated (g)', 'Polyunsaturated (g)', 'Saturated (g)',
      'Sodium (mg)',
      'Weight (lbs)', 'Burned Calories',
      'Energy (kcal)', 'asleep', 'Historic Glucose mg/dL',
      'weight', 'speed', 'using_laptop', 'using_phone',
  ], 'out.html')

  # TODO Rank activities by time spent in them here.


if __name__ == '__main__':
  main()
