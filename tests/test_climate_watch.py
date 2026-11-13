import unittest
import pandas as pd

from agrovision_climate import parse_gistemp_csv, parse_noaa_co2_csv


class ClimateWatchParserTests(unittest.TestCase):
    def test_gistemp_monthly_rows_and_fill_values(self):
        header = "Year,Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec,J-D,D-N,D"
        row = "2024,1.0,1.1,1.2,1.3,1.4,1.5,1.6,1.7,1.8,1.9,2.0,2.1,1.5,1.5,1.5"
        data = parse_gistemp_csv(header + "\n" + row)
        self.assertEqual(len(data), 12)
        self.assertAlmostEqual(data.iloc[0]["Anomaly_C"], 1.0)
        self.assertEqual(data.iloc[-1]["Date"].month, 12)

    def test_noaa_co2_comments_and_missing_values(self):
        csv = "# NOAA monthly data\nyear, month, decimal date, average, deseasonalized, ndays, sdev, unc\n2024, 1, 2024.04, 422.8, 421.9, 31, 0.2, 0.1\n2024, 2, 2024.13, -99.99, -99.99, 0, -1, -1\n"
        data = parse_noaa_co2_csv(csv)
        self.assertEqual(len(data), 1)
        self.assertAlmostEqual(data.iloc[0]["CO2_ppm"], 422.8)


if __name__ == "__main__":
    unittest.main()
