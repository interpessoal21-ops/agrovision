import unittest
import pandas as pd

from agrovision_quality import climate_quality_report, modis_quality_report


class ClimateQualityTests(unittest.TestCase):
    def test_detects_missing_days_duplicates_missing_cells_and_ranges(self):
        dates = pd.to_datetime(["2025-01-01", "2025-01-01", "2025-01-03"])
        frame = pd.DataFrame({
            "T2M": [25.0, None, 88.0],
            "T2M_MAX": [30.0, 29.0, 20.0],
            "T2M_MIN": [18.0, 17.0, 21.0],
            "PRECTOTCORR": [0.0, 2.0, 4.0],
        }, index=dates)
        report = climate_quality_report(frame)
        self.assertEqual(report["expected_days"], 3)
        self.assertEqual(report["observed_days"], 2)
        self.assertEqual(report["missing_dates"], 1)
        self.assertEqual(report["duplicate_dates"], 2)
        self.assertEqual(report["missing_cells"], 1)
        self.assertGreaterEqual(report["out_of_range_cells"], 2)

    def test_empty_climate_frame_is_reported_without_failure(self):
        report = climate_quality_report(pd.DataFrame(index=pd.DatetimeIndex([])))
        self.assertEqual(report["coverage_pct"], 0.0)
        self.assertEqual(report["expected_days"], 0)


class ModisQualityTests(unittest.TestCase):
    def test_counts_usable_ndvi_and_quality_issues(self):
        frame = pd.DataFrame({
            "Date": pd.to_datetime(["2025-01-01", "2025-01-17", "2025-02-02", "2025-02-18"]),
            "NDVI": [0.6, 1.2, None, 0.3],
            "Quality": [0, 0, 1, 3],
        })
        report = modis_quality_report(frame)
        self.assertEqual(report["rows"], 4)
        self.assertEqual(report["valid_ndvi"], 1)
        self.assertEqual(report["missing_ndvi"], 1)
        self.assertEqual(report["invalid_ndvi"], 1)
        self.assertEqual(report["poor_or_unknown_quality"], 1)


if __name__ == "__main__":
    unittest.main()
