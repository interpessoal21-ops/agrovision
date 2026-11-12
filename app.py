import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="AGROVISION", page_icon="🌱", layout="wide")

st.markdown("""
<style>
    :root { --agro-green: #2f855a; --agro-deep: #164b35; --agro-light: #eaf5ee; }
    .stApp { background: linear-gradient(180deg, rgba(234,245,238,.55) 0%, rgba(248,250,248,0) 260px); }
    [data-testid="stSidebar"] { background: #f1f7f2; border-right: 1px solid #dce9df; }
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #164b35; }
    .hero {
        padding: 1.65rem 1.8rem; border-radius: 20px; color: white;
        background: linear-gradient(120deg, #164b35 0%, #28734e 58%, #65a879 100%);
        margin: .25rem 0 1.2rem 0; box-shadow: 0 8px 24px rgba(22,75,53,.13);
    }
    .hero h1 { color: white; font-size: 2.35rem; margin: 0 0 .35rem 0; letter-spacing: -.04em; }
    .hero p { color: #e5f4e9; font-size: 1.02rem; margin: 0; max-width: 850px; }
    .eyebrow { color: #c5e8d0; text-transform: uppercase; letter-spacing: .14em; font-size: .72rem; font-weight: 700; margin-bottom: .55rem; }
    .step-card {
        background: white; border: 1px solid #dce9df; border-radius: 15px;
        padding: 1rem; min-height: 142px; box-shadow: 0 3px 12px rgba(20,65,43,.045);
    }
    .step-number {
        display: inline-flex; width: 30px; height: 30px; border-radius: 50%;
        align-items: center; justify-content: center; background: #e3f2e8;
        color: #1d6843; font-weight: 800; margin-bottom: .55rem;
    }
    .step-card strong { display: block; color: #194d35; margin-bottom: .3rem; }
    .step-card span { color: #52665a; font-size: .88rem; line-height: 1.4; }
    div[data-testid="stMetric"] {
        background: white; border: 1px solid #e0ebe3; padding: 1rem 1.1rem;
        border-radius: 14px; box-shadow: 0 3px 12px rgba(20,65,43,.04);
    }
    div[data-testid="stMetricLabel"] { color: #547160; }
    div[data-testid="stTabs"] button[aria-selected="true"] { color: #1e7048; border-bottom-color: #2f855a; }
    .section-note {
        padding: .8rem 1rem; border-left: 4px solid #55a477; background: #edf6ef;
        border-radius: 0 10px 10px 0; color: #315b42; margin: .5rem 0 1rem 0;
    }
    @media (max-width: 700px) {
        .hero { padding: 1.2rem; border-radius: 14px; }
        .hero h1 { font-size: 1.8rem; }
    }
</style>
<div class="hero">
  <div class="eyebrow">NASA Earth observation · Agricultural insights</div>
  <h1>🌱 AGROVISION</h1>
  <p>Explore climate and vegetation data for your study area, then compare illustrative crop-rotation strategies in one place.</p>
</div>
""", unsafe_allow_html=True)

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

st.subheader("🗺️ Select your study area on the map")
st.caption("Click anywhere on the map to choose a point. You can also enter exact coordinates in the Study area panel.")
map_center = [st.session_state.get("lat_value", -15.8), st.session_state.get("lon_value", -47.0)]
study_map = folium.Map(location=map_center, zoom_start=5, control_scale=True, tiles="CartoDB positron")
folium.CircleMarker(
    location=map_center, radius=8, color="#176b45", weight=3,
    fill=True, fill_color="#4da978", fill_opacity=0.9,
    tooltip="Current study area"
).add_to(study_map)
map_event = st_folium(study_map, height=360, use_container_width=True, returned_objects=["last_clicked"], key="agrovision_study_map")
if map_event and map_event.get("last_clicked"):
    clicked_lat = round(float(map_event["last_clicked"]["lat"]), 4)
    clicked_lon = round(float(map_event["last_clicked"]["lng"]), 4)
    if (clicked_lat, clicked_lon) != (st.session_state.get("lat_value", -15.8), st.session_state.get("lon_value", -47.0)):
        st.session_state["lat_value"] = clicked_lat
        st.session_state["lon_value"] = clicked_lon
        st.rerun()

with st.sidebar:
    st.header("Study area")
    st.caption("Enter the coordinates of the area you want to investigate.")
    lat = st.number_input("Latitude", -90.0, 90.0, -15.8, 0.01, format="%.4f", key="lat_value", help="Decimal degrees. Locations south of the Equator use negative values.")
    lon = st.number_input("Longitude", -180.0, 180.0, -47.0, 0.01, format="%.4f", key="lon_value", help="Decimal degrees. Locations west of Greenwich use negative values.")
    st.divider()
    st.header("Farm context")
    irrigation = st.selectbox("Water availability", ["Rainfed","Supplemental irrigation","Irrigated"], help="Choose the water supply used or planned for the study area.")
    soil = st.selectbox("Soil texture (local input)", ["Unknown","Sandy","Loamy","Clayey"], help="This is information supplied by you; it is not measured by NASA in this prototype.")
    fertility = st.select_slider("Soil fertility (local input)", ["Low","Medium","High"], value="Medium", help="A qualitative local estimate, not a satellite measurement.")
    st.caption("Soil and management inputs are supplied by the user, not measured by NASA.")
    st.info("First visit? Open the Start here tab for a short walkthrough.")

tab_help, tab1, tab2, tab3 = st.tabs(["👋 Start here · Help","Environmental dashboard","Rotation scenarios","Data & limitations"])

with tab_help:
    st.header("Your first steps")
    st.write("New here? Follow this short path to get from a location to an informed exploration of the data.")
    st.markdown("""
    <div class="step-card" style="min-height:0; margin-bottom:1rem">
      <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:.65rem">
        <div><div class="step-number">1</div><strong>Locate</strong><span>Enter farm coordinates</span></div>
        <div><div class="step-number">2</div><strong>Describe</strong><span>Add local farm context</span></div>
        <div><div class="step-number">3</div><strong>Explore</strong><span>Load NASA indicators</span></div>
        <div><div class="step-number">4</div><strong>Compare</strong><span>Review rotation scenarios</span></div>
        <div><div class="step-number">5</div><strong>Interpret</strong><span>Check limits and assumptions</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="section-note">You do not need to know everything before starting. Open each step below for a short explanation, and use the question-mark tips beside fields whenever you need them.</div>', unsafe_allow_html=True)

    with st.expander("1. Choose your study area", expanded=True):
        st.markdown("""
        - In the **Study area** panel on the left, enter the latitude and longitude of the farm or area you want to study.
        - Use decimal degrees, not degrees/minutes/seconds.
        - South of the Equator = negative latitude. North = positive latitude.
        - West of Greenwich = negative longitude. East = positive longitude.
        - Make sure the point represents the agricultural area you are investigating. A point in a nearby city may describe a different environment.
        """)
        st.caption("Tip: use a trusted map or GPS tool to obtain the farm coordinates. The default coordinates are only a starting point, not a recommended farm location.")

    with st.expander("2. Describe the farm context"):
        st.markdown("""
        These options help frame the exploratory rotation comparison:
        - **Rainfed:** crops depend mainly on rainfall.
        - **Supplemental irrigation:** irrigation is used to complement rainfall when needed.
        - **Irrigated:** irrigation is a regular part of the production system.
        - **Sandy / Loamy / Clayey:** choose the closest known soil texture. If you do not know it, leave **Unknown**.
        - **Soil fertility:** choose a low, medium, or high qualitative estimate based on local knowledge or soil analysis.
        """)
        st.warning("These are user-provided context values. AGROVISION does not measure soil texture or fertility from NASA data.")

    with st.expander("3. Load the environmental data"):
        st.markdown("""
        1. Open the **Environmental dashboard** tab.
        2. Check the coordinates in the left panel.
        3. Click **Load environmental data**.
        4. Wait for the NASA POWER and MODIS requests to finish.
        5. Review the indicators and time series displayed on the dashboard.

        NASA POWER provides the climate series for 2020–2025. The current MODIS request retrieves vegetation observations for the first quarter of 2024.
        """)
        st.info("The first request can take a little time because the platform retrieves data from external NASA-related services. Repeated requests may be faster because results are temporarily cached.")

    with st.expander("4. Understand the environmental indicators"):
        st.markdown("""
        - **Mean air temperature:** average daily near-surface air temperature for the retrieved period.
        - **Total precipitation:** accumulated precipitation across the 2020–2025 dataset. It is not the rainfall for a single year.
        - **Mean solar radiation:** average daily solar energy reaching the surface in the retrieved period.
        - **Annual climate series:** shows how annual precipitation totals and mean temperature vary over time.
        - **NDVI:** a satellite-derived vegetation greenness indicator. It can help observe vegetation patterns, but it does not identify a crop or prove that a field is healthy or productive.
        """)
        st.caption("Clouds, mixed land cover, pixel size, observation dates, and data quality can affect satellite indicators. Interpret them together with field information.")

    with st.expander("5. Compare crop-rotation scenarios"):
        st.markdown("""
        1. First load the environmental data in the dashboard.
        2. Open **Rotation scenarios**.
        3. Review the three illustrative strategies: maize/common bean, soybean/sorghum, and a diversified rotation with a cover crop.
        4. Compare their screening scores and the bar chart.
        5. Read the note below the results before drawing conclusions.

        The score is a transparent, provisional rule-based screening exercise. It is not a calibrated crop model, yield forecast, profitability estimate, or agronomic recommendation. A higher score does not guarantee a better harvest.
        """)

    with st.expander("6. Common questions and troubleshooting"):
        st.markdown("""
        **The dashboard says data could not be loaded.**
        - Check your internet connection and confirm the coordinates are valid.
        - Try again after a short wait. The external data service may be temporarily unavailable.
        - If the problem continues, note the error message and report it to the project team.

        **The MODIS chart is empty.**
        - The selected point or observation period may not have usable observations.
        - Cloud cover and pixel-quality flags can reduce the number of valid observations.

        **Why can I not see SMAP data?**
        - SMAP is not yet connected in this public version. The platform must not present an unavailable dataset as if it had been measured.

        **Can I use the score to decide what to plant?**
        - No. Use it only to explore the prototype. Real decisions require local soil tests, crop calendars, water availability, management information, and advice from qualified agronomists.
        """)

    st.divider()
    st.subheader("What the platform does — and does not do")
    left, right = st.columns(2)
    with left:
        st.markdown("**AGROVISION can help you:**")
        st.markdown("- Explore climate indicators for a selected location.\n- View satellite-derived vegetation observations.\n- Compare illustrative crop-rotation scenarios.\n- Understand where Earth-observation data can support agricultural analysis.")
    with right:
        st.markdown("**AGROVISION does not currently:**")
        st.markdown("- Measure the soil directly.\n- Predict crop yield or farm profit.\n- Provide a certified planting recommendation.\n- Display SMAP data in this public deployment.")
    st.caption("AGROVISION · First-visit guide · Prototype for NASA Space Apps Challenge 2026")

with tab1:
    st.subheader("Your study area, from space")
    st.caption("Live climate data from NASA POWER and vegetation observations from MODIS.")
    if st.button("🛰️ Load environmental data", type="primary", use_container_width=True):
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
    st.subheader("🌾 Explore crop-rotation strategies")
    st.markdown('<div class="section-note">Compare three illustrative approaches using the same climate baseline and the farm context entered in the sidebar.</div>', unsafe_allow_html=True)
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
