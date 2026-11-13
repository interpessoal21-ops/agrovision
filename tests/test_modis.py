import unittest

from agrovision_modis import parse_modis_subset, calculate_ndvi_from_reflectance


class ModisSubsetParsingTests(unittest.TestCase):
    def test_parses_documented_modis_date_and_groups_bands(self):
        payload = {
            "subset": [
                {"band": "250m_16_days_NIR_reflectance", "data": [6000], "modis_date": "A2025049"},
                {"band": "250m_16_days_red_reflectance", "data": [2000], "modis_date": "A2025049"},
                {"band": "250m_16_days_pixel_reliability", "data": [0], "modis_date": "A2025049"},
            ]
        }
        result = parse_modis_subset(payload)
        self.assertEqual(list(result), ["2025-02-18"])
        self.assertEqual(result["2025-02-18"]["250m_16_days_NIR_reflectance"], 6000.0)
        self.assertEqual(result["2025-02-18"]["250m_16_days_red_reflectance"], 2000.0)
        self.assertEqual(result["2025-02-18"]["250m_16_days_pixel_reliability"], 0.0)

    def test_accepts_iso_calendar_date_compatibility(self):
        result = parse_modis_subset({
            "subset": [{"band": "ndvi", "data": [0.5], "calendar_date": "2025-02-18"}]
        })
        self.assertEqual(result, {"2025-02-18": {"ndvi": 0.5}})

    def test_ignores_invalid_rows_without_fabricating_data(self):
        result = parse_modis_subset({
            "subset": [
                {"band": "ndvi", "data": [], "modis_date": "A2025049"},
                {"band": "ndvi", "data": ["not-a-number"], "modis_date": "A2025049"},
                {"band": "ndvi", "data": [0.4], "modis_date": "not-a-date"},
            ]
        })
        self.assertEqual(result, {})



class ModisNdviQualityTests(unittest.TestCase):
    def test_valid_good_and_marginal_pixels(self):
        self.assertAlmostEqual(calculate_ndvi_from_reflectance(6000, 2000, 0), 0.5)
        self.assertAlmostEqual(calculate_ndvi_from_reflectance(6000, 2000, 1), 0.5)

    def test_fill_values_are_rejected(self):
        self.assertIsNone(calculate_ndvi_from_reflectance(-1000, 2000, 0))
        self.assertIsNone(calculate_ndvi_from_reflectance(6000, -1000, 0))

    def test_out_of_range_reflectance_is_rejected(self):
        self.assertIsNone(calculate_ndvi_from_reflectance(10001, 2000, 0))
        self.assertIsNone(calculate_ndvi_from_reflectance(6000, -1, 0))

    def test_bad_quality_missing_values_and_zero_denominator_are_rejected(self):
        self.assertIsNone(calculate_ndvi_from_reflectance(6000, 2000, 2))
        self.assertIsNone(calculate_ndvi_from_reflectance(0, 0, 0))
        self.assertIsNone(calculate_ndvi_from_reflectance(None, 2000, 0))


if __name__ == "__main__":
    unittest.main()
