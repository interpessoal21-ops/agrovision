import unittest
import pandas as pd
from agrovision_validation import paired_validation_metrics


class ValidationMetricsTests(unittest.TestCase):
    def test_perfect_match(self):
        idx = pd.date_range("2025-01-01", periods=4, freq="D")
        values = pd.Series([10.0, 12.0, 8.0, 15.0], index=idx)
        result = paired_validation_metrics(values, values)
        self.assertEqual(result["n"], 4)
        self.assertAlmostEqual(result["bias"], 0.0)
        self.assertAlmostEqual(result["mae"], 0.0)
        self.assertAlmostEqual(result["rmse"], 0.0)
        self.assertAlmostEqual(result["r_squared"], 1.0)

    def test_positive_bias_and_missing_pairs(self):
        idx = pd.date_range("2025-01-01", periods=4, freq="D")
        model = pd.Series([11.0, 13.0, None, 16.0], index=idx)
        observed = pd.Series([10.0, 12.0, 8.0, 15.0], index=idx)
        result = paired_validation_metrics(model, observed)
        self.assertEqual(result["n"], 3)
        self.assertAlmostEqual(result["bias"], 1.0)
        self.assertAlmostEqual(result["mae"], 1.0)
        self.assertAlmostEqual(result["rmse"], 1.0)

    def test_requires_three_pairs(self):
        idx = pd.date_range("2025-01-01", periods=2, freq="D")
        values = pd.Series([1.0, 2.0], index=idx)
        with self.assertRaises(ValueError):
            paired_validation_metrics(values, values)


if __name__ == "__main__":
    unittest.main()
