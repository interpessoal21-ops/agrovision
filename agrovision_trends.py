"""Transparent non-parametric trend statistics for annual Earth-system indicators.

Mann–Kendall tests monotonic association; Sen's slope estimates the median
pairwise rate of change. Neither establishes causation or physical mechanism.
"""
from __future__ import annotations

import math
from itertools import combinations

import numpy as np


def _clean_pairs(years, values):
    pairs = []
    for year, value in zip(years, values):
        try:
            y, v = float(year), float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(y) and math.isfinite(v):
            pairs.append((y, v))
    pairs.sort(key=lambda item: item[0])
    if len({year for year, _ in pairs}) != len(pairs):
        raise ValueError("Each year must occur only once.")
    if len(pairs) < 8:
        raise ValueError("At least eight valid annual observations are required.")
    return pairs


def mann_kendall(years, values):
    """Return S, Kendall tau, tie-corrected variance, z and two-sided p-value."""
    pairs = _clean_pairs(years, values)
    vals = [v for _, v in pairs]
    n = len(vals)
    s = sum((vals[j] > vals[i]) - (vals[j] < vals[i])
            for i, j in combinations(range(n), 2))
    from collections import Counter
    tie_sum = sum(count * (count - 1) * (2 * count + 5)
                  for count in Counter(vals).values() if count > 1)
    variance = (n * (n - 1) * (2 * n + 5) - tie_sum) / 18.0
    if variance <= 0:
        z = 0.0
        tau = 0.0
        p = 1.0
    else:
        z = (s - 1) / math.sqrt(variance) if s > 0 else (
            (s + 1) / math.sqrt(variance) if s < 0 else 0.0
        )
        tau = s / (n * (n - 1) / 2)
        p = math.erfc(abs(z) / math.sqrt(2))
    return {"n": n, "s": int(s), "tau": float(tau),
            "variance_s": float(variance), "z": float(z), "p_value": float(p)}


def sens_slope(years, values):
    """Median of all pairwise slopes, expressed in value units per year."""
    pairs = _clean_pairs(years, values)
    slopes = [(v2 - v1) / (y2 - y1)
              for (y1, v1), (y2, v2) in combinations(pairs, 2)
              if y2 != y1]
    if not slopes:
        raise ValueError("At least two distinct years are required.")
    return float(np.median(slopes))


def analyze_annual_series(years, values, alpha=0.05):
    pairs = _clean_pairs(years, values)
    mk = mann_kendall([p[0] for p in pairs], [p[1] for p in pairs])
    slope = sens_slope([p[0] for p in pairs], [p[1] for p in pairs])
    p = mk["p_value"]
    direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "no linear direction"
    return {
        **mk,
        "sen_slope_per_year": slope,
        "direction": direction,
        "significant_at_alpha": bool(p < alpha),
        "alpha": float(alpha),
        "first_year": int(pairs[0][0]),
        "last_year": int(pairs[-1][0]),
        "first_value": float(pairs[0][1]),
        "last_value": float(pairs[-1][1]),
    }
