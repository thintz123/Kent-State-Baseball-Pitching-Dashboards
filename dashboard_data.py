"""Read and normalize TrackMan files for screen and PDF reports."""

from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from dashboard_config import (
    STRIKE_ZONE_X_MIN, STRIKE_ZONE_X_MAX, STRIKE_ZONE_Y_MIN, STRIKE_ZONE_Y_MAX,
)
from dashboard_stats import get_pitch_color_map_and_types


@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    """Load and normalize the TrackMan export."""
    return normalize_data(pd.read_excel(path))



@st.cache_data
def read_upload(content: bytes, filename: str, sheet: str | int = 0) -> pd.DataFrame:
    if Path(filename).suffix.lower() == ".csv":
        try:
            return pd.read_csv(BytesIO(content), encoding="utf-8-sig")
        except UnicodeDecodeError:
            return pd.read_csv(BytesIO(content), encoding="cp1252")
    return pd.read_excel(BytesIO(content), sheet_name=sheet)



def normalize_data(data: pd.DataFrame) -> pd.DataFrame:
    """Validate pitcher identity and keep unavailable measurements missing."""
    data = data.copy()
    data.columns = data.columns.astype(str).str.strip()
    if data.columns.duplicated().any():
        raise ValueError("The file contains duplicate column names.")
    if data.empty:
        raise ValueError("The selected file or worksheet has no pitch rows.")
    if "Pitcher" not in data:
        raise ValueError("The file needs a Pitcher column to create individual reports.")
    if data["Pitcher"].isna().any() or data["Pitcher"].astype(str).str.strip().eq("").any():
        raise ValueError("Every pitch row needs a pitcher name in the Pitcher column.")
    if not {"TaggedPitchType", "AutoPitchType"}.intersection(data.columns):
        raise ValueError("Include TaggedPitchType or AutoPitchType in the export.")
    for column, default in {
        "TaggedPitchType": "Other", "AutoPitchType": None,
        "PitchCall": "Unknown", "KorBB": "Undefined", "PitcherTeam": "Unknown",
        "BatterSide": "Unknown", "Tilt": None,
    }.items():
        if column not in data:
            data[column] = default
    for column in ["Pitcher", "PitcherTeam", "BatterSide", "TaggedPitchType", "AutoPitchType"]:
        data[column] = data[column].astype("string").str.strip().replace("", pd.NA)
    data["PitchNo"] = np.arange(1, len(data) + 1)
    numeric_columns = [
        "RelSpeed",
        "SpinRate",
        "SpinAxis",
        "SpinAxis3dSpinEfficiency",
        "VertBreak",
        "InducedVertBreak",
        "HorzBreak",
        "PlateLocHeight",
        "PlateLocSide",
        "ExitSpeed",
        "Angle",
        "Extension",
        "RelSide",
        "RelHeight",
        "VertApprAngle",
        "HorzApprAngle",
    ]
    for column in numeric_columns:
        if column not in data:
            data[column] = np.nan
        data[column] = pd.to_numeric(data[column], errors="coerce").replace(
            [np.inf, -np.inf], np.nan
        )
    data["AutoPitchType"] = data["AutoPitchType"].fillna(data["TaggedPitchType"])
    data["TaggedPitchType"] = data["TaggedPitchType"].fillna("Other")
    _, data = get_pitch_color_map_and_types(data)
    data["PitchCall"] = data["PitchCall"].fillna("Unknown")
    data["KorBB"] = data["KorBB"].fillna("Undefined")
    data["Pitcher"] = data["Pitcher"].fillna("Unknown")
    data["PitcherTeam"] = data["PitcherTeam"].fillna("Unknown")
    data["BatterSide"] = data["BatterSide"].fillna("Unknown")
    data["IsStrike"] = data["PitchCall"].isin(
        ["StrikeCalled", "StrikeSwinging", "FoulBallNotFieldable", "InPlay"]
    )
    data["IsWhiff"] = data["PitchCall"].eq("StrikeSwinging")
    data["IsInPlay"] = data["PitchCall"].eq("InPlay")
    data["IsZone"] = data["PlateLocSide"].between(
        STRIKE_ZONE_X_MIN, STRIKE_ZONE_X_MAX
    ) & data["PlateLocHeight"].between(STRIKE_ZONE_Y_MIN, STRIKE_ZONE_Y_MAX)
    data["PreviousPitch"] = pd.NA
    if {"GameID", "PAofInning"}.issubset(data.columns):
        data["PreviousPitch"] = data.groupby(["Pitcher", "GameID", "PAofInning"])[
            "MappedPitchType"
        ].shift()
    return data

