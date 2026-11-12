"""Transparent quality-control summaries for AGROVISION input datasets.

These checks flag issues for review; they never impute, clip, or rewrite source data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


CLIMATE_RANGES = {
    "T2M": (-90.0, 60.0),
    "T2M_MAX": (-90.0, 65.0),
    "T2M_MIN": (-100.0, 60.0),
    "T2MDEW": (-100.0, 60.0),
    "WS2M": (0.0, 75.0),
    "PRECTOTCORR": (0.0, 2000.0),
    "ALLSKY_SFC_SW_DWN": (0.0, 50.0),
}


def climate_quality_report(frame: pd.DataFrame) -> dict:
    """Summarize daily coverage, duplicate dates, missing cells and broad range flags."""
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("Climate input must be a pandas DataFrame.")
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise TypeError("Climate data must use a DatetimeIndex.")
    if frame.empty:
        return {
            "start_date": "—", "end_date": "—", "expected_days": 0,
            "observed_days": 0, "missing_dates": 0, "coverage_pct": 0.0,
            "duplicate_dates": 0, "missing_cells": 0, "out_of_range_cells": 0,
            "variables": [],
        }

    dates = frame.index.normalize()
    start, end = dates.min(), dates.max()
    expected_days = len(pd.date_range(start, end, freq="D"))
    observed_days = int(dates.nunique())
    missing_dates = max(0, expected_days - observed_days)
    duplicate_dates = int(dates.duplicated(keep=False).sum())
    variables = []
    missing_cells = 0
    out_of_range_cells = 0

    for column, (lower, upper) in CLIMATE_RANGES.items():
        if column not in frame.columns:
            continue
        values = pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan)
        missing = int(values.isna().sum())
        outside = int(((values < lower) | (values > upper)).sum())
        missing_cells += missing
        out_of_range_cells += outside
        variables.append({
            "Variable": column,
            "Missing": missing,
            "Outside broad physical range": outside,
            "Expected range": f"{lower:g} to {upper:g}",
        })

    if {"T2M_MAX", "T2M_MIN"}.issubset(frame.columns):
        tmax = pd.to_numeric(frame["T2M_MAX"], errors="coerce")
        tmin = pd.to_numeric(frame["T2M_MIN"], errors="coerce")
        inverted = int((tmax < tmin).fillna(False).sum())
        variables.append({
            "Variable": "T2M_MAX < T2M_MIN",
            "Missing": 0,
            "Outside broad physical range": inverted,
            "Expected range": "Maximum should be >= minimum",
        })
        out_of_range_cells += inverted

    return {
        "start_date": start.date().isoformat(),
        "end_date": end.date().isoformat(),
        "expected_days": expected_days,
        "observed_days": observed_days,
        "missing_dates": missing_dates,
        "coverage_pct": round(100 * observed_days / expected_days, 1) if expected_days else 0.0,
        "duplicate_dates": duplicate_dates,
        "missing_cells": missing_cells,
        "out_of_range_cells": out_of_range_cells,
        "variables": variables,
    }


def modis_quality_report(frame: pd.DataFrame) -> dict:
    """Summarize MODIS NDVI range and pixel-reliability flags without altering rows."""
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("MODIS input must be a pandas DataFrame.")
    if frame.empty:
        return {
            "rows": 0, "valid_ndvi": 0, "missing_ndvi": 0,
            "invalid_ndvi": 0, "poor_or_unknown_quality": 0,
            "duplicate_dates": 0,
        }
    ndvi = pd.to_numeric(frame.get("NDVI", pd.Series(index=frame.index, dtype=float)), errors="coerce")
    quality = pd.to_numeric(frame.get("Quality", pd.Series(index=frame.index, dtype=float)), errors="coerce")
    valid_ndvi = ndvi.notna() & ndvi.between(-1, 1)
    invalid_ndvi = ndvi.notna() & ~ndvi.between(-1, 1)
    accepted_quality = quality.isin([0, 1])
    if "Date" in frame.columns:
        duplicate_dates = int(pd.to_datetime(frame["Date"], errors="coerce").duplicated(keep=False).sum())
    else:
        duplicate_dates = 0
    return {
        "rows": int(len(frame)),
        "valid_ndvi": int((valid_ndvi & accepted_quality).sum()),
        "missing_ndvi": int(ndvi.isna().sum()),
        "invalid_ndvi": int(invalid_ndvi.sum()),
        "poor_or_unknown_quality": int((~accepted_quality).sum()),
        "duplicate_dates": duplicate_dates,
    }
