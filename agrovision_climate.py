"""Climate Watch data access and parsing.

Primary series:
- NASA GISTEMP v4 global monthly temperature anomalies (1951-1980 baseline).
- NOAA GML Mauna Loa monthly atmospheric CO2 observations.

These are observational/research datasets with publication latency, not live telemetry.
"""
from __future__ import annotations

from io import StringIO
import pandas as pd
import requests

NASA_GISTEMP_URL = "https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv"
NOAA_CO2_URL = "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.csv"
SOURCES = {
    "temperature": {
        "name": "NASA GISS GISTEMP v4",
        "url": "https://data.giss.nasa.gov/gistemp/",
        "baseline": "1951–1980",
        "frequency": "Monthly; typically updated around the 10th",
    },
    "co2": {
        "name": "NOAA Global Monitoring Laboratory — Mauna Loa",
        "url": "https://gml.noaa.gov/ccgg/trends/",
        "baseline": "Observed monthly mean; not a global surface average",
        "frequency": "Monthly; subject to measurement and publication latency",
    },
}


def parse_gistemp_csv(text: str) -> pd.DataFrame:
    """Parse NASA's wide GISTEMP table into a monthly long-form series."""
    frame = pd.read_csv(StringIO(text), skipinitialspace=True)
    if "Year" not in frame.columns:
        raise ValueError("NASA GISTEMP file has no Year column.")
    month_columns = [m for m in
        ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
        if m in frame.columns]
    if len(month_columns) != 12:
        raise ValueError("NASA GISTEMP file does not contain all 12 monthly columns.")
    long = frame[["Year", *month_columns]].melt(
        id_vars="Year", var_name="Month", value_name="Anomaly_C"
    )
    long["Year"] = pd.to_numeric(long["Year"], errors="coerce")
    long["Anomaly_C"] = pd.to_numeric(long["Anomaly_C"], errors="coerce")
    month_numbers = {name: i for i, name in enumerate(
        ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1)}
    long["Month_Number"] = long["Month"].map(month_numbers)
    long = long.dropna(subset=["Year", "Month_Number", "Anomaly_C"])
    long = long[long["Anomaly_C"] > -90].copy()
    long["Date"] = pd.to_datetime(dict(
        year=long["Year"].astype(int), month=long["Month_Number"], day=1
    ))
    return long[["Date", "Anomaly_C"]].sort_values("Date").reset_index(drop=True)


def parse_noaa_co2_csv(text: str) -> pd.DataFrame:
    """Parse NOAA's Mauna Loa monthly CSV, excluding missing-value sentinels."""
    frame = pd.read_csv(StringIO(text), comment="#", skipinitialspace=True)
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    required = {"year", "month", "average"}
    if not required.issubset(frame.columns):
        raise ValueError("NOAA CO2 file is missing year, month or average columns.")
    frame["year"] = pd.to_numeric(frame["year"], errors="coerce")
    frame["month"] = pd.to_numeric(frame["month"], errors="coerce")
    frame["average"] = pd.to_numeric(frame["average"], errors="coerce")
    frame = frame.dropna(subset=["year", "month", "average"])
    frame = frame[frame["average"] > 0].copy()
    frame["Date"] = pd.to_datetime(dict(
        year=frame["year"].astype(int), month=frame["month"].astype(int), day=1
    ), errors="coerce")
    return frame.dropna(subset=["Date"])[["Date", "average"]].rename(
        columns={"average": "CO2_ppm"}
    ).sort_values("Date").reset_index(drop=True)


def fetch_climate_watch(timeout: int = 35) -> dict:
    """Fetch both authoritative source files and return parsed time series."""
    headers = {"User-Agent": "AGROVISION-ClimateWatch/1.0 (research dashboard)"}
    temp_response = requests.get(NASA_GISTEMP_URL, timeout=timeout, headers=headers)
    temp_response.raise_for_status()
    co2_response = requests.get(NOAA_CO2_URL, timeout=timeout, headers=headers)
    co2_response.raise_for_status()
    return {
        "temperature": parse_gistemp_csv(temp_response.text),
        "co2": parse_noaa_co2_csv(co2_response.text),
        "retrieved_at": pd.Timestamp.now(tz="UTC"),
        "sources": SOURCES,
    }
