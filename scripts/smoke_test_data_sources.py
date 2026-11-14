"""Live integration smoke checks for the public data sources used by GUMA.

These checks validate endpoint reachability and response shape only. They are not
field validation, scientific validation, or proof of local representativeness.
Transient upstream failures are reported explicitly.
"""
import csv
import io
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agrovision_modis import parse_modis_subset

LAT, LON = 45.0, 10.0
TIMEOUT = 45
RETRYABLE = {429, 500, 502, 503, 504}
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "GUMA-Earth-Intelligence/1.0 (public data integration smoke test)"})


def get_with_retry(url, *, params=None, timeout=TIMEOUT, attempts=3):
    last = None
    for attempt in range(attempts):
        try:
            response = SESSION.get(url, params=params, timeout=timeout)
            if response.status_code not in RETRYABLE:
                response.raise_for_status()
                return response
            last = requests.HTTPError(f"{response.status_code} upstream response", response=response)
        except requests.RequestException as exc:
            last = exc
        if attempt + 1 < attempts:
            time.sleep(2 ** attempt)
    if getattr(last, "response", None) is not None and last.response.status_code in {502, 503, 504}:
        print(f"UPSTREAM TEMPORARILY UNAVAILABLE: {url} ({last.response.status_code}); check deferred.")
        return None
    raise last


def check_power():
    response = get_with_retry(
        "https://power.larc.nasa.gov/api/temporal/daily/point",
        params={"parameters": "T2M,PRECTOTCORR", "community": "AG", "longitude": LON,
                "latitude": LAT, "start": "20250101", "end": "20250110", "format": "JSON"},
    )
    if response is None:
        return False
    data = response.json()["properties"]["parameter"]
    for name in ("T2M", "PRECTOTCORR"):
        values = data.get(name, {})
        valid = [v for v in values.values() if v is not None and float(v) != -999]
        assert len(valid) >= 8, f"NASA POWER: insufficient valid {name} records"
    print("NASA POWER OK: T2M and PRECTOTCORR; daily global point response.")
    return True


def check_gistemp():
    response = get_with_retry("https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv")
    if response is None:
        return False
    frame = pd.read_csv(io.StringIO(response.text), skiprows=1, skipinitialspace=True,
                        na_values=["***", "*** "])
    frame.columns = [str(c).strip().lstrip("\ufeff") for c in frame.columns]
    assert "Year" in frame.columns, f"NASA GISTEMP missing Year; columns={list(frame.columns[:8])}"
    assert "J-D" in frame.columns or all(m in frame.columns for m in
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]), \
        "NASA GISTEMP missing annual J-D and monthly fallback columns"
    annual = pd.to_numeric(frame["J-D"], errors="coerce").dropna() if "J-D" in frame else pd.Series(dtype=float)
    assert len(annual) >= 8, "NASA GISTEMP has fewer than eight annual values"
    print(f"NASA GISTEMP OK: annual schema and {len(annual)} J-D records.")
    return True


def check_sentinel2():
    url = "https://earth-search.aws.element84.com/v1/search"
    payload = {
        "collections": ["sentinel-2-c1-l2a"],
        "intersects": {"type": "Point", "coordinates": [LON, LAT]},
        "datetime": "2025-01-01T00:00:00Z/2025-01-31T23:59:59Z",
        "limit": 3,
        "query": {"eo:cloud_cover": {"lte": 80}},
    }
    last = None
    for attempt in range(3):
        try:
            response = SESSION.post(url, json=payload, headers={"Accept": "application/geo+json"},
                                    timeout=TIMEOUT)
            if response.status_code in RETRYABLE:
                last = requests.HTTPError(f"{response.status_code} upstream response", response=response)
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
            response.raise_for_status()
            data = response.json()
            assert data.get("type") == "FeatureCollection", "Earth Search response is not a FeatureCollection"
            features = data.get("features", [])
            assert isinstance(features, list), "Earth Search features is not a list"
            print(f"Element 84 Earth Search OK: Sentinel-2 L2A query returned {len(features)} scenes (0 is a valid empty window).")
            return True
        except requests.RequestException as exc:
            last = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
    if getattr(last, "response", None) is not None and last.response.status_code in {502, 503, 504}:
        print(f"Earth Search temporarily unavailable after retries: {last}")
        return False
    raise last


def check_firms_global():
    url = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_24h.csv"
    response = get_with_retry(url, timeout=120)
    if response is None:
        return False
    reader = csv.reader(response.text.splitlines())
    header = next(reader, [])
    required = {"latitude", "longitude", "acq_date", "acq_time"}
    assert required.issubset(set(header)), "NASA FIRMS global CSV missing required columns"
    first_record = next(reader, None)
    assert first_record is not None, "NASA FIRMS global CSV contained no data rows"
    print("NASA FIRMS OK: global NOAA-20 VIIRS rolling 24-hour CSV and required fields.")
    return True


def check_ibge():
    response = get_with_retry("https://servicodados.ibge.gov.br/api/v1/localidades/estados",
                              params={"orderBy": "nome"})
    if response is None:
        return False
    rows = response.json()
    assert len(rows) == 27, f"IBGE expected 27 federative units, received {len(rows)}"
    assert all({"id", "nome", "sigla"}.issubset(row) for row in rows), "IBGE state schema changed"
    print("IBGE OK: 27 Brazilian federative units; national-only reference.")
    return True


def check_modis():
    root = "https://modis.ornl.gov/rst/api/v1/MOD13Q1"
    params = {"latitude": LAT, "longitude": LON}
    try:
        dates_response = get_with_retry(root + "/dates", params=params)
        if dates_response is None:
            return False
    except requests.RequestException as exc:
        print(f"MODIS temporarily unavailable after retries: {exc}")
        return False
    dates = dates_response.json().get("dates", [])
    available = sorted(item["modis_date"] for item in dates
                       if isinstance(item, dict) and item.get("modis_date"))
    assert available, "MODIS: no composite dates returned"
    day = available[-1]
    subset_params = {**params, "startDate": day, "endDate": day,
                     "kmAboveBelow": 0, "kmLeftRight": 0}
    try:
        subset_response = get_with_retry(root + "/subset", params=subset_params)
        if subset_response is None:
            return False
    except requests.RequestException as exc:
        print(f"MODIS subset temporarily unavailable after retries: {exc}")
        return False
    parsed = parse_modis_subset(subset_response.json())
    assert parsed, "MODIS: subset response contained no parseable band data"
    bands = next(iter(parsed.values()))
    required = {"250m_16_days_NIR_reflectance", "250m_16_days_red_reflectance",
                "250m_16_days_pixel_reliability"}
    assert required.issubset(bands), "MODIS: required NDVI/QA bands missing"
    print(f"MODIS ORNL OK: composite {day}; NIR, red and pixel-reliability bands received.")
    return True


if __name__ == "__main__":
    results = {
        "NASA POWER": check_power(),
        "NASA GISTEMP": check_gistemp(),
        "Element 84 Sentinel-2": check_sentinel2(),
        "NASA FIRMS": check_firms_global(),
        "IBGE": check_ibge(),
        "MODIS": check_modis(),
    }
    failed = [name for name, ok in results.items() if not ok]
    if failed:
        print("SMOKE CHECK DEGRADED: temporarily unavailable providers: " + ", ".join(failed))
        sys.exit(2)
    print("All live source integration smoke checks passed (not field validation).")
