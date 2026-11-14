import pytest

from agrovision_trends import analyze_annual_series, mann_kendall, sens_slope


def test_monotonic_increase_detected():
    result = analyze_annual_series(range(2000, 2012), range(12))
    assert result["direction"] == "increasing"
    assert result["significant_at_alpha"] is True
    assert result["sen_slope_per_year"] == pytest.approx(1.0)


def test_monotonic_decrease_detected():
    result = analyze_annual_series(range(2000, 2012), range(12, 0, -1))
    assert result["direction"] == "decreasing"
    assert result["significant_at_alpha"] is True


def test_ties_do_not_break_test():
    result = mann_kendall(range(2000, 2010), [1, 1, 2, 2, 3, 3, 4, 4, 5, 5])
    assert 0 < result["p_value"] <= 1
    assert result["tau"] > 0


def test_duplicate_years_rejected():
    with pytest.raises(ValueError, match="only once"):
        sens_slope([2000, 2000, 2001], [1, 2, 3])


def test_minimum_observations_enforced():
    with pytest.raises(ValueError, match="eight"):
        analyze_annual_series(range(2000, 2006), range(6))
