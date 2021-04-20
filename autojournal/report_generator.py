import click
import plotly.graph_objects as go

from . import credentials
from . import drive_api
from .parsers import cronometer


METRIC_COLORS = [
    '#673ab7', '#E91E63', '#795548', '#607d8b', '#2196F3'
]


# Map from metric names to other metric names that should be used as labels.
LABEL_METRICS = {
    'Energy (kcal)': ('Food Name', 'Amount'),
    'Fiber (g)': ('Food Name', 'Amount'),
}


def create_plot(data, metrics_to_plot, html_name) -> str:
    # Create figure
    fig = go.Figure()

    x = [point.timestamp for point in data]
    for i, m in enumerate(metrics_to_plot):
        fig.add_trace(go.Scatter(
            x=x,
            y=[point.data[m] for point in data],
            name=m,
            text=[', '.join(point.data[lm] for lm in LABEL_METRICS[m])
                  if m in LABEL_METRICS else str(point.data[m])
                  for point in data],
            yaxis='y' + (str(i) if i != 0 else ''),
        ))

    # style all the traces
    fig.update_traces(
        hoverinfo="name+x+text",
        line=dict(width=1.5, shape='spline'),
        marker={"size": 8},
        mode="lines+markers",
        showlegend=False
    )

    # Update axes
    axis_domain_size = 1 / len(metrics_to_plot)
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
        **{'yaxis' + (str(i) if i != 0 else ''): dict(
                anchor="x",
                autorange=True,
                domain=[axis_domain_size * i, axis_domain_size * (i + 1)],
                linecolor=METRIC_COLORS[i],
                mirror=True,
                range=[min(point.data[m] for point in data),
                       max(point.data[m] for point in data)],
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
            for i, m in enumerate(metrics_to_plot)
        }
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


@click.command()
def main():
    creds = credentials.get_credentials([
        # If modifying scopes, delete the file token.pickle.
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/photoslibrary.readonly'])
    drive_api_instance = drive_api.DriveApi(creds)

    spreadsheet_data = drive_api_instance.read_all_spreadsheet_data(
        'activitywatch-data', only={'servings.csv', 'notes.csv'})

    event_data = cronometer.parse_nutrition(spreadsheet_data)

    create_plot(event_data, ['Energy (kcal)', 'Fiber (g)'], 'out.html')


if __name__ == '__main__':
    main()
