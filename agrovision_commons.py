"""Privacy-aware community climate fingerprints for AGROVISION."""
import pandas as pd


def build_climate_fingerprint(climate: pd.DataFrame) -> dict:
    """Create shareable aggregate indicators; never includes coordinates or dates."""
    required = {"T2M", "T2M_MAX", "PRECTOTCORR"}
    missing = required.difference(climate.columns)
    if missing:
        raise ValueError(f"Climate series missing required columns: {sorted(missing)}")
    if not isinstance(climate.index, pd.DatetimeIndex):
        raise ValueError("Climate series must use a DatetimeIndex.")
    clean = climate[list(required)].apply(pd.to_numeric, errors="coerce").sort_index()
    if clean.empty:
        raise ValueError("Climate series is empty.")
    monthly = clean.assign(Month=clean.index.month).groupby("Month").agg(
        mean_temp_c=("T2M", "mean"),
        precipitation_mm=("PRECTOTCORR", "mean"),
    )
    annual = clean.groupby(clean.index.year).agg(
        mean_temp_c=("T2M", "mean"),
        annual_precipitation_mm=("PRECTOTCORR", "sum"),
        hot_days_35c=("T2M_MAX", lambda s: int(s.ge(35).sum())),
        valid_days=("T2M", "count"),
    )
    return {
        "mean_temp_c": round(float(clean["T2M"].mean()), 2),
        "annual_precipitation_mm": round(float(annual["annual_precipitation_mm"].mean()), 1),
        "hot_days_35c_per_year": round(float(annual["hot_days_35c"].mean()), 1),
        "valid_days": int(clean["T2M"].count()),
        "monthly_temperature_c": {
            str(int(k)): round(float(v), 2)
            for k, v in monthly["mean_temp_c"].dropna().items()
        },
        "monthly_precipitation_mm_day": {
            str(int(k)): round(float(v), 2)
            for k, v in monthly["precipitation_mm"].dropna().items()
        },
        "period_start": str(clean.index.min().date()),
        "period_end": str(clean.index.max().date()),
    }


def comparison_distance(left: dict, right: dict) -> float:
    """Euclidean distance on three standardized-scale indicators; lower is closer.

    This is a descriptive similarity index, not a climate-risk or suitability score.
    """
    keys = ("mean_temp_c", "annual_precipitation_mm", "hot_days_35c_per_year")
    scales = {"mean_temp_c": 5.0, "annual_precipitation_mm": 1000.0, "hot_days_35c_per_year": 60.0}
    if any(k not in left or k not in right for k in keys):
        raise ValueError("Both fingerprints must contain all comparison indicators.")
    return round(sum(((float(left[k]) - float(right[k])) / scales[k]) ** 2 for k in keys) ** 0.5, 3)
