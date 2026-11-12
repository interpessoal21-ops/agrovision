import unittest
import numpy as np
import pandas as pd

from agrovision_agronomy import (
    fao56_reference_et0,
    crop_coefficient_curve,
    simulate_root_zone_balance,
)


class AgronomyCalculationsTests(unittest.TestCase):
    def setUp(self):
        self.dates = pd.date_range("2024-01-01", periods=12, freq="D")
        self.weather = pd.DataFrame({
            "T2M": [24.0] * 12,
            "T2M_MAX": [30.0] * 12,
            "T2M_MIN": [19.0] * 12,
            "T2MDEW": [17.0] * 12,
            "WS2M": [2.0] * 12,
            "ALLSKY_SFC_SW_DWN": [5.5] * 12,
            "PRECTOTCORR": [0.0] * 12,
        }, index=self.dates)

    def test_fao56_et0_returns_positive_daily_values(self):
        et0 = fao56_reference_et0(self.weather, -22.9, 50)
        self.assertEqual(len(et0), 12)
        self.assertTrue(et0.notna().all())
        self.assertTrue((et0 > 0).all())
        self.assertTrue((et0 < 15).all())

    def test_kc_curve_sums_to_cycle(self):
        curve = crop_coefficient_curve(120, 20, 30, 40, 0.3, 1.2, 0.4)
        self.assertEqual(len(curve), 120)
        self.assertAlmostEqual(curve[0], 0.3)
        self.assertAlmostEqual(curve[19], 0.3)
        self.assertAlmostEqual(curve[49], 1.2)
        self.assertAlmostEqual(curve[89], 1.2)
        self.assertAlmostEqual(curve[-1], 0.4)

    def test_rainfed_bucket_has_no_irrigation(self):
        et0 = fao56_reference_et0(self.weather, -22.9, 50)
        kc = crop_coefficient_curve(12, 2, 3, 4, 0.3, 1.2, 0.4)
        result = simulate_root_zone_balance(
            self.weather, et0, -22.9, 100, 0.6, 0.5, 0.8, kc
        )
        self.assertEqual(len(result), 12)
        self.assertAlmostEqual(result["Net irrigation (mm)"].sum(), 0.0)
        self.assertTrue((result["Root-zone depletion (mm)"] >= 0).all())

    def test_triggered_irrigation_refills_after_raw_threshold(self):
        dry = self.weather.copy()
        dry["PRECTOTCORR"] = 0.0
        et0 = fao56_reference_et0(dry, -22.9, 50)
        kc = crop_coefficient_curve(12, 2, 3, 4, 0.3, 1.2, 0.4)
        result = simulate_root_zone_balance(
            dry, et0, -22.9, 100, 0.6, 0.5, 0.8, kc,
            irrigation_mode="triggered_supplemental", irrigation_efficiency=0.85
        )
        self.assertGreater(result["Net irrigation (mm)"].sum(), 0)
        self.assertGreaterEqual(
            result["Gross irrigation estimate (mm)"].sum(),
            result["Net irrigation (mm)"].sum()
        )

    def test_missing_meteorology_is_not_silently_filled(self):
        broken = self.weather.copy()
        broken.loc[self.dates[3], "T2MDEW"] = np.nan
        et0 = fao56_reference_et0(broken, -22.9, 50)
        self.assertTrue(np.isnan(et0.loc[self.dates[3]]))


if __name__ == "__main__":
    unittest.main()
