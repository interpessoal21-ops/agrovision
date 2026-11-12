import unittest

from agrovision_modis import parse_modis_subset


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


if __name__ == "__main__":
    unittest.main()
