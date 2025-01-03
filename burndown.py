import os
import requests
import pandas as pd
from dash import Dash, html, dcc, Input, Output, dash_table
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from datetime import datetime, timezone

# Configure the app
app = Dash(__name__)

DEBUG = False

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


def process_gitlab_mr(issue, labels):
    is_mr = (
        "gitlab merge request" in labels
        and (issue.get("closedAt") or "").startswith("2023-07-07")
        and issue["title"].endswith(("[merged]", "[closed]"))
    )

    closed_date = None
    if is_mr:
        for comment in issue["comments"]["nodes"]:
            if "merged" in comment["body"] or "closed" in comment["body"]:
                closed_date = comment["createdAt"]
                break

    return is_mr, closed_date


def fetch_github_data(orgrepo, token):
    issues = []

    query_issue = """
        issues(first: 100, after: $cursorIssues, states: [OPEN, CLOSED]) {
          edges {
            node {
              number
              title
              createdAt
              closedAt
              labels(first: 10) {
                nodes {
                  name
                }
              }
              comments(first: 10) {
                nodes {
                  body
                  createdAt
                }
              }
            }
            cursor
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
    """

    query_pr = """
        pullRequests(first: 100, after: $cursorPRs, states: [OPEN, CLOSED]) {
          edges {
            node {
              number
              title
              createdAt
              closedAt
              labels(first: 10) {
                nodes {
                  name
                }
              }
            }
            cursor
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
    """
    query_start = """
    query($owner: String!, $name: String!,"""
    query_issue_mid = " $cursorIssues: String"
    query_pr_mid = "$cursorPRs: String"
    query_mid = """) {
      repository(owner: $owner, name: $name) {
    """
    query_end = """
      }
    }
    """

    headers = {"Authorization": f"Bearer {token}"} if token else {}

    owner, name = orgrepo.split("/")
    cursor_issues = cursor_prs = None
    has_next_page_issues = has_next_page_prs = True
    page_count = 0
    while (has_next_page_issues or has_next_page_prs) and (
        (DEBUG and page_count < 10) or not DEBUG
    ):
        if has_next_page_prs and has_next_page_issues:
            query = (
                query_start
                + f"{query_issue_mid}, {query_pr_mid}{query_mid}"
                + query_issue
                + query_pr
                + query_end
            )
        elif has_next_page_issues:
            query = query_start + f"{query_issue_mid}{query_mid}" + query_issue + query_end
        elif has_next_page_prs:
            query = query_start + f"{query_pr_mid}{query_mid}" + query_pr + query_end
        variables = {
            "owner": owner,
            "name": name,
            "cursorIssues": cursor_issues,
            "cursorPRs": cursor_prs,
        }
        response = requests.post(
            "https://api.github.com/graphql",
            json={"query": query, "variables": variables},
            headers=headers,
        )
        data = response.json()

        if data.get("errors"):
            print(data.get("errors"))
            has_next_page_prs = has_next_page_issues = False
            continue

        if has_next_page_issues:
            for edge in data["data"]["repository"]["issues"]["edges"]:
                issue = edge["node"]
                labels = [label["name"] for label in issue["labels"]["nodes"]]
                is_mr, closed_date = process_gitlab_mr(issue, labels)

                issues.append({
                    "issue_number": issue["number"],
                    "title": issue["title"],
                    "created_at": issue["createdAt"],
                    "closed_at": closed_date if is_mr else issue.get("closedAt", None),
                    "is_pr": is_mr,
                })

            # Check if there are more pages
            page_info_is = data["data"]["repository"]["issues"]["pageInfo"]
            has_next_page_issues = page_info_is["hasNextPage"]
            cursor_issues = page_info_is["endCursor"]

        if has_next_page_prs:
            for edge in data["data"]["repository"]["pullRequests"]["edges"]:
                issue = edge["node"]
                labels = [label["name"] for label in issue["labels"]["nodes"]]
                closed_date = issue["closedAt"] if issue["closedAt"] else None
                issues.append({
                    "issue_number": issue["number"],
                    "title": issue["title"],
                    "created_at": issue["createdAt"],
                    "closed_at": closed_date,
                    "is_pr": True,
                })

            # Check if there are more pages
            page_info_pr = data["data"]["repository"]["pullRequests"]["pageInfo"]
            has_next_page_prs = page_info_pr["hasNextPage"]
            cursor_prs = page_info_pr["endCursor"]

        page_count += 1

    return pd.DataFrame(issues)


@app.callback(
    Output("github-data", "data"),
    Input("submit-button", "n_clicks"),
    Input("orgrepo", "value"),
    Input("token", "value"),
)
def update_data(n_clicks, orgrepo, token):
    if n_clicks == 0 or orgrepo == "" or "/" not in orgrepo:
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
    app.run_server(debug=True)
