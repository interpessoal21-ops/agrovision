"""Live endpoint smoke checks for NASA POWER and ORNL MODIS at Rio Verde."""
import requests

from agrovision_modis import parse_modis_subset

LAT, LON = -17.79, -50.91
TIMEOUT = 45


def check_power():
    response = requests.get(
        "https://power.larc.nasa.gov/api/temporal/daily/point",
        params={
            "parameters": "T2M,PRECTOTCORR",
            "community": "AG",
            "longitude": LON,
            "latitude": LAT,
            "start": "20250101",
            "end": "20250110",
            "format": "JSON",
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()["properties"]["parameter"]
    for name in ("T2M", "PRECTOTCORR"):
        values = data.get(name, {})
        valid = [v for v in values.values() if v is not None and float(v) != -999]
        assert len(valid) >= 8, f"NASA POWER: insufficient valid {name} records"
    print("NASA POWER OK: T2M and PRECTOTCORR, at least 8 valid daily records.")


def check_modis():
    root = "https://modis.ornl.gov/rst/api/v1/MOD13Q1"
    params = {"latitude": LAT, "longitude": LON}
    dates_response = requests.get(root + "/dates", params=params, timeout=TIMEOUT)
    dates_response.raise_for_status()
    dates = dates_response.json().get("dates", [])
    available = sorted(
        item["modis_date"] for item in dates
        if isinstance(item, dict) and item.get("modis_date")
    )
    assert available, "MODIS: no composite dates returned"
    day = available[-1]
    subset_params = {
        **params, "startDate": day, "endDate": day,
        "kmAboveBelow": 0, "kmLeftRight": 0,
    }
    subset_response = requests.get(root + "/subset", params=subset_params, timeout=TIMEOUT)
    subset_response.raise_for_status()
    parsed = parse_modis_subset(subset_response.json())
    assert parsed, "MODIS: subset response contained no parseable band data"
    bands = next(iter(parsed.values()))
    required = {
        "250m_16_days_NIR_reflectance",
        "250m_16_days_red_reflectance",
        "250m_16_days_pixel_reliability",
    }
    assert required.issubset(bands), "MODIS: required NDVI/QA bands missing"
    print(f"MODIS ORNL OK: composite {day}; NIR, red and pixel-reliability bands received.")


if __name__ == "__main__":
    check_power()
    check_modis()
    print("Live source integration smoke checks passed (not field validation).")
