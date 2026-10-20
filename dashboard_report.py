"""Compose the interactive pitching report and its supporting charts."""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard_config import PITCH_COLORS
from dashboard_stats import pitch_summary, report_table, pitch_tilt_info, tilt_to_minutes
from dashboard_charts import (
    render_plate_location, render_pitch_movement, render_movement_clock,
    render_approach_angle_heatmaps, report_chart_layout,
)


def compose_report(data: pd.DataFrame, ui=st) -> None:
    """Render the pitching report."""
    summary = pitch_summary(data)
    table = report_table(data)
    ui.markdown(
        "<div class='report-title'><h1>Trackman Pitching Report</h1>"
        "<p>Kent State Baseball | Pitcher development report</p></div>",
        unsafe_allow_html=True,
    )
    ui.dataframe(
        table,
        column_config={
            "Spin Efficiency": st.column_config.NumberColumn(
                "Spin Efficiency",
                format="%.1f",
            ),
        },
        hide_index=True,
        use_container_width=True,
        height=min(250, 38 + len(table) * 35),
    )

    location, movement = ui.columns(2)
    with location:
        render_plate_location(data, ui=ui)
    with movement:
        render_pitch_movement(data, ui=ui)
    ui.markdown(
        "<p class='scatter-caption'>Pitch Locations and Pitch Movement Scatterplots</p>",
        unsafe_allow_html=True,
    )
    render_movement_clock(data, ui=ui)

    ui.subheader("Velocity consistency")
    fig = px.violin(
        data,
        x="RelSpeed",
        y="MappedPitchType",
        color="MappedPitchType",
        orientation="h",
        box=True,
        points="all",
        color_discrete_map=PITCH_COLORS,
    )
    fig.update_xaxes(title="Velocity (mph)")
    fig.update_yaxes(title="")
    ui.plotly_chart(report_chart_layout(fig, 300), use_container_width=True)

    render_approach_angle_heatmaps(data, ui=ui)

    usage, release, tilt = ui.columns(3)
    with usage:
        ui.subheader("Pitch usage %")
        fig = px.pie(
            summary,
            values="Pitches",
            names="MappedPitchType",
            color="MappedPitchType",
            color_discrete_map=PITCH_COLORS,
            hole=0.02,
        )
        fig.update_traces(textinfo="label+percent")
        ui.plotly_chart(report_chart_layout(fig, 300), use_container_width=True)
    with release:
        ui.subheader("Pitch release points")
        release_data = data.dropna(subset=["RelSide", "RelHeight"])
        fig = go.Figure()
        for pitch_type in release_data["MappedPitchType"].dropna().unique():
            pitch_data = release_data[
                release_data["MappedPitchType"].eq(pitch_type)
            ]
            fig.add_trace(
                go.Scatter(
                    x=pitch_data["RelSide"],
                    y=pitch_data["RelHeight"],
                    mode="markers",
                    name=pitch_type,
                    marker=dict(
                        color=PITCH_COLORS.get(pitch_type, "black"),
                        size=12,
                        line=dict(color="black", width=1),
                    ),
                    customdata=pitch_data[["RelSpeed", "Extension"]].to_numpy(),
                    hovertemplate=(
                        "%{fullData.name}<br>"
                        "Release side: %{x:.1f} ft<br>"
                        "Release height: %{y:.1f} ft<br>"
                        "Velocity: %{customdata[0]:.1f} mph"
                        "<extra></extra>"
                    ),
                )
            )
        mean_x = release_data["RelSide"].mean()
        mean_y = release_data["RelHeight"].mean()
        if pd.notna(mean_x) and pd.notna(mean_y):
            fig.add_trace(
                go.Scatter(
                    x=[mean_x],
                    y=[mean_y],
                    mode="markers",
                    name=f"Side = {mean_x:.1f}<br>Height = {mean_y:.1f}",
                    marker=dict(
                        color="black",
                        symbol="diamond",
                        size=16,
                        line=dict(color="black", width=1),
                    ),
                    hovertemplate=(
                        "Mean release point<br>"
                        "Side: %{x:.1f} ft<br>"
                        "Height: %{y:.1f} ft"
                        "<extra></extra>"
                    ),
                )
            )
            fig.add_hline(y=mean_y, line_color="black", line_width=1)
            fig.add_vline(x=mean_x, line_color="black", line_width=1)
        fig.update_xaxes(title="Release side (ft)")
        fig.update_yaxes(title="Release height (ft)")
        fig.update_layout(
            showlegend=True,
            legend=dict(orientation="h", y=-0.2),
        )
        ui.plotly_chart(report_chart_layout(fig, 300), use_container_width=True)
    with tilt:
        ui.subheader("Tilt Consistency")
        tilt_info = pitch_tilt_info(data)
        fig = go.Figure()
        for pitch_type, info in tilt_info.items():
            degrees = info["tilt_degs"]
            if not degrees:
                continue
            color = PITCH_COLORS.get(pitch_type, "black")
            min_deg = info["min_deg"]
            max_deg = info["max_deg"]
            if min_deg is None or max_deg is None:
                continue

            # Build a true circular wedge instead of joining only the two
            # endpoints with straight lines. The wrapped case is represented
            # as one continuous clockwise arc past 360 degrees.
            end_deg = max_deg if min_deg <= max_deg else max_deg + 360
            arc = np.linspace(min_deg, end_deg, 48)
            sector_theta = np.concatenate(([min_deg], arc, [min_deg]))
            sector_r = np.concatenate(([0], np.ones(arc.size), [0]))
            fig.add_trace(
                go.Scatterpolar(
                    r=sector_r,
                    theta=sector_theta,
                    mode="lines",
                    fill="toself",
                    fillcolor=color,
                    line=dict(color=color, width=0),
                    opacity=0.22,
                    name=f"{pitch_type} range",
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
            avg_minutes = tilt_to_minutes(info["avg_tilt"])
            if avg_minutes is None:
                continue
            avg_deg = avg_minutes / (12 * 60) * 360
            fig.add_trace(
                go.Scatterpolar(
                    r=[0, 1],
                    theta=[avg_deg, avg_deg],
                    mode="lines",
                    line=dict(color=color, width=3),
                    name=pitch_type,
                    customdata=[[info["avg_tilt"], min_deg, max_deg]],
                    hovertemplate=(
                        "%{fullData.name}<br>"
                        "Average: %{customdata[0]}<br>"
                        "Range: %{customdata[1]:.0f}°–%{customdata[2]:.0f}°"
                        "<extra></extra>"
                    ),
                )
            )
            fig.add_trace(
                go.Scatterpolar(
                    r=[1.13],
                    theta=[avg_deg],
                    mode="text",
                    text=[pitch_type],
                    textfont=dict(color="#111111", size=11),
                    showlegend=False,
                    hoverinfo="skip",
                    ),
            )
        fig.update_layout(
            height=390,
            margin=dict(l=8, r=8, t=8, b=8),
            paper_bgcolor="white",
            plot_bgcolor="white",
            font=dict(color="#111111", size=11),
            showlegend=False,
            polar=dict(
                bgcolor="white",
                angularaxis=dict(
                    direction="clockwise",
                    rotation=90,
                    tickmode="array",
                    tickvals=list(range(0, 360, 30)),
                    ticktext=["12", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"],
                    gridcolor="#111111",
                    gridwidth=2,
                    linecolor="#111111",
                    linewidth=2,
                    tickfont=dict(color="#111111", size=12),
                ),
                radialaxis=dict(
                    visible=False,
                    range=[0, 1.2],
                    gridcolor="#dddddd",
                ),
            ),
        )
        ui.plotly_chart(fig, use_container_width=True)

    ui.caption(
        "Actionable review: compare each pitch's shape and location with its results. "
        "Prioritize pitches with distinct movement, repeatable release, and a location "
        "that supports the intended plan. Dataset: TrackMan export provided by Kent State."
    )



def render_report(data: pd.DataFrame, source_name: str = "", batter_side: str = "Both") -> None:
    """Display the same browser document used by the PDF exporter."""
    import streamlit.components.v1 as components
    from report_html import build_report_html

    components.html(
        build_report_html(data, source_name, batter_side),
        height=1000,
        scrolling=True,
    )
