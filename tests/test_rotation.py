import unittest
import pandas as pd

from agrovision_rotation import (
    ROTATION_SCENARIOS,
    compare_rotation_scenarios,
    scenario_disclosure,
)


class RotationScenarioTests(unittest.TestCase):
    def setUp(self):
        dates = pd.date_range("2020-01-01", "2022-12-31", freq="D")
        self.climate = pd.DataFrame({
            "PRECTOTCORR": [5.0] * len(dates),
            "T2M": [24.0] * len(dates),
            "ALLSKY_SFC_SW_DWN": [5.2] * len(dates),
        }, index=dates)
        self.modis = pd.DataFrame({
            "Date": pd.date_range("2020-01-01", "2022-12-31", freq="16D"),
            "NDVI": [0.6] * len(pd.date_range("2020-01-01", "2022-12-31", freq="16D")),
        })

    def test_all_scenarios_return_comparable_records(self):
        detail, summary = compare_rotation_scenarios(self.climate, self.modis, 10)
        self.assertEqual(set(summary["Scenario"]), set(ROTATION_SCENARIOS))
        self.assertTrue((detail["Rainfall (mm)"] > 0).all())
        self.assertTrue((detail["Mean temperature (°C)"] == 24.0).all())

    def test_second_crop_adds_a_separate_window(self):
        detail, _ = compare_rotation_scenarios(self.climate, self.modis, 10)
        counts = detail.groupby("Scenario")["Phase"].nunique().to_dict()
        self.assertEqual(counts["A · Soybean → fallow"], 1)
        self.assertEqual(counts["B · Soybean → second-season maize"], 2)

    def test_modis_is_context_not_crop_identity(self):
        detail, _ = compare_rotation_scenarios(self.climate, self.modis, 10)
        self.assertTrue(detail["Regional MODIS NDVI mean"].notna().all())
        self.assertTrue(any("does not identify the crop" in item for item in scenario_disclosure()))

    def test_incomplete_windows_are_excluded(self):
        short = self.climate.loc["2022-10-01":"2022-12-31"]
        detail, summary = compare_rotation_scenarios(short, self.modis, 10)
        self.assertTrue(detail.empty)
        self.assertTrue(summary.empty)

    def test_invalid_month_is_rejected(self):
        with self.assertRaises(ValueError):
            compare_rotation_scenarios(self.climate, self.modis, 13)


if __name__ == "__main__":
    unittest.main()
