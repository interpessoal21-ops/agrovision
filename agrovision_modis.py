"""Robust parsing helpers for ORNL DAAC MODIS subset responses."""
from __future__ import annotations

from datetime import datetime
from typing import Any


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
