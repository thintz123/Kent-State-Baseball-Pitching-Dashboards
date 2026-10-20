# Kent State pitching reports

This is a Streamlit application. GitHub Pages cannot run the Python/Streamlit
server, so the app should be deployed with [Streamlit Community
Cloud](https://share.streamlit.io/) from this GitHub repository. GitHub Pages
can host static files, but it cannot provide this app's upload controls,
interactive report generation, or PDF export.

## Deploy on Streamlit Community Cloud

1. Create or sign in to a Streamlit Community Cloud account.
2. Select this repository and the `main` branch.
3. Set the main file to `baseball_dashboard.py`.
4. Deploy. Dependencies are read from `requirements.txt`.

Install and launch from this folder:

```sh
python -m pip install -r requirements.txt
python -m streamlit run baseball_dashboard.py
```

Drop a TrackMan CSV, XLSX, or XLS file into the sidebar uploader. Excel files
offer a worksheet selector; column headers must be in the first row.
No data or reports load until a file is uploaded. Removing the upload clears the report and PDF downloads.

Every pitch needs a `Pitcher` name. Include `TaggedPitchType` or `AutoPitchType`.
Standard TrackMan measurement column names are used; missing measurements
display as unavailable. Spin efficiency is expected on the TrackMan 0-1 scale
and displayed on the 0-100 scale without a percent sign.

Choose a team, pitcher, and batter-side filter to preview the report.
In the sidebar under **Download PDF reports**, generate a selected pitcher's PDF or a ZIP of
separate PDFs for all pitchers on the selected team. The ZIP uses the batter-side
filter and ignores the individual pitcher selection. Uploaded files and generated
downloads are processed in memory; downloads clear when the source or filters change.

The website preview and PDFs use the same self-contained HTML report and Plotly
charts, including density contours, velocity violins, and tilt consistency.
The preview scales the report to the available width and scrolls vertically.
PDFs preserve the full layout on a single continuous page rather than splitting
charts across letter-sized pages. Hover and zoom remain available in the website;
the PDF is static. Plotly is bundled locally, so exports do not require a CDN.
Playwright's Chromium browser is installed automatically by the server the first
time a PDF is generated. Users do not need to install Chromium. For local
development, run `python -m playwright install chromium` once if you want to
avoid downloading it on the first local PDF export.

Run regression checks:

```sh
python -m unittest test_reports
```

## Code layout

- `baseball_dashboard.py`: app entry point, upload controls, filters, and downloads.
- `dashboard_config.py`: shared paths, colors, pitch categories, and zone dimensions.
- `dashboard_data.py`: CSV/Excel reading and data validation/normalization.
- `dashboard_stats.py`: pitch classification, tilt calculations, and summary tables.
- `dashboard_charts.py`: location, movement, approach-angle, and sequencing charts.
- `dashboard_report.py`: shared report composition and website preview.
- `report_html.py`: shared HTML/CSS layout and interactive Plotly rendering.
- `pitcher_pdf.py`: browser printing of the shared document and ZIP packaging.
- `test_reports.py`: data and export regression checks.
