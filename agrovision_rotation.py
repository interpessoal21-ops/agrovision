"""Transparent, non-predictive crop-sequence climate screening.

This module compares weather exposure during assumed crop-cycle windows. It
does not estimate yield, profitability, soil-carbon change, crop suitability,
or a calibrated rotation benefit. Crop-cycle lengths are illustrative
midpoints of the reference ranges already documented in app.py.
"""
from __future__ import annotations

import pandas as pd

CROP_CYCLES_DAYS = {
    "Soybean": 143,             # midpoint of 135–150 day reference range
    "Maize (grain)": 153,       # rounded midpoint of 125–180 day range
}

ROTATION_SCENARIOS = {
    "A · Soybean only (single modeled crop)": {
        "crops": ["Soybean"],
        "management_note": "One soybean cycle; the remaining period is not modeled as a cover crop.",
        "cover_crop_modeled": False,
    },
    "B · Soybean → second-season maize": {
        "crops": ["Soybean", "Maize (grain)"],
        "management_note": "Two sequential crop windows; the remaining period is not modeled.",
        "cover_crop_modeled": False,
    },
    "C · Soybean → maize + Brachiaria cover": {
        "crops": ["Soybean", "Maize (grain)"],
        "management_note": (
            "Same modeled cash-crop windows as scenario B. Brachiaria is a "
            "management overlay only; its growth, water use and soil effects "
            "are not simulated or quantified."
        ),
        "cover_crop_modeled": False,
    },
}


def _normalise_modis(modis_frame: pd.DataFrame | None) -> pd.DataFrame:
    if modis_frame is None or modis_frame.empty or not {"Date", "NDVI"}.issubset(modis_frame.columns):
        return pd.DataFrame(columns=["Date", "NDVI"])
    result = modis_frame[["Date", "NDVI"]].copy()
    result["Date"] = pd.to_datetime(result["Date"], errors="coerce").dt.normalize()
    result["NDVI"] = pd.to_numeric(result["NDVI"], errors="coerce")
    result = result.dropna(subset=["Date", "NDVI"])
    return result[result["NDVI"].between(-1, 1)]


def compare_rotation_scenarios(
    climate_frame: pd.DataFrame,
    modis_frame: pd.DataFrame | None,
    sowing_month: int,
    scenario_names: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return per-season crop-window records and scenario summaries.

    Only complete daily climate windows are retained. The MODIS statistic is
    a regional/pixel vegetation-context summary for dates overlapping each
    crop window; it must not be interpreted as crop-specific NDVI.
    """
    required = {"PRECTOTCORR", "T2M"}
    if not isinstance(climate_frame.index, pd.DatetimeIndex):
        raise TypeError("Climate data must use a DatetimeIndex.")
    missing = required.difference(climate_frame.columns)
    if missing:
        raise ValueError("Missing climate columns: " + ", ".join(sorted(missing)))
    if not 1 <= int(sowing_month) <= 12:
        raise ValueError("Sowing month must be between 1 and 12.")

    chosen = scenario_names or list(ROTATION_SCENARIOS)
    unknown = [name for name in chosen if name not in ROTATION_SCENARIOS]
    if unknown:
        raise ValueError("Unknown scenario: " + ", ".join(unknown))

    climate = climate_frame.copy().sort_index()
    climate = climate[~climate.index.duplicated(keep="last")]
    climate["PRECTOTCORR"] = pd.to_numeric(climate["PRECTOTCORR"], errors="coerce")
    climate["T2M"] = pd.to_numeric(climate["T2M"], errors="coerce")
    modis = _normalise_modis(modis_frame)
    years = sorted(set(climate.index.year))
    records: list[dict] = []

    for scenario_name in chosen:
        scenario = ROTATION_SCENARIOS[scenario_name]
        for year in years:
            cursor = pd.Timestamp(year=int(year), month=int(sowing_month), day=1)
            sequence_records = []
            for phase, crop in enumerate(scenario["crops"], start=1):
                days = CROP_CYCLES_DAYS[crop]
                end = cursor + pd.Timedelta(days - 1, unit="D")
                window = climate.loc[cursor:end]
                if len(window) < days - 2:
                    sequence_records = []
                    break
                rain = window["PRECTOTCORR"].dropna()
                temp = window["T2M"].dropna()
                if len(rain) < days * 0.95 or len(temp) < days * 0.95:
                    sequence_records = []
                    break
                vegetation = modis[(modis["Date"] >= cursor) & (modis["Date"] <= end)]
                sequence_records.append({
                    "Scenario": scenario_name,
                    "Year": int(year),
                    "Phase": phase,
                    "Crop": crop,
                    "Start date": cursor.date().isoformat(),
                    "End date": end.date().isoformat(),
                    "Cycle days": days,
                    "Rainfall (mm)": round(float(rain.sum()), 1),
                    "Mean temperature (°C)": round(float(temp.mean()), 2),
                    "Mean solar radiation (kWh/m²/day)": (
                        round(float(pd.to_numeric(window["ALLSKY_SFC_SW_DWN"], errors="coerce").mean()), 2)
                        if "ALLSKY_SFC_SW_DWN" in window else None
                    ),
                    "Regional MODIS NDVI mean": (
                        round(float(vegetation["NDVI"].mean()), 3) if not vegetation.empty else None
                    ),
                    "MODIS composites": int(len(vegetation)),
                    "Management note": scenario["management_note"],
                })
                cursor = end + pd.Timedelta(1, unit="D")
            if sequence_records:
                records.extend(sequence_records)

    detail = pd.DataFrame(records)
    if detail.empty:
        return detail, pd.DataFrame(columns=[
            "Scenario", "Complete seasons", "Crop windows", "Median sequence duration (days)", "Median sequence rainfall (mm)",
            "Median daily rainfall (mm/day)", "Median mean temperature (°C)", "Median regional NDVI", "Interpretation"
        ])

    grouped = detail.groupby("Scenario", sort=False)
    summaries = []
    for name, group in grouped:
        by_season = group.groupby("Year").agg(
            rainfall=("Rainfall (mm)", "sum"),
            duration=("Cycle days", "sum"),
            mean_temp=("Mean temperature (°C)", "mean"),
            ndvi=("Regional MODIS NDVI mean", "mean"),
        )
        scenario = ROTATION_SCENARIOS[name]
        summaries.append({
            "Scenario": name,
            "Complete seasons": int(by_season.shape[0]),
            "Crop windows": int(len(group)),
            "Median sequence duration (days)": round(float(by_season["duration"].median()), 1),
            "Median sequence rainfall (mm)": round(float(by_season["rainfall"].median()), 1),
            "Median daily rainfall (mm/day)": round(float((by_season["rainfall"] / by_season["duration"]).median()), 2),
            "Median mean temperature (°C)": round(float(by_season["mean_temp"].median()), 2),
            "Median regional NDVI": (
                round(float(by_season["ndvi"].dropna().median()), 3)
                if by_season["ndvi"].notna().any() else None
            ),
            "Interpretation": scenario["management_note"],
        })
    return detail, pd.DataFrame(summaries)


def scenario_disclosure() -> list[str]:
    return [
        "This is historical climate-window screening, not a crop-yield or profitability forecast.",
        "Crop-cycle lengths are illustrative reference-range midpoints, not cultivar-specific phenology.",
        "Rainfall during a crop window is not effective rainfall and is not a root-zone water balance.",
        "MODIS NDVI is date-overlapping vegetation context; it does not identify the crop or field.",
        "Brachiaria is not simulated in scenario C; no water use, biomass, soil-carbon or yield benefit is quantified.",
        "Local soil texture/fertility inputs are displayed as context and are not converted into measured hydraulic properties.",
        "Confirm municipality, soil class, cultivar group, management and sowing dekad against the current official MAPA ZARC record.",
    ]
