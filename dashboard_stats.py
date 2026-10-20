"""Pitch classification, tilt calculations, and shared summary statistics."""

import numpy as np
import pandas as pd

from dashboard_config import PITCH_CATEGORY_SETS, TAGGED_DATA_THRESHOLD


def rate(numerator: pd.Series, denominator: int) -> float:
    return float(numerator.sum() / denominator) if denominator else 0.0



def fmt(value: float, suffix: str = "") -> str:
    return f"{value:.1f}{suffix}"



def classify_pitch_types(data: pd.DataFrame) -> tuple[bool, dict[str, set[str]]]:
    """Classify known pitch labels and determine whether tags are sufficiently complete."""
    tagged = data["TaggedPitchType"].fillna("Other")
    tagged_ratio = tagged.ne("Other").mean()
    return tagged_ratio >= TAGGED_DATA_THRESHOLD, PITCH_CATEGORY_SETS



def get_pitch_color_map_and_types(
    data: pd.DataFrame,
) -> tuple[dict[str, str], pd.DataFrame]:
    """Map pitch labels to detailed types or broad categories based on tag coverage."""
    sufficient_tagged_data, pitch_types = classify_pitch_types(data)
    data = data.copy()

    if sufficient_tagged_data:
        color_map = {
            "Fastball": "red",
            "Four-Seam": "red",
            "FourSeamFastBall": "red",
            "Slider": "yellow",
            "Curveball": "blue",
            "Changeup": "green",
            "ChangeUp": "green",
            "Cutter": "mediumorchid",
            "Sinker": "orange",
            "TwoSeamFastBall": "orange",
            "Splitter": "cyan",
            "Knuckleball": "purple",
            "Sweeper": "brown",
            "Slurve": "lime",
            "Forkball": "darkblue",
            "Screwball": "magenta",
            "Other": "gray",
        }
        data["MappedPitchType"] = data["TaggedPitchType"]
    else:
        color_map = {
            "Fastball": "red",
            "Offspeed": "green",
            "Breaking": "blue",
            "Other": "gray",
        }
        pitch_to_category = {
            pitch: category
            for category, pitches in pitch_types.items()
            for pitch in pitches
        }
        data["MappedPitchType"] = (
            data["TaggedPitchType"]
            .where(data["TaggedPitchType"].ne("Other"), data["AutoPitchType"])
            .map(pitch_to_category)
            .fillna("Other")
        )

    return color_map, data



def tilt_to_minutes(tilt_time: object) -> int | None:
    """Convert a clock-formatted tilt value to modular 12-hour minutes."""
    if hasattr(tilt_time, "hour") and hasattr(tilt_time, "minute"):
        hours = tilt_time.hour
        minutes = tilt_time.minute
    elif isinstance(tilt_time, str) and ":" in tilt_time:
        try:
            hours, minutes = map(int, tilt_time.split(":")[:2])
        except ValueError:
            return None
    else:
        return None

    if not 0 <= minutes < 60 or not 0 <= hours <= 23:
        return None
    return (0 if hours == 12 else hours) * 60 + minutes



def minutes_to_tilt(total_minutes: int | None) -> str | None:
    """Convert modular 12-hour minutes back to a clock-formatted tilt."""
    if total_minutes is None:
        return None
    hours = (total_minutes // 60) % 12
    minutes = total_minutes % 60
    return f"{12 if hours == 0 else hours}:{minutes:02d}"



def average_tilt(tilt_values: list[object]) -> str | None:
    """Compute a circular average tilt rounded to the nearest 15 minutes."""
    angles = []
    for tilt in tilt_values:
        minutes = tilt_to_minutes(tilt)
        if minutes is not None:
            angle = (minutes / (12 * 60)) * 2 * np.pi
            angles.append(angle)

    if not angles:
        return None

    mean_x = np.mean(np.cos(angles))
    mean_y = np.mean(np.sin(angles))
    average_angle = np.arctan2(mean_y, mean_x) % (2 * np.pi)
    average_minutes = (average_angle / (2 * np.pi)) * (12 * 60)
    rounded_minutes = int(round(average_minutes / 15.0) * 15)
    return minutes_to_tilt(rounded_minutes)



def pitch_tilt_info(data: pd.DataFrame) -> dict[str, dict[str, object]]:
    """Calculate average and wrapped tilt ranges for each mapped pitch type."""
    pitch_types_info: dict[str, dict[str, object]] = {}
    for pitch_type, group in data.groupby("MappedPitchType", dropna=True):
        tilt_values = [
            value
            for value in group["Tilt"].tolist()
            if tilt_to_minutes(value) is not None
        ]
        avg_str = average_tilt(tilt_values)
        tilt_degs = [
            (tilt_to_minutes(value) / (12 * 60)) * 360 % 360
            for value in tilt_values
        ]

        if tilt_degs:
            raw_min_deg = min(tilt_degs)
            raw_max_deg = max(tilt_degs)
            if raw_min_deg <= 60 and raw_max_deg >= 270:
                group_a = [value for value in tilt_degs if 180 <= value <= 352.5]
                group_b = [value for value in tilt_degs if 0 <= value <= 172.5]
                if group_a and group_b:
                    min_deg = min(group_a)
                    max_deg = max(group_b)
                else:
                    min_deg = raw_min_deg
                    max_deg = raw_max_deg
            else:
                min_deg = raw_min_deg
                max_deg = raw_max_deg
        else:
            min_deg = None
            max_deg = None

        pitch_types_info[pitch_type] = {
            "tilt_degs": tilt_degs,
            "avg_tilt": avg_str,
            "min_deg": min_deg,
            "max_deg": max_deg,
        }
    return pitch_types_info



def pitch_summary(data: pd.DataFrame) -> pd.DataFrame:
    summary = (
        data.groupby("MappedPitchType", dropna=False)
        .agg(
            Pitches=("PitchNo", "count"),
            Usage=("PitchNo", lambda values: len(values) / len(data)),
            Velo=("RelSpeed", "mean"),
            Spin=("SpinRate", "mean"),
            SpinEfficiency=("SpinAxis3dSpinEfficiency", "mean"),
            IVB=("InducedVertBreak", "mean"),
            HB=("HorzBreak", "mean"),
            Zone=("IsZone", "mean"),
            Whiff=("IsWhiff", "mean"),
            InPlay=("IsInPlay", "mean"),
        )
        .reset_index()
        .sort_values("Pitches", ascending=False)
    )
    return summary



def report_table(data: pd.DataFrame) -> pd.DataFrame:
    """Build shared screen/PDF statistics without rounding efficiency early."""
    summary = pitch_summary(data)
    column_mapping = {
        "Max Velo": ["RelSpeed"],
        "Avg Velo": ["RelSpeed"],
        "Spin": ["SpinRate"],
        "Max IVB": ["InducedVertBreak"],
        "Max HB": ["HorzBreak"],
        "Avg IVB": ["InducedVertBreak"],
        "Avg HB": ["HorzBreak"],
        "Tilt": ["Tilt"],
        "Extension": ["Extension"],
        "VAA": ["VertApprAngle"],
        "HAA": ["HorzApprAngle"],
    }
    pitch_stats = {
        pitch: {
            table_col: [
                value
                for value in data.loc[data["MappedPitchType"].eq(pitch), source_col]
                if not pd.isna(value)
            ]
            for table_col, source_columns in column_mapping.items()
            for source_col in source_columns
            if source_col in data
        }
        for pitch in summary["MappedPitchType"]
    }
    for pitch, stats in pitch_stats.items():
        for table_col, values in stats.items():
            if not values:
                continue
            if "Max" in table_col:
                summary.loc[summary["MappedPitchType"].eq(pitch), table_col] = round(
                    max(values, key=abs), 1
                )
            elif "Tilt" in table_col:
                summary.loc[summary["MappedPitchType"].eq(pitch), table_col] = (
                    average_tilt(values)
                )
            else:
                summary.loc[summary["MappedPitchType"].eq(pitch), table_col] = round(
                    sum(values) / len(values), 1
                )

    summary["Pitch"] = summary["MappedPitchType"]
    summary["Count"] = summary["Pitches"]
    summary["Spin Efficiency"] = summary["SpinEfficiency"] * 100

    table_columns = [
        "Pitch",
        "Count",
        "Max Velo",
        "Avg Velo",
        "Spin",
        "Spin Efficiency",
        "Max IVB",
        "Max HB",
        "Avg IVB",
        "Avg HB",
        "Tilt",
        "Extension",
        "VAA",
        "HAA",
    ]
    table = summary.reindex(columns=table_columns).rename(columns={"Spin": "Spin Rate"})
    for column in table.columns[2:]:
        if column != "Tilt":
            table[column] = pd.to_numeric(table[column], errors="coerce").round(1)
    table["Count"] = table["Count"].astype(int)
    return table

