"""Global, source-attributed Earth observation integrations for GUMA."""
from __future__ import annotations
from datetime import date
from io import StringIO
import pandas as pd
import requests

EARTH_SEARCH_URL = "https://earth-search.aws.element84.com/v1/search"
NASA_FIRMS_NOAA20_GLOBAL_7D = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_7d.csv"
IBGE_LOCALITIES_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"

def _bbox_geometry(latitude: float, longitude: float, half_width: float = 0.08) -> dict:
    lat, lon = float(latitude), float(longitude)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Latitude or longitude is outside valid WGS84 bounds.")
    dx, dy = min(float(half_width), 0.25), min(float(half_width), 0.25)
    ring = [[lon-dx,lat-dy],[lon+dx,lat-dy],[lon+dx,lat+dy],[lon-dx,lat+dy],[lon-dx,lat-dy]]
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

def load_nasa_firms_global_7d(region: str="Global",
    bbox: tuple[float,float,float,float] | None=None) -> tuple[pd.DataFrame,str]:
    """Load the global NOAA-20 VIIRS rolling 7-day file; bbox=(west,south,east,north)."""
    response=requests.get(NASA_FIRMS_NOAA20_GLOBAL_7D,
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
    return frame,NASA_FIRMS_NOAA20_GLOBAL_7D

def load_ibge_states() -> pd.DataFrame:
    """Brazil-only national territorial reference."""
    response=requests.get(IBGE_LOCALITIES_URL,params={"orderBy":"nome"},
        headers={"Accept":"application/json"},timeout=30)
    response.raise_for_status()
    rows=response.json()
    frame=pd.DataFrame([{"ibge_state_code":x.get("id"),"state":x.get("nome"),"uf":x.get("sigla")} for x in rows])
    if frame.empty or not {"ibge_state_code","state","uf"}.issubset(frame.columns):
        raise ValueError("IBGE returned an unexpected state-localities schema.")
    return frame.sort_values("state").reset_index(drop=True)
