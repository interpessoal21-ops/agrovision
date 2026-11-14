import unittest

from agrovision_trends import analyze_annual_series, mann_kendall, sens_slope


class TrendAnalysisTests(unittest.TestCase):
    def test_monotonic_increase_detected(self):
        result = analyze_annual_series(range(2000, 2012), range(12))
        self.assertEqual(result["direction"], "increasing")
        self.assertTrue(result["significant_at_alpha"])
        self.assertAlmostEqual(result["sen_slope_per_year"], 1.0)

    def test_monotonic_decrease_detected(self):
        result = analyze_annual_series(range(2000, 2012), range(12, 0, -1))
        self.assertEqual(result["direction"], "decreasing")
        self.assertTrue(result["significant_at_alpha"])

    def test_ties_do_not_break_test(self):
        result = mann_kendall(range(2000, 2010), [1, 1, 2, 2, 3, 3, 4, 4, 5, 5])
        self.assertGreater(result["p_value"], 0)
        self.assertLessEqual(result["p_value"], 1)
        self.assertGreater(result["tau"], 0)

    def test_duplicate_years_rejected(self):
        with self.assertRaisesRegex(ValueError, "only once"):
            sens_slope([2000, 2000, 2001], [1, 2, 3])

    def test_minimum_observations_enforced(self):
        with self.assertRaisesRegex(ValueError, "eight"):
            analyze_annual_series(range(2000, 2006), range(6))


if __name__ == "__main__":
    unittest.main()
