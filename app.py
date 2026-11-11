import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="AGROVISION", page_icon="🌱", layout="wide")
st.title("🌱 AGROVISION")
st.caption("Agricultural decision support powered by NASA Earth observation data")
st.write("Explore local climate and vegetation indicators, then compare crop-rotation scenarios as an initial screening tool.")

@st.cache_data(ttl=3600, show_spinner=False)
def get_nasa_power(lat, lon):
    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    params = {"parameters":"T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,ALLSKY_SFC_SW_DWN","community":"AG","longitude":lon,"latitude":lat,"start":"20200101","end":"20251231","format":"JSON"}
    response = requests.get(url, params=params, timeout=90)
    response.raise_for_status()
    values = response.json()["properties"]["parameter"]
    frame = pd.DataFrame(values)
    frame.index = pd.to_datetime(frame.index, format="%Y%m%d")
    return frame.replace(-999, pd.NA)

@st.cache_data(ttl=86400, show_spinner=False)
def get_modis(lat, lon):
    url = "https://modis.ornl.gov/rst/api/v1/MOD13Q1/subset"
    params = {"latitude":lat,"longitude":lon,"startDate":"A2024001","endDate":"A2024091","kmAboveBelow":0,"kmLeftRight":0}
    response = requests.get(url, params=params, timeout=90)
    response.raise_for_status()
    records = {}
    for item in response.json().get("subset", []):
        day, band, vals = item.get("calendar_date"), item.get("band"), item.get("data", [])
        if day and vals:
            records.setdefault(day, {})[band] = vals[0]
    rows = []
    for day, bands in records.items():
        nir = bands.get("250m_16_days_NIR_reflectance")
        red = bands.get("250m_16_days_red_reflectance")
        quality = bands.get("250m_16_days_pixel_reliability")
        ndvi = (nir-red)/(nir+red) if nir is not None and red is not None and quality in (0,1) and nir+red != 0 else None
        rows.append({"Date":pd.to_datetime(day),"Quality":quality,"NDVI":ndvi})
    return pd.DataFrame(rows).sort_values("Date") if rows else pd.DataFrame()

with st.sidebar:
    st.header("Study area")
    lat = st.number_input("Latitude", -90.0, 90.0, -15.8, 0.01, format="%.4f")
    lon = st.number_input("Longitude", -180.0, 180.0, -47.0, 0.01, format="%.4f")
    st.divider()
    st.header("Farm context")
    irrigation = st.selectbox("Water availability", ["Rainfed","Supplemental irrigation","Irrigated"])
    soil = st.selectbox("Soil texture (local input)", ["Unknown","Sandy","Loamy","Clayey"])
    fertility = st.select_slider("Soil fertility (local input)", ["Low","Medium","High"], value="Medium")
    st.caption("Soil and management inputs are supplied by the user, not measured by NASA.")

tab1, tab2, tab3 = st.tabs(["Environmental dashboard","Rotation scenarios","Data & limitations"])
with tab1:
    st.subheader("NASA climate indicators")
    if st.button("Load environmental data", type="primary"):
        try:
            with st.spinner("Requesting NASA POWER and MODIS data..."):
                climate = get_nasa_power(lat, lon)
                modis = get_modis(lat, lon)
            st.session_state["climate"], st.session_state["modis"] = climate, modis
            st.session_state["coords"] = (lat, lon)
            st.success("Environmental data loaded.")
        except Exception as exc:
            st.error(f"Data request failed: {exc}")
    if "climate" in st.session_state and st.session_state.get("coords") == (lat, lon):
        climate = st.session_state["climate"]
        c1,c2,c3 = st.columns(3)
        c1.metric("Mean air temperature", f"{climate['T2M'].mean():.1f} °C")
        c2.metric("Total precipitation, 2020–2025", f"{climate['PRECTOTCORR'].sum():,.0f} mm")
        c3.metric("Mean solar radiation", f"{climate['ALLSKY_SFC_SW_DWN'].mean():.1f} kWh/m²/day")
        annual = climate[["PRECTOTCORR","T2M"]].resample("YE").agg({"PRECTOTCORR":"sum","T2M":"mean"})
        annual.index = annual.index.year
        st.markdown("**Annual climate series**")
        st.line_chart(annual)
        st.caption("Source: NASA POWER Daily API, Agroclimatology community, 2020–2025.")
        modis = st.session_state.get("modis", pd.DataFrame())
        st.markdown("**MODIS vegetation index (NDVI)**")
        if not modis.empty and modis["NDVI"].notna().any():
            st.line_chart(modis.set_index("Date")[["NDVI"]])
            st.caption("MODIS/Terra MOD13Q1, 16-day composites, 2024-01-01 to 2024-03-31; quality flags 0 and 1.")
        else:
            st.info("No usable MODIS observations were returned for this point and period.")
    else:
        st.info("Enter coordinates and click Load environmental data to query NASA.")

with tab2:
    st.subheader("Compare rotation strategies")
    st.warning("Prototype screening only: this transparent rule-based comparison is not a calibrated crop model, yield forecast, or agronomic prescription.")
    if "climate" not in st.session_state or st.session_state.get("coords") != (lat, lon):
        st.info("Load environmental data in the first tab before comparing scenarios.")
    else:
        climate = st.session_state["climate"]
        rain_year = climate["PRECTOTCORR"].resample("YE").sum().mean()
        temp = climate["T2M"].mean()
        rain_score = max(0,min(100,(rain_year/1200)*100))
        heat_score = max(0,min(100,100-abs(temp-23)*5))
        water_bonus = {"Rainfed":0,"Supplemental irrigation":8,"Irrigated":15}[irrigation]
        soil_bonus = {"Unknown":0,"Sandy":-5,"Loamy":8,"Clayey":2}[soil]
        fertility_bonus = {"Low":-8,"Medium":0,"High":6}[fertility]
        scenarios = [("A — Maize / common bean",0),("B — Soybean / sorghum",8),("C — Diversified rotation with cover crop",5)]
        rows = []
        for name, adjustment in scenarios:
            score = max(0,min(100,0.55*rain_score+0.45*heat_score+water_bonus+soil_bonus+fertility_bonus+adjustment))
            rows.append({"Scenario":name,"Screening score":round(score,1)})
        results = pd.DataFrame(rows).sort_values("Screening score",ascending=False)
        st.dataframe(results,use_container_width=True,hide_index=True)
        st.bar_chart(results.set_index("Scenario"))
        st.caption(f"Climate baseline: mean annual precipitation {rain_year:.0f} mm; mean temperature {temp:.1f} °C. Local inputs: {irrigation.lower()}, {soil.lower()} soil, {fertility.lower()} fertility.")
        st.info("Scenario adjustments are provisional demonstration weights. Validate with local agronomic data before real-world decisions.")

with tab3:
    st.subheader("Data sources and limitations")
    st.markdown("- **NASA POWER:** daily temperature, precipitation and solar radiation; queried live for selected coordinates.\n- **MODIS MOD13Q1:** vegetation index (NDVI) composites for Q1 2024; queried live.\n- **SMAP:** not yet connected in this public deployment. The earlier prototype used authenticated Earthdata access; its single snapshot is not a field measurement.\n- Satellite pixels represent broader areas and do not replace field sampling.\n- Rotation scores are exploratory; they do not estimate yield, profit, or crop suitability.")
    st.markdown("[NASA POWER API](https://power.larc.nasa.gov/) · [MODIS/ORNL DAAC](https://modis.ornl.gov/) · [NASA SMAP](https://smap.jpl.nasa.gov/)")
st.divider()
st.caption("AGROVISION · Prototype for NASA Space Apps Challenge 2026")
