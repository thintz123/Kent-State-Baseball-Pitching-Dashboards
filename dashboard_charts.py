"""Plotly location, movement, approach-angle, and sequencing charts."""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard_config import (
    PITCH_COLORS, PITCH_HEATMAPS, STRIKE_ZONE_X_MIN, STRIKE_ZONE_X_MAX,
    STRIKE_ZONE_Y_MIN, STRIKE_ZONE_Y_MAX,
)


def render_plate_location(data: pd.DataFrame, ui=st) -> None:
    plot_data = data.dropna(subset=["PlateLocSide", "PlateLocHeight"])
    fig = go.Figure()
    for pitch_type in plot_data["MappedPitchType"].dropna().unique():
        pitch_data = plot_data[plot_data["MappedPitchType"].eq(pitch_type)]
        fig.add_trace(
            go.Scatter(
                x=pitch_data["PlateLocSide"],
                y=pitch_data["PlateLocHeight"],
                mode="markers",
                marker=dict(
                    color=PITCH_COLORS.get(pitch_type, "black"),
                    size=9,
                    line=dict(color="black", width=1),
                ),
                name=pitch_type,
                customdata=pitch_data[["PitchCall", "RelSpeed"]].to_numpy(),
                hovertemplate=(
                    "%{fullData.name}<br>"
                    "Call: %{customdata[0]}<br>"
                    "Velocity: %{customdata[1]:.1f} mph"
                    "<extra></extra>"
                ),
            )
        )
    fig.add_shape(
        type="rect",
        x0=STRIKE_ZONE_X_MIN,
        x1=STRIKE_ZONE_X_MAX,
        y0=STRIKE_ZONE_Y_MIN,
        y1=STRIKE_ZONE_Y_MAX,
        line=dict(color="#111", width=3),
        fillcolor="#d9d9d9",
        opacity=0.55,
        layer="below",
    )
    for x in [-0.27, 0.27]:
        fig.add_shape(
            type="line",
            x0=x,
            x1=x,
            y0=STRIKE_ZONE_Y_MIN,
            y1=STRIKE_ZONE_Y_MAX,
            line=dict(color="#888", width=1, dash="dash"),
        )
    for y in [
        STRIKE_ZONE_Y_MIN + (STRIKE_ZONE_Y_MAX - STRIKE_ZONE_Y_MIN) / 3,
        STRIKE_ZONE_Y_MIN + 2 * (STRIKE_ZONE_Y_MAX - STRIKE_ZONE_Y_MIN) / 3,
    ]:
        fig.add_shape(
            type="line",
            x0=STRIKE_ZONE_X_MIN,
            x1=STRIKE_ZONE_X_MAX,
            y0=y,
            y1=y,
            line=dict(color="#888", width=1, dash="dash"),
        )
    fig.add_shape(
        type="path",
        path="M -0.55,0.55 L 0,0.38 L 0.55,0.55 L 0.42,0.72 L -0.42,0.72 Z",
        line=dict(color="#111", width=3),
        fillcolor="white",
    )
    fig.update_layout(
        height=520,
        title=dict(text="Pitch Locations", x=0.5, xanchor="center"),
        legend_title_text="",
        margin=dict(l=10, r=10, t=20, b=10),
        plot_bgcolor="white",
    )
    fig.update_xaxes(
        title="Catcher's view: horizontal location (ft)",
        range=[-2.2, 2.2],
        zeroline=False,
    )
    fig.update_yaxes(
        title="Vertical location (ft)",
        range=[0.3, 4.5],
        zeroline=False,
    )
    ui.plotly_chart(fig, use_container_width=True)



def render_pitch_movement(data: pd.DataFrame, ui=st) -> None:
    plot_data = data.dropna(subset=["HorzBreak", "InducedVertBreak"])
    fig = go.Figure()
    for pitch_type in plot_data["MappedPitchType"].dropna().unique():
        pitch_data = plot_data[plot_data["MappedPitchType"].eq(pitch_type)]
        fig.add_trace(
            go.Histogram2dContour(
                x=pitch_data["HorzBreak"],
                y=pitch_data["InducedVertBreak"],
                colorscale=PITCH_HEATMAPS.get(pitch_type, "Greys"),
                contours=dict(coloring="fill", showlines=False),
                ncontours=10,
                showscale=False,
                opacity=0.35,
                hoverinfo="skip",
                name=f"{pitch_type} density",
                showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=pitch_data["HorzBreak"],
                y=pitch_data["InducedVertBreak"],
                mode="markers",
                marker=dict(
                    color=PITCH_COLORS.get(pitch_type, "black"),
                    size=9,
                    line=dict(color="black", width=1),
                ),
                name=pitch_type,
                customdata=pitch_data[["RelSpeed", "SpinRate", "SpinAxis"]].to_numpy(),
                hovertemplate=(
                    "%{fullData.name}<br>"
                    "Horizontal break: %{x:.1f} in<br>"
                    "Vertical break: %{y:.1f} in<br>"
                    "Velocity: %{customdata[0]:.1f} mph"
                    "<extra></extra>"
                ),
            )
        )
    fig.add_hline(y=0, line_color="#222", line_width=2)
    fig.add_vline(x=0, line_color="#222", line_width=2)
    fig.update_layout(
        height=520,
        title=dict(text="Pitch Movements", x=0.5, xanchor="center"),
        margin=dict(l=60, r=10, t=20, b=45),
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend=dict(orientation="h", y=-0.15),
    )
    fig.update_xaxes(
        title="Horizontal Break (inches)",
        range=[-25, 25],
        dtick=5,
        showgrid=True,
        gridcolor="#d0d0d0",
    )
    fig.update_yaxes(
        title="Vertical Break (inches)",
        range=[-30, 30],
        dtick=5,
        showgrid=True,
        gridcolor="#d0d0d0",
    )
    ui.plotly_chart(fig, use_container_width=True)



def build_movement_clock(data: pd.DataFrame) -> go.Figure:
    """Bin movement vectors into 30-minute clock sectors, using export signs."""
    columns = ["HorzBreak", "InducedVertBreak"]
    movement = data[columns].apply(pd.to_numeric, errors="coerce")
    valid = np.isfinite(movement).all(axis=1) & movement.ne(0).any(axis=1)
    plot_data = data.loc[valid, ["MappedPitchType"]].copy()
    # Zero degrees is up (12); positive horizontal break points right (3).
    plot_data["Direction"] = (
        np.degrees(np.arctan2(
            movement.loc[valid, "HorzBreak"],
            movement.loc[valid, "InducedVertBreak"],
        )) % 360
    )
    plot_data["Sector"] = (
        np.floor((plot_data["Direction"] + 7.5) / 15).astype(int) % 24
    )
    counts = plot_data.groupby(["MappedPitchType", "Sector"]).size()
    fig = go.Figure()
    for pitch_type in plot_data["MappedPitchType"].dropna().unique():
        pitch_counts = counts.loc[pitch_type]
        sectors = pitch_counts.index.to_numpy()
        clock_labels = [
            f"{(int(sector) // 2) or 12}:{30 * (int(sector) % 2):02d}"
            for sector in sectors
        ]
        fig.add_trace(go.Barpolar(
            theta=sectors * 15,
            r=pitch_counts.to_numpy(),
            width=15,
            name=pitch_type,
            marker=dict(
                color=PITCH_COLORS.get(pitch_type, "gray"),
                line=dict(color="#333", width=1),
            ),
            customdata=clock_labels,
            hovertemplate=(
                "%{fullData.name}<br>Movement direction: %{customdata}"
                "<br>Pitches: %{r}<extra></extra>"
            ),
        ))
    fig.update_layout(
        height=300,
        width=640,
        barmode="stack",
        paper_bgcolor="white",
        margin=dict(l=40, r=40, t=35, b=40),
        legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.15),
        polar=dict(
            hole=0.25,
            bgcolor="white",
            angularaxis=dict(
                rotation=90,
                direction="clockwise",
                tickmode="array",
                tickvals=list(range(0, 360, 30)),
                ticktext=["12"] + [str(hour) for hour in range(1, 12)],
            ),
            radialaxis=dict(
                title="Pitch count", rangemode="tozero", nticks=4,
                tickfont=dict(size=9),
            ),
        ),
    )
    return fig



def render_movement_clock(data: pd.DataFrame, ui=st) -> None:
    ui.subheader("Observed movement direction by pitch type")
    fig = build_movement_clock(data)
    if not fig.data:
        ui.info("No nonzero movement measurements are available for these filters.")
        return
    ui.plotly_chart(fig, use_container_width=True)
    ui.caption(
        "Direction is calculated from horizontal break and induced vertical break "
        "(IVB), using the same signs as the movement scatterplot: positive HB "
        "points to 3; positive IVB points to 12. Each sector spans 30 clock minutes; "
        "bar length shows pitch count, not movement distance. IVB excludes gravity. "
        "This is movement direction, not measured spin direction. "
        "Missing, nonfinite, and zero-length movement vectors are excluded."
    )



def render_approach_angle_heatmaps(data: pd.DataFrame, ui=st) -> None:
    """Render 3x3 VAA and HAA grids using the strike-zone thirds."""
    angle_data = data.dropna(
        subset=["PlateLocSide", "PlateLocHeight", "VertApprAngle", "HorzApprAngle"]
    ).copy()
    if angle_data.empty:
        ui.info("Approach-angle data is not available for the selected filters.")
        return

    horizontal_bins = [
        STRIKE_ZONE_X_MIN,
        STRIKE_ZONE_X_MIN + (STRIKE_ZONE_X_MAX - STRIKE_ZONE_X_MIN) / 3,
        STRIKE_ZONE_X_MIN + 2 * (STRIKE_ZONE_X_MAX - STRIKE_ZONE_X_MIN) / 3,
        STRIKE_ZONE_X_MAX,
    ]
    vertical_bins = [
        STRIKE_ZONE_Y_MIN,
        STRIKE_ZONE_Y_MIN + (STRIKE_ZONE_Y_MAX - STRIKE_ZONE_Y_MIN) / 3,
        STRIKE_ZONE_Y_MIN + 2 * (STRIKE_ZONE_Y_MAX - STRIKE_ZONE_Y_MIN) / 3,
        STRIKE_ZONE_Y_MAX,
    ]

    angle_data["HorizontalThird"] = pd.cut(
        angle_data["PlateLocSide"],
        bins=horizontal_bins,
        labels=["Left 1/3", "Center 1/3", "Right 1/3"],
        include_lowest=True,
    )
    angle_data["VerticalThird"] = pd.cut(
        angle_data["PlateLocHeight"],
        bins=vertical_bins,
        labels=["Bottom 1/3", "Middle 1/3", "Top 1/3"],
        include_lowest=True,
    )

    row_labels = ["Top 1/3", "Middle 1/3", "Bottom 1/3"]
    column_labels = ["Left 1/3", "Center 1/3", "Right 1/3"]

    def make_grid(column: str) -> pd.DataFrame:
        grid = (
            angle_data.pivot_table(
                index="VerticalThird",
                columns="HorizontalThird",
                values=column,
                aggfunc="mean",
                observed=False,
            )
            .reindex(index=row_labels, columns=column_labels)
            .astype(float)
        )
        return grid

    def make_figure(grid: pd.DataFrame, title: str) -> go.Figure:
        annotations = []
        for row_index, row in enumerate(grid.index):
            for column_index, column in enumerate(grid.columns):
                value = grid.loc[row, column]
                annotations.append(
                    dict(
                        x=column_index,
                        y=row_index,
                        text="" if pd.isna(value) else f"{value:.1f}°",
                        showarrow=False,
                        font=dict(size=14, color="#222"),
                    )
                )
        fig = go.Figure(
            go.Heatmap(
                z=grid.to_numpy(),
                x=list(range(3)),
                y=list(range(3)),
                colorscale="RdYlGn",
                zmid=0,
                hoverongaps=False,
                hovertemplate=(
                    f"{title}<br>%{{text}}<extra></extra>"
                ),
                text=[
                    ["" if pd.isna(value) else f"{value:.1f}°" for value in grid.iloc[row]]
                    for row in range(3)
                ],
                colorbar=dict(title="Degrees"),
            )
        )
        fig.update_layout(
            title=dict(text=title, x=0.5, xanchor="center"),
            height=330,
            margin=dict(l=85, r=20, t=45, b=65),
            paper_bgcolor="white",
            plot_bgcolor="white",
            annotations=annotations,
        )
        fig.update_xaxes(
            tickmode="array",
            tickvals=list(range(3)),
            ticktext=column_labels,
            title="Horizontal location",
            constrain="domain",
            range=[-0.5, 2.5],
            showgrid=False,
            zeroline=False,
        )
        fig.update_yaxes(
            tickmode="array",
            tickvals=list(range(3)),
            ticktext=row_labels,
            range=[2.5, -0.5],
            autorange=False,
            title="Vertical location",
            scaleanchor="x",
            scaleratio=1,
            constrain="domain",
            showgrid=False,
            zeroline=False,
        )
        # Draw the box edges at half-integers, not through the cell centers.
        # Explicit edges also keep cells with missing measurements visible in PDF.
        for edge in [-0.5, 0.5, 1.5, 2.5]:
            fig.add_shape(type="line", x0=edge, x1=edge, y0=-0.5, y1=2.5,
                          line=dict(color="#888", width=1), xref="x", yref="y")
            fig.add_shape(type="line", x0=-0.5, x1=2.5, y0=edge, y1=edge,
                          line=dict(color="#888", width=1), xref="x", yref="y")
        return fig

    vaa, haa = ui.columns(2)
    with vaa:
        ui.plotly_chart(make_figure(make_grid("VertApprAngle"), "VAA"), use_container_width=True)
    with haa:
        ui.plotly_chart(make_figure(make_grid("HorzApprAngle"), "HAA"), use_container_width=True)



def render_sequence_chart(data: pd.DataFrame, ui=st) -> None:
    sequence = data.dropna(subset=["PreviousPitch"]).copy()
    sequence = sequence[sequence["PreviousPitch"] != sequence["MappedPitchType"]]
    if sequence.empty:
        ui.info("There are not enough different-pitch transitions for a sequencing view.")
        return
    sequence["Result"] = sequence["PitchCall"].replace(
        {
            "StrikeSwinging": "Whiff",
            "StrikeCalled": "Called strike",
            "InPlay": "In play",
            "FoulBallNotFieldable": "Foul",
        }
    )
    transitions = (
        sequence.groupby(["PreviousPitch", "MappedPitchType"])
        .agg(
            Pitches=("PitchNo", "count"),
            Whiff=("IsWhiff", "mean"),
            Strike=("IsStrike", "mean"),
        )
        .reset_index()
    )
    transitions["Label"] = transitions.apply(
        lambda row: f"{row['Pitches']} pitches | {row['Whiff']:.0%} whiff", axis=1
    )
    fig = px.scatter(
        transitions,
        x="PreviousPitch",
        y="MappedPitchType",
        size="Pitches",
        color="Whiff",
        text="Label",
        color_continuous_scale="RdYlGn",
        labels={
            "PreviousPitch": "Pitch before",
            "MappedPitchType": "Next pitch",
            "Whiff": "Whiff rate",
        },
        height=420,
    )
    fig.update_traces(textposition="top center")
    fig.update_layout(margin=dict(l=10, r=10, t=20, b=10))
    ui.plotly_chart(fig, use_container_width=True)



def report_chart_layout(fig: go.Figure, height: int = 300) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=25, r=20, t=45, b=30),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(size=11),
        showlegend=False,
    )
    return fig

