from datetime import datetime, timezone

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.colors import sample_colorscale
from plotly.subplots import make_subplots


def create_colourbar(marker_dict):
    return go.Scatter(
        x=[None],
        y=[None],
        mode="markers",
        marker=marker_dict,
        name=None,
        hoverinfo="none",
        showlegend=False,
    )


def figure1(df):
    # Plot 1
    fig1 = go.Figure()

    # Add lines for each issue's open and close dates with color based on months
    colours = sample_colorscale(
        "Plasma",
        np.linspace(0, 1, df["issue_number"].max()),
    )
    for _index, row in df.iterrows():
        fig1.add_trace(
            go.Scatter(
                x=[row["months"], row["months"]],
                y=[row["created_at"], row["end_date"]],
                mode="lines",
                line={"color": colours[row["issue_number"] - 1]},
                name=f"Issue {row['issue_number']}",
                showlegend=False,
            ),
        )

    fig1.update_layout(
        xaxis_title="Months",
        yaxis_title="Time span",
        xaxis={"rangeslider": {"visible": True}, "autorange": True},
        yaxis={"autorange": True, "fixedrange": False},
        coloraxis={"colorscale": "Plasma", "colorbar": {"title": "Issue Number"}},
    )

    colourbar_trace = create_colourbar({
        "colorscale": "Plasma",
        "showscale": True,
        "cmin": 1,
        "cmax": df["issue_number"].max(),
        "colorbar": {
            "thickness": 20,
            "outlinewidth": 0,
            "title": "Issue Number",
        },
    })

    fig1.add_trace(colourbar_trace)

    return fig1


def figure2(df):
    # # Plot 2
    fig2 = go.Figure()

    max_duration = df["months"].max()
    min_duration = df["months"].min()

    colours = sample_colorscale(
        "Plasma",
        (df["months"] - min_duration) / (max_duration - min_duration),
    )
    # Add lines for each issue's open and close dates with color based on months
    for no, (_index, row) in enumerate(df.iterrows()):
        fig2.add_trace(
            go.Scatter(
                x=[row["issue_number"], row["issue_number"]],
                y=[row["created_at"], row["end_date"]],
                mode="lines",
                line={"color": colours[no]},
                name=f"Issue {row['issue_number']}",
                showlegend=False,
            ),
        )

    # Update layout
    fig2.update_layout(
        xaxis_title="Issue number",
        yaxis_title="Time taken to close issue",
        xaxis={"rangeslider": {"visible": True}, "autorange": True},
        yaxis={"autorange": True, "fixedrange": False},
        coloraxis={
            "colorbar": {"title": "Duration (Months)"},
            "colorscale": "Plasma",
            "cmin": min_duration,
            "cmax": max_duration,
        },
    )
    colourbar_trace = create_colourbar({
        "colorscale": "Plasma",
        "showscale": True,
        "cmin": min_duration,
        "cmax": max_duration,
        "colorbar": {"thickness": 20, "outlinewidth": 0, "title": "Months"},
    })

    fig2.add_trace(colourbar_trace)
    return fig2


def figure3(df):
    fig3 = px.scatter(
        df,
        x="end_date",
        y="months",
        color="issue_number",
        title="Issue number vs Time taken to complete",
    )
    fig3.update_layout(
        xaxis={"rangeslider": {"visible": True}, "autorange": True},
        yaxis={"autorange": True, "fixedrange": False},
    )
    return fig3


def figure4(df):
    fig4 = px.scatter(
        df,
        x="end_date",
        y="issue_number",
        color="months",
        title="Issue close date vs Issue number",
    )
    fig4.update_layout(
        xaxis={"rangeslider": {"visible": True}, "autorange": True},
        yaxis={"autorange": True, "fixedrange": False},
    )
    return fig4


def figure5(df):
    fig5 = px.histogram(
        df,
        x="months",
        log_y=True,
        title="Binned distribution of time taken to complete issues",
    )
    fig5.update_layout(
        xaxis={"rangeslider": {"visible": True}, "autorange": True},
        yaxis={"autorange": True, "fixedrange": False},
    )
    return fig5


def figure6(df):
    start = pd.to_datetime(df["created_at"])
    end = pd.to_datetime(df["end_date"], format="mixed")
    days = pd.date_range(
        start=start.min(),
        end=datetime.now().replace(tzinfo=timezone.utc),
        freq="D",
    )

    def dd(day):
        return (day > start) & (day < end)

    df2 = pd.DataFrame({
        "days": days,
        "issues": [(dd(day) & ~df["is_pr"]).sum() for day in days],
        "pull requests": [(dd(day) & df["is_pr"]).sum() for day in days],
    })

    fig6 = make_subplots(specs=[[{"secondary_y": True}]])
    fig6 = fig6.add_trace(
        go.Scatter(x=df2["days"], y=df2["issues"], name="Issues", mode="lines"),
    )
    fig6 = fig6.add_trace(
        go.Scatter(
            x=df2["days"],
            y=df2["pull requests"],
            name="Pull Requests",
            mode="lines",
        ),
        secondary_y=True,
    )
    # Add titles and labels
    fig6.update_layout(
        title_text="Total issues open at any given time",
        xaxis_title="days",
        yaxis_title="Issues",
        yaxis2_title="Pull Requests",
        xaxis={"rangeslider": {"visible": True}, "autorange": True},
        yaxis={"autorange": True, "fixedrange": False},
    )
    return fig6


def figure7(df):
    df["Day"] = pd.to_datetime(df["end_date"], format="mixed").dt.date
    stats = (
        df[df["Day"] < datetime.now().date()]
        .groupby("Day")
        .size()
        .reset_index(name="Count")
    )
    fig7 = px.bar(stats, x="Day", y="Count", title="Issues closed per day")
    fig7.update_layout(
        xaxis={"rangeslider": {"visible": True}, "autorange": True},
        yaxis={"autorange": True, "fixedrange": False},
    )
    return fig7
