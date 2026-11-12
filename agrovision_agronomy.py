"""FAO-56 reference ET and a transparent single-layer root-zone bucket.

This is an exploratory daily water-balance implementation, not a ZARC clone,
calibrated crop model, or irrigation prescription. Soil and crop parameters
must be supplied/confirmed by the user.
"""
import numpy as np
import pandas as pd

SIGMA = 4.903e-9  # MJ K-4 m-2 day-1


def _extraterrestrial_radiation(latitude_deg, day_of_year):
    lat = np.deg2rad(float(latitude_deg))
    dr = 1 + 0.033 * np.cos(2 * np.pi * day_of_year / 365)
    solar_declination = 0.409 * np.sin(2 * np.pi * day_of_year / 365 - 1.39)
    sunset_angle = np.arccos(np.clip(-np.tan(lat) * np.tan(solar_declination), -1, 1))
    return (24 * 60 / np.pi) * 0.0820 * dr * (
        sunset_angle * np.sin(lat) * np.sin(solar_declination)
        + np.cos(lat) * np.cos(solar_declination) * np.sin(sunset_angle)
    )


def fao56_reference_et0(weather, latitude_deg, elevation_m):
    """Calculate daily FAO-56 Penman-Monteith ET0 in mm/day.

    Required NASA POWER daily columns and units:
    T2M (°C), T2M_MAX/MIN (°C), T2MDEW (°C), WS2M (m/s),
    ALLSKY_SFC_SW_DWN (kWh/m²/day).
    """
    required = ["T2M", "T2M_MAX", "T2M_MIN", "T2MDEW", "WS2M", "ALLSKY_SFC_SW_DWN"]
    missing = [c for c in required if c not in weather.columns]
    if missing:
        raise ValueError("Missing FAO-56 input columns: " + ", ".join(missing))
    if not isinstance(weather.index, pd.DatetimeIndex):
        raise TypeError("Weather data must use a DatetimeIndex.")
    if not -90 <= float(latitude_deg) <= 90:
        raise ValueError("Latitude must be between -90 and 90 degrees.")
    if not -500 <= float(elevation_m) <= 9000:
        raise ValueError("Elevation is outside the supported sanity-check range.")

    w = weather[required].apply(pd.to_numeric, errors="coerce").replace([-999, np.inf, -np.inf], np.nan)
    t = w["T2M"]
    tmax, tmin, tdew = w["T2M_MAX"], w["T2M_MIN"], w["T2MDEW"]
    u2 = w["WS2M"].clip(lower=0)
    rs = w["ALLSKY_SFC_SW_DWN"] * 3.6  # kWh m-2 day-1 -> MJ m-2 day-1

    es_tmax = 0.6108 * np.exp((17.27 * tmax) / (tmax + 237.3))
    es_tmin = 0.6108 * np.exp((17.27 * tmin) / (tmin + 237.3))
    es = (es_tmax + es_tmin) / 2
    ea = 0.6108 * np.exp((17.27 * tdew) / (tdew + 237.3))
    delta = 4098 * (0.6108 * np.exp((17.27 * t) / (t + 237.3))) / ((t + 237.3) ** 2)

    pressure = 101.3 * (((293 - 0.0065 * float(elevation_m)) / 293) ** 5.26)
    gamma = 0.000665 * pressure
    doy = w.index.dayofyear
    ra = pd.Series([_extraterrestrial_radiation(latitude_deg, d) for d in doy], index=w.index)
    rso = (0.75 + 2e-5 * float(elevation_m)) * ra
    rns = 0.77 * rs
    rs_rso = (rs / rso.replace(0, np.nan)).clip(lower=0, upper=1)
    cloud_factor = (1.35 * rs_rso - 0.35).clip(lower=0.05, upper=1.0)
    tmax_k = tmax + 273.16
    tmin_k = tmin + 273.16
    rnl = SIGMA * ((tmax_k ** 4 + tmin_k ** 4) / 2) * (
        0.34 - 0.14 * np.sqrt(ea.clip(lower=0))
    ) * cloud_factor
    rn = rns - rnl
    numerator = 0.408 * delta * rn + gamma * (900 / (t + 273)) * u2 * (es - ea)
    denominator = delta + gamma * (1 + 0.34 * u2)
    et0 = (numerator / denominator).clip(lower=0)
    valid = w.notna().all(axis=1) & (tmax >= tmin) & (ea <= es + 0.2)
    return et0.where(valid).rename("ET0_FAO56_mm_day")


def crop_coefficient_curve(cycle_days, initial_days, development_days, midseason_days,
                           kc_initial, kc_mid, kc_end):
    """Daily single Kc curve: Kc ini, linear rise, Kc mid, linear decline."""
    cycle_days = int(cycle_days)
    initial_days, development_days, midseason_days = map(
        int, (initial_days, development_days, midseason_days)
    )
    end_days = cycle_days - initial_days - development_days - midseason_days
    if min(initial_days, development_days, midseason_days, end_days) < 1:
        raise ValueError("All four crop stages must have at least one day and sum to the cycle.")
    if not all(0 <= float(v) <= 2.0 for v in (kc_initial, kc_mid, kc_end)):
        raise ValueError("Kc values must be between 0 and 2.")
    values = ([float(kc_initial)] * initial_days)
    if development_days:
        values += np.linspace(float(kc_initial), float(kc_mid), development_days + 1)[1:].tolist()
    values += [float(kc_mid)] * midseason_days
    values += np.linspace(float(kc_mid), float(kc_end), end_days + 1)[1:].tolist()
    return np.asarray(values[:cycle_days], dtype=float)


def simulate_root_zone_balance(weather_window, et0, latitude_deg, available_water_mm_m,
                               root_depth_m, depletion_fraction, initial_storage_fraction,
                               kc_curve, irrigation_mode="rainfed", irrigation_efficiency=0.85):
    """Run a one-layer daily bucket water balance.

    Rain is assumed to infiltrate until field capacity; runoff, capillary rise,
    lateral flow, changing root depth and salinity are not represented.
    Supplemental irrigation is an idealized trigger at RAW, refilling to 50% RAW.
    """
    if "PRECTOTCORR" not in weather_window.columns:
        raise ValueError("PRECTOTCORR is required for the water balance.")
    if not 34 <= float(available_water_mm_m) <= 184:
        raise ValueError("Available water must be between 34 and 184 mm/m; use a soil analysis/ZARC class.")
    if not 0.1 <= float(root_depth_m) <= 2.5:
        raise ValueError("Effective root depth must be between 0.1 and 2.5 m.")
    if not 0.1 <= float(depletion_fraction) <= 0.8:
        raise ValueError("Depletion fraction must be between 0.1 and 0.8.")
    if not 0 <= float(initial_storage_fraction) <= 1:
        raise ValueError("Initial soil-water storage fraction must be between 0 and 1.")
    if not 0.5 <= float(irrigation_efficiency) <= 1:
        raise ValueError("Irrigation efficiency must be between 0.5 and 1.")
    if len(weather_window) != len(et0) or len(kc_curve) != len(weather_window):
        raise ValueError("Weather, ET0 and Kc arrays must have equal lengths.")
    if et0.isna().any():
        raise ValueError("FAO-56 ET0 has missing days; this cycle cannot be simulated reliably.")

    taw = float(available_water_mm_m) * float(root_depth_m)
    raw = float(depletion_fraction) * taw
    depletion = (1 - float(initial_storage_fraction)) * taw
    rain = pd.to_numeric(weather_window["PRECTOTCORR"], errors="coerce").to_numpy(dtype=float)
    if np.isnan(rain).any() or (rain < 0).any():
        raise ValueError("Daily precipitation contains missing or negative values.")
    et0_values = et0.to_numpy(dtype=float)
    records = []
    for date, p, eto, kc in zip(weather_window.index, rain, et0_values, kc_curve):
        # Rainfall first refills the root-zone bucket. Excess is deep drainage;
        # surface runoff is not separately estimated in this simplified model.
        depletion = max(0.0, depletion - p)
        net_irrigation = 0.0
        if irrigation_mode == "triggered_supplemental" and depletion > raw:
            target_depletion = 0.5 * raw
            net_irrigation = max(0.0, depletion - target_depletion)
            depletion = target_depletion
        ks = 1.0 if depletion <= raw else max(0.0, min(1.0, (taw - depletion) / (taw - raw)))
        etc = float(kc) * eto
        eta = ks * etc
        depletion = min(taw, depletion + eta)
        records.append({
            "Date": date, "Precipitation (mm)": p, "ET0 FAO-56 (mm)": eto,
            "Kc": float(kc), "ETc potential (mm)": etc, "Stress coefficient Ks": ks,
            "ETa actual estimate (mm)": eta, "Water deficit (mm)": max(0.0, etc - eta),
            "Root-zone depletion (mm)": depletion, "Net irrigation (mm)": net_irrigation,
            "Gross irrigation estimate (mm)": net_irrigation / float(irrigation_efficiency),
            "TAW (mm)": taw, "RAW trigger (mm)": raw
        })
    return pd.DataFrame(records)
