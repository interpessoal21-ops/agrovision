import unittest
import numpy as np
from agrovision_trends import (analyze_annual_series, mann_kendall, sens_slope,
                               sen_slope_block_bootstrap_ci)


class TrendAnalysisTests(unittest.TestCase):
    def test_monotonic_increase_detected(self):
        result=analyze_annual_series(range(2000,2012),range(12),bootstrap_replicates=250)
        self.assertEqual(result["direction"],"increasing")
        self.assertTrue(result["significant_at_alpha"])
        self.assertAlmostEqual(result["sen_slope_per_year"],1.0)
        self.assertLessEqual(result["sen_slope_ci"]["lower"],1.0)
        self.assertGreaterEqual(result["sen_slope_ci"]["upper"],1.0)

    def test_monotonic_decrease_detected(self):
        result=analyze_annual_series(range(2000,2012),range(12,0,-1),bootstrap_replicates=250)
        self.assertEqual(result["direction"],"decreasing")
        self.assertTrue(result["significant_at_alpha"])

    def test_ties_do_not_break_test(self):
        result=mann_kendall(range(2000,2010),[1,1,2,2,3,3,4,4,5,5])
        self.assertGreater(result["p_value"],0)
        self.assertLessEqual(result["p_value"],1)
        self.assertGreater(result["tau"],0)

    def test_duplicate_years_rejected(self):
        with self.assertRaisesRegex(ValueError,"only once"): sens_slope([2000,2000,2001],[1,2,3])

    def test_minimum_observations_enforced(self):
        with self.assertRaisesRegex(ValueError,"eight"): sens_slope(range(2000,2006),range(6))

    def test_gap_rejected_for_autocorrelation_method(self):
        with self.assertRaisesRegex(ValueError,"consecutive annual"): mann_kendall([2000,2001,2003,2004,2005,2006,2007,2008],[1,2,3,4,5,6,7,8])

    def test_hamed_rao_reports_variance_adjustment(self):
        years=np.arange(1980,2020); rng=np.random.default_rng(9)
        noise=np.zeros(len(years))
        for i in range(1,len(noise)): noise[i]=.75*noise[i-1]+rng.normal()
        values=.03*np.arange(len(years))+noise
        result=mann_kendall(years,values)
        self.assertEqual(result["autocorrelation_method"],"hamed-rao")
        self.assertGreaterEqual(result["variance_correction_factor"],1/len(years))
        self.assertTrue(0<=result["p_value"]<=1)

    def test_bootstrap_is_reproducible(self):
        years=np.arange(2000,2020); values=.2*(years-2000)+np.sin(years)
        a=sen_slope_block_bootstrap_ci(years,values,replicates=250,seed=7)
        b=sen_slope_block_bootstrap_ci(years,values,replicates=250,seed=7)
        self.assertEqual(a,b)


if __name__=="__main__": unittest.main()
