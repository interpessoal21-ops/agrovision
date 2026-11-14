from datetime import date, timedelta
import pandas as pd
import streamlit as st
from guma_brand import apply_brand, render_brand_hero
from guma_earth_data import load_ibge_states, load_nasa_firms_global_7d, search_sentinel2_scenes

st.set_page_config(page_title="GUMA · Earth Data Observatory",page_icon="🌎",layout="wide")
apply_brand()
render_brand_hero()
st.markdown('<div class="guma-eyebrow">Earth observation · Global open data</div>',unsafe_allow_html=True)
st.title("Earth Data Observatory")
st.write("A planetary observatory for satellite acquisitions, active-fire observations and territorial data. Brazil is one regional lens within a global system—not the platform's geographic boundary.")
tab_sat,tab_fire,tab_ibge,tab_method=st.tabs(["Sentinel-2 · global search","NASA FIRMS · global fire","IBGE · Brazil","Methods & sources"])

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
    st.write("NASA FIRMS global rolling 7-day CSV. Choose a global view or filter a WGS84 bounding box. Bounding boxes are not country borders.")
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
            with st.spinner("Downloading NASA FIRMS global 7-day observations…"):
                fires,source_url=load_nasa_firms_global_7d(scope,bbox)
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
        st.download_button("Download all returned detections CSV",fires.to_csv(index=False).encode("utf-8"),file_name="guma_nasa_firms_noaa20_global_7d.csv",mime="text/csv")
        st.caption("Source: "+str(st.session_state.get("guma_fires_source","")))
    st.markdown("[NASA FIRMS active-fire data](https://firms.modaps.eosdis.nasa.gov/)")

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
    - **NASA FIRMS:** global NOAA-20 VIIRS rolling 7-day active-fire detections. A hotspot is not automatically a confirmed fire perimeter, burned area or identified cause.
    - **IBGE:** Brazil-only national source, explicitly labelled.
    - **Spatial filters:** bounding boxes are search windows, not administrative boundaries.
    - **No causal inference:** spatial or temporal coincidence alone does not establish causality.
    - **No pixel indices yet:** this page does not claim to compute field-level vegetation indices.
    """)
    st.markdown("[NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) · [Earth Search](https://earth-search.aws.element84.com/) · [IBGE](https://www.ibge.gov.br/)")
