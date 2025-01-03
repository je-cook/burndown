import os
import requests
import pandas as pd
import dash_bootstrap_components as dbc
from dash import Dash, html, dcc, Input, Output, dash_table
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from datetime import datetime, timezone

# Configure the app
app = Dash(__name__)

DEBUG = True

global_size = 18

app.layout = html.Div(
    style={"padding": "20px", "fontFamily": "Arial, sans-serif"},
    children=[
        html.H1("Issue Burndown Charts", style={"textAlign": "center", "color": "#2c3e50"}),
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
        ),
        dcc.Input(
            id="token",
            type="text",
            placeholder="Optional custom token",
            value="",
            style={"width": "50%", "padding": "10px", "marginBottom": "20px"},
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
        # dcc.Progress(
        #     id='progress-bar',
        #     value=0,  # Initial value of the progress bar
        #     max=100,  # Maximum value of the progress bar
        # ),
        dcc.Store(id="github-data"),  # Store for caching the fetched data
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
)


def process_gitlab_mr(headers, issue, labels):
    is_mr = (
        "gitlab merge request" in labels
        and (issue.get("closed_at", "") or "").startswith("2023-07-07")
        and issue["title"].endswith(("[merged]", "[closed]"))
    )
    if not is_mr:
        return is_mr, None

    response = requests.get(issue["comments_url"], headers=headers)

    comments = response.json()
    if not comments:
        closed_date = None
    for comment in comments:
        if "merged" in comment["body"] or "closed" in comment["body"]:
            closed_date = comment["created_at"]
            break
    else:
        closed_date = None

    return is_mr, closed_date


def fetch_github_data(orgrepo, token):
    issues = []
    page = 1
    while (page < 30) if DEBUG else True:
        headers = {"Authorization": f"token {token}"} if token else {}
        response = requests.get(
            f"https://api.github.com/repos/{orgrepo}/issues?state=all&page={page}",
            headers=headers,
        )
        data = response.json()

        if not data:
            break

        for issue in data:
            labels = [l["name"] for l in issue["labels"]]
            is_mr = (
                "gitlab merge request" in labels
                and (issue.get("closed_at", "") or "").startswith("2023-07-07")
                and issue["title"].endswith(("[merged]", "[closed]"))
            )
            if not is_mr:
                return is_mr, None

            response = requests.get(issue["comments_url"], headers=headers)

            comments = response.json()
            if not comments:
                closed_date = None
            for comment in comments:
                if "merged" in comment["body"] or "closed" in comment["body"]:
                    closed_date = comment["created_at"]
                    break
            else:
                closed_date = None

            issues.append({
                "issue_number": issue["number"],
                "title": issue["title"],
                "created_at": issue["created_at"],
                "closed_at": closed_date if is_mr else issue.get("closed_at", None),
                "is_pr": "pull_request" in issue or is_mr,
            })

        page += 1

    return pd.DataFrame(issues)


@app.callback(
    Output("github-data", "data"),
    Input("submit-button", "n_clicks"),
    Input("orgrepo", "value"),
    Input("token", "value"),
)
def update_data(n_clicks, orgrepo, token):
    if n_clicks == 0 or orgrepo == "":
        return None

    df = fetch_github_data(orgrepo, token)
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["closed_at"] = pd.to_datetime(df["closed_at"])
    df["end_date"] = df["closed_at"].fillna(datetime.now())
    df["end_date"] = pd.to_datetime(df["end_date"], utc=True)
    df["months"] = (df["end_date"] - df["created_at"]).dt.days / 30

    return df.to_dict("records")  # Store the data as a dictionary


@app.callback(Output("content", "children"), Input("tabs", "value"), Input("github-data", "data"))
def update_content(tab, data):
    if data is None:
        return []

    df = pd.DataFrame(data)

    if tab == "p1":
        # Plot 1
        fig1 = px.line(
            df,
            x="months",
            y="issue_number",
            color="months",
            title="Months to complete vs Time span that issue covered",
        )
        return dcc.Graph(figure=fig1)

    elif tab == "p2":
        # Plot 2
        fig2 = px.line(
            df,
            x="issue_number",
            y="months",
            color="months",
            title="Issues completed over time",
        )
        return dcc.Graph(figure=fig2)
    elif tab == "p3":
        fig3 = px.scatter(
            df,
            x="end_date",
            y="months",
            color="months",
            title="Issue number vs Time taken to complete",
        )
        return dcc.Graph(figure=fig3)

    elif tab == "p4":
        fig4 = px.scatter(
            df,
            x="end_date",
            y="issue_number",
            color="months",
            title="Issue close date vs Issue number",
        )

        return dcc.Graph(figure=fig4)

    elif tab == "p5":
        fig5 = px.histogram(
            df,
            x="months",
            log_y=True,
            title="Binned distribution of time taken to complete issues",
        )

        return dcc.Graph(figure=fig5)

    elif tab == "p6":
        df["start"] = pd.to_datetime(df["created_at"])
        df["end"] = pd.to_datetime(df["end_date"], format="mixed")
        days = pd.date_range(
            start=df["start"].min(),
            end=datetime.now().replace(tzinfo=timezone.utc),
            freq="D",
        )
        total_issues = [
            ((df["start"] < day) & (df["end"] > day) & ~df["is_pr"]).sum() for day in days
        ]
        total_pr = [((df["start"] < day) & (df["end"] > day) & df["is_pr"]).sum() for day in days]
        df2 = pd.DataFrame({
            "days": days,
            "issues": total_issues,
            "pull requests": total_pr,
        })

        fig6 = make_subplots(specs=[[{"secondary_y": True}]])
        fig6 = fig6.add_trace(
            go.Scatter(x=df2["days"], y=df2["issues"], name="Issues", mode="lines")
        )
        fig6 = fig6.add_trace(
            go.Scatter(x=df2["days"], y=df2["pull requests"], name="Pull Requests", mode="lines"),
            secondary_y=True,
        )
        # Add titles and labels
        fig6.update_layout(
            title_text="Total issues open at any given time",
            xaxis_title="days",
            yaxis_title="Issues",
            yaxis2_title="Pull Requests",
        )
        # fig6.update_layout(yaxis_title='total open')

        return dcc.Graph(figure=fig6)

    elif tab == "p7":
        df["Day"] = pd.to_datetime(df["end_date"], format="mixed").dt.date
        stats = df.groupby("Day").size().reset_index(name="Count")
        fig7 = px.bar(stats, x="Day", y="Count", title="Issues closed per day")
        return dcc.Graph(figure=fig7)

    elif tab == "table-tab":
        # Data Table
        table = dash_table.DataTable(
            data=df.to_dict("records"),
            columns=[{"name": i, "id": i} for i in df.columns],
            page_size=10,
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left"},
        )
        return table


if __name__ == "__main__":
    app.run_server(debug=True, port=8051)
