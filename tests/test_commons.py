import unittest
import pandas as pd
from agrovision_commons import build_climate_fingerprint, comparison_distance


class ClimateCommonsTests(unittest.TestCase):
    def test_fingerprint_aggregates_without_coordinates(self):
        dates = pd.date_range("2024-01-01", periods=4, freq="D")
        frame = pd.DataFrame({
            "T2M": [20.0, 22.0, 24.0, 26.0],
            "T2M_MAX": [30.0, 36.0, 34.0, 38.0],
            "PRECTOTCORR": [1.0, 0.0, 2.0, 1.0],
        }, index=dates)
        result = build_climate_fingerprint(frame)
        self.assertEqual(result["mean_temp_c"], 23.0)
        self.assertEqual(result["annual_precipitation_mm"], 4.0)
        self.assertEqual(result["hot_days_35c_per_year"], 2.0)
        self.assertNotIn("latitude", result)
        self.assertNotIn("longitude", result)

    def test_similarity_is_zero_for_identical_profiles(self):
        profile = {"mean_temp_c": 24, "annual_precipitation_mm": 1200,
                   "hot_days_35c_per_year": 10}
        self.assertEqual(comparison_distance(profile, profile), 0.0)

    def test_missing_columns_rejected(self):
        with self.assertRaises(ValueError):
            build_climate_fingerprint(pd.DataFrame({"T2M": [20]}))


if __name__ == "__main__":
    unittest.main()
