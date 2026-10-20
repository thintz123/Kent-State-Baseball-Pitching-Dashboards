"""Shared paths, pitch colors, and strike-zone settings."""

from pathlib import Path

DATA_FILE = Path(__file__).with_name("20261009-OlgaMuralField-1_unverified.xlsx")
KENT_STATE_TEAM = "KS_GF"
STRIKE_ZONE_WIDTH_FT = 19.44 / 12
STRIKE_ZONE_Y_MIN = 19.44 / 12
STRIKE_ZONE_Y_MAX = 38.52 / 12
STRIKE_ZONE_X_MIN = -STRIKE_ZONE_WIDTH_FT / 2
STRIKE_ZONE_X_MAX = STRIKE_ZONE_WIDTH_FT / 2
PITCH_COLORS = {
    "Fastball": "red",
    "Four-Seam": "#c8102e",
    "FourSeamFastBall": "#c8102e",
    "Sinker": "#f28e2b",
    "TwoSeamFastBall": "#f28e2b",
    "Slider": "yellow",
    "Curveball": "blue",
    "Changeup": "green",
    "ChangeUp": "green",
    "Cutter": "mediumorchid",
    "Splitter": "cyan",
    "Knuckleball": "purple",
    "Sweeper": "brown",
    "Slurve": "lime",
    "Forkball": "darkblue",
    "Screwball": "magenta",
    "Offspeed": "green",
    "Breaking": "blue",
    "Other": "gray",
}
PITCH_HEATMAPS = {
    "Fastball": "Reds",
    "Four-Seam": "Reds",
    "FourSeamFastBall": "Reds",
    "Sinker": "YlOrBr",
    "TwoSeamFastBall": "YlOrBr",
    "Slider": "YlOrBr",
    "Curveball": "Blues",
    "Changeup": "Greens",
    "ChangeUp": "Greens",
    "Cutter": "Purples",
    "Splitter": "BuGn",
    "Knuckleball": "Purples",
    "Sweeper": "Oranges",
    "Slurve": "YlGn",
    "Forkball": "PuBu",
    "Screwball": "PuRd",
    "Offspeed": "Greens",
    "Breaking": "Blues",
    "Other": "Greys",
}
PITCH_CATEGORY_SETS = {
    "Fastball": {
        "Fastball",
        "Four-Seam",
        "FourSeamFastBall",
        "Sinker",
        "TwoSeamFastBall",
        "Cutter",
    },
    "Offspeed": {"Changeup", "ChangeUp", "Splitter", "Forkball", "Screwball", "Knuckleball"},
    "Breaking": {"Slider", "Curveball", "Sweeper", "Slurve"},
}
TAGGED_DATA_THRESHOLD = 0.8
