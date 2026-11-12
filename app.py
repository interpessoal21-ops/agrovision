import streamlit as st
import pandas as pd
import requests
import folium
import io
import json
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from streamlit_folium import st_folium

st.set_page_config(page_title="AGROVISION", page_icon="🌱", layout="wide")

st.markdown("""
<style>
    :root {
        --agro-bg: #0b1712; --agro-panel: #14251d; --agro-panel-2: #1a3025;
        --agro-green: #56a878; --agro-deep: #08130e; --agro-gold: #d6b36a;
        --agro-text: #e6eee8; --agro-muted: #a8b9ae; --agro-border: #2b4436;
    }
    .stApp {
        background:
          radial-gradient(ellipse at 85% 0%, rgba(76,139,98,.16) 0%, transparent 35%),
          linear-gradient(180deg, #102219 0%, #0b1712 420px);
        color: var(--agro-text);
    }
    [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stMainBlockContainer"] {
        background: transparent;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #102219 0%, #0d1b14 100%);
        border-right: 1px solid var(--agro-border);
    }
    [data-testid="stHeader"] { background: rgba(11,23,18,.88); }
    [data-testid="stToolbar"], [data-testid="stDecoration"] { background: transparent; }
    .block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1440px; }
    h1, h2, h3, h4, h5, h6, p, li, label, .stMarkdown, [data-testid="stCaptionContainer"] {
        color: var(--agro-text);
    }
    [data-testid="stCaptionContainer"], .stCaption, small { color: var(--agro-muted) !important; }
    a { color: #86d5a5 !important; }
    div.stButton > button[kind="primary"], .stFormSubmitButton > button {
        background: linear-gradient(105deg, #20583c, #347b52);
        color: #fff; border: 1px solid #4c9569;
        box-shadow: 0 5px 16px rgba(0,0,0,.22);
    }
    div.stButton > button {
        border-radius: 11px; font-weight: 650; color: var(--agro-text);
        background: #1b3025; border: 1px solid #385542;
    }
    div.stButton > button:hover { border-color: #79bd91; color: #fff; }
    [data-testid="stMetric"], div[data-testid="stMetric"] {
        background: #172b21; border: 1px solid var(--agro-border);
        padding: 1rem 1.1rem; border-radius: 14px;
        box-shadow: 0 3px 12px rgba(0,0,0,.16);
    }
    [data-testid="stMetricLabel"], [data-testid="stMetricValue"], [data-testid="stMetricDelta"] {
        color: var(--agro-text) !important;
    }
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #c4e6cf; }
    .hero {
        padding: 2rem 2.1rem; border-radius: 22px; color: white; position: relative; overflow: hidden;
        background: radial-gradient(circle at 88% 18%, rgba(214,179,106,.27), transparent 23%), linear-gradient(118deg, #081b12 0%, #174b31 58%, #286b46 100%);
        margin: .25rem 0 1.35rem 0; box-shadow: 0 14px 34px rgba(0,0,0,.28);
        border: 1px solid rgba(151,201,164,.18);
    }
    .hero h1 { color: white; font-size: 2.35rem; margin: 0 0 .35rem 0; letter-spacing: -.04em; }
    .hero p { color: #d5e9db; font-size: 1.02rem; margin: 0; max-width: 850px; }
    .eyebrow { color: #d6c18f; text-transform: uppercase; letter-spacing: .14em; font-size: .72rem; font-weight: 700; margin-bottom: .55rem; }
    .step-card {
        background: #172b21; border: 1px solid var(--agro-border); border-radius: 15px;
        padding: 1rem; min-height: 142px; box-shadow: 0 3px 12px rgba(0,0,0,.16);
    }
    .step-number {
        display: inline-flex; width: 30px; height: 30px; border-radius: 50%;
        align-items: center; justify-content: center; background: #244a34;
        color: #bce7c9; font-weight: 800; margin-bottom: .55rem;
    }
    .step-card strong { display: block; color: #d4eadb; margin-bottom: .3rem; }
    .step-card span { color: #afc2b5; font-size: .88rem; line-height: 1.4; }
    div[data-testid="stTabs"] button { color: #b9cabe; }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: #a8e0b9; border-bottom-color: #65b783;
    }
    .section-note {
        padding: .8rem 1rem; border-left: 4px solid #65b783; background: #193426;
        border-radius: 0 10px 10px 0; color: #c7dfce; margin: .5rem 0 1rem 0;
    }
    [data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div,
    [data-testid="stDateInput"] input, [data-testid="stNumberInput"] input {
        background: #172b21 !important; color: #e6eee8 !important;
        border-color: #385542 !important;
    }
    input, textarea { color: #e6eee8 !important; }
    [data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"] {
        background: #172b21 !important; color: #e6eee8 !important;
    }
    [data-testid="stDataFrame"], [data-testid="stTable"] {
        background: #14251d; border: 1px solid var(--agro-border); border-radius: 12px;
    }
    [data-testid="stAlert"] { background: #1b3025; color: #e6eee8; border: 1px solid #385542; }
    hr { border-color: #2b4436 !important; }
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
    st.markdown("### " + tx("Welcome to AGROVISION", "Bem-vindo ao AGROVISION"))
    st.write(tx("Choose how you want to explore the platform.", "Escolha como deseja explorar a plataforma."))
    login_tab, signup_tab = st.tabs([tx("✉️ Sign in", "✉️ Entrar"), tx("Create account", "Criar conta")])
    supabase_url, supabase_key, _supabase_key_source = supabase_settings()
    email_enabled = bool(supabase_url and supabase_key)

    if not email_enabled:
        st.info(tx("Email access is being prepared. For now, you can explore the complete prototype as a visitor.", "O acesso por e-mail está sendo preparado. Por enquanto, você pode explorar o protótipo como visitante."))
    with login_tab:
        with st.form("agrovision_signin"):
            email = st.text_input(tx("Email", "E-mail"), placeholder="you@example.com")
            password = st.text_input(tx("Password", "Senha"), type="password")
            submitted = st.form_submit_button(tx("Sign in", "Entrar"), use_container_width=True, disabled=not email_enabled)
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
            new_email = st.text_input(tx("Email address", "Endereço de e-mail"), key="signup_email", placeholder="you@example.com")
            new_password = st.text_input(tx("Create password", "Crie uma senha"), type="password", key="signup_password", help=tx("Use at least 8 characters.", "Use pelo menos 8 caracteres."))
            confirm_password = st.text_input(tx("Confirm password", "Confirme a senha"), type="password", key="signup_confirm")
            create_account = st.form_submit_button(tx("Create account", "Criar conta"), use_container_width=True, disabled=not email_enabled)
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
    st.markdown("**" + tx("Or explore without an account", "Ou explore sem uma conta") + "**")
    if st.button(tx("Continue as visitor →", "Continuar como visitante →"), type="primary", use_container_width=True):
        st.session_state["agrovision_auth_mode"] = "guest"
        st.rerun()
    st.caption(tx("Visitor access does not require registration. Email authentication will become available after the project owner configures Supabase.", "O acesso de visitante não exige cadastro. A autenticação por e-mail depende da configuração do Supabase pelo responsável pelo projeto."))
    st.stop()

with st.sidebar:
    if st.session_state.get("agrovision_auth_mode") == "email":
        st.caption(f"Signed in as {st.session_state.get('agrovision_user_email', 'user')}")
    else:
        st.caption(tx("Browsing as a visitor", "Navegando como visitante"))
    if st.button(tx("Sign out / Exit", "Sair da conta"), use_container_width=True):
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
    frame = pd.DataFrame(values).apply(pd.to_numeric, errors="coerce")
    frame.index = pd.to_datetime(frame.index, format="%Y%m%d")
    # NASA POWER uses -999 as a missing-value sentinel; convert it to NaN
    # while keeping the climate columns numeric for aggregation and charts.
    return frame.mask(frame == -999)

@st.cache_data(ttl=86400, show_spinner=False)
def get_modis(lat, lon, start_year=2020, end_year=2025):
    """Retrieve MOD13Q1 observations in batches of at most ten composites.

    ORNL DAAC's point-subset endpoint limits each request to ten MODIS dates.
    The dates endpoint is used to obtain the actual available composite dates.
    """
    api_root = "https://modis.ornl.gov/rst/api/v1/MOD13Q1"
    common = {"latitude": lat, "longitude": lon}
    dates_response = requests.get(
        f"{api_root}/dates",
        params=common,
        timeout=60
    )
    dates_response.raise_for_status()
    available = dates_response.json().get("dates", [])
    start_date = f"A{int(start_year)}001"
    end_day = 366 if end_year % 4 == 0 else 365
    end_date = f"A{int(end_year)}{end_day:03d}"
    selected_dates = [
        item.get("modis_date")
        for item in available
        if item.get("modis_date") and start_date <= item["modis_date"] <= end_date
    ]
    selected_dates = sorted(set(selected_dates))
    records = {}
    for offset in range(0, len(selected_dates), 10):
        date_batch = selected_dates[offset:offset + 10]
        params = {
            **common,
            "startDate": date_batch[0],
            "endDate": date_batch[-1],
            "kmAboveBelow": 0,
            "kmLeftRight": 0
        }
        response = requests.get(f"{api_root}/subset", params=params, timeout=90)
        response.raise_for_status()
        for item in response.json().get("subset", []):
            day, band, vals = item.get("calendar_date"), item.get("band"), item.get("data", [])
            if day and vals:
                records.setdefault(day, {})[band] = vals[0]
    rows = []
    for day, bands in records.items():
        nir = bands.get("250m_16_days_NIR_reflectance")
        red = bands.get("250m_16_days_red_reflectance")
        quality = bands.get("250m_16_days_pixel_reliability")
        valid_reflectance = (
            nir is not None and red is not None
            and nir >= -1000 and red >= -1000
            and nir + red != 0
        )
        ndvi = (
            (nir - red) / (nir + red)
            if valid_reflectance and quality in (0, 1)
            else None
        )
        rows.append({
            "Date": pd.to_datetime(day),
            "Quality": quality,
            "Quality label": {0: "Good", 1: "Marginal", 2: "Snow/ice", 3: "Cloudy"}.get(quality, "Unknown"),
            "NDVI": ndvi
        })
    return pd.DataFrame(rows).sort_values("Date") if rows else pd.DataFrame()

# Restore a saved project's coordinates before the sidebar widgets are instantiated.
if "pending_study_coords" in st.session_state:
    pending_lat, pending_lon = st.session_state.pop("pending_study_coords")
    st.session_state["lat_value"] = pending_lat
    st.session_state["lon_value"] = pending_lon

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
    st.info(tx("First visit? Open the Start here tab for a short walkthrough.", "Primeira visita? Abra a aba Comece aqui para ver um guia rápido."))

tab_help, tab1, tab2, tab3, tab4 = st.tabs([
    tx("👋 Start here · Help", "👋 Comece aqui · Ajuda"),
    tx("Environmental dashboard", "Painel ambiental"),
    tx("Rotation scenarios", "Cenários de rotação"),
    tx("Data & limitations", "Dados e limitações"),
    tx("Saved projects", "Projetos salvos")
])

with tab_help:
    st.header(tx("Your first steps", "Seus primeiros passos"))
    st.write(tx("New here? Follow this short path to get from a location to an informed exploration of the data.", "É sua primeira vez? Siga este roteiro para sair da escolha de um local e chegar à exploração dos dados."))
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
        3. Select maize, soybean and/or common bean, then choose an assumed sowing month.
        4. Review observed rainfall and temperature during complete historical crop-cycle windows.
        5. Compare those observations with published indicative crop-cycle and water-need ranges.

        The analysis does not rank crops. It is an initial climate-screening layer, not a calibrated crop model, yield forecast, soil-water balance or agronomic recommendation.
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
    st.subheader(tx("What the platform does — and does not do", "O que a plataforma faz — e o que não faz"))
    left, right = st.columns(2)
    with left:
        st.markdown("**AGROVISION can help you:**")
        st.markdown("- Explore climate indicators for a selected location.\n- View satellite-derived vegetation observations.\n- Compare historical climate during representative cycles of maize, soybean and common bean.\n- Review the reference ranges and assumptions behind each crop screen.")
    with right:
        st.markdown("**AGROVISION does not currently:**")
        st.markdown("- Measure soil properties directly.\n- Calculate effective rainfall or a complete soil-water balance.\n- Predict crop yield or farm profit.\n- Provide a certified planting recommendation.\n- Display SMAP data in this public deployment.")
    st.caption("AGROVISION · " + tx("First-visit guide · Prototype for NASA Space Apps Challenge 2026", "Guia inicial · Protótipo para o NASA Space Apps Challenge 2026"))

with tab1:
    st.subheader(tx("Your study area, from space", "Sua área de estudo vista do espaço"))
    st.caption(tx("Live climate data from NASA POWER and vegetation observations from MODIS.", "Dados climáticos da NASA POWER e observações de vegetação do MODIS."))
    analysis_mode = st.radio(
        tx("Analysis depth", "Profundidade da análise"),
        [tx("Quick · 3 years", "Rápida · 3 anos"), tx("Deep · 6 years", "Profunda · 6 anos")],
        horizontal=True,
        help=tx("Quick mode retrieves a shorter MODIS period. Deep mode retrieves the full 2020–2025 record.", "A rápida consulta um período MODIS menor. A profunda busca todo o histórico de 2020 a 2025.")
    )
    if analysis_mode == tx("Quick · 3 years", "Rápida · 3 anos"):
        modis_years = (2023, 2025)
        st.caption(tx("Faster retrieval: MODIS 2023–2025, with the same NASA POWER climate baseline.", "Consulta mais rápida: MODIS 2023–2025, mantendo a mesma série climática NASA POWER."))
    else:
        modis_years = (2020, 2025)
        st.caption(tx("Deeper retrieval: full MODIS 2020–2025 record. This may take longer on the first request.", "Consulta aprofundada: histórico MODIS completo de 2020–2025. A primeira consulta pode demorar mais."))
    if st.button(tx("🛰️ Load environmental data", "🛰️ Carregar dados ambientais"), type="primary", use_container_width=True):
        try:
            status = st.status(tx("Starting parallel data requests…", "Iniciando consultas paralelas…"), expanded=True)
            status.write(tx("NASA POWER: requesting daily climate series.", "NASA POWER: consultando a série climática diária."))
            status.write(tx("MODIS: retrieving vegetation observations.", "MODIS: buscando observações de vegetação."))
            with ThreadPoolExecutor(max_workers=2) as executor:
                climate_future = executor.submit(get_nasa_power, lat, lon)
                modis_future = executor.submit(get_modis, lat, lon, modis_years[0], modis_years[1])
                climate = climate_future.result()
                status.write(tx("NASA POWER data received.", "Dados NASA POWER recebidos."))
                modis = modis_future.result()
            st.session_state["climate"], st.session_state["modis"] = climate, modis
            st.session_state["coords"] = (lat, lon)
            st.session_state["modis_years"] = modis_years
            st.session_state["analysis_mode"] = "deep" if modis_years[0] == 2020 else "quick"
            status.update(label=tx("Environmental data loaded successfully.", "Dados ambientais carregados com sucesso."), state="complete", expanded=False)
            st.success(tx("Environmental data loaded.", "Dados ambientais carregados."))
        except Exception as exc:
            try:
                status.update(label=tx("Data request failed.", "Falha ao consultar os dados."), state="error", expanded=True)
            except Exception:
                pass
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
        st.markdown("**" + tx("MODIS vegetation index (NDVI)", "Índice de vegetação MODIS (NDVI)") + "**")
        if not modis.empty and modis["NDVI"].notna().any():
            st.line_chart(modis.set_index("Date")[["NDVI"]])
            st.caption(f"MODIS/Terra MOD13Q1 · 16-day composites · {st.session_state.get('modis_years', (2023, 2025))[0]}–{st.session_state.get('modis_years', (2023, 2025))[1]} · QA reliability 0 (good) and 1 (marginal).")
            st.dataframe(modis[["Date", "NDVI", "Quality label"]], use_container_width=True, hide_index=True)
        else:
            st.info(tx("No usable MODIS observations were returned for this point and period.", "Não foram encontradas observações MODIS válidas para este ponto e período."))
    else:
        st.info(tx("Enter coordinates and click Load environmental data to query NASA.", "Informe as coordenadas e clique em Carregar dados ambientais para consultar a NASA."))

# Crop screening uses crop-specific reference ranges and observed rainfall during
# a user-selected sowing window. It deliberately does not create a suitability score.
CROP_REFERENCE = {
    "Maize (grain)": {
        "pt": "Milho (grão)", "cycle_min": 125, "cycle_max": 180,
        "water_min": 500, "water_max": 800,
        "source": "FAO Irrigation and Drainage Paper 56 / Crop Water Needs"
    },
    "Soybean": {
        "pt": "Soja", "cycle_min": 135, "cycle_max": 150,
        "water_min": 450, "water_max": 700,
        "source": "FAO Crop Water Needs; Embrapa Ageitec"
    },
    "Common bean (dry)": {
        "pt": "Feijão-comum (grão)", "cycle_min": 95, "cycle_max": 110,
        "water_min": 300, "water_max": 500,
        "source": "FAO Crop Water Needs; Embrapa Arroz e Feijão"
    }
}

def calculate_crop_climate_windows(climate_frame, sowing_month, selected_crops):
    """Summarize observed daily climate over representative crop-cycle windows.

    Cycle length is the midpoint of a published indicative range. This is a
    climate-screening calculation, not a calibrated phenology or crop model.
    """
    rows = []
    annual_rows = []
    for crop in selected_crops:
        profile = CROP_REFERENCE[crop]
        cycle_days = round((profile["cycle_min"] + profile["cycle_max"]) / 2)
        for year in sorted(set(climate_frame.index.year)):
            start = pd.Timestamp(year=int(year), month=int(sowing_month), day=1)
            end = start + pd.Timedelta(days=cycle_days - 1)
            window = climate_frame.loc[start:end]
            # Only compare complete daily windows; do not silently treat missing
            # months or an incomplete final year as zero rainfall.
            if len(window) < cycle_days - 2:
                continue
            rainfall = window["PRECTOTCORR"].dropna()
            temperature = window["T2M"].dropna()
            radiation = window["ALLSKY_SFC_SW_DWN"].dropna()
            if len(rainfall) < cycle_days * 0.95:
                continue
            item = {
                "Crop": crop,
                "Year": int(year),
                "Cycle days (reference midpoint)": cycle_days,
                "Rainfall during cycle (mm)": float(rainfall.sum()),
                "Mean air temperature (°C)": float(temperature.mean()) if not temperature.empty else None,
                "Mean solar radiation (kWh/m²/day)": float(radiation.mean()) if not radiation.empty else None,
                "Indicative crop-water need (mm/cycle)": f'{profile["water_min"]}–{profile["water_max"]}'
            }
            annual_rows.append(item)
        crop_years = [r for r in annual_rows if r["Crop"] == crop]
        if crop_years:
            rain_values = [r["Rainfall during cycle (mm)"] for r in crop_years]
            temp_values = [r["Mean air temperature (°C)"] for r in crop_years if r["Mean air temperature (°C)"] is not None]
            rows.append({
                "Crop": crop,
                "Complete seasons": len(crop_years),
                "Reference cycle (days)": f'{profile["cycle_min"]}–{profile["cycle_max"]}',
                "Median cycle rainfall (mm)": round(float(pd.Series(rain_values).median()), 1),
                "Median mean temperature (°C)": round(float(pd.Series(temp_values).median()), 1) if temp_values else None,
                "Indicative crop-water need (mm/cycle)": f'{profile["water_min"]}–{profile["water_max"]}',
                "Reference": profile["source"]
            })
    return pd.DataFrame(rows), pd.DataFrame(annual_rows)

with tab2:
    st.subheader(tx("🌾 Crop-specific climate screening", "🌾 Análise climática por cultura"))
    st.markdown(
        '<div class="section-note">' +
        tx("Compare maize, soybean and common bean using observed daily climate during a selected planting window.",
           "Compare milho, soja e feijão-comum usando o clima diário observado durante uma janela de semeadura escolhida.") +
        '</div>', unsafe_allow_html=True
    )
    st.warning(tx(
        "This is a first agronomic screening layer, not a validated crop model or planting recommendation. It compares observed rainfall with published indicative crop-water ranges; rainfall is not the same as effective rainfall or crop evapotranspiration.",
        "Esta é uma primeira camada de análise agronômica, não um modelo de culturas validado nem uma recomendação de plantio. Ela compara a chuva observada com faixas indicativas publicadas de necessidade hídrica; chuva não equivale à chuva efetiva nem à evapotranspiração da cultura."
    ))
    if "climate" not in st.session_state or st.session_state.get("coords") != (lat, lon):
        st.info(tx("Load environmental data in the first tab before running the crop analysis.", "Carregue os dados ambientais na primeira aba antes de executar a análise das culturas."))
    else:
        climate = st.session_state["climate"]
        crop_names = list(CROP_REFERENCE.keys())
        crop_labels = [CROP_REFERENCE[c]["pt"] if st.session_state.get("agrovision_language") == "Português" else c for c in crop_names]
        selected_labels = st.multiselect(
            tx("Crops to analyze", "Culturas para analisar"),
            crop_labels,
            default=crop_labels
        )
        selected_crops = [crop_names[crop_labels.index(label)] for label in selected_labels]
        month_names_en = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        month_names_pt = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        month_names = month_names_pt if st.session_state.get("agrovision_language") == "Português" else month_names_en
        selected_month = st.selectbox(tx("Assumed sowing month", "Mês de semeadura considerado"), month_names, index=9)
        sowing_month = month_names.index(selected_month) + 1
        if selected_crops:
            summary, seasons = calculate_crop_climate_windows(climate, sowing_month, selected_crops)
            if summary.empty:
                st.warning(tx("No complete crop-cycle windows are available for this month in the loaded climate record. Choose an earlier sowing month or load a longer period.", "Não há janelas completas de ciclo disponíveis para este mês no histórico climático carregado. Escolha um mês de semeadura anterior ou carregue um período maior."))
            else:
                display_summary = summary.copy()
                if st.session_state.get("agrovision_language") == "Português":
                    display_summary["Crop"] = display_summary["Crop"].map({k: v["pt"] for k, v in CROP_REFERENCE.items()})
                    display_summary = display_summary.rename(columns={
                        "Crop": "Cultura", "Complete seasons": "Safras completas",
                        "Reference cycle (days)": "Ciclo de referência (dias)",
                        "Median cycle rainfall (mm)": "Mediana de chuva no ciclo (mm)",
                        "Median mean temperature (°C)": "Mediana da temperatura média (°C)",
                        "Indicative crop-water need (mm/cycle)": "Necessidade hídrica indicativa (mm/ciclo)",
                        "Reference": "Referência"
                    })
                st.dataframe(display_summary, use_container_width=True, hide_index=True)
                chart_data = summary.set_index("Crop")[["Median cycle rainfall (mm)"]]
                st.markdown("**" + tx("Observed rainfall during representative crop cycles", "Chuva observada durante ciclos representativos") + "**")
                st.bar_chart(chart_data)
                st.markdown("**" + tx("Season-by-season observations", "Observações por safra") + "**")
                season_view = seasons.copy()
                if st.session_state.get("agrovision_language") == "Português":
                    season_view["Crop"] = season_view["Crop"].map({k: v["pt"] for k, v in CROP_REFERENCE.items()})
                    season_view = season_view.rename(columns={
                        "Crop": "Cultura", "Year": "Ano de início",
                        "Cycle days (reference midpoint)": "Duração usada (dias)",
                        "Rainfall during cycle (mm)": "Chuva no ciclo (mm)",
                        "Mean air temperature (°C)": "Temperatura média (°C)",
                        "Mean solar radiation (kWh/m²/day)": "Radiação média (kWh/m²/dia)",
                        "Indicative crop-water need (mm/cycle)": "Necessidade hídrica indicativa (mm/ciclo)"
                    })
                st.dataframe(season_view, use_container_width=True, hide_index=True)
                st.caption(tx(
                    "Method: the midpoint of each published crop-cycle range defines the observation window beginning on day 1 of the selected month. Only complete daily windows are included. The table reports historical observations, not future weather.",
                    "Método: o ponto médio da faixa publicada de duração do ciclo define a janela de observação, iniciada no primeiro dia do mês escolhido. Apenas janelas diárias completas entram no cálculo. A tabela mostra observações históricas, não previsão do tempo."
                ))
                st.info(tx(
                    "Important: the FAO crop-water requirement is an indicative evapotranspiration-based range under defined crop conditions. Comparing it with gross rainfall alone does not calculate water deficit, irrigation demand, yield, or crop suitability. Effective rainfall, reference evapotranspiration, soil water storage, cultivar, planting date and local ZARC rules are still needed.",
                    "Importante: a necessidade hídrica da FAO é uma faixa indicativa baseada na evapotranspiração em condições definidas de cultivo. Compará-la apenas com a chuva bruta não calcula déficit hídrico, demanda de irrigação, produtividade ou aptidão. Ainda são necessários chuva efetiva, evapotranspiração de referência, armazenamento de água no solo, cultivar, data de plantio e regras locais do ZARC."
                ))
        else:
            st.info(tx("Select at least one crop to analyze.", "Selecione ao menos uma cultura para analisar."))

with tab3:
    st.subheader(tx("Data sources and limitations", "Fontes de dados e limitações"))
    st.markdown(tx(
        "- **NASA POWER:** daily temperature, precipitation and solar radiation; queried live for selected coordinates.\n- **MODIS MOD13Q1:** 16-day NDVI composites for the selected 2020–2025 period; queried live in batches that respect the ORNL request limit.\n- **Crop references:** indicative crop-cycle and seasonal water-need ranges from FAO and Embrapa publications.\n- **SMAP:** not yet connected in this public deployment; authenticated Earthdata access is still required.\n- Satellite pixels represent broader areas and do not replace field sampling.\n- The crop screen summarizes historical weather; it does not calculate effective rainfall, crop evapotranspiration, soil-water balance, yield, or planting suitability.",
        "- **NASA POWER:** temperatura diária, precipitação e radiação solar; consulta ao vivo para as coordenadas selecionadas.\n- **MODIS MOD13Q1:** composições de NDVI a cada 16 dias no período selecionado entre 2020 e 2025; consultas divididas em lotes conforme o limite da ORNL.\n- **Referências das culturas:** faixas indicativas de ciclo e necessidade hídrica sazonal de publicações da FAO e da Embrapa.\n- **SMAP:** ainda não conectado nesta versão pública; exige autenticação Earthdata.\n- Pixels de satélite representam áreas mais amplas e não substituem amostragem de campo.\n- A análise resume o clima histórico; não calcula chuva efetiva, evapotranspiração da cultura, balanço hídrico do solo, produtividade ou aptidão de plantio."
    ))
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

def build_pdf_report(climate_frame, vegetation_frame, latitude, longitude):
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
    story.extend([Spacer(1, 16), Paragraph("Scientific note: this report summarizes historical environmental observations. NDVI is not a direct measure of yield or crop health. Rainfall totals alone are not a soil-water balance or crop water deficit estimate. Crop reference ranges are indicative and must be checked against cultivar, local ZARC calendar, soil tests, management and field observations.", styles["Italic"])])\n    doc.build(story)
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
                    st.session_state["pending_study_coords"] = (float(selected["latitude"]), float(selected["longitude"]))
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
    st.text_input(tx("Project name", "Nome do projeto"), key="project_name", value=f"Study {lat:.3f}, {lon:.3f}")
    export_col1, export_col2, export_col3 = st.columns(3)
    with export_col1:
        csv_frame = climate_for_export.copy()
        csv_frame.index.name = "Date"
        st.download_button(tx("Download climate CSV", "Baixar CSV climático"), csv_frame.to_csv().encode("utf-8"), file_name="agrovision_nasa_power.csv", mime="text/csv", use_container_width=True)
        if not modis_for_export.empty:
            st.download_button(tx("Download MODIS CSV", "Baixar CSV do MODIS"), modis_for_export.to_csv(index=False).encode("utf-8"), file_name="agrovision_modis_ndvi.csv", mime="text/csv", use_container_width=True)
    with export_col2:
        pdf_bytes = build_pdf_report(climate_for_export, modis_for_export, lat, lon)
        st.download_button(tx("Download PDF report", "Baixar relatório PDF"), pdf_bytes, file_name="agrovision_report.pdf", mime="application/pdf", use_container_width=True)
    with export_col3:
        if st.button(tx("Save project to account", "Salvar projeto na conta"), use_container_width=True):
            project_name = st.session_state.get("project_name", f"Study {lat:.3f}, {lon:.3f}")
            climate_records = climate_for_export.reset_index().rename(columns={"index": "Date"})
            climate_records["Date"] = climate_records["Date"].astype(str)
            climate_records = climate_records.astype(object).where(pd.notna(climate_records), None)
            if not modis_for_export.empty:
                modis_records = modis_for_export.copy()
                modis_records["Date"] = modis_records["Date"].astype(str)
                modis_records = modis_records.astype(object).where(pd.notna(modis_records), None)
                modis_payload = modis_records.to_dict(orient="records")
            else:
                modis_payload = []
            payload = {
                "climate_rows": len(climate_for_export),
                "modis_rows": len(modis_for_export),
                "modis_years": st.session_state.get("modis_years"),
                "climate_data": climate_records.to_dict(orient="records"),
                "modis_data": modis_payload,
                "irrigation": irrigation, "soil": soil, "fertility": fertility,
                "saved_at": datetime.now(timezone.utc).isoformat()
            }
            try:
                save_project_record(project_name, payload)
                st.success(tx("Project saved to your account.", "Projeto salvo na sua conta."))
                st.session_state.pop("saved_projects", None)
            except Exception as exc:
                st.error(str(exc))
st.divider()
st.caption("AGROVISION · Crop-specific climate screening · Research and validation in progress")
