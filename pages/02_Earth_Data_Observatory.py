from datetime import date, timedelta
from io import StringIO
import pandas as pd
import requests
import streamlit as st
from guma_brand import apply_brand, render_brand_hero
import guma_earth_data as earth_data

# The deployed Streamlit image can temporarily lag behind GitHub main while
# Cloud rebuilds. Resolve capabilities independently so one missing helper
# never prevents the entire Observatory page from rendering.
def load_ibge_states():
    if hasattr(earth_data, "load_ibge_states"):
        return earth_data.load_ibge_states()
    response = requests.get("https://servicodados.ibge.gov.br/api/v1/localidades/estados",
                            params={"orderBy":"nome"}, timeout=30)
    response.raise_for_status()
    frame = pd.DataFrame([{"ibge_state_code":x.get("id"),"state":x.get("nome"),"uf":x.get("sigla")}
                          for x in response.json()])
    if len(frame) != 27:
        raise ValueError("IBGE returned an unexpected number of Brazilian federative units.")
    return frame.sort_values("state").reset_index(drop=True)

def load_nasa_firms_global_24h(region="Global", bbox=None):
    loader = getattr(earth_data, "load_nasa_firms_global_24h",
                     getattr(earth_data, "load_nasa_firms_global_7d", None))
    if loader:
        return loader(region, bbox)
    url = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_24h.csv"
    response = requests.get(url, timeout=120, headers={"User-Agent":"GUMA-Earth-Intelligence/1.0"})
    response.raise_for_status()
    if not response.text.strip() or "<html" in response.text[:500].lower():
        raise ValueError("NASA FIRMS did not return CSV data.")
    frame = pd.read_csv(StringIO(response.text))
    required = {"latitude","longitude","acq_date","acq_time"}
    if not required.issubset(frame.columns):
        raise ValueError("NASA FIRMS response is missing required columns.")
    for col in ("latitude","longitude"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame = frame.dropna(subset=["latitude","longitude"])
    if bbox is not None:
        west,south,east,north = map(float,bbox)
        if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
            raise ValueError("Invalid WGS84 bounding box.")
        frame = frame[frame.longitude.between(west,east) & frame.latitude.between(south,north)].copy()
    frame["acq_time"] = frame["acq_time"].astype(str).str.zfill(4)
    frame["acquired_at_utc"] = pd.to_datetime(frame["acq_date"].astype(str)+" "+frame["acq_time"],
                                               format="%Y-%m-%d %H%M", errors="coerce", utc=True)
    return frame.sort_values("acquired_at_utc", ascending=False).reset_index(drop=True), url

def load_nasa_power_global_point(latitude, longitude, start, end):
    if hasattr(earth_data, "load_nasa_power_global_point"):
        return earth_data.load_nasa_power_global_point(latitude, longitude, start, end)
    if start > end or not (-90 <= float(latitude) <= 90 and -180 <= float(longitude) <= 180):
        raise ValueError("Check the date range and global WGS84 coordinates.")
    if (end-start).days > 3660:
        raise ValueError("Select no more than ten years per request.")
    response = requests.get("https://power.larc.nasa.gov/api/temporal/daily/point", params={
        "parameters":"T2M,T2M_MAX,T2M_MIN,T2MDEW,WS2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN",
        "community":"AG","longitude":float(longitude),"latitude":float(latitude),
        "start":start.strftime("%Y%m%d"),"end":end.strftime("%Y%m%d"),"format":"JSON"
    }, timeout=90)
    response.raise_for_status()
    payload = response.json()
    raw = payload["properties"]["parameter"]
    frame = pd.DataFrame(raw).apply(pd.to_numeric, errors="coerce")
    frame.index = pd.to_datetime(frame.index, format="%Y%m%d", errors="coerce")
    frame.index.name = "date_utc"
    frame = frame.mask(frame == -999).dropna(how="all").sort_index()
    if frame.empty:
        raise ValueError("NASA POWER returned no valid daily observations.")
    info = payload["properties"].get("parameter_information", {})
    meta = {"source":"NASA POWER","url":response.url,"latitude":float(latitude),"longitude":float(longitude),
            "start":start.isoformat(),"end":end.isoformat(),"temporal_resolution":"daily",
            "units":{k:v.get("units") for k,v in info.items() if isinstance(v,dict)}}
    return frame, meta

def search_sentinel2_scenes(latitude, longitude, start, end, max_cloud_cover_pct=60, limit=20):
    if hasattr(earth_data, "search_sentinel2_scenes"):
        return earth_data.search_sentinel2_scenes(latitude, longitude, start, end, max_cloud_cover_pct, limit)
    if start > end or not (-90 <= float(latitude) <= 90 and -180 <= float(longitude) <= 180):
        raise ValueError("Check date range and global WGS84 coordinates.")
    h = 0.08
    ring = [[longitude-h,latitude-h],[longitude+h,latitude-h],[longitude+h,latitude+h],
            [longitude-h,latitude+h],[longitude-h,latitude-h]]
    payload = {"collections":["sentinel-2-c1-l2a"],"intersects":{"type":"Polygon","coordinates":[ring]},
               "datetime":f"{start.isoformat()}T00:00:00Z/{end.isoformat()}T23:59:59Z",
               "limit":max(1,min(int(limit),100)),
               "query":{"eo:cloud_cover":{"lte":float(max_cloud_cover_pct)}},
               "sortby":[{"field":"properties.datetime","direction":"desc"}]}
    response = requests.post("https://earth-search.aws.element84.com/v1/search",json=payload,
                             headers={"Accept":"application/geo+json"},timeout=45)
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


st.set_page_config(page_title="GUMA · Earth Data Observatory",page_icon="🌎",layout="wide")
apply_brand()
render_brand_hero()
st.markdown('<div class="guma-eyebrow">Earth observation · Global open data</div>',unsafe_allow_html=True)
st.title("Earth Data Observatory")
st.write("A planetary observatory for satellite acquisitions, active-fire observations and territorial data. Brazil is one regional lens within a global system—not the platform's geographic boundary.")
tab_sat,tab_fire,tab_climate,tab_ibge,tab_method=st.tabs(["Sentinel-2 · global search","NASA FIRMS · global fire","NASA POWER · climate","IBGE · Brazil","Methods & sources"])

with tab_sat:
    st.subheader("Global Sentinel-2 L2A scene discovery")
    st.caption("Earth Search STAC catalogue. Search any WGS84 coordinate; the rectangular search window is not a property boundary.")
    c1,c2,c3=st.columns(3)
    lat=c1.number_input("Latitude",min_value=-90.0,max_value=90.0,value=0.0,format="%.5f")
    lon=c2.number_input("Longitude",min_value=-180.0,max_value=180.0,value=0.0,format="%.5f")
    cloud=c3.slider("Maximum tile cloud cover (%)",0,100,40)
    today=date.today()
    d1,d2=st.columns(2)
    start=d1.date_input("Start date",value=today-timedelta(days=45),max_value=today)
    end=d2.date_input("End date",value=today,min_value=start,max_value=today)
    if st.button("Search global satellite catalogue",type="primary",key="guma_sentinel_search"):
        try:
            with st.spinner("Querying Sentinel-2 STAC…"):
                scenes=search_sentinel2_scenes(lat,lon,start,end,cloud)
            st.session_state["guma_sentinel_scenes"]=scenes
            st.session_state["guma_sentinel_query"]={"latitude":lat,"longitude":lon,"start":start.isoformat(),"end":end.isoformat(),"cloud_limit_pct":cloud}
        except Exception as exc: st.error(f"Sentinel-2 catalogue query failed: {exc}")
    scenes=st.session_state.get("guma_sentinel_scenes")
    if isinstance(scenes,pd.DataFrame):
        q=st.session_state.get("guma_sentinel_query",{})
        st.caption(f"Last search: {q.get('start')} to {q.get('end')} · {q.get('latitude')}, {q.get('longitude')}")
        if scenes.empty: st.info("No scenes matched. Widen the date range or cloud threshold.")
        else:
            st.metric("Scene/tile matches",len(scenes))
            st.dataframe(scenes,use_container_width=True,hide_index=True)
            st.download_button("Download scene metadata CSV",scenes.to_csv(index=False).encode("utf-8"),file_name="guma_sentinel2_global_scenes.csv",mime="text/csv")
            st.info("Cloud cover is a scene/tile estimate, not cloud share inside a field. This page discovers metadata; it does not calculate pixel-level NDVI/EVI/NDMI.")
    st.caption("Coverage: global catalogue, subject to Sentinel-2 acquisition and catalogue availability.")
    st.markdown("[Element 84 Earth Search STAC](https://earth-search.aws.element84.com/v1)")

with tab_fire:
    st.subheader("Global active-fire observations · NOAA-20 VIIRS")
    st.write("NASA FIRMS global rolling 24-hour CSV. Choose a global view or filter a WGS84 bounding box. Bounding boxes are not country borders.")
    scope=st.radio("Geographic scope",["Global","Custom bounding box"],horizontal=True,key="guma_firms_scope")
    bbox=None
    if scope=="Custom bounding box":
        a,b,c,d=st.columns(4)
        west=a.number_input("West longitude",-180.0,180.0,-74.0)
        south=b.number_input("South latitude",-90.0,90.0,-34.0)
        east=c.number_input("East longitude",-180.0,180.0,-34.0)
        north=d.number_input("North latitude",-90.0,90.0,6.0)
        bbox=(west,south,east,north)
    if st.button("Update global fire observations",type="primary",key="guma_firms_refresh"):
        try:
            with st.spinner("Downloading NASA FIRMS global 24-hour observations…"):
                fires,source_url=load_nasa_firms_global_24h(scope,bbox)
            st.session_state["guma_fires"]=fires
            st.session_state["guma_fires_source"]=source_url
            st.session_state["guma_fires_scope"]=scope
        except Exception as exc: st.error(f"NASA FIRMS query failed: {exc}")
    fires=st.session_state.get("guma_fires")
    if isinstance(fires,pd.DataFrame):
        a,b,c=st.columns(3)
        a.metric("Detections in selected scope",len(fires))
        if "frp" in fires.columns:
            frp=pd.to_numeric(fires["frp"],errors="coerce")
            b.metric("Sum of reported FRP (MW)",f"{frp.sum():,.1f}" if frp.notna().any() else "—")
        c.metric("Scope",str(st.session_state.get("guma_fires_scope","—")))
        if not fires.empty:
            st.map(fires[["latitude","longitude"]].head(10000),size=5)
            keep=[x for x in ["acquired_at_utc","latitude","longitude","confidence","frp","bright_ti4","satellite","instrument"] if x in fires.columns]
            st.dataframe(fires[keep].head(1000),use_container_width=True,hide_index=True)
            st.caption("Map displays at most 10,000 detections and table at most 1,000; CSV contains all returned rows.")
        else: st.info("No detections returned for this scope and period.")
        st.download_button("Download all returned detections CSV",fires.to_csv(index=False).encode("utf-8"),file_name="guma_nasa_firms_noaa20_global_24h.csv",mime="text/csv")
        st.caption("Source: "+str(st.session_state.get("guma_fires_source","")))
    st.markdown("[NASA FIRMS active-fire data](https://firms.modaps.eosdis.nasa.gov/)")


with tab_climate:
    st.subheader("Global daily agroclimatology · NASA POWER")
    st.write("Retrieve daily meteorological and solar variables for any point on Earth. This is gridded satellite/model-informed data, not a local weather-station observation.")
    c1,c2,c3=st.columns(3)
    p_lat=c1.number_input("Climate latitude",min_value=-90.0,max_value=90.0,value=0.0,format="%.5f",key="guma_power_lat")
    p_lon=c2.number_input("Climate longitude",min_value=-180.0,max_value=180.0,value=0.0,format="%.5f",key="guma_power_lon")
    p_end=c3.date_input("End date",value=date.today()-timedelta(days=5),max_value=date.today(),key="guma_power_end")
    p_start=st.date_input("Start date",value=p_end-timedelta(days=30),max_value=p_end,key="guma_power_start")
    st.caption("Daily parameters: air temperature, maximum/minimum temperature, dew point, wind speed, corrected precipitation and all-sky surface shortwave radiation.")
    if st.button("Retrieve global climate series",type="primary",key="guma_power_query"):
        try:
            with st.spinner("Querying NASA POWER…"):
                climate,meta=load_nasa_power_global_point(p_lat,p_lon,p_start,p_end)
            st.session_state["guma_power_frame"]=climate
            st.session_state["guma_power_meta"]=meta
        except Exception as exc: st.error(f"NASA POWER request failed: {exc}")
    climate=st.session_state.get("guma_power_frame")
    meta=st.session_state.get("guma_power_meta",{})
    if isinstance(climate,pd.DataFrame):
        st.caption(f"Retrieved at {meta.get('retrieved_at_utc')} · {meta.get('latitude')}, {meta.get('longitude')} · {meta.get('start')} to {meta.get('end')}")
        st.line_chart(climate[[x for x in ["T2M","T2M_MAX","T2M_MIN"] if x in climate.columns]])
        st.line_chart(climate[[x for x in ["PRECTOTCORR","WS2M","ALLSKY_SFC_SW_DWN"] if x in climate.columns]])
        a,b,c=st.columns(3)
        if "T2M" in climate:
            a.metric("Mean air temperature",f"{climate['T2M'].mean():.1f} °C")
        if "PRECTOTCORR" in climate:
            b.metric("Accumulated precipitation",f"{climate['PRECTOTCORR'].sum():.1f} mm")
        c.metric("Valid daily rows",len(climate))
        st.dataframe(climate,use_container_width=True)
        st.download_button("Download climate series CSV",climate.to_csv(index_label="date_utc").encode("utf-8"),file_name="guma_nasa_power_global_daily.csv",mime="text/csv")
        with st.expander("Data provenance and units"):
            st.json(meta)
    st.markdown("[NASA POWER API documentation](https://power.larc.nasa.gov/docs/tutorials/service-data-request/api/)")
    st.warning("NASA POWER meteorological grid resolution is approximately 0.5° × 0.625°; solar parameters are approximately 1° × 1°. Do not interpret these values as field-scale measurements.")

with tab_ibge:
    st.subheader("Brazil national territorial reference")
    st.info("IBGE is intentionally scoped to Brazil. It complements—not replaces—global territorial sources.")
    if st.button("Load Brazilian state codes",key="guma_ibge_states"):
        try:
            with st.spinner("Querying IBGE…"): st.session_state["guma_ibge_states"]=load_ibge_states()
        except Exception as exc: st.error(f"IBGE query failed: {exc}")
    states=st.session_state.get("guma_ibge_states")
    if isinstance(states,pd.DataFrame):
        st.metric("Brazilian federative units",len(states))
        st.dataframe(states,use_container_width=True,hide_index=True)
        st.download_button("Download IBGE state codes CSV",states.to_csv(index=False).encode("utf-8"),file_name="guma_ibge_uf.csv",mime="text/csv")
    st.markdown("[IBGE Localities API](https://servicodados.ibge.gov.br/api/docs/localidades)")

with tab_method:
    st.subheader("Provenance, coverage and limitations")
    st.markdown("""
    - **Sentinel-2:** global STAC discovery of L2A scene metadata; availability varies by acquisition and catalogue coverage.
    - **NASA POWER:** global daily agroclimatology at a point, with parameter units and native grid resolution disclosed.
    - **NASA FIRMS:** global NOAA-20 VIIRS rolling 24-hour active-fire detections. A hotspot is not automatically a confirmed fire perimeter, burned area or identified cause.
    - **IBGE:** Brazil-only national source, explicitly labelled.
    - **Spatial filters:** bounding boxes are search windows, not administrative boundaries.
    - **No causal inference:** spatial or temporal coincidence alone does not establish causality.
    - **No pixel indices yet:** this page does not claim to compute field-level vegetation indices.
    """)
    st.markdown("[NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) · [Earth Search](https://earth-search.aws.element84.com/) · [IBGE](https://www.ibge.gov.br/)")
