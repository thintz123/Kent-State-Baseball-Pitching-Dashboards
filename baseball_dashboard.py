"""Streamlit entry point: uploads, filters, and PDF downloads.

Run with: streamlit run baseball_dashboard.py
"""

from pathlib import Path
from io import BytesIO
import hashlib

import pandas as pd
import streamlit as st

from dashboard_config import KENT_STATE_TEAM
from dashboard_data import normalize_data, read_upload
from dashboard_report import render_report


def main() -> None:
    st.set_page_config(
        page_title="Kent State TrackMan Dashboard",
        page_icon="⚾",
        layout="wide",
    )
    st.markdown(
        """
        <style>
        .report-title { text-align: center; margin: -20px 0 8px; }
        .report-title h1 { margin-bottom: 0; font-size: 2rem; }
        .report-title p { margin-top: 2px; color: #666; }
        .scatter-caption { text-align: center; color: #666; font-size: 1.25rem; margin: -12px 0 12px; }
        [data-testid="stDataFrame"] { border: 1px solid #aaa; }
        h2 { font-size: 1.1rem !important; text-align: center; margin: 5px 0 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.header("Upload pitch data")
    uploaded = st.sidebar.file_uploader(
        "Drop a TrackMan CSV or Excel file here",
        type=["csv", "xlsx", "xls"],
        help="Include Pitcher and TaggedPitchType or AutoPitchType. Missing measurements remain unavailable.",
    )
    if uploaded is None:
        st.session_state.pop("pdf_downloads", None)
        st.session_state.pop("pdf_export_key", None)
        st.info("Upload a TrackMan CSV or Excel file in the sidebar to get started.")
        st.stop()

    sheet = 0
    try:
        content = uploaded.getvalue()
        source_name = uploaded.name
        if Path(source_name).suffix.lower() in {".xlsx", ".xls"}:
            with pd.ExcelFile(BytesIO(content)) as workbook:
                sheet = st.sidebar.selectbox("Worksheet", workbook.sheet_names)
        data = normalize_data(read_upload(content, source_name, sheet))
    except Exception as exc:
        st.error(f"Could not read this pitch file: {exc}")
        st.info("Use a TrackMan export with column headers in the first row.")
        st.stop()
    source_id = hashlib.sha256(content).hexdigest()
    st.sidebar.caption(f"{len(data):,} pitches | {data['Pitcher'].nunique()} pitchers")

    with st.sidebar:
        st.header("Report filters")
        teams = sorted(data["PitcherTeam"].unique())
        default_team = KENT_STATE_TEAM if KENT_STATE_TEAM in teams else teams[0]
        team = st.selectbox("Pitcher team", teams, index=teams.index(default_team))
        team_data = data[data["PitcherTeam"].eq(team)]
        pitchers = ["All pitchers"] + sorted(team_data["Pitcher"].unique())
        pitcher = st.selectbox("Pitcher", pitchers)
        sides = ["Both"] + sorted(team_data["BatterSide"].unique())
        batter_side = st.selectbox("Batter side", sides)
        if pitcher != "All pitchers":
            team_data = team_data[team_data["Pitcher"].eq(pitcher)]
        if batter_side != "Both":
            team_data = team_data[team_data["BatterSide"].eq(batter_side)]
        st.divider()
        st.caption("All charts update together for the selected pitcher and batter side.")

    if team_data.empty:
        st.warning("No pitches match the selected filters.")
        st.stop()

    with st.sidebar.expander("Download PDF reports", expanded=True):
        st.caption(
            "Each PDF uses the same layout and charts as the report preview, on one continuous page. "
            "The ZIP includes every pitcher on the selected team, using the batter-side filter."
        )
        export_key = ("shared-html-v2", source_id, source_name, str(sheet), team, pitcher, batter_side)
        if st.session_state.get("pdf_export_key") != export_key:
            st.session_state.pop("pdf_downloads", None)
            st.session_state["pdf_export_key"] = export_key
        make_single = st.button(
            "Generate selected pitcher's PDF",
            disabled=pitcher == "All pitchers",
            help="Choose an individual pitcher in the sidebar.",
            use_container_width=True,
        )
        make_all = st.button("Generate all pitcher PDFs (ZIP)", use_container_width=True)
        if make_single or make_all:
            try:
                from pitcher_pdf import build_pitcher_pdf, build_report_zip, pdf_filename
                with st.spinner("Generating pitcher reports..."):
                    if make_single:
                        result = build_pitcher_pdf(
                            team_data, source_name, batter_side,
                        )
                        filename, mime = pdf_filename(pitcher), "application/pdf"
                    else:
                        batch = data[data["PitcherTeam"].eq(team)]
                        if batter_side != "Both":
                            batch = batch[batch["BatterSide"].eq(batter_side)]
                        result = build_report_zip(
                            batch, source_name, batter_side,
                        )
                        filename, mime = "pitcher_reports.zip", "application/zip"
                    st.session_state["pdf_downloads"] = (result, filename, mime)
            except ImportError:
                st.error("Install the report dependencies with: pip install -r requirements.txt")
            except Exception as exc:
                st.error(f"Could not generate the reports: {exc}")
        if "pdf_downloads" in st.session_state:
            result, filename, mime = st.session_state["pdf_downloads"]
            st.download_button("Download reports", result, file_name=filename, mime=mime)

    render_report(team_data, source_name, batter_side)



if __name__ == "__main__":
    main()
