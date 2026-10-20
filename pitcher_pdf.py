"""Print the website's shared report document to PDF using Chromium."""

from contextlib import contextmanager
from io import BytesIO
import subprocess
import sys
import re
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from report_html import REPORT_WIDTH, build_report_html


def pdf_filename(pitcher: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_-]+", "_", str(pitcher)).strip("_")[:90]
    return f"{name or 'pitcher'}_report.pdf"


@contextmanager
def report_browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser_path = playwright.chromium.executable_path
        if not browser_path or not Path(browser_path).exists():
            try:
                subprocess.run(
                    [sys.executable, "-m", "playwright", "install", "chromium"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as exc:
                detail = (exc.stderr or exc.stdout or "").strip()
                raise RuntimeError(
                    "Could not install the PDF browser on the server."
                    + (f" {detail}" if detail else "")
                ) from exc
        try:
            browser = playwright.chromium.launch()
        except Exception as exc:
            raise RuntimeError(
                "Could not start the PDF browser after installing Chromium."
            ) from exc
        try:
            yield browser
        finally:
            browser.close()


def print_report(browser, document):
    """Use a continuous page so browser columns and charts are never split."""
    page = browser.new_page(viewport={"width": REPORT_WIDTH, "height": 1000}, device_scale_factor=1)
    try:
        # The document embeds Plotly and needs no network access or uploaded-file URLs.
        page.route("**/*", lambda route: route.abort())
        page.set_content(document, wait_until="load")
        page.wait_for_function("window.reportReady || window.reportError", timeout=60000)
        error = page.evaluate("window.reportError")
        if error:
            raise RuntimeError(f"Report chart rendering failed: {error}")
        page.emulate_media(media="screen")
        height = page.locator("#report").evaluate("element => Math.ceil(element.scrollHeight) + 2")
        return page.pdf(
            width=f"{REPORT_WIDTH}px", height=f"{height}px",
            print_background=True, margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            scale=1,
        )
    finally:
        page.close()


def build_pitcher_pdf(data, source_name, batter_side="Both"):
    if data.empty or data["Pitcher"].nunique() != 1:
        raise ValueError("A PDF must contain pitches from exactly one pitcher.")
    document = build_report_html(data, source_name, batter_side)
    with report_browser() as browser:
        return print_report(browser, document)


def build_report_zip(data, source_name, batter_side="Both"):
    """Reuse one browser; isolate each pitcher and avoid filename collisions."""
    if data.empty:
        raise ValueError("No pitches are available to export.")
    output = BytesIO()
    with report_browser() as browser, ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for index, (_, group) in enumerate(data.groupby("Pitcher", sort=True), start=1):
            filename = f"{index:03d}_{pdf_filename(group['Pitcher'].iloc[0])}"
            document = build_report_html(group, source_name, batter_side)
            archive.writestr(filename, print_report(browser, document))
    return output.getvalue()
