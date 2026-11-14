"""Standalone startup tests for the dedicated multipage workspaces."""
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class DedicatedPageStartupTests(unittest.TestCase):
    def test_trend_detective_renders_without_exception(self):
        app = AppTest.from_file(str(ROOT / "pages" / "01_Trend_Detective.py"), default_timeout=90).run()
        self.assertFalse(app.exception, msg="Trend Detective page exception: " +
                         "; ".join(str(item.message) for item in app.exception))
        rendered_text = list(app.title) + list(app.header) + list(app.subheader) + list(app.caption)
        self.assertTrue(any("Trend Detective" in str(item.value) for item in rendered_text),
                        "Trend Detective title was not rendered")

    def test_earth_data_observatory_renders_without_exception(self):
        app = AppTest.from_file(str(ROOT / "pages" / "02_Earth_Data_Observatory.py"), default_timeout=90).run()
        self.assertFalse(app.exception, msg="Earth Data Observatory page exception: " +
                         "; ".join(str(item.message) for item in app.exception))
        rendered_text = list(app.title) + list(app.header) + list(app.subheader) + list(app.caption)
        self.assertTrue(any("Earth Data Observatory" in str(item.value)
                            for item in rendered_text),
                        "Earth Data Observatory title was not rendered")


if __name__ == "__main__":
    unittest.main()
