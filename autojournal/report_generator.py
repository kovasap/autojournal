import click
from datetime import datetime
from dateutil import tz
import plotly.graph_objects as go
from typing import Union

from . import credentials
from . import drive_api
from . import calendar_api
from .parsers import cronometer
from . import data_model


METRIC_COLORS = [
    '#673ab7', '#E91E63', '#795548', '#607d8b', '#2196F3'
]


# Map from metric names to other metric names that should be used as labels.
LABEL_METRICS = {
    'Energy (kcal)': ('Food Name', 'Amount'),
    'Fiber (g)': ('Food Name', 'Amount'),
    'asleep': ('description',),
}


def create_plot(data, metrics_to_plot, html_name) -> str:
    # Create figure
    fig = go.Figure()

    def get_points_with_metric(metric: str):
        return [p for p in data if metric in p.data]

    axis_domain_size = 1.0 / len(metrics_to_plot)
    y_axes = {}
    for i, m in enumerate(metrics_to_plot):
        pts = get_points_with_metric(m)
        y_data = [p.data[m] for p in pts]
        fig.add_trace(go.Scatter(
            x=[p.timestamp for p in pts],
            y=y_data,
            name=m,
            text=[', '.join(p.data.get(lm, '') for lm in LABEL_METRICS[m])
                  if m in LABEL_METRICS else str(p.data[m])
                  for p in pts],
            yaxis=f'y{i + 1}',
        ))
        y_axes[f'yaxis{i + 1}'] = dict(
            anchor="x",
            autorange=True,
            domain=[axis_domain_size * i, axis_domain_size * (i + 1)],
            linecolor=METRIC_COLORS[i],
            mirror=True,
            range=[min(y_data), max(y_data)],
            showline=True,
            side="right",
            tickfont={"color": METRIC_COLORS[i]},
            tickmode="auto",
            ticks="",
            title=m,
            titlefont={"color": METRIC_COLORS[i]},
            type="linear",
            zeroline=False
        )

    # style all the traces
    fig.update_traces(
        hoverinfo="name+x+text",
        line=dict(width=1.5, shape='spline'),
        marker={"size": 8},
        mode="lines+markers",
        showlegend=False
    )

    # Update axes
    fig.update_layout(
        xaxis=dict(
            autorange=True,
            range=[data[0].timestamp, data[-1].timestamp],
            rangeslider=dict(
                autorange=True,
                range=[data[0].timestamp, data[-1].timestamp],
            ),
            type="date"
        ),
        **y_axes
    )

    # Update layout
    fig.update_layout(
        dragmode="zoom",
        hovermode="closest",
        legend=dict(traceorder="reversed"),
        height=600,
        template="plotly_white",
        margin=dict(
            t=100,
            b=100
        ),
    )

    fig.write_html(html_name)


def parse_date(s: Union[str, datetime]) -> datetime:
    if isinstance(s, datetime):
        return s
    for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=DEFAULT_TIMEZONE)
        except ValueError:
            pass
    raise ValueError('no valid date format found')


DEFAULT_TIMEZONE = tz.gettz('PST')


@click.command()
@click.option('--start_date', default='2000-01-01')
@click.option('--end_date', default=datetime.now().replace(tzinfo=DEFAULT_TIMEZONE))
def main(start_date: str, end_date: str):
    start_date, end_date = parse_date(start_date), parse_date(end_date)


    creds = credentials.get_credentials([
        # If modifying scopes, delete the file token.pickle.
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/photoslibrary.readonly'])
    drive_api_instance = drive_api.DriveApi(creds)
    cal_api_instance = calendar_api.CalendarApi(creds)

    spreadsheet_data = drive_api_instance.read_all_spreadsheet_data(
        'activitywatch-data', only={'servings.csv', 'notes.csv'})

    sleep_data = cal_api_instance.get_events(
        cal_api_instance.get_calendar_id('Sleep'))
    event_data = cronometer.parse_nutrition(spreadsheet_data)

    for e in sleep_data:
        event_data.append(data_model.Event(
            timestamp=datetime.fromisoformat(e['start']['dateTime']),
            data={'description': e.get('description', ''), 'asleep': 1},
        ))
        event_data.append(data_model.Event(
            timestamp=datetime.fromisoformat(e['end']['dateTime']),
            data={'description': e.get('description', ''), 'asleep': 0},
        ))
    # Filter events by date
    event_data = [e for e in event_data if start_date < e.timestamp < end_date]
    event_data = sorted(event_data, key=lambda e: e.timestamp)

    create_plot(event_data, ['Energy (kcal)', 'Fiber (g)', 'asleep'],
                'out.html')


if __name__ == '__main__':
    main()
