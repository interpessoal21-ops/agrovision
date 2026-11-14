"""Global, source-attributed Earth observation integrations for GUMA."""
from __future__ import annotations
from datetime import date
from io import StringIO
import time
import pandas as pd
import requests

EARTH_SEARCH_URL = "https://earth-search.aws.element84.com/v1/search"
NASA_FIRMS_NOAA20_GLOBAL_24H = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_24h.csv"
# Backward-compatible alias; the endpoint is a rolling 24-hour product, not seven days.
NASA_FIRMS_NOAA20_GLOBAL_7D = NASA_FIRMS_NOAA20_GLOBAL_24H
IBGE_LOCALITIES_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"

def _bbox_geometry(latitude: float, longitude: float, half_width: float = 0.08) -> dict:
    lat, lon = float(latitude), float(longitude)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Latitude or longitude is outside valid WGS84 bounds.")
    if not (0 < float(half_width) <= 0.25):
        raise ValueError("half_width must be greater than zero and no larger than 0.25 degrees.")
    dx = dy = float(half_width)
    west, east = max(-180.0, lon-dx), min(180.0, lon+dx)
    south, north = max(-90.0, lat-dy), min(90.0, lat+dy)
    ring = [[west,south],[east,south],[east,north],[west,north],[west,south]]
    return {"type":"Polygon","coordinates":[ring]}

def search_sentinel2_scenes(latitude: float, longitude: float, start: date, end: date,
                            max_cloud_cover_pct: float=60, limit: int=20) -> pd.DataFrame:
    if start > end: raise ValueError("The start date must be on or before the end date.")
    payload={"collections":["sentinel-2-c1-l2a"],"intersects":_bbox_geometry(latitude,longitude),
             "datetime":f"{start.isoformat()}T00:00:00Z/{end.isoformat()}T23:59:59Z",
             "limit":max(1,min(int(limit),100)),"query":{"eo:cloud_cover":{"lte":float(max_cloud_cover_pct)}},
             "sortby":[{"field":"properties.datetime","direction":"desc"}]}
    response=requests.post(EARTH_SEARCH_URL,json=payload,
        headers={"Accept":"application/geo+json","Content-Type":"application/json"},timeout=45)
    response.raise_for_status()
    rows=[]
    for feature in response.json().get("features",[]):
        props=feature.get("properties") or {}
        rows.append({"scene_id":feature.get("id"),"date_utc":props.get("datetime"),
                     "platform":props.get("platform"),"tile_cloud_cover_pct":props.get("eo:cloud_cover"),
                     "mgrs_tile":props.get("grid:code"),"collection":feature.get("collection"),
                     "item_url":next((x.get("href") for x in feature.get("links",[]) if x.get("rel")=="self"),None)})
    frame=pd.DataFrame(rows)
    if not frame.empty:
        frame["date_utc"]=pd.to_datetime(frame["date_utc"],utc=True,errors="coerce")
        frame=frame.sort_values("date_utc",ascending=False).reset_index(drop=True)
    return frame

def load_nasa_firms_global_24h(region: str="Global",
    bbox: tuple[float,float,float,float] | None=None) -> tuple[pd.DataFrame,str]:
    """Load the global NOAA-20 VIIRS rolling 24-hour file; bbox=(west,south,east,north)."""
    response=requests.get(NASA_FIRMS_NOAA20_GLOBAL_24H,
        headers={"User-Agent":"GUMA-Earth-Intelligence/1.0"},timeout=120)
    response.raise_for_status()
    if not response.text.strip() or "<html" in response.text[:500].lower():
        raise ValueError("NASA FIRMS did not return the expected CSV data.")
    frame=pd.read_csv(StringIO(response.text),dtype={"acq_time":"string"})
    required={"latitude","longitude","acq_date","acq_time"}
    missing=required.difference(frame.columns)
    if missing: raise ValueError("NASA FIRMS CSV is missing required columns: "+", ".join(sorted(missing)))
    frame["latitude"]=pd.to_numeric(frame["latitude"],errors="coerce")
    frame["longitude"]=pd.to_numeric(frame["longitude"],errors="coerce")
    frame=frame.dropna(subset=["latitude","longitude"])
    if bbox is not None:
        west,south,east,north=map(float,bbox)
        if not (-180<=west<east<=180 and -90<=south<north<=90):
            raise ValueError("Invalid bbox. Expected west,south,east,north in WGS84.")
        frame=frame[frame["longitude"].between(west,east)&frame["latitude"].between(south,north)].copy()
    frame["acq_time"]=frame["acq_time"].str.zfill(4)
    frame["acquired_at_utc"]=pd.to_datetime(frame["acq_date"].astype(str)+" "+frame["acq_time"],
        format="%Y-%m-%d %H%M",errors="coerce",utc=True)
    frame=frame.sort_values("acquired_at_utc",ascending=False).reset_index(drop=True)
    frame["query_scope"]=region
    return frame,NASA_FIRMS_NOAA20_GLOBAL_24H

# Compatibility wrapper for older internal callers; this is not a seven-day dataset.
def load_nasa_firms_global_7d(region: str="Global",
    bbox: tuple[float,float,float,float] | None=None) -> tuple[pd.DataFrame,str]:
    return load_nasa_firms_global_24h(region, bbox)

def load_ibge_states() -> pd.DataFrame:
    """Brazil-only national territorial reference with one bounded retry."""
    last_error = None
    response = None
    for attempt in range(2):
        try:
            response = requests.get(
                IBGE_LOCALITIES_URL,
                params={"orderBy": "nome"},
                headers={"Accept": "application/json", "User-Agent": "GUMA-Earth-Intelligence/1.0"},
                timeout=(12, 25),
            )
            response.raise_for_status()
            break
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(1.5)
                continue
            raise requests.RequestException(
                f"IBGE Localities API unavailable after 2 attempts: {exc}"
            ) from exc
    if response is None:
        raise requests.RequestException(f"IBGE Localities API unavailable: {last_error}")
    rows = response.json()
    frame = pd.DataFrame([
        {"ibge_state_code": x.get("id"), "state": x.get("nome"), "uf": x.get("sigla")}
        for x in rows
    ])
    if frame.empty or not {"ibge_state_code", "state", "uf"}.issubset(frame.columns):
        raise ValueError("IBGE returned an unexpected state-localities schema.")
    if len(frame) != 27:
        raise ValueError(f"IBGE returned {len(frame)} federative units; expected 27.")
    return frame.sort_values("state").reset_index(drop=True)


def load_nasa_power_global_point(latitude: float, longitude: float,
                                 start: date, end: date) -> tuple[pd.DataFrame, dict]:
    """Daily NASA POWER agroclimatology at any global WGS84 point."""
    if start > end:
        raise ValueError("The start date must be on or before the end date.")
    if not (-90 <= float(latitude) <= 90 and -180 <= float(longitude) <= 180):
        raise ValueError("Coordinates must be valid WGS84 latitude/longitude.")
    if (end - start).days > 3660:
        raise ValueError("Select a maximum time window of ten years per request.")
    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    params = {
        "parameters": "T2M,T2M_MAX,T2M_MIN,T2MDEW,WS2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN",
        "community": "AG",
        "longitude": float(longitude),
        "latitude": float(latitude),
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
        "time-standard": "UTC",
    }
    response = requests.get(url, params=params, timeout=90)
    response.raise_for_status()
    payload = response.json()
    try:
        props = payload["properties"]
        raw = props["parameter"]
        units = props.get("parameter_information", {})
    except (KeyError, TypeError) as exc:
        raise ValueError("NASA POWER returned an unexpected response schema.") from exc
    frame = pd.DataFrame(raw).apply(pd.to_numeric, errors="coerce")
    frame.index = pd.to_datetime(frame.index, format="%Y%m%d", errors="coerce")
    frame.index.name = "date_utc"
    frame = frame.mask(frame == -999).dropna(how="all").sort_index()
    if frame.empty:
        raise ValueError("NASA POWER returned no valid observations for this point and period.")
    known_ag_units = {
        "T2M": "°C", "T2M_MAX": "°C", "T2M_MIN": "°C", "T2MDEW": "°C",
        "WS2M": "m/s", "PRECTOTCORR": "mm/day", "ALLSKY_SFC_SW_DWN": "MJ/m²/day",
    }
    returned_units = {
        k: v.get("units") for k, v in units.items()
        if isinstance(v, dict) and v.get("units")
    }
    parameter_units = {key: returned_units.get(key, unit) for key, unit in known_ag_units.items()
                       if key in frame.columns}
    metadata = {
        "source": "NASA POWER", "url": response.url,
        "latitude": float(latitude), "longitude": float(longitude),
        "community": "AG", "start": start.isoformat(), "end": end.isoformat(),
        "temporal_resolution": "daily", "time_standard": "UTC",
        "meteorology_grid_resolution": "0.5 x 0.625 degree",
        "solar_grid_resolution": "1 x 1 degree", "units": parameter_units,
        "parameter_dictionary_url": "https://power.larc.nasa.gov/docs/tutorials/parameters/",
        "time_standard_documentation": "https://power.larc.nasa.gov/docs/services/api/temporal/daily/",
        "retrieved_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
    }
    return frame, metadata
