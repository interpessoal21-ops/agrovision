import unittest
from unittest.mock import Mock, patch

import pandas as pd

from guma_earth_data import (
    NASA_FIRMS_NOAA20_GLOBAL_24H,
    NASA_FIRMS_NOAA20_GLOBAL_7D,
    load_nasa_firms_global_24h,
    _bbox_geometry,
    load_nasa_firms_global_7d,
    load_nasa_power_global_point,
)


class EarthDataGeometryTests(unittest.TestCase):
    def test_bbox_is_closed_wgs84_polygon(self):
        geometry = _bbox_geometry(-15.785, -47.875)
        self.assertEqual(geometry["type"], "Polygon")
        ring = geometry["coordinates"][0]
        self.assertEqual(ring[0], ring[-1])
        self.assertEqual(len(ring), 5)
        self.assertTrue(all(-180 <= point[0] <= 180 for point in ring))
        self.assertTrue(all(-90 <= point[1] <= 90 for point in ring))

    def test_rejects_invalid_latitude(self):
        with self.assertRaises(ValueError):
            _bbox_geometry(95, -47.875)

    def test_rejects_invalid_longitude(self):
        with self.assertRaises(ValueError):
            _bbox_geometry(-15.785, 190)

    def test_bbox_clips_at_dateline_and_poles(self):
        ring = _bbox_geometry(89.99, 179.99)["coordinates"][0]
        self.assertTrue(all(-180 <= p[0] <= 180 and -90 <= p[1] <= 90 for p in ring))
        self.assertEqual(ring[0], ring[-1])


class GlobalFirmsTests(unittest.TestCase):
    def test_uses_global_noaa20_24_hour_endpoint(self):
        self.assertIn("Global_24h.csv", NASA_FIRMS_NOAA20_GLOBAL_24H)
        self.assertEqual(NASA_FIRMS_NOAA20_GLOBAL_7D, NASA_FIRMS_NOAA20_GLOBAL_24H)

    @patch("guma_earth_data.requests.get")
    def test_global_file_is_not_brazil_filtered_by_default(self, get):
        response = Mock()
        response.text = (
            "latitude,longitude,acq_date,acq_time,satellite,confidence,frp\n"
            "40.0,-3.0,2026-11-13,1200,N20,high,4.2\n"
            "-15.0,-47.0,2026-11-13,1210,N20,nominal,3.1\n"
        )
        response.raise_for_status.return_value = None
        get.return_value = response
        frame, source = load_nasa_firms_global_24h()
        self.assertEqual(len(frame), 2)
        self.assertEqual(set(frame["query_scope"]), {"Global"})
        self.assertIn("Global_24h.csv", source)

    @patch("guma_earth_data.requests.get")
    def test_bbox_filter_is_explicit_and_validated(self, get):
        response = Mock()
        response.text = (
            "latitude,longitude,acq_date,acq_time,satellite,confidence,frp\n"
            "40.0,-3.0,2026-11-13,1200,N20,high,4.2\n"
            "-15.0,-47.0,2026-11-13,1210,N20,nominal,3.1\n"
        )
        response.raise_for_status.return_value = None
        get.return_value = response
        frame, _ = load_nasa_firms_global_24h("Custom bbox", (-50,-20,-40,-10))
        self.assertEqual(len(frame), 1)
        self.assertAlmostEqual(frame.iloc[0]["latitude"], -15.0)


    @patch("guma_earth_data.requests.get")
    def test_nasa_power_parses_global_point_and_missing_values(self, get):
        response = Mock()
        response.url = "https://power.larc.nasa.gov/api/temporal/daily/point?latitude=45"
        response.json.return_value = {
            "properties": {
                "parameter": {
                    "T2M": {"20260101": 10.0, "20260102": -999},
                    "PRECTOTCORR": {"20260101": 2.5, "20260102": 0.0},
                },
                "parameter_information": {
                    "T2M": {"units": "C"},
                    "PRECTOTCORR": {"units": "mm/day"},
                },
            }
        }
        response.raise_for_status.return_value = None
        get.return_value = response
        from datetime import date
        frame, metadata = load_nasa_power_global_point(45.0, 10.0, date(2026, 1, 1), date(2026, 1, 2))
        self.assertEqual(len(frame), 2)
        self.assertTrue(pd.isna(frame.iloc[1]["T2M"]))
        self.assertEqual(metadata["meteorology_grid_resolution"], "0.5 x 0.625 degree")

    def test_nasa_power_rejects_invalid_coordinates_before_request(self):
        from datetime import date
        with patch("guma_earth_data.requests.get") as get:
            with self.assertRaises(ValueError):
                load_nasa_power_global_point(95, 10, date(2026,1,1), date(2026,1,2))
            get.assert_not_called()

    def test_nasa_power_rejects_windows_over_ten_years(self):
        from datetime import date
        with patch("guma_earth_data.requests.get") as get:
            with self.assertRaises(ValueError):
                load_nasa_power_global_point(0, 0, date(2000,1,1), date(2026,1,1))
            get.assert_not_called()

    def test_rejects_invalid_bbox(self):
        with patch("guma_earth_data.requests.get") as get:
            response = Mock()
            response.text = "latitude,longitude,acq_date,acq_time\n1,1,2026-11-13,1200\n"
            response.raise_for_status.return_value = None
            get.return_value = response
            with self.assertRaises(ValueError):
                load_nasa_firms_global_7d("bad", (10,10,-10,-10))


if __name__ == "__main__":
    unittest.main()
