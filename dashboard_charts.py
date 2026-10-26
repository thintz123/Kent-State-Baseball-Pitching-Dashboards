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
from dashboard_stats import tilt_to_minutes


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



def _build_clock_figure(plot_data: pd.DataFrame, hover_label: str) -> go.Figure:
    """Build a 30-minute sector polar bar clock from pitch directions in degrees."""
    plot_data = plot_data.copy()
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
                f"%{{fullData.name}}<br>{hover_label}: %{{customdata}}"
                "<br>Pitches: %{r}<extra></extra>"
            ),
        ))
    fig.update_layout(
        height=320,
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



def build_tilt_clock(data: pd.DataFrame) -> go.Figure:
    """Bin spin-based tilt into 30-minute clock sectors."""
    direction = pd.Series(np.nan, index=data.index, dtype=float)
    if "SpinAxis" in data:
        spin_axis = pd.to_numeric(data["SpinAxis"], errors="coerce")
        direction = (spin_axis + 180) % 360
    if "Tilt" in data:
        minutes = data["Tilt"].map(tilt_to_minutes)
        tilt_direction = (minutes / (12 * 60)) * 360 % 360
        direction = direction.where(direction.notna(), tilt_direction)
    valid = np.isfinite(direction)
    plot_data = data.loc[valid, ["MappedPitchType"]].copy()
    plot_data["Direction"] = direction.loc[valid].to_numpy(dtype=float)
    return _build_clock_figure(plot_data, "Tilt direction")



def render_tilt_clock(data: pd.DataFrame, ui=st) -> None:
    ui.subheader("Tilt direction by pitch type")
    fig = build_tilt_clock(data)
    if not fig.data:
        ui.info("No tilt or spin-axis measurements are available for these filters.")
        return
    ui.plotly_chart(fig, use_container_width=True)
    ui.caption(
        "Direction shows spin-based movement (tilt) from pitcher POV on a 12-hour "
        "clock: 12 is pure backspin; 6 is pure topspin; 3 and 9 are sidespin. "
        "Each sector spans 30 clock minutes; bar length shows pitch count. "
        "Missing or invalid tilt measurements are excluded."
    )



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
    return _build_clock_figure(plot_data, "Movement direction")



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



def _svg_path(points: list[tuple[float, float | str]], sign: float = 1.0) -> str:
    """Build an SVG path string while mirroring x-coordinates by sign."""
    tokens = []
    for item in points:
        cmd = item[0]
        coords = item[1:]
        scaled = [
            f"{val * sign if idx % 2 == 0 else val:.3f}"
            for idx, val in enumerate(coords)
        ]
        tokens.append(f"{cmd} {' '.join(scaled)}")
    return " ".join(tokens) + " Z"



def build_arm_slot_chart(data: pd.DataFrame) -> go.Figure:
    """Render a pitcher silhouette and mound with arm-slot cones to mean release points."""
    release_data = data.dropna(subset=["RelSide", "RelHeight"])
    fig = go.Figure()
    if release_data.empty:
        return fig

    throws = (
        release_data["PitcherThrows"].dropna().astype(str).str.upper().tolist()
        if "PitcherThrows" in release_data
        else []
    )
    if any(val.startswith("L") for val in throws) and not any(val.startswith("R") for val in throws):
        sign = -1.0
    elif any(val.startswith("R") for val in throws):
        sign = 1.0
    else:
        sign = -1.0 if release_data["RelSide"].mean() < 0 else 1.0

    # Silhouette body, shading, and belt in feet (RHP default; mirrored by sign for LHP)
    body_path = _svg_path([
        ("M", 0.20, 1.12),
        ("L", 0.14, 1.82),
        ("Q", 0.02, 2.48, -0.18, 3.08),
        ("L", -0.28, 3.18),
        ("Q", -0.60, 2.86, -0.74, 3.18),
        ("Q", -0.84, 3.62, -0.64, 4.18),
        ("Q", -0.50, 4.44, -0.34, 4.48),
        ("Q", -0.56, 4.54, -0.66, 4.82),
        ("Q", -0.74, 5.14, -0.44, 5.24),
        ("Q", -0.16, 5.26, -0.10, 4.90),
        ("Q", -0.06, 4.70, -0.08, 4.60),
        ("Q", 0.22, 4.64, 0.46, 4.50),
        ("Q", 0.64, 4.38, 0.60, 4.08),
        ("Q", 0.68, 3.64, 0.78, 3.18),
        ("Q", 0.90, 2.70, 0.88, 2.22),
        ("Q", 0.94, 1.82, 0.90, 1.62),
        ("Q", 0.74, 1.30, 0.52, 1.12),
    ], sign)

    shade_upper = _svg_path([
        ("M", -0.28, 3.18),
        ("Q", -0.60, 2.86, -0.74, 3.18),
        ("Q", -0.84, 3.62, -0.64, 4.18),
        ("Q", -0.46, 4.38, -0.16, 4.34),
        ("Q", -0.06, 3.88, -0.24, 3.48),
    ], sign)

    shade_lower = _svg_path([
        ("M", 0.20, 1.12),
        ("L", 0.14, 1.82),
        ("Q", 0.04, 2.38, -0.12, 2.95),
        ("Q", 0.32, 2.90, 0.60, 2.68),
        ("Q", 0.56, 2.08, 0.52, 1.12),
    ], sign)

    belt_path = _svg_path([
        ("M", -0.18, 3.08),
        ("Q", 0.30, 3.20, 0.78, 3.14),
        ("L", 0.76, 3.26),
        ("Q", 0.30, 3.32, -0.20, 3.20),
    ], sign)

    shapes = [
        # Silhouette base & two-tone shading
        dict(
            type="path", path=body_path,
            fillcolor="#d4e3e3", line=dict(color="#7a9090", width=1.8),
            layer="below",
        ),
        dict(
            type="path", path=shade_upper,
            fillcolor="#bfd2d2", line=dict(width=0),
            layer="below",
        ),
        dict(
            type="path", path=shade_lower,
            fillcolor="#bfd2d2", line=dict(width=0),
            layer="below",
        ),
        dict(
            type="path", path=belt_path,
            fillcolor="#d4e3e3", line=dict(color="#8aa0a0", width=1.3),
            layer="below",
        ),
        # Leg separation contour
        dict(
            type="path",
            path=f"M {0.36 * sign:.3f} 2.48 L {0.38 * sign:.3f} 1.80 Q {0.50 * sign:.3f} 1.55 {0.42 * sign:.3f} 1.14",
            line=dict(color="#7a9090", width=1.5),
            layer="below",
        ),
    ]

    sx, sy = 0.36 * sign, 4.42
    pitch_Order = list(release_data["MappedPitchType"].dropna().unique())
    pitch_points = []

    for pitch_type in pitch_Order:
        pitch_data = release_data[release_data["MappedPitchType"].eq(pitch_type)]
        rx = float(pitch_data["RelSide"].mean())
        ry = float(pitch_data["RelHeight"].mean())
        dx, dy = rx - sx, ry - sy
        dist = float(np.hypot(dx, dy))
        if dist > 1e-3:
            ux, uy = dx / dist, dy / dist
            nx, ny = -uy, ux
            w0, w1 = 0.11, 0.14
            p1x, p1y = sx + nx * w0, sy + ny * w0
            p2x, p2y = rx + nx * w1, ry + ny * w1
            p3x, p3y = rx - nx * w1, ry - ny * w1
            p4x, p4y = sx - nx * w0, sy - ny * w0
            cone_path = (
                f"M {p1x:.3f} {p1y:.3f} L {p2x:.3f} {p2y:.3f} "
                f"L {p3x:.3f} {p3y:.3f} L {p4x:.3f} {p4y:.3f} Z"
            )
            shapes.append(dict(
                type="path", path=cone_path,
                fillcolor="rgba(205, 224, 224, 0.78)",
                line=dict(color="#6b8282", width=1.8),
                layer="below",
            ))
        slot_deg = float(np.degrees(np.arctan2(ry - sy, abs(rx - sx))))
        pitch_points.append((pitch_type, rx, ry, slot_deg, len(pitch_data)))

    # Shoulder pivot circle on top of cone bases
    r_sh = 0.12
    shapes.append(dict(
        type="circle",
        x0=sx - r_sh, x1=sx + r_sh, y0=sy - r_sh, y1=sy + r_sh,
        fillcolor="#d4e3e3", line=dict(color="#6b8282", width=2),
        layer="below",
    ))

    # Grass, mound, and pitching rubber at the bottom
    shapes.extend([
        dict(
            type="rect", x0=-3.4, x1=3.4, y0=0.0, y1=0.38,
            fillcolor="#507c48", line=dict(color="#3d6136", width=1),
            layer="below",
        ),
        dict(
            type="rect", x0=-1.15, x1=1.15, y0=0.0, y1=0.38,
            fillcolor="#476f40", line=dict(width=0),
            layer="below",
        ),
        dict(
            type="rect", x0=-3.4, x1=3.4, y0=0.38, y1=0.55,
            fillcolor="#75371d", line=dict(width=0),
            layer="below",
        ),
        dict(
            type="path",
            path="M -3.4 0.55 L -3.4 0.92 Q 0 1.12 3.4 0.92 L 3.4 0.55 Z",
            fillcolor="#8a4224", line=dict(width=0),
            layer="below",
        ),
        dict(
            type="path",
            path="M -3.4 0.92 Q 0 1.12 3.4 0.92",
            line=dict(color="#2b1d16", width=3),
            layer="below",
        ),
        dict(
            type="path",
            path="M -0.60 0.99 L 0.60 0.99 L 0.56 1.12 L -0.56 1.12 Z",
            fillcolor="#f5f5f5", line=dict(color="#666666", width=1.5),
            layer="below",
        ),
    ])

    for pitch_type, rx, ry, slot_deg, count in pitch_points:
        fig.add_trace(
            go.Scatter(
                x=[rx],
                y=[ry],
                mode="markers",
                name=pitch_type,
                marker=dict(
                    color=PITCH_COLORS.get(pitch_type, "gray"),
                    size=15,
                    line=dict(color="#2b2b2b", width=2),
                ),
                customdata=[[slot_deg, count]],
                hovertemplate=(
                    "%{fullData.name}<br>"
                    "Avg release side: %{x:.2f} ft<br>"
                    "Avg release height: %{y:.2f} ft<br>"
                    "Arm slot: %{customdata[0]:.1f}°<br>"
                    "Pitches: %{customdata[1]}"
                    "<extra></extra>"
                ),
            )
        )

    max_ry = max((pt[2] for pt in pitch_points), default=6.2)
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=10, b=35),
        paper_bgcolor="white",
        plot_bgcolor="white",
        shapes=shapes,
        showlegend=True,
        legend=dict(orientation="h", x=0.5, xanchor="center", y=-0.12),
    )
    fig.update_xaxes(
        visible=False,
        range=[-3.4, 3.4],
        fixedrange=True,
    )
    fig.update_yaxes(
        visible=False,
        range=[0.0, max(6.6, max_ry + 0.5)],
        scaleanchor="x",
        scaleratio=1,
        fixedrange=True,
    )
    return fig



def render_arm_slot(data: pd.DataFrame, ui=st) -> None:
    ui.subheader("Release point & arm slot")
    fig = build_arm_slot_chart(data)
    if not fig.data:
        ui.info("Release point measurements are not available for these filters.")
        return
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

