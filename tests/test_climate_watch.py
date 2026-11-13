import unittest
from agrovision_climate import parse_gistemp_csv, parse_noaa_co2_csv, parse_noaa_global_gas_csv

class ClimateWatchParserTests(unittest.TestCase):
    def test_gistemp_monthly_rows(self):
        header="Year,Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec,J-D,D-N,D"
        row="2024,1.0,1.1,1.2,1.3,1.4,1.5,1.6,1.7,1.8,1.9,2.0,2.1,1.5,1.5,1.5"
        data=parse_gistemp_csv(header+"\n"+row)
        self.assertEqual(len(data),12); self.assertAlmostEqual(data.iloc[0]["Anomaly_C"],1.0)
        self.assertEqual(data.iloc[-1]["Date"].month,12)
    def test_noaa_co2_comments_and_missing_values(self):
        csv="# NOAA monthly data\n# year, month, decimal date, average, deseasonalized, ndays, sdev, unc\n2024, 1, 2024.04, 422.8, 421.9, 31, 0.2, 0.1\n2024, 2, 2024.13, -99.99, -99.99, 0, -1, -1\n"
        data=parse_noaa_co2_csv(csv); self.assertEqual(len(data),1)
        self.assertAlmostEqual(data.iloc[0]["CO2_ppm"],422.8)
    def test_noaa_global_gases(self):
        csv="# NOAA global means\n# year, month, decimal date, average, trend, days\n2025, 6, 2025.46, 1929.17, 1925.00, 30\n2025, 7, 2025.54, -999.99, -999.99, 0\n"
        ch4=parse_noaa_global_gas_csv(csv,"ch4"); n2o=parse_noaa_global_gas_csv(csv,"n2o")
        self.assertEqual(len(ch4),1); self.assertAlmostEqual(ch4.iloc[0]["CH4_ppb"],1929.17)
        self.assertAlmostEqual(n2o.iloc[0]["N2O_ppb"],1929.17)
    def test_reject_unknown_gas(self):
        with self.assertRaises(ValueError): parse_noaa_global_gas_csv("header","co2")

    def test_local_extremes_counts_and_dry_spell(self):
        import pandas as pd
        from agrovision_climate import summarize_local_extremes
        dates = pd.date_range("2024-01-01", periods=7, freq="D")
        frame = pd.DataFrame({
            "PRECTOTCORR": [0.0, 0.2, 1.5, 0.0, 0.0, 55.0, 2.0],
            "T2M_MAX": [36.0, 34.0, 37.0, 35.0, 31.0, 29.0, 40.0],
        }, index=dates)
        result = summarize_local_extremes(frame)
        self.assertEqual(result.loc[0, "Hot days (Tmax threshold)"], 4)
        self.assertEqual(result.loc[0, "Heavy-rain days"], 1)
        self.assertEqual(result.loc[0, "Longest dry spell (days)"], 2)

    def test_local_extremes_missing_day_breaks_dry_spell(self):
        import pandas as pd
        from agrovision_climate import summarize_local_extremes
        dates = pd.date_range("2024-01-01", periods=4, freq="D")
        frame = pd.DataFrame({
            "PRECTOTCORR": [0.0, float("nan"), 0.0, 0.0],
            "T2M_MAX": [30.0, 30.0, 30.0, 30.0],
        }, index=dates)
        result = summarize_local_extremes(frame)
        self.assertEqual(result.loc[0, "Longest dry spell (days)"], 2)


    def test_gistemp_skips_metadata_and_bom(self):
        header="\\ufeffYear,Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec,J-D,D-N,D"
        row="2023,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0,1.1,1.2,0.6,0.6,0.6"
        data=parse_gistemp_csv("Land-Ocean Temperature Index\\nSource: NASA GISS\\n"+header+"\\n"+row)
        self.assertEqual(len(data),12)
        self.assertEqual(data.iloc[0]["Date"].year,2023)
        self.assertAlmostEqual(data.iloc[-1]["Anomaly_C"],1.2)

    def test_gistemp_reports_non_csv_response_clearly(self):
        with self.assertRaisesRegex(ValueError, "HTML/error page or changed format"):
            parse_gistemp_csv("<html><title>Service unavailable</title></html>")

if __name__=="__main__": unittest.main()
