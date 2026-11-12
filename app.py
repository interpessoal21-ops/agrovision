import streamlit as st
import pandas as pd
import requests
import folium
import io
import json
from datetime import datetime, timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
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

# Language preference is stored in the Streamlit session and works for visitors too.
if "agrovision_language" not in st.session_state:
    st.session_state["agrovision_language"] = "English"

def tx(en, pt):
    return pt if st.session_state.get("agrovision_language") == "Português" else en

def supabase_settings():
    """Read Supabase credentials from Streamlit Secrets without exposing them."""
    try:
        base_url = str(st.secrets.get("SUPABASE_URL", "")).strip().rstrip("/")
        candidates = [
            ("SUPABASE_PUBLISHABLE_KEY", str(st.secrets.get("SUPABASE_PUBLISHABLE_KEY", "")).strip()),
            ("SUPABASE_ANON_KEY", str(st.secrets.get("SUPABASE_ANON_KEY", "")).strip()),
            ("SUPABASE_KEY", str(st.secrets.get("SUPABASE_KEY", "")).strip()),
        ]
        # Prefer a valid modern publishable key, then a legacy anon JWT.
        for name, value in candidates:
            if value.startswith("sb_publishable_") or value.startswith("eyJ"):
                return base_url, value, name
        # Return the first configured value so validation can explain the mismatch.
        for name, value in candidates:
            if value:
                return base_url, value, name
        return base_url, "", "none"
    except Exception:
        return "", "", "unreadable"

def supabase_auth(endpoint, payload):
    base_url, anon_key, key_source = supabase_settings()
    if not base_url or not anon_key:
        raise RuntimeError("Email login is not configured yet. Guest access is available.")
    if not base_url.startswith("https://") or not base_url.endswith(".supabase.co"):
        raise RuntimeError("Supabase URL format looks incorrect. Use the Project URL without /rest/v1/.")
    if not (anon_key.startswith("sb_publishable_") or anon_key.startswith("eyJ")):
        if anon_key.startswith("sb_secret_"):
            detected = "Secret key (server-only), not a Publishable key"
        elif anon_key.startswith("sb_"):
            detected = "unrecognized sb_ key type"
        else:
            detected = "value without a recognized Supabase key prefix"
        raise RuntimeError(
            f"{key_source} is configured, but its value is {detected} "
            f"(length: {len(anon_key)}). In Streamlit Secrets, set "
            "SUPABASE_PUBLISHABLE_KEY to the project's Publishable key "
            "(starts with sb_publishable_). Do not use a Secret key."
        )
    response = requests.post(
        f"{base_url}/auth/v1/{endpoint}",
        json=payload,
        headers={"apikey": anon_key, "Content-Type": "application/json"},
        timeout=25,
    )
    try:
        data = response.json()
    except ValueError:
        data = {}
    if not response.ok:
        message = data.get("msg") or data.get("message") or data.get("error_description") or data.get("error") or "Authentication failed."
        # Include the HTTP status and any safe provider error code so setup
        # problems can be diagnosed without ever displaying the API key.
        error_code = data.get("code")
        detail = f" (code: {error_code})" if error_code else ""
        raise RuntimeError(f"Supabase returned HTTP {response.status_code}: {message}{detail}")
    return data

with st.sidebar:
    st.selectbox("Language / Idioma", ["English", "Português"], key="agrovision_language")

auth_mode = st.session_state.get("agrovision_auth_mode")
if auth_mode not in ("guest", "email"):
    st.markdown("### Welcome · Bem-vindo ao AGROVISION")
    st.write("Choose how you want to explore the platform.")
    login_tab, signup_tab = st.tabs(["✉️ Sign in", "Create account"])
    supabase_url, supabase_key, _supabase_key_source = supabase_settings()
    email_enabled = bool(supabase_url and supabase_key)

    if not email_enabled:
        st.info("Email access is being prepared. For now, you can explore the complete prototype as a visitor.")
    with login_tab:
        with st.form("agrovision_signin"):
            email = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True, disabled=not email_enabled)
        if submitted:
            try:
                result = supabase_auth("token?grant_type=password", {"email": email.strip(), "password": password})
                st.session_state["agrovision_auth_mode"] = "email"
                st.session_state["agrovision_access_token"] = result.get("access_token", "")
                st.session_state["agrovision_user_email"] = result.get("user", {}).get("email", email.strip())
                st.rerun()
            except Exception as exc:
                st.error(f"Could not sign in: {exc}")
    with signup_tab:
        with st.form("agrovision_signup"):
            new_email = st.text_input("Email address", key="signup_email", placeholder="you@example.com")
            new_password = st.text_input("Create password", type="password", key="signup_password", help="Use at least 8 characters.")
            confirm_password = st.text_input("Confirm password", type="password", key="signup_confirm")
            create_account = st.form_submit_button("Create account", use_container_width=True, disabled=not email_enabled)
        if create_account:
            if new_password != confirm_password:
                st.error("The passwords do not match.")
            elif len(new_password) < 8:
                st.error("Choose a password with at least 8 characters.")
            else:
                try:
                    result = supabase_auth("signup", {"email": new_email.strip(), "password": new_password})
                    if result.get("access_token"):
                        st.session_state["agrovision_auth_mode"] = "email"
                        st.session_state["agrovision_access_token"] = result["access_token"]
                        st.session_state["agrovision_user_email"] = result.get("user", {}).get("email", new_email.strip())
                        st.rerun()
                    else:
                        st.success("Account created. Check your email to confirm your address, then sign in here.")
                except Exception as exc:
                    st.error(f"Could not create account: {exc}")
    st.divider()
    st.markdown("**Or explore without an account**")
    if st.button("Continue as visitor →", type="primary", use_container_width=True):
        st.session_state["agrovision_auth_mode"] = "guest"
        st.rerun()
    st.caption("Visitor access does not require registration. Email authentication will become available after the project owner configures Supabase.")
    st.stop()

with st.sidebar:
    if st.session_state.get("agrovision_auth_mode") == "email":
        st.caption(f"Signed in as {st.session_state.get('agrovision_user_email', 'user')}")
    else:
        st.caption("Browsing as a visitor")
    if st.button("Sign out / Exit", use_container_width=True):
        for key in ("agrovision_auth_mode", "agrovision_access_token", "agrovision_user_email", "climate", "modis", "coords"):
            st.session_state.pop(key, None)
        st.rerun()

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
def get_modis(lat, lon, start_year=2020, end_year=2025):
    """Retrieve MOD13Q1 observations for a selectable year range."""
    url = "https://modis.ornl.gov/rst/api/v1/MOD13Q1/subset"
    end_day = 366 if end_year % 4 == 0 else 365
    params = {
        "latitude": lat, "longitude": lon,
        "startDate": f"A{int(start_year)}001",
        "endDate": f"A{int(end_year)}{end_day:03d}",
        "kmAboveBelow": 0, "kmLeftRight": 0
    }
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
        rows.append({
            "Date": pd.to_datetime(day), "Quality": quality,
            "Quality label": {0: "Good", 1: "Marginal", 2: "Snow/ice", 3: "Cloudy"}.get(quality, "Unknown"),
            "NDVI": ndvi
        })
    return pd.DataFrame(rows).sort_values("Date") if rows else pd.DataFrame()

st.subheader(tx("🗺️ Select your study area on the map", "🗺️ Selecione a área de estudo no mapa"))
st.caption(tx("Click anywhere on the map to choose a point. You can also enter exact coordinates in the Study area panel.", "Clique no mapa para escolher um ponto ou informe as coordenadas no painel Área de estudo."))
map_center = [st.session_state.get("lat_value", -15.8), st.session_state.get("lon_value", -47.0)]
study_map = folium.Map(location=map_center, zoom_start=5, control_scale=True, tiles="OpenStreetMap")
folium.CircleMarker(
    location=map_center, radius=8, color="#176b45", weight=3,
    fill=True, fill_color="#4da978", fill_opacity=0.9,
    tooltip="Current study area"
).add_to(study_map)
map_event = st_folium(study_map, height=360, use_container_width=True, returned_objects=["last_clicked"], key="agrovision_study_map")
if map_event and map_event.get("last_clicked"):
    clicked_lat = round(float(map_event["last_clicked"]["lat"]), 4)
    clicked_lon = round(float(map_event["last_clicked"]["lng"]), 4)
    clicked_point = (clicked_lat, clicked_lon)
    if clicked_point != st.session_state.get("last_map_click"):
        st.session_state["last_map_click"] = clicked_point
        st.session_state["lat_value"] = clicked_lat
        st.session_state["lon_value"] = clicked_lon
        st.rerun()

with st.sidebar:
    st.header(tx("Study area", "Área de estudo"))
    st.caption(tx("Enter the coordinates of the area you want to investigate.", "Informe as coordenadas da área que deseja investigar."))
    lat = st.number_input("Latitude", -90.0, 90.0, -15.8, 0.01, format="%.4f", key="lat_value", help="Decimal degrees. Locations south of the Equator use negative values.")
    lon = st.number_input("Longitude", -180.0, 180.0, -47.0, 0.01, format="%.4f", key="lon_value", help="Decimal degrees. Locations west of Greenwich use negative values.")
    st.divider()
    st.header(tx("Farm context", "Contexto da propriedade"))
    irrigation_options = ["Rainfed", "Supplemental irrigation", "Irrigated"]
    irrigation_labels = [tx("Rainfed", "Sequeiro"), tx("Supplemental irrigation", "Irrigação suplementar"), tx("Irrigated", "Irrigado")]
    irrigation_label = st.selectbox(tx("Water availability", "Disponibilidade de água"), irrigation_labels, help=tx("Choose the water supply used or planned for the study area.", "Selecione o regime hídrico da área."))
    irrigation = dict(zip(irrigation_labels, irrigation_options))[irrigation_label]
    soil_options = ["Unknown", "Sandy", "Loamy", "Clayey"]
    soil_labels = [tx("Unknown", "Desconhecida"), tx("Sandy", "Arenosa"), tx("Loamy", "Franca"), tx("Clayey", "Argilosa")]
    soil_label = st.selectbox(tx("Soil texture (local input)", "Textura do solo (dado local)"), soil_labels, help=tx("This is information supplied by you; it is not measured by NASA in this prototype.", "Informação fornecida pelo usuário; não é medida pela NASA."))
    soil = dict(zip(soil_labels, soil_options))[soil_label]
    fertility_labels = [tx("Low", "Baixa"), tx("Medium", "Média"), tx("High", "Alta")]
    fertility_label = st.select_slider(tx("Soil fertility (local input)", "Fertilidade do solo (dado local)"), fertility_labels, value=tx("Medium", "Média"), help=tx("A qualitative local estimate, not a satellite measurement.", "Estimativa qualitativa local, não é medição por satélite."))
    fertility = dict(zip(fertility_labels, ["Low", "Medium", "High"]))[fertility_label]
    st.caption(tx("Soil and management inputs are supplied by the user, not measured by NASA.", "Os dados de solo e manejo são informados pelo usuário, não medidos pela NASA."))
    st.info("First visit? Open the Start here tab for a short walkthrough.")

tab_help, tab1, tab2, tab3, tab4 = st.tabs([
    tx("👋 Start here · Help", "👋 Comece aqui · Ajuda"),
    tx("Environmental dashboard", "Painel ambiental"),
    tx("Rotation scenarios", "Cenários de rotação"),
    tx("Data & limitations", "Dados e limitações"),
    tx("Saved projects", "Projetos salvos")
])

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
    st.subheader(tx("Your study area, from space", "Sua área de estudo vista do espaço"))
    st.caption(tx("Live climate data from NASA POWER and vegetation observations from MODIS.", "Dados climáticos da NASA POWER e observações de vegetação do MODIS."))
    modis_years = st.slider(tx("MODIS observation period", "Período de observação MODIS"), 2020, 2025, (2023, 2025))
    if st.button("🛰️ Load environmental data", type="primary", use_container_width=True):
        try:
            with st.spinner(tx("Requesting NASA POWER and MODIS data...", "Consultando dados NASA POWER e MODIS...")):
                climate = get_nasa_power(lat, lon)
                modis = get_modis(lat, lon, modis_years[0], modis_years[1])
            st.session_state["climate"], st.session_state["modis"] = climate, modis
            st.session_state["coords"] = (lat, lon)
            st.session_state["modis_years"] = modis_years
            st.success(tx("Environmental data loaded.", "Dados ambientais carregados."))
        except Exception as exc:
            st.error(f"Data request failed: {exc}")
    if "climate" in st.session_state and st.session_state.get("coords") == (lat, lon):
        climate = st.session_state["climate"]
        c1,c2,c3 = st.columns(3)
        c1.metric(tx("Mean air temperature", "Temperatura média do ar"), f"{climate['T2M'].mean():.1f} °C")
        c2.metric(tx("Total precipitation, 2020–2025", "Precipitação acumulada, 2020–2025"), f"{climate['PRECTOTCORR'].sum():,.0f} mm")
        c3.metric(tx("Mean solar radiation", "Radiação solar média"), f"{climate['ALLSKY_SFC_SW_DWN'].mean():.1f} kWh/m²/day")
        annual = climate[["PRECTOTCORR", "T2M"]].resample("YE").agg({"PRECTOTCORR": "sum", "T2M": "mean"})
        annual.index = annual.index.year
        annual["Rainfall anomaly (%)"] = ((annual["PRECTOTCORR"] / annual["PRECTOTCORR"].mean()) - 1) * 100
        annual["Temperature anomaly (°C)"] = annual["T2M"] - annual["T2M"].mean()
        st.markdown("**" + tx("Annual climate series", "Série climática anual") + "**")
        st.line_chart(annual[["PRECTOTCORR", "T2M"]])
        anomaly_col1, anomaly_col2 = st.columns(2)
        anomaly_col1.markdown("**" + tx("Rainfall anomaly vs. 2020–2025 mean", "Anomalia de chuva vs. média 2020–2025") + "**")
        anomaly_col1.bar_chart(annual[["Rainfall anomaly (%)"]])
        anomaly_col2.markdown("**" + tx("Temperature anomaly vs. 2020–2025 mean", "Anomalia de temperatura vs. média 2020–2025") + "**")
        anomaly_col2.bar_chart(annual[["Temperature anomaly (°C)"]])
        st.caption("Source: NASA POWER Daily API · Agroclimatology community · 2020–2025. Anomalies are relative to this six-year baseline.")
        modis = st.session_state.get("modis", pd.DataFrame())
        st.markdown("**MODIS vegetation index (NDVI)**")
        if not modis.empty and modis["NDVI"].notna().any():
            st.line_chart(modis.set_index("Date")[["NDVI"]])
            st.caption(f"MODIS/Terra MOD13Q1 · 16-day composites · {st.session_state.get('modis_years', (2023, 2025))[0]}–{st.session_state.get('modis_years', (2023, 2025))[1]} · QA reliability 0 (good) and 1 (marginal).")
            st.dataframe(modis[["Date", "NDVI", "Quality label"]], use_container_width=True, hide_index=True)
        else:
            st.info("No usable MODIS observations were returned for this point and period.")
    else:
        st.info("Enter coordinates and click Load environmental data to query NASA.")

with tab2:
    st.subheader(tx("🌾 Explore crop-rotation strategies", "🌾 Explore estratégias de rotação de culturas"))
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
        scenario_catalog = {
            "A — Maize / common bean": 0,
            "B — Soybean / sorghum": 8,
            "C — Diversified rotation with cover crop": 5,
            "D — Soybean / maize / cover crop": 6,
        }
        selected_scenarios = st.multiselect(
            tx("Select rotation systems to compare", "Selecione os sistemas de rotação para comparar"),
            list(scenario_catalog),
            default=list(scenario_catalog)[:3]
        )
        scenarios = [(name, scenario_catalog[name]) for name in selected_scenarios]
        rows = []
        for name, adjustment in scenarios:
            climate_component = 0.55 * rain_score + 0.45 * heat_score
            local_context_component = water_bonus + soil_bonus + fertility_bonus
            score = max(0, min(100, climate_component + local_context_component + adjustment))
            rows.append({
                "Scenario": name, "Screening score": round(score, 1),
                "Climate component": round(climate_component, 1),
                "Local context adjustment": round(local_context_component, 1),
                "Scenario adjustment": adjustment
            })
        results = pd.DataFrame(rows).sort_values("Screening score",ascending=False)
        st.session_state["rotation_results"] = results
        st.dataframe(results, use_container_width=True, hide_index=True)
        st.bar_chart(results.set_index("Scenario")[["Screening score"]])
        with st.expander(tx("How is the screening score constructed?", "Como a pontuação exploratória é calculada?")):
            st.write(tx(
                "Climate component = 55% rainfall screening + 45% temperature screening. Local context adds transparent adjustments for irrigation, soil texture and fertility. Each illustrative rotation has a small demonstration adjustment. These weights are not calibrated against field outcomes.",
                "Componente climático = 55% da triagem de chuva + 45% da triagem de temperatura. O contexto local adiciona ajustes explícitos para irrigação, textura e fertilidade. Cada rotação ilustrativa recebe um pequeno ajuste demonstrativo. Esses pesos não foram calibrados com resultados de campo."
            ))
            st.dataframe(results.set_index("Scenario"), use_container_width=True)
        st.caption(f"Climate baseline: mean annual precipitation {rain_year:.0f} mm; mean temperature {temp:.1f} °C. Local inputs: {irrigation.lower()}, {soil.lower()} soil, {fertility.lower()} fertility.")
        st.info(tx("Scenario adjustments are provisional demonstration weights. Validate with local agronomic data before real-world decisions.", "Os ajustes dos cenários são pesos demonstrativos provisórios. Valide-os com dados agronômicos locais antes de qualquer decisão real."))

with tab3:
    st.subheader(tx("Data sources and limitations", "Fontes de dados e limitações"))
    st.markdown("- **NASA POWER:** daily temperature, precipitation and solar radiation; queried live for selected coordinates.\n- **MODIS MOD13Q1:** vegetation index (NDVI) composites for Q1 2024; queried live.\n- **SMAP:** not yet connected in this public deployment. The earlier prototype used authenticated Earthdata access; its single snapshot is not a field measurement.\n- Satellite pixels represent broader areas and do not replace field sampling.\n- Rotation scores are exploratory; they do not estimate yield, profit, or crop suitability.")
    st.markdown("[NASA POWER API](https://power.larc.nasa.gov/) · [MODIS/ORNL DAAC](https://modis.ornl.gov/) · [NASA SMAP](https://smap.jpl.nasa.gov/)")
# Data export and persistence tools are shared across authenticated users.
def supabase_rest_headers():
    base_url, public_key, _ = supabase_settings()
    token = st.session_state.get("agrovision_access_token", "")
    if not base_url or not public_key or not token:
        return None, None
    return base_url, {
        "apikey": public_key, "Authorization": f"Bearer {token}",
        "Content-Type": "application/json", "Prefer": "return=representation"
    }

def save_project_record(project_name, payload):
    base_url, headers = supabase_rest_headers()
    if not headers:
        raise RuntimeError("Sign in with an email account to save projects. Visitor sessions are temporary.")
    response = requests.post(
        f"{base_url}/rest/v1/farm_projects",
        headers=headers,
        json={"project_name": project_name, "latitude": float(lat), "longitude": float(lon), "payload": payload},
        timeout=25
    )
    if not response.ok:
        raise RuntimeError(f"Project save failed (HTTP {response.status_code}): {response.text[:300]}")
    return response.json()

def fetch_saved_projects():
    base_url, headers = supabase_rest_headers()
    if not headers:
        return []
    response = requests.get(
        f"{base_url}/rest/v1/farm_projects?select=id,project_name,latitude,longitude,created_at,payload&order=created_at.desc",
        headers=headers, timeout=25
    )
    if not response.ok:
        raise RuntimeError(f"Project list failed (HTTP {response.status_code}): {response.text[:300]}")
    return response.json()

def build_pdf_report(climate_frame, vegetation_frame, latitude, longitude, score_frame=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=38, leftMargin=38, topMargin=38, bottomMargin=38)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("AGROVISION — Environmental assessment", styles["Title"]),
        Paragraph(f"Study coordinates: {latitude:.4f}, {longitude:.4f}", styles["Normal"]),
        Paragraph(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("NASA POWER climate summary (2020–2025)", styles["Heading2"])
    ]
    summary = [
        ["Indicator", "Value"],
        ["Mean air temperature", f"{climate_frame['T2M'].mean():.2f} °C"],
        ["Accumulated precipitation", f"{climate_frame['PRECTOTCORR'].sum():.1f} mm"],
        ["Mean solar radiation", f"{climate_frame['ALLSKY_SFC_SW_DWN'].mean():.2f} kWh/m²/day"]
    ]
    table = Table(summary, colWidths=[270, 180])
    table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#164b35")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("GRID", (0,0), (-1,-1), .4, colors.HexColor("#cbd5ce")), ("PADDING", (0,0), (-1,-1), 7)]))
    story.extend([table, Spacer(1, 12), Paragraph("MODIS/Terra MOD13Q1 vegetation observations", styles["Heading2"])])
    if vegetation_frame is not None and not vegetation_frame.empty:
        valid = vegetation_frame["NDVI"].dropna()
        story.append(Paragraph(f"Valid observations: {len(valid)} · Mean NDVI: {valid.mean():.3f}" if len(valid) else "No quality-screened NDVI observations were available.", styles["Normal"]))
    else:
        story.append(Paragraph("No MODIS observations available for this analysis.", styles["Normal"]))
    if score_frame is not None and not score_frame.empty:
        story.extend([Spacer(1, 12), Paragraph("Illustrative crop-rotation screening", styles["Heading2"])])
        rows = [["Scenario", "Screening score"]] + [[str(row["Scenario"]), str(row["Screening score"])] for _, row in score_frame.iterrows()]
        score_table = Table(rows, colWidths=[320, 130])
        score_table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#164b35")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("GRID", (0,0), (-1,-1), .4, colors.HexColor("#cbd5ce")), ("PADDING", (0,0), (-1,-1), 7)]))
        story.append(score_table)
    story.extend([Spacer(1, 16), Paragraph("Scientific note: this report is exploratory. NDVI is not a direct measure of yield or crop health. Rotation screening scores are provisional, not calibrated crop models or agronomic recommendations. Verify findings with local field data.", styles["Italic"])])
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

with tab4:
    st.subheader(tx("Saved projects", "Projetos salvos"))
    if st.session_state.get("agrovision_auth_mode") != "email":
        st.info(tx("Sign in with an email account to save and retrieve projects. Visitor analyses remain in this browser session only.", "Entre com uma conta de e-mail para salvar e recuperar projetos. Análises de visitantes ficam apenas nesta sessão."))
    else:
        if st.button(tx("Refresh project list", "Atualizar lista de projetos")):
            try:
                st.session_state["saved_projects"] = fetch_saved_projects()
            except Exception as exc:
                st.error(str(exc))
        if "saved_projects" not in st.session_state:
            try:
                st.session_state["saved_projects"] = fetch_saved_projects()
            except Exception as exc:
                st.warning(tx("The project table may not be configured yet. Run the SQL setup described in the README.", "A tabela ainda pode não estar configurada. Execute o SQL descrito no README."))
                st.caption(str(exc))
        saved = st.session_state.get("saved_projects", [])
        if saved:
            st.dataframe(pd.DataFrame([{k: row.get(k) for k in ("project_name", "latitude", "longitude", "created_at")} for row in saved]), use_container_width=True, hide_index=True)
            project_options = {f"{row.get('project_name', 'Untitled')} · {row.get('created_at', '')[:10]}": row for row in saved}
            chosen_project = st.selectbox(tx("Choose a saved analysis", "Escolha uma análise salva"), list(project_options))
            if st.button(tx("Load selected analysis", "Carregar análise selecionada")):
                selected = project_options[chosen_project]
                payload = selected.get("payload") or {}
                climate_records = payload.get("climate_data", [])
                if climate_records:
                    restored = pd.DataFrame(climate_records)
                    restored["Date"] = pd.to_datetime(restored["Date"])
                    restored = restored.set_index("Date")
                    st.session_state["climate"] = restored
                    st.session_state["coords"] = (float(selected["latitude"]), float(selected["longitude"]))
                    st.session_state["lat_value"] = float(selected["latitude"])
                    st.session_state["lon_value"] = float(selected["longitude"])
                    vegetation_records = payload.get("modis_data", [])
                    restored_modis = pd.DataFrame(vegetation_records)
                    if not restored_modis.empty:
                        restored_modis["Date"] = pd.to_datetime(restored_modis["Date"])
                    st.session_state["modis"] = restored_modis
                    st.session_state["modis_years"] = tuple(payload.get("modis_years", [2023, 2025]))
                    st.success(tx("Saved analysis loaded. Open the dashboard tab to review it.", "Análise carregada. Abra o painel ambiental para revisá-la."))
                    st.rerun()
        else:
            st.caption(tx("No saved projects found yet.", "Nenhum projeto salvo ainda."))

if "climate" in st.session_state and st.session_state.get("coords") == (lat, lon):
    climate_for_export = st.session_state["climate"]
    modis_for_export = st.session_state.get("modis", pd.DataFrame())
    st.divider()
    st.subheader(tx("Export and save this analysis", "Exportar e salvar esta análise"))
    export_col1, export_col2, export_col3 = st.columns(3)
    with export_col1:
        csv_frame = climate_for_export.copy()
        csv_frame.index.name = "Date"
        st.download_button(tx("Download climate CSV", "Baixar CSV climático"), csv_frame.to_csv().encode("utf-8"), file_name="agrovision_nasa_power.csv", mime="text/csv", use_container_width=True)
    with export_col2:
        pdf_bytes = build_pdf_report(climate_for_export, modis_for_export, lat, lon, st.session_state.get("rotation_results"))
        st.download_button(tx("Download PDF report", "Baixar relatório PDF"), pdf_bytes, file_name="agrovision_report.pdf", mime="application/pdf", use_container_width=True)
    with export_col3:
        if st.button(tx("Save project to account", "Salvar projeto na conta"), use_container_width=True):
            project_name = st.session_state.get("project_name", f"Study {lat:.3f}, {lon:.3f}")
            payload = {
                "climate_rows": len(climate_for_export),
                "modis_rows": len(modis_for_export),
                "modis_years": st.session_state.get("modis_years"),
                "climate_data": climate_for_export.reset_index().rename(columns={"index": "Date"}).assign(Date=lambda frame: frame["Date"].astype(str)).to_dict(orient="records"),
                "modis_data": (modis_for_export.assign(Date=modis_for_export["Date"].astype(str)).to_dict(orient="records") if not modis_for_export.empty else []),
                "irrigation": irrigation, "soil": soil, "fertility": fertility,
                "saved_at": datetime.now(timezone.utc).isoformat()
            }
            try:
                save_project_record(project_name, payload)
                st.success(tx("Project saved to your account.", "Projeto salvo na sua conta."))
                st.session_state.pop("saved_projects", None)
            except Exception as exc:
                st.error(str(exc))
    st.text_input(tx("Project name", "Nome do projeto"), key="project_name", value=f"Study {lat:.3f}, {lon:.3f}")

st.divider()
st.caption("AGROVISION · Prototype for NASA Space Apps Challenge 2026")
