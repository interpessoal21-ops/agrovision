"""Live public-endpoint smoke checks; transient provider outages are reported, not hidden."""
import csv
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agrovision_modis import parse_modis_subset

# One land test point in Europe. The application itself accepts global WGS84 coordinates.
LAT, LON = 45.0, 10.0
TIMEOUT = 45
RETRYABLE = {429, 500, 502, 503, 504}


def get_with_retry(url, *, params=None, timeout=TIMEOUT, attempts=3):
    last = None
    for attempt in range(attempts):
        try:
            response = requests.get(url, params=params, timeout=timeout)
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
        params={"parameters":"T2M,PRECTOTCORR","community":"AG","longitude":LON,
                "latitude":LAT,"start":"20250101","end":"20250110","format":"JSON"},
    )
    if response is None:
        raise RuntimeError("NASA POWER unavailable after retries.")
    data = response.json()["properties"]["parameter"]
    for name in ("T2M", "PRECTOTCORR"):
        values = data.get(name, {})
        valid = [v for v in values.values() if v is not None and float(v) != -999]
        assert len(valid) >= 8, f"NASA POWER: insufficient valid {name} records"
    print("NASA POWER OK: T2M and PRECTOTCORR at the global smoke-test point.")


def check_modis():
    root = "https://modis.ornl.gov/rst/api/v1/MOD13Q1"
    params = {"latitude": LAT, "longitude": LON}
    dates_response = get_with_retry(root + "/dates", params=params)
    if dates_response is None:
        return False
    dates = dates_response.json().get("dates", [])
    available = sorted(item["modis_date"] for item in dates
                       if isinstance(item, dict) and item.get("modis_date"))
    assert available, "MODIS: no composite dates returned"
    day = available[-1]
    subset_params = {**params,"startDate":day,"endDate":day,"kmAboveBelow":0,"kmLeftRight":0}
    subset_response = get_with_retry(root + "/subset", params=subset_params)
    if subset_response is None:
        return False
    parsed = parse_modis_subset(subset_response.json())
    assert parsed, "MODIS: subset response contained no parseable band data"
    bands = next(iter(parsed.values()))
    required = {"250m_16_days_NIR_reflectance","250m_16_days_red_reflectance",
                "250m_16_days_pixel_reliability"}
    assert required.issubset(bands), "MODIS: required NDVI/QA bands missing"
    print(f"MODIS ORNL OK: composite {day}; NIR, red and pixel-reliability bands received.")
    return True


def check_firms_global():
    url = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_7d.csv"
    response = get_with_retry(url, timeout=120)
    if response is None:
        return False
    reader = csv.reader(response.text.splitlines())
    header = next(reader, [])
    required = {"latitude","longitude","acq_date","acq_time"}
    assert required.issubset(set(header)), "NASA FIRMS global CSV missing required columns"
    first_record = next(reader, None)
    assert first_record is not None, "NASA FIRMS global CSV contained no data rows"
    print("NASA FIRMS OK: global NOAA-20 VIIRS rolling 7-day CSV and required fields.")
    return True


if __name__ == "__main__":
    check_power()
    modis_ok = check_modis()
    firms_ok = check_firms_global()
    if not modis_ok or not firms_ok:
        print("SMOKE CHECK DEGRADED: at least one external provider was temporarily unavailable; this is not a data-validation pass.")
    else:
        print("Live source integration smoke checks passed (not field validation).")
