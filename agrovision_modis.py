"""Robust parsing helpers for ORNL DAAC MODIS subset responses."""
from __future__ import annotations

from datetime import datetime
from typing import Any
import math


def calculate_ndvi_from_reflectance(nir: Any, red: Any, quality: Any) -> float | None:
    """Calculate NDVI only from valid MOD13Q1 reflectance and accepted QA.

    MOD13Q1 reflectance uses -1000 as fill and 0..10000 as its valid range.
    Pixel reliability 0 (good) and 1 (marginal) are retained; other values
    are rejected. The common reflectance scale factor cancels in the ratio.
    """
    try:
        nir_value = float(nir)
        red_value = float(red)
        quality_value = int(quality)
    except (TypeError, ValueError, OverflowError):
        return None
    if not (math.isfinite(nir_value) and math.isfinite(red_value)):
        return None
    if not (0 <= nir_value <= 10000 and 0 <= red_value <= 10000):
        return None
    if quality_value not in (0, 1):
        return None
    denominator = nir_value + red_value
    if denominator <= 0:
        return None
    return (nir_value - red_value) / denominator


def _parse_modis_date(value: Any) -> str | None:
    """Convert ORNL AYYYYDDD tokens (or ISO dates) to YYYY-MM-DD."""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if len(raw) == 8 and raw.startswith("A"):
        try:
            return datetime.strptime(raw, "A%Y%j").date().isoformat()
        except ValueError:
            return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def parse_modis_subset(payload: dict) -> dict[str, dict[str, float]]:
    """Group band values by date, accepting documented modis_date and calendar_date."""
    records: dict[str, dict[str, float]] = {}
    if not isinstance(payload, dict):
        return records
    subset = payload.get("subset", [])
    if not isinstance(subset, list):
        return records
    for item in subset:
        if not isinstance(item, dict):
            continue
        day = _parse_modis_date(item.get("modis_date") or item.get("calendar_date"))
        band = item.get("band")
        values = item.get("data")
        if day is None or not isinstance(band, str) or not band or not isinstance(values, list) or not values:
            continue
        try:
            value = float(values[0])
        except (TypeError, ValueError):
            continue
        records.setdefault(day, {})[band] = value
    return records
