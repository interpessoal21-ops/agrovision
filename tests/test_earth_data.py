import unittest
from unittest.mock import Mock, patch

import pandas as pd

from guma_earth_data import (
    NASA_FIRMS_NOAA20_GLOBAL_7D,
    _bbox_geometry,
    load_nasa_firms_global_7d,
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


class GlobalFirmsTests(unittest.TestCase):
    def test_uses_global_noaa20_seven_day_endpoint(self):
        self.assertIn("Global_24h.csv", NASA_FIRMS_NOAA20_GLOBAL_7D)

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
        frame, source = load_nasa_firms_global_7d()
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
        frame, _ = load_nasa_firms_global_7d("Custom bbox", (-50,-20,-40,-10))
        self.assertEqual(len(frame), 1)
        self.assertAlmostEqual(frame.iloc[0]["latitude"], -15.0)

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
