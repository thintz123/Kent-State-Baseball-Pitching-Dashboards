"""One self-contained, interactive report document for the website and PDF."""

from contextlib import contextmanager
from html import escape
import json

import pandas as pd
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs
from plotly.utils import PlotlyJSONEncoder

REPORT_WIDTH = 1400

REPORT_CSS = """
* { box-sizing: border-box; }
html, body { margin: 0; background: white; color: #202124; }
body { font-family: Arial, sans-serif; font-size: 14px; overflow-x: hidden; }
#report { width: 1400px; padding: 24px; transform-origin: top left; }
.report-title { text-align: center; margin: 0 0 12px; }
.report-title h1 { margin: 0 0 6px; font-size: 32px; }
.report-title p { margin: 0; color: #666; }
h2 { font-size: 18px; text-align: center; margin: 12px 0 6px; }
.columns { display: grid; gap: 16px; align-items: start; margin-top: 12px; }
.column { min-width: 0; }
.plot { width: 100%; }
.scatter-caption { text-align: center; color: #666; font-size: 20px; margin: 4px 0 12px; }
.caption { color: #666; line-height: 1.5; margin: 8px 0 12px; }
.metadata { text-align: center; margin: 0 0 12px; }
.info { background: #edf5fc; padding: 12px; border-radius: 6px; }
table { width: 100%; border-collapse: collapse; font-size: 12px; table-layout: fixed; }
th, td { border: 1px solid #ddd; padding: 9px 5px; text-align: right; overflow-wrap: anywhere; }
th { background: #f4f5f7; font-weight: 600; }
th:first-child, td:first-child { text-align: left; width: 120px; }
@media print { body { print-color-adjust: exact; -webkit-print-color-adjust: exact; } }
"""


class ReportHTML:
    """Render the report's UI calls into HTML without global Streamlit patching."""

    def __init__(self):
        self.root = []
        self.current = self.root
        self.plots = []

    def markdown(self, text, unsafe_allow_html=False):
        self.current.append(text if unsafe_allow_html else f"<p>{escape(text)}</p>")

    def caption(self, text):
        self.current.append(f'<p class="caption">{escape(text)}</p>')

    def info(self, text):
        self.current.append(f'<p class="info">{escape(text)}</p>')

    def subheader(self, text):
        self.current.append(f"<h2>{escape(text)}</h2>")

    def dataframe(self, table, **kwargs):
        # Export every row and column, without a scrollable/cropped table canvas.
        display = table.copy().astype(object)
        for column in display:
            display[column] = [
                "-" if pd.isna(value) else (
                    str(int(value)) if column == "Count" else
                    f"{value:.1f}" if isinstance(value, (float, int)) else str(value)
                )
                for value in display[column]
            ]
        self.current.append(display.to_html(index=False, escape=True, border=0))

    @contextmanager
    def _column(self, target):
        previous = self.current
        self.current = target
        try:
            yield
        finally:
            self.current = previous

    def columns(self, count):
        children = [[] for _ in range(count)]
        self.current.append(children)
        return [self._column(child) for child in children]

    def plotly_chart(self, figure, **kwargs):
        plot_id = f"plot-{len(self.plots)}"
        figure = go.Figure(figure)
        # Streamlit normally adjusts chart spacing. Give standalone browser charts
        # enough room for complete tick labels and axis titles in both outputs.
        figure.update_xaxes(automargin=True)
        figure.update_yaxes(automargin=True)
        margin = figure.layout.margin.to_plotly_json()
        minimum = dict(l=75, r=30, t=45, b=65)
        if any(trace.type in {"scatterpolar", "barpolar"} for trace in figure.data):
            minimum = dict(l=45, r=45, t=40, b=40)
            figure.update_polars(radialaxis_title_text="")
        figure.update_layout(margin={
            key: max(margin.get(key, 0), value) for key, value in minimum.items()
        })
        spec = figure.to_plotly_json()
        height = spec["layout"].get("height", 450)
        self.plots.append({"id": plot_id, "figure": spec})
        width = spec["layout"].get("width")
        sizing = f"width:{width}px;max-width:100%;margin:0 auto;" if width else ""
        self.current.append(f'<div class="plot" id="{plot_id}" style="{sizing}height:{height}px"></div>')

    def _render(self, nodes):
        parts = []
        for node in nodes:
            if isinstance(node, str):
                parts.append(node)
            else:
                columns = "".join(f'<div class="column">{self._render(child)}</div>' for child in node)
                parts.append(
                    f'<div class="columns" style="grid-template-columns:repeat({len(node)},1fr)">'
                    f"{columns}</div>"
                )
        return "".join(parts)

    def document(self):
        # Escape HTML-sensitive characters in JSON so uploaded labels cannot end a script.
        payload = json.dumps(self.plots, cls=PlotlyJSONEncoder).replace(
            "<", "\\u003c"
        ).replace(">", "\\u003e").replace("&", "\\u0026")
        return (
            '<!doctype html><html><head><meta charset="utf-8">'
            '<title>TrackMan Pitching Report</title>'
            f"<style>{REPORT_CSS}</style></head><body>"
            f'<main id="report">{self._render(self.root)}</main>'
            f"<script>{get_plotlyjs()}</script>"
            f'<script type="application/json" id="plot-specs">{payload}</script>'
            """<script>
window.reportReady = false;
const report = document.getElementById('report');
function fitReport() {
    const scale = Math.min(1, document.documentElement.clientWidth / 1400);
    report.style.transform = `scale(${scale})`;
    document.body.style.height = `${Math.ceil(report.offsetHeight * scale)}px`;
}
async function drawReport() {
    try {
        await document.fonts.ready;
        const specs = JSON.parse(document.getElementById('plot-specs').textContent);
        for (const {id, figure} of specs) {
            await Plotly.newPlot(id, figure.data, figure.layout, {
                displayModeBar: false, responsive: false, staticPlot: false
            });
        }
        fitReport();
        window.reportReady = true;
    } catch (error) {
        window.reportError = String(error);
    }
}
window.addEventListener('resize', fitReport);
drawReport();
</script></body></html>"""
        )


def build_report_html(data, source_name="", batter_side="Both"):
    from dashboard_report import compose_report

    renderer = ReportHTML()
    pitchers = data["Pitcher"].dropna().unique()
    identity = str(pitchers[0]) if len(pitchers) == 1 else f"{len(pitchers)} pitchers"
    details = f"{identity} | {len(data)} pitches | Batter side: {batter_side}"
    if source_name:
        details += f" | Source: {source_name}"
    renderer.markdown(f'<p class="caption metadata">{escape(details)}</p>', unsafe_allow_html=True)
    compose_report(data, ui=renderer)
    return renderer.document()
