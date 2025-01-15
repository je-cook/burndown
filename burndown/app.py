from argparse import ArgumentParser
import sys
from datetime import datetime

import pandas as pd
from dash import Dash, Input, Output, State, dash_table, dcc, html

from burndown.figures import (
    figure1,
    figure2,
    figure3,
    figure4,
    figure5,
    figure6,
    figure7,
)

try:
    from waitress import serve

    DEBUG = False
except ImportError:
    DEBUG = True


def parse_args():
    parser = ArgumentParser("Issue Burndown Graphs")

    parser.add_argument("--debug", action="store_true", default=False)
    parser.add_argument("--rest", action="store_true", default=False)
    return parser.parse_args()


class BurndownApp:
    def __init__(self, *, serve: bool = True):
        args = parse_args()
        if args.rest:
            from burndown.rest_api import fetch_github_data
        else:
            from burndown.graphql_api import fetch_github_data
        self.fetcher = fetch_github_data

        self.debug = DEBUG or args.debug

        self.app = self.create_app()

        if serve:
            self.serve()

    def serve(self):
        if self.debug:
            self.app.run_server(debug=self.debug)
        else:
            print("address: http://127.0.0.1:8050")
            serve(self.app.server, host="0.0.0.0", port=8050)

    def create_app(self):
        # Configure the app
        app = Dash(__name__)

        app.layout = html.Div(
            style={"padding": "20px", "fontFamily": "Arial, sans-serif"},
            children=[
                html.H1(
                    "Issue Burndown Charts",
                    style={"textAlign": "center", "color": "#2c3e50"},
                ),
                html.A(
                    "Source code repo",
                    href="https://github.com/je-cook/burndown",
                    target="_blank",
                    style={
                        "display": "block",
                        "textAlign": "center",
                        "marginBottom": "20px",
                        "color": "#2980b9",
                    },
                ),
                html.Br(),
                dcc.Input(
                    id="orgrepo",
                    type="text",
                    placeholder="Enter org/repo e.g. fusion-power-plant-framework/bluemira",
                    value="fusion-power-plant-framework/bluemira",
                    style={"width": "50%", "padding": "10px", "marginBottom": "10px"},
                    debounce=True,
                ),
                dcc.Input(
                    id="token",
                    type="text",
                    placeholder="Optional custom token",
                    value="",
                    style={"width": "50%", "padding": "10px", "marginBottom": "20px"},
                    debounce=True,
                ),
                html.Button(
                    "Submit",
                    id="submit-button",
                    n_clicks=0,
                    style={
                        "width": "50%",
                        "padding": "10px",
                        "backgroundColor": "#3498db",
                        "color": "white",
                        "border": "none",
                        "borderRadius": "5px",
                    },
                ),
                dcc.Loading(
                    id="loading",
                    type="circle",  # You can also use "default" or "square"
                    children=[
                        dcc.Store(
                            id="github-data"
                        ),  # Store for caching the fetched data
                        dcc.Tabs(
                            id="tabs",
                            value="plots-tab",
                            children=[
                                dcc.Tab(label="Plot 1", value="p1"),
                                dcc.Tab(label="Plot 2", value="p2"),
                                dcc.Tab(label="Plot 3", value="p3"),
                                dcc.Tab(label="Plot 4", value="p4"),
                                dcc.Tab(label="Plot 5", value="p5"),
                                dcc.Tab(label="Plot 6", value="p6"),
                                dcc.Tab(label="Plot 7", value="p7"),
                                dcc.Tab(label="Data Table", value="table-tab"),
                            ],
                            style={"marginBottom": "20px"},
                            content_style={"padding": "20px"},
                        ),
                        html.Div(id="content"),
                    ],
                ),
            ],
        )

        @app.callback(
            [Output("github-data", "data"), Output("submit-button", "n_clicks")],
            Input("submit-button", "n_clicks"),
            State("submit-button", "n_clicks"),
            Input("orgrepo", "value"),
            Input("token", "value"),
        )
        def update_data(
            n_clicks: int,
            current_n_clicks: int,
            orgrepo: str,
            token: str,
        ) -> tuple[str, int]:
            if n_clicks == 0 or orgrepo == "" or "/" not in orgrepo:
                return None, 0

            df = self.fetcher(orgrepo, token, debug=self.debug)
            df["created_at"] = pd.to_datetime(df["created_at"])
            df["closed_at"] = pd.to_datetime(df["closed_at"])
            df["end_date"] = df["closed_at"].fillna(datetime.now())
            df["end_date"] = pd.to_datetime(df["end_date"], utc=True)
            df["months"] = (df["end_date"] - df["created_at"]).dt.days / 30

            return df.to_dict("records"), 0

        @app.callback(
            Output("content", "children"),
            Input("tabs", "value"),
            Input("github-data", "data"),
        )
        def update_content(tab, data):
            if data is None:
                return []

            df = pd.DataFrame(data)

            if tab == "p1":
                return dcc.Graph(figure=figure1(df))
            if tab == "p2":
                return dcc.Graph(figure=figure2(df))
            if tab == "p3":
                return dcc.Graph(figure=figure3(df))
            if tab == "p4":
                return dcc.Graph(figure=figure4(df))
            if tab == "p5":
                return dcc.Graph(figure=figure5(df))
            if tab == "p6":
                return dcc.Graph(figure=figure6(df))
            if tab == "p7":
                return dcc.Graph(figure=figure7(df))
            if tab == "table-tab":
                # Data Table
                return dash_table.DataTable(
                    data=df.to_dict("records"),
                    columns=[{"name": i, "id": i} for i in df.columns],
                    page_size=10,
                    style_table={"overflowX": "auto"},
                    style_cell={"textAlign": "left"},
                )
            return []

        return app
