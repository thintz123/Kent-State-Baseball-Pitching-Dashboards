"""Run with: python -m unittest test_reports."""

from io import BytesIO
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import pandas as pd

from dashboard_data import normalize_data, read_upload
from dashboard_stats import report_table
from pitcher_pdf import build_report_zip


class ReportTests(unittest.TestCase):
    def test_csv_and_excel_worksheet(self):
        raw = pd.DataFrame({"Pitcher": ["Test"], "TaggedPitchType": ["Fastball"]})
        csv = read_upload(raw.to_csv(index=False).encode(), "pitches.csv")
        pd.testing.assert_frame_equal(csv, raw)
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            raw.to_excel(writer, sheet_name="Pitches", index=False)
            pd.DataFrame({"Other": [1]}).to_excel(writer, sheet_name="Notes", index=False)
        excel = read_upload(buffer.getvalue(), "pitches.xlsx", "Pitches")
        pd.testing.assert_frame_equal(excel, raw)

    def test_missing_metrics_stay_missing(self):
        data = normalize_data(pd.DataFrame({
            "Pitcher": ["Test"], "AutoPitchType": ["Fastball"],
        }))
        table = report_table(data)
        self.assertEqual(table["Count"].iloc[0], 1)
        self.assertTrue(pd.isna(table["Spin Efficiency"].iloc[0]))
        self.assertTrue(pd.isna(table["Avg Velo"].iloc[0]))

    def test_efficiency_uses_unrounded_mean(self):
        data = normalize_data(pd.DataFrame({
            "Pitcher": ["Test"] * 3, "TaggedPitchType": ["Fastball"] * 3,
            "SpinAxis3dSpinEfficiency": [.923, .931, None],
        }))
        self.assertEqual(report_table(data)["Spin Efficiency"].iloc[0], 92.7)

    def test_rejects_missing_pitcher_identity(self):
        for raw in [
            pd.DataFrame({"TaggedPitchType": ["Fastball"]}),
            pd.DataFrame({"Pitcher": [""], "TaggedPitchType": ["Fastball"]}),
            pd.DataFrame({"Pitcher": [None], "TaggedPitchType": ["Fastball"]}),
        ]:
            with self.assertRaises(ValueError):
                normalize_data(raw)

    def test_zip_isolates_pitchers_and_avoids_filename_collisions(self):
        data = normalize_data(pd.DataFrame({
            "Pitcher": ["A/B", "A B", "A/B"], "TaggedPitchType": ["Fastball"] * 3,
        }))
        def fake_document(group, *args):
            self.assertEqual(group["Pitcher"].nunique(), 1)
            return group["Pitcher"].iloc[0]
        with (
            patch("pitcher_pdf.report_browser"),
            patch("pitcher_pdf.build_report_html", side_effect=fake_document),
            patch("pitcher_pdf.print_report", side_effect=lambda browser, document: document.encode()),
        ):
            result = build_report_zip(data, "test.csv")
        with ZipFile(BytesIO(result)) as archive:
            self.assertEqual(len(set(archive.namelist())), 2)
            self.assertEqual({archive.read(name) for name in archive.namelist()}, {b"A/B", b"A B"})

    def test_shared_report_keeps_website_charts_and_escapes_upload_labels(self):
        from report_html import build_report_html
        import json
        import re
        data = normalize_data(pd.DataFrame({
            "Pitcher": ["Test"], "TaggedPitchType": ["</script><script>alert(1)</script>"],
            "HorzBreak": [3], "InducedVertBreak": [12], "RelSpeed": [90],
            "Tilt": ["12:30"], "VertApprAngle": [-5], "HorzApprAngle": [1],
            "PlateLocSide": [0], "PlateLocHeight": [2],
            "RelSide": [1.9], "RelHeight": [5.8],
        }))
        html = build_report_html(data, "<test.csv>")
        specs = json.loads(re.search(
            r'<script type="application/json" id="plot-specs">(.*?)</script>', html, re.S,
        ).group(1))
        kinds = {trace["type"] for spec in specs for trace in spec["figure"]["data"]}
        barpolar_plots = [
            spec for spec in specs
            if any(trace["type"] == "barpolar" for trace in spec["figure"]["data"])
        ]
        self.assertTrue({"histogram2dcontour", "violin", "barpolar", "heatmap"} <= kinds)
        self.assertEqual(len(barpolar_plots), 2)
        self.assertIn("Tilt direction by pitch type", html)
        self.assertIn("Observed movement direction by pitch type", html)
        self.assertIn("Release point &amp; arm slot", html)
        self.assertIn("&lt;test.csv&gt;", html)
        self.assertNotIn("</script><script>alert(1)</script>", html)


if __name__ == "__main__":
    unittest.main()
