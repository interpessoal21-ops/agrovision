import unittest

from guma_earth_data import _bbox_geometry


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


if __name__ == "__main__":
    unittest.main()
