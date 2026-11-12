import streamlit as st
import pandas as pd
from agrovision_validation import paired_validation_metrics
from agrovision_agronomy import fao56_reference_et0, crop_coefficient_curve, simulate_root_zone_balance
from agrovision_zarc import list_zarc_resources, load_zarc_csv, find_column, unique_values, filter_zarc_rows, decendio_columns, expand_decendios, crop_matches_app_crop
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
  <p>Explore climate, vegetation and crop-water indicators for your selected study area.</p>
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
        st.info(tx("Email access is being prepared. For now, you can explore the platform as a visitor.", "O acesso por e-mail está sendo preparado. Por enquanto, você pode explorar o protótipo como visitante."))
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
    params = {"parameters":"T2M,T2M_MAX,T2M_MIN,T2MDEW,WS2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN","community":"AG","longitude":lon,"latitude":lat,"start":"20200101","end":"20251231","format":"JSON"}
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
    elevation_m = st.number_input(tx("Elevation (m above sea level)", "Altitude (m acima do nível do mar)"), -500.0, 9000.0, 100.0, 1.0, key="elevation_m", help=tx("Required by FAO-56 atmospheric pressure and clear-sky radiation calculations. Enter a reliable local elevation.", "Necessária nos cálculos de pressão atmosférica e radiação de céu claro FAO-56. Informe uma altitude local confiável."))
    st.divider()
    st.header(tx("Farm context", "Contexto da propriedade"))
    irrigation_options = ["Rainfed", "Supplemental irrigation", "Irrigated"]
    irrigation_labels = [tx("Rainfed", "Sequeiro"), tx("Supplemental irrigation", "Irrigação suplementar"), tx("Irrigated", "Irrigado")]
    irrigation_label = st.selectbox(tx("Water availability", "Disponibilidade de água"), irrigation_labels, help=tx("Choose the water supply used or planned for the study area.", "Selecione o regime hídrico da área."))
    irrigation = dict(zip(irrigation_labels, irrigation_options))[irrigation_label]
    soil_options = ["Unknown", "Sandy", "Loamy", "Clayey"]
    soil_labels = [tx("Unknown", "Desconhecida"), tx("Sandy", "Arenosa"), tx("Loamy", "Franca"), tx("Clayey", "Argilosa")]
    soil_label = st.selectbox(tx("Soil texture (local input)", "Textura do solo (dado local)"), soil_labels, help=tx("This is information supplied by you; it is not measured by NASA in this platform.", "Informação fornecida pelo usuário; não é medida pela NASA."))
    soil = dict(zip(soil_labels, soil_options))[soil_label]
    fertility_labels = [tx("Low", "Baixa"), tx("Medium", "Média"), tx("High", "Alta")]
    fertility_label = st.select_slider(tx("Soil fertility (local input)", "Fertilidade do solo (dado local)"), fertility_labels, value=tx("Medium", "Média"), help=tx("A qualitative local estimate, not a satellite measurement.", "Estimativa qualitativa local, não é medição por satélite."))
    fertility = dict(zip(fertility_labels, ["Low", "Medium", "High"]))[fertility_label]
    st.caption(tx("Soil and management inputs are supplied by the user, not measured by NASA.", "Os dados de solo e manejo são informados pelo usuário, não medidos pela NASA."))
    st.info(tx("First visit? Open the Start here tab for a short walkthrough.", "Primeira visita? Abra a aba Comece aqui para ver um guia rápido."))

tab_help, tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    tx("👋 Start here · Help", "👋 Comece aqui · Ajuda"),
    tx("Environmental dashboard", "Painel ambiental"),
    tx("Crop analysis", "Análise de culturas"),
    tx("Data & limitations", "Dados e limitações"),
    tx("Saved projects", "Projetos salvos"),
    tx("Scientific validation", "Validação científica"),
    tx("📚 Knowledge", "📚 Conhecimento")
])


with tab6:
    st.header(tx("AGROVISION Knowledge", "Conhecimento AGROVISION"))
    st.write(tx(
        "A practical science library for understanding the data behind agricultural decisions.",
        "Uma biblioteca científica prática para entender os dados por trás das análises agrícolas."
    ))
    st.markdown(
        '<div class="section-note">Material educativo e referências técnicas. O conteúdo explica métodos e fontes; não substitui análise local, assistência técnica ou recomendação agronômica.</div>',
        unsafe_allow_html=True
    )

    knowledge_items = [
        {
            "title": "NASA POWER: clima em escala global",
            "topic": "NASA e dados climáticos",
            "kind": "Fonte institucional",
            "summary": "O NASA POWER disponibiliza séries meteorológicas e de radiação derivadas de observações por satélite e modelos. Os dados ajudam a caracterizar o contexto climático de um ponto, mas não equivalem a uma estação instalada dentro da propriedade.",
            "details": "Antes de interpretar uma série, confira variável, unidade, período, resolução espacial e valores ausentes. Produtos em grade representam uma área e podem divergir de medições locais por relevo, altitude, cobertura do solo e eventos convectivos. Para decisões operacionais, compare com estações próximas e documente a distância e a diferença de altitude.",
            "source": "NASA POWER — Data Access Viewer e documentação",
            "url": "https://power.larc.nasa.gov/docs/",
            "related": "Painel ambiental · Validação científica"
        },
        {
            "title": "ET₀, ETc e o método FAO-56",
            "topic": "Água e evapotranspiração",
            "kind": "Explicação técnica",
            "summary": "A evapotranspiração de referência (ET₀) representa a demanda evaporativa da atmosfera sobre uma superfície de referência. A evapotranspiração da cultura (ETc) é estimada, em condições padrão, por ETc = Kc × ET₀.",
            "details": "O método FAO Penman–Monteith estima ET₀ a partir de radiação, temperatura, umidade e vento. A qualidade do resultado depende das unidades, da altura de medição do vento, da pressão atmosférica e da consistência dos dados meteorológicos. Kc varia conforme cultura, estádio fenológico, manejo e clima. ETc padrão não representa automaticamente a evapotranspiração real sob estresse hídrico.",
            "source": "FAO Irrigation and Drainage Paper 56",
            "url": "https://www.fao.org/4/X0490E/X0490E00.htm",
            "related": "Análise de culturas · Balanço hídrico"
        },
        {
            "title": "Balanço hídrico na zona radicular",
            "topic": "Água e evapotranspiração",
            "kind": "Explicação técnica",
            "summary": "Um balanço hídrico acompanha entradas e saídas de água no solo ao longo do tempo. A chuva efetiva e a irrigação podem repor armazenamento; a evapotranspiração da cultura reduz a água disponível.",
            "details": "Modelos de reservatório na zona radicular dependem da capacidade de água disponível do solo, profundidade efetiva das raízes, fração de depleção, coeficientes da cultura, armazenamento inicial e regras para escoamento e drenagem. Parâmetros genéricos são hipóteses de cenário, não medições. Resultados devem ser confrontados com umidade do solo, manejo observado e dados de campo.",
            "source": "FAO-56 — Crop evapotranspiration",
            "url": "https://www.fao.org/4/X0490E/X0490E00.htm",
            "related": "Análise de culturas"
        },
        {
            "title": "ZARC: risco climático e calendário de plantio",
            "topic": "ZARC e planejamento",
            "kind": "Fonte oficial",
            "summary": "O Zoneamento Agrícola de Risco Climático identifica períodos de semeadura associados a níveis de risco para combinações específicas de município, cultura, grupo de cultivar e tipo de solo.",
            "details": "A consulta correta exige conferir a portaria vigente para a safra e a combinação exata de município, cultura, ciclo ou grupo de cultivar e classe de solo. As faixas de risco divulgadas pelo programa não são uma previsão do tempo nem uma garantia de produtividade. O enquadramento oficial deve ser confirmado no sistema e na portaria aplicável.",
            "source": "MAPA — ZARC / SISZARC",
            "url": "https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico",
            "related": "Fluxo ZARC"
        },
        {
            "title": "MODIS e NDVI: o que a vegetação revela",
            "topic": "Sensoriamento remoto",
            "kind": "Explicação técnica",
            "summary": "O NDVI é calculado pela diferença normalizada entre a reflectância no infravermelho próximo e no vermelho. Ele é usado como indicador da atividade e do verdor da vegetação.",
            "details": "NDVI não identifica sozinho a cultura, a causa de uma anomalia, a presença de doença ou a produtividade. Solo exposto, nuvens, sombra, água, estádio fenológico e saturação em vegetação densa influenciam a interpretação. Verifique a qualidade do pixel e combine séries temporais com calendário agrícola, imagens de maior resolução e observações de campo.",
            "source": "NASA Earthdata — Vegetation Indices",
            "url": "https://www.earthdata.nasa.gov/topics/land-surface/vegetation",
            "related": "Painel ambiental"
        },
        {
            "title": "Como validar dados ambientais",
            "topic": "Validação científica",
            "kind": "Método científico",
            "summary": "Uma comparação válida usa pares de observações correspondentes no tempo, na variável, na unidade e, tanto quanto possível, na localização e no período de agregação.",
            "details": "Documente a estação, coordenadas, altitude, instrumento, manutenção, controle de qualidade e lacunas. Bias mede erro médio com sinal; MAE resume erro absoluto; RMSE penaliza mais erros grandes; R² descreve associação/ajuste, mas não deve ser interpretado isoladamente como prova de concordância. Uma amostra pequena ou enviesada não sustenta generalização para outras regiões.",
            "source": "NASA POWER — DAV Validate / PRUVE",
            "url": "https://power.larc.nasa.gov/docs/services/api/validate/",
            "related": "Validação científica"
        },
        {
            "title": "Solo: textura não é capacidade de água medida",
            "topic": "Solo e manejo",
            "kind": "Explicação técnica",
            "summary": "Textura descreve a proporção de areia, silte e argila. Ela influencia retenção e movimento da água, mas não determina sozinha a capacidade de água disponível de um talhão.",
            "details": "Estrutura, matéria orgânica, compactação, profundidade, pedregosidade e horizonte restritivo também importam. Para parametrizar balanços hídricos, prefira análise física do perfil e dados locais; classes amplas como arenoso, franco ou argiloso são aproximações. Não confunda uma categoria informada pelo usuário com uma medição por satélite.",
            "source": "Embrapa — Solos",
            "url": "https://www.embrapa.br/tema-solos",
            "related": "Contexto da propriedade · Balanço hídrico"
        }
    ]

    topic_options = [tx("All topics", "Todos os temas")] + sorted({item["topic"] for item in knowledge_items})
    selected_topic = st.selectbox(tx("Filter by topic", "Filtrar por tema"), topic_options, key="knowledge_topic")
    search_text = st.text_input(
        tx("Search the library", "Pesquisar na biblioteca"),
        placeholder=tx("Try: rainfall, ZARC, NDVI, soil...", "Ex.: chuva, ZARC, NDVI, solo..."),
        key="knowledge_search"
    ).strip().casefold()

    visible_items = [
        item for item in knowledge_items
        if (selected_topic == topic_options[0] or item["topic"] == selected_topic)
        and (
            not search_text
            or search_text in " ".join([
                item["title"], item["topic"], item["kind"],
                item["summary"], item["details"], item["source"]
            ]).casefold()
        )
    ]
    st.caption(tx(f"{len(visible_items)} materials in this view · reviewed 12 Nov 2026", f"{len(visible_items)} materiais nesta visualização · revisão editorial em 12 nov. 2026"))
    if not visible_items:
        st.info(tx("No material matches this search. Try another term or topic.", "Nenhum material corresponde à busca. Tente outro termo ou tema."))
    for start in range(0, len(visible_items), 2):
        cols = st.columns(2)
        for col, item in zip(cols, visible_items[start:start + 2]):
            with col:
                with st.container(border=True):
                    st.caption(f"{item['topic']} · {item['kind']}")
                    st.subheader(item["title"])
                    st.write(item["summary"])
                    with st.expander(tx("Read explanation and source", "Ler explicação e fonte")):
                        st.write(item["details"])
                        st.markdown(f"**{tx('Primary reference', 'Referência principal')}:** [{item['source']}]({item['url']})")
                        st.caption(f"{tx('Related area', 'Área relacionada')}: {item['related']}")

    st.divider()
    st.subheader(tx("How to use this library", "Como usar esta biblioteca"))
    st.write(tx(
        "Start with the explanation, open the primary reference, and then return to the relevant AGROVISION tool. Each material is educational: verify the source, date, geographic scope and assumptions before using information in a real-world decision.",
        "Comece pela explicação, abra a referência primária e depois volte à ferramenta correspondente do AGROVISION. Os materiais são educativos: confira fonte, data, abrangência geográfica e hipóteses antes de usar a informação em uma decisão real."
    ))
    st.caption(tx(
        "Editorial library · Foundational references, not a live news feed. New research and official updates are reviewed separately.",
        "Biblioteca editorial · Referências fundamentais, não um feed de notícias em tempo real. Novas pesquisas e atualizações oficiais são verificadas separadamente."
    ))

with tab_help:
    st.header(tx("Your first steps", "Seus primeiros passos"))
    st.write(tx("New here? Follow this short path to get from a location to an informed exploration of the data.", "É sua primeira vez? Siga este roteiro para sair da escolha de um local e chegar à exploração dos dados."))
    st.markdown("""
    <div class="step-card" style="min-height:0; margin-bottom:1rem">
      <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:.65rem">
        <div><div class="step-number">1</div><strong>Locate</strong><span>Enter farm coordinates</span></div>
        <div><div class="step-number">2</div><strong>Describe</strong><span>Add local farm context</span></div>
        <div><div class="step-number">3</div><strong>Explore</strong><span>Load NASA indicators</span></div>
        <div><div class="step-number">4</div><strong>Compare</strong><span>Review crop-specific climate and water-balance scenarios</span></div>
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
        These options provide local context for the crop and water-balance analysis:
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

    with st.expander("5. Analyze crops and water balance"):
        st.markdown("""
        1. First load the environmental data in the dashboard.
        2. Open **Crop analysis**.
        3. Select maize, soybean and/or common bean, then choose an assumed sowing month.
        4. Review observed rainfall and temperature during complete historical crop-cycle windows.
        5. Compare those observations with published indicative crop-cycle and water-need ranges.

        The crop screen does not rank crops. The FAO-56 water balance is a simplified, uncalibrated root-zone estimate, not a yield forecast or agronomic recommendation.
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
        - No. Do not use it alone for planting decisions. Real decisions require local soil tests, ZARC calendars, cultivar details, water balance, management information, and advice from qualified agronomists.
        """)

    st.divider()
    st.subheader(tx("What the platform does — and does not do", "O que a plataforma faz — e o que não faz"))
    left, right = st.columns(2)
    with left:
        st.markdown("**AGROVISION can help you:**")
        st.markdown("- Explore climate indicators for a selected location.\n- View satellite-derived vegetation observations.\n- Compare historical climate during representative cycles of maize, soybean and common bean.\n- Review the reference ranges and assumptions behind each crop screen.")
    with right:
        st.markdown("**AGROVISION does not currently:**")
        st.markdown("- Measure soil properties directly.\n- Reproduce the full official ZARC/SARRA model.\n- Predict crop yield or farm profit.\n- Provide a certified planting or irrigation recommendation.\n- Display SMAP data in this public deployment.")
    st.caption("AGROVISION · " + tx("First-visit guide · Agricultural climate analysis", "Guia inicial · Análise climática agrícola"))

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
        "source": "FAO Crop Water Needs (indicative seasonal ranges)"
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

        # Daily FAO-56 water-balance diagnostic. All crop and soil parameters
        # are explicit user inputs; generic Kc defaults are not a recommendation.
        st.divider()
        st.subheader(tx("Daily water balance · FAO-56", "Balanço hídrico diário · FAO-56"))
        st.markdown(tx(
            "This diagnostic estimates reference evapotranspiration (ET0), crop evapotranspiration (ETc) and root-zone water depletion. It is a simplified single-layer bucket, not the official ZARC SARRA model.",
            "Este diagnóstico estima evapotranspiração de referência (ET0), evapotranspiração da cultura (ETc) e depleção de água na zona radicular. É um reservatório simplificado de uma camada, não o modelo SARRA oficial do ZARC."
        ))
        if not selected_crops:
            st.info(tx("Select a crop above to configure the water-balance scenario.", "Selecione uma cultura acima para configurar o balanço hídrico."))
        else:
            water_crop = st.selectbox(
                tx("Crop for water-balance simulation", "Cultura para simulação do balanço hídrico"),
                selected_crops,
                format_func=lambda c: CROP_REFERENCE[c]["pt"] if st.session_state.get("agrovision_language") == "Português" else c,
                key="water_balance_crop"
            )
            profile = CROP_REFERENCE[water_crop]
            cycle_days = round((profile["cycle_min"] + profile["cycle_max"]) / 2)
            water_sowing_day = st.selectbox(
                tx("Sowing day / ZARC 10-day period", "Dia de semeadura / decêndio ZARC"),
                [1, 11, 21], format_func=lambda d: {1: "1–10", 11: "11–20", 21: "21–end"}[d],
                key="water_sowing_day"
            )
            try:
                et0_all = fao56_reference_et0(climate, lat, elevation_m)
                st.caption(tx(
                    "ET0 uses NASA POWER T2M, daily maximum/minimum temperature, dew-point temperature, 2 m wind speed and solar radiation. Solar radiation is converted from kWh/m²/day to MJ/m²/day.",
                    "A ET0 usa T2M, temperaturas máxima/mínima diárias, ponto de orvalho, vento a 2 m e radiação solar do NASA POWER. A radiação é convertida de kWh/m²/dia para MJ/m²/dia."
                ))
                candidate_years = []
                for candidate_year in sorted(set(climate.index.year)):
                    candidate_start = pd.Timestamp(year=int(candidate_year), month=int(sowing_month), day=int(water_sowing_day))
                    candidate_end = candidate_start + pd.Timedelta(days=cycle_days - 1)
                    candidate_weather = climate.loc[candidate_start:candidate_end]
                    candidate_et0 = et0_all.loc[candidate_start:candidate_end]
                    if (len(candidate_weather) == cycle_days
                        and candidate_weather["PRECTOTCORR"].notna().all()
                        and candidate_et0.notna().all()):
                        candidate_years.append(int(candidate_year))
                if not candidate_years:
                    st.warning(tx(
                        "No complete crop-cycle window has all required FAO-56 weather variables. Check data coverage, choose another sowing month or crop, or reload NASA POWER.",
                        "Nenhuma janela completa do ciclo possui todas as variáveis meteorológicas exigidas pelo FAO-56. Verifique a cobertura, escolha outro mês ou cultura, ou recarregue o NASA POWER."
                    ))
                else:
                    water_year = st.selectbox(tx("Historical season to simulate", "Safra histórica para simular"), candidate_years, index=len(candidate_years)-1, key="water_balance_year")
                    st.caption(tx(
                        f"Representative cycle: {cycle_days} days, beginning {sowing_month:02d}/{water_sowing_day:02d}/{water_year}. The midpoint cycle is a screening assumption, not cultivar phenology.",
                        f"Ciclo representativo: {cycle_days} dias, iniciando em {water_sowing_day:02d}/{sowing_month:02d}/{water_year}. A duração intermediária é uma hipótese de triagem, não a fenologia da cultivar."
                    ))
                    crop_widget_key = water_crop.lower().replace(" ", "_").replace("(", "").replace(")", "")
                    with st.expander(tx("Crop and soil parameters", "Parâmetros da cultura e do solo"), expanded=True):
                        c1,c2,c3=st.columns(3)
                        initial_days = c1.number_input(tx("Initial stage (days)", "Fase inicial (dias)"), 1, cycle_days-3, max(1, round(cycle_days*0.2)), key=f"kc_initial_days_{crop_widget_key}")
                        development_days = c2.number_input(tx("Development (days)", "Desenvolvimento (dias)"), 1, cycle_days-2, max(1, round(cycle_days*0.25)), key=f"kc_development_days_{crop_widget_key}")
                        midseason_days = c3.number_input(tx("Mid-season (days)", "Meia-estação (dias)"), 1, cycle_days-1, max(1, round(cycle_days*0.35)), key=f"kc_mid_days_{crop_widget_key}")
                        end_days = cycle_days - int(initial_days) - int(development_days) - int(midseason_days)
                        st.caption(tx(f"Late season is calculated as the remaining {end_days} days.", f"A fase final será calculada com os {end_days} dias restantes."))
                        kc_defaults = {
                            "Maize (grain)": (0.30, 1.20, 0.35),
                            "Soybean": (0.40, 1.15, 0.50),
                            "Common bean (dry)": (0.40, 1.15, 0.35)
                        }
                        k0, km, ke = kc_defaults[water_crop]
                        k1,k2,k3=st.columns(3)
                        kc_ini = k1.number_input(tx("Kc initial", "Kc inicial"), 0.0, 2.0, k0, 0.05, key=f"kc_ini_{crop_widget_key}")
                        kc_mid = k2.number_input(tx("Kc mid-season", "Kc de meia-estação"), 0.0, 2.0, km, 0.05, key=f"kc_mid_{crop_widget_key}")
                        kc_end = k3.number_input(tx("Kc end-season", "Kc final"), 0.0, 2.0, ke, 0.05, key=f"kc_end_{crop_widget_key}")
                        st.caption(tx(
                            "Kc starting values are generic FAO-56 reference values. Adjust them to cultivar, climate, planting density, ground cover and local technical guidance.",
                            "Os Kc iniciais são valores genéricos de referência FAO-56. Ajuste-os conforme cultivar, clima, densidade, cobertura do solo e orientação técnica local."
                        ))
                        st.markdown("[FAO-56 crop coefficient tables](https://www.fao.org/4/X0490E/x0490e0b.htm) · [FAO Penman–Monteith method](https://www.fao.org/4/x0490e/x0490e06.htm)")
                        st.markdown("**" + tx("Soil water properties", "Propriedades hídricas do solo") + "**")
                        q1,q2,q3=st.columns(3)
                        available_water = q1.number_input(tx("Available water (mm/m)", "Água disponível (mm/m)"), 34.0, 184.0, 100.0, 1.0, key="soil_available_water")
                        root_depth = q2.number_input(tx("Effective root depth (m)", "Profundidade efetiva das raízes (m)"), 0.1, 2.5, 0.6, 0.05, key="effective_root_depth")
                        depletion_fraction = q3.number_input("FAO depletion fraction (p)", 0.1, 0.8, 0.5, 0.05, key="depletion_fraction")
                        initial_storage = st.slider(tx("Initial soil-water storage (% of field capacity)", "Armazenamento inicial de água no solo (% da capacidade de campo)"), 0, 100, 80, 5, key="initial_soil_storage") / 100
                        st.caption(tx(
                            "Available water default (100 mm/m), root depth (0.6 m) and initial storage (80%) are placeholders. Replace them with a soil analysis and crop-specific rooting information. MAPA ZARC uses soil available-water classes; see the official classification.",
                            "Os valores iniciais de água disponível (100 mm/m), raízes (0,6 m) e armazenamento (80%) são apenas placeholders. Substitua-os por análise de solo e informação de enraizamento da cultura. O ZARC/MAPA utiliza classes de água disponível no solo; consulte a classificação oficial."
                        ))
                    irrigation_mode_label = st.radio(
                        tx("Water-management scenario", "Cenário de manejo hídrico"),
                        [tx("Rainfed · no irrigation", "Sequeiro · sem irrigação"), tx("Idealized supplemental irrigation", "Irrigação suplementar idealizada")],
                        horizontal=True, key="water_irrigation_scenario"
                    )
                    irrigation_mode = "triggered_supplemental" if irrigation_mode_label == tx("Idealized supplemental irrigation", "Irrigação suplementar idealizada") else "rainfed"
                    irrigation_efficiency = st.slider(tx("Application efficiency (%)", "Eficiência de aplicação (%)"), 50, 100, 85, 5, key="water_irrigation_efficiency") / 100 if irrigation_mode == "triggered_supplemental" else 0.85
                    current_parameters = {
                        "available_water_mm_m": float(available_water), "root_depth_m": float(root_depth),
                        "depletion_fraction": float(depletion_fraction), "initial_storage_fraction": float(initial_storage),
                        "elevation_m": float(elevation_m), "irrigation_mode": irrigation_mode,
                        "irrigation_efficiency": float(irrigation_efficiency),
                        "initial_days": int(initial_days), "development_days": int(development_days),
                        "midseason_days": int(midseason_days), "kc_initial": float(kc_ini),
                        "kc_mid": float(kc_mid), "kc_end": float(kc_end),
                        "sowing_day": int(water_sowing_day)
                    }
                    if end_days < 1:
                        st.error(tx("Crop-stage durations exceed the cycle. Reduce one or more stages.", "A soma das fases excede o ciclo. Reduza uma ou mais fases."))
                    elif st.button(tx("Calculate daily water balance", "Calcular balanço hídrico diário"), type="primary", key="run_water_balance"):
                        try:
                            start = pd.Timestamp(year=int(water_year), month=int(sowing_month), day=int(water_sowing_day))
                            end = start + pd.Timedelta(days=cycle_days - 1)
                            weather_window = climate.loc[start:end]
                            et0_window = et0_all.loc[start:end]
                            kc_curve = crop_coefficient_curve(
                                cycle_days, initial_days, development_days, midseason_days,
                                kc_ini, kc_mid, kc_end
                            )
                            balance = simulate_root_zone_balance(
                                weather_window, et0_window, lat, available_water, root_depth,
                                depletion_fraction, initial_storage, kc_curve,
                                irrigation_mode=irrigation_mode,
                                irrigation_efficiency=irrigation_efficiency
                            )
                            st.session_state["latest_water_balance"] = {
                                "crop": water_crop, "year": int(water_year), "coords": (float(lat), float(lon)), "sowing_month": int(sowing_month),
                                "sowing_day": int(water_sowing_day), "table": balance, "parameters": current_parameters
                            }
                        except Exception as exc:
                            st.error(tx("Water-balance calculation failed: ", "Falha no cálculo do balanço hídrico: ") + str(exc))
                    saved_balance = st.session_state.get("latest_water_balance")
                    if saved_balance and saved_balance.get("crop") == water_crop and saved_balance.get("year") == int(water_year) and saved_balance.get("coords") == (float(lat), float(lon)) and saved_balance.get("sowing_month") == int(sowing_month) and saved_balance.get("sowing_day") == int(water_sowing_day) and saved_balance.get("parameters") == current_parameters:
                        balance = saved_balance["table"]
                        total_etc = balance["ETc potential (mm)"].sum()
                        total_eta = balance["ETa actual estimate (mm)"].sum()
                        total_rain = balance["Precipitation (mm)"].sum()
                        total_net_irrigation = balance["Net irrigation (mm)"].sum()
                        total_gross_irrigation = balance["Gross irrigation estimate (mm)"].sum()
                        days_stressed = int((balance["Stress coefficient Ks"] < 0.999).sum())
                        zarc_saved = st.session_state.get("zarc_reference")
                        if zarc_saved:
                            zarc_crop_matches = crop_matches_app_crop(zarc_saved.get("Crop", ""), water_crop)
                            target_dekad = (int(sowing_month) - 1) * 3 + (1 if int(water_sowing_day) == 1 else 2 if int(water_sowing_day) == 11 else 3)
                            recommended = zarc_saved.get("Recommended decendios", [])
                            matching_dekad = next((item for item in recommended if int(item.get("Decêndio", -1)) == target_dekad), None)
                            if zarc_crop_matches and matching_dekad and matching_dekad.get("Risco (%)") in (20, 30, 40):
                                st.success(tx(
                                    f"The selected sowing dekad appears in the official MAPA record with {matching_dekad['Risco (%)']}% risk. This checks the selected row only; confirm that its municipality, cultivar group, soil class, management and climate match the farm.",
                                    f"O decêndio selecionado consta no registro oficial do MAPA com risco de {matching_dekad['Risco (%)']}%. Esta verificação considera apenas a linha selecionada; confirme se município, grupo de cultivar, classe de solo, manejo e clima correspondem à propriedade."
                                ))
                            else:
                                st.warning(tx(
                                    "The selected crop or sowing dekad is not listed as a 20%, 30% or 40% window in the selected official MAPA record. Confirm all ZARC filters and the applicable ordinance.",
                                    "A cultura ou o decêndio selecionado não aparece como janela de 20%, 30% ou 40% no registro oficial escolhido. Confira todos os filtros do ZARC e a portaria aplicável."
                                ))
                        st.markdown("**" + tx("Seasonal indicators", "Indicadores da safra") + "**")
                        a1,a2,a3,a4=st.columns(4)
                        a1.metric(tx("ET0", "ET0"), f'{balance["ET0 FAO-56 (mm)"].sum():.0f} mm')
                        a2.metric(tx("Potential ETc", "ETc potencial"), f"{total_etc:.0f} mm")
                        a3.metric(tx("Estimated actual ETa", "ETa real estimada"), f"{total_eta:.0f} mm")
                        a4.metric(tx("Days with water stress", "Dias com estresse hídrico"), f"{days_stressed}/{len(balance)}")
                        b1,b2,b3=st.columns(3)
                        b1.metric(tx("Cycle rainfall", "Chuva no ciclo"), f"{total_rain:.0f} mm")
                        b2.metric(tx("Net irrigation", "Irrigação líquida"), f"{total_net_irrigation:.0f} mm")
                        b3.metric(tx("Gross irrigation estimate", "Estimativa de irrigação bruta"), f"{total_gross_irrigation:.0f} mm")
                        chart = balance.set_index("Date")[["Root-zone depletion (mm)", "RAW trigger (mm)"]]
                        st.line_chart(chart)
                        st.dataframe(balance, use_container_width=True, hide_index=True)
                        st.download_button(
                            tx("Download daily water-balance CSV", "Baixar CSV do balanço hídrico diário"),
                            balance.to_csv(index=False).encode("utf-8"),
                            file_name=f"agrovision_water_balance_{water_crop.lower().replace(' ','_')}_{water_year}.csv",
                            mime="text/csv"
                        )
                        st.warning(tx(
                            "Interpretation limits: rainfall is treated as infiltrating until field capacity; runoff, capillary rise, lateral flow, changing root depth, salinity and field-specific soil hydraulic properties are not modeled. Supplemental irrigation is an idealized trigger/refill scenario, not a prescription. ET0 depends on gridded NASA POWER weather and entered elevation; validate it against a local station.",
                            "Limites: a chuva é considerada infiltrada até a capacidade de campo; escoamento superficial, ascensão capilar, fluxo lateral, variação da profundidade radicular, salinidade e propriedades hidráulicas específicas do talhão não são modelados. A irrigação suplementar é um cenário idealizado de gatilho/reposição, não uma recomendação. A ET0 depende do clima em grade do NASA POWER e da altitude informada; valide-a com estação local."
                        ))
            except Exception as exc:
                st.error(tx("FAO-56 weather inputs are unavailable or invalid: ", "As variáveis meteorológicas FAO-56 estão indisponíveis ou inválidas: ") + str(exc))

        st.divider()
        st.subheader(tx("ZARC · Official MAPA open-data lookup", "ZARC · Consulta à base oficial aberta do MAPA"))
        st.markdown(tx(
            "Search the MAPA risk table directly. The app downloads the official season CSV, filters the exact municipality/crop/soil/cultivar-management combination and expands the 36 sowing dekads. Values 20, 30 and 40 are shown as their official risk levels; 0 is kept as outside the recommended window.",
            "Consulte diretamente a tábua de risco do MAPA. O app baixa o CSV oficial da safra, filtra a combinação exata de município/cultura/solo/ciclo e expande os 36 decêndios. Valores 20, 30 e 40 são exibidos como níveis oficiais de risco; 0 é mantido como fora da janela recomendada."
        ))
        st.markdown("[Portal de Dados Abertos do MAPA — Tábua de Risco](https://dados.agricultura.gov.br/dataset/tabua-de-risco-zoneamento-agricola-de-risco-climatico) · [Painel ZARC](https://mapa-indicadores.agricultura.gov.br/publico/extensions/Zarc/Zarc.html) · [SISZARC](https://sistemasweb.agricultura.gov.br/siszarc/base.action)")
        @st.cache_data(ttl=3600, show_spinner=False)
        def _cached_zarc_resources():
            return list_zarc_resources()

        @st.cache_data(ttl=3600, show_spinner=False)
        def _cached_zarc_table(url):
            return load_zarc_csv(url)

        try:
            with st.spinner(tx("Loading the MAPA catalogue…", "Carregando o catálogo do MAPA…")):
                zarc_resources = _cached_zarc_resources()
            resource_labels = [r["title"] for r in zarc_resources]
            default_resource = next((i for i, resource in enumerate(zarc_resources) if ("2026" in resource["title"] and "2027" in resource["title"]) or ("2026" in resource["url"] and "2027" in resource["url"])), 0)
            chosen_resource_label = st.selectbox(
                tx("Official ZARC season dataset", "Base oficial da safra ZARC"),
                resource_labels, index=default_resource, key="zarc_official_resource"
            )
            chosen_resource = zarc_resources[resource_labels.index(chosen_resource_label)]
            with st.spinner(tx("Downloading and parsing the official MAPA CSV…", "Baixando e lendo o CSV oficial do MAPA…")):
                zarc_data = _cached_zarc_table(chosen_resource["url"])
            crop_col = find_column(zarc_data, "Nome_cultura", "cultura")
            uf_col = find_column(zarc_data, "UF")
            municipality_col = find_column(zarc_data, "municipio")
            soil_col = find_column(zarc_data, "Cod_Solo", "solo")
            cycle_col = find_column(zarc_data, "Cod_Ciclo", "grupo")
            management_col = find_column(zarc_data, "Nome_Outros_Manejos", "outros_manejos")
            climate_col = find_column(zarc_data, "Nome_Clima", "clima")
            dec_cols = decendio_columns(zarc_data)
            if not all([crop_col, uf_col, municipality_col, soil_col, cycle_col]) or not dec_cols:
                raise ValueError("The MAPA CSV structure does not match the published ZARC data dictionary. No result was inferred.")
            st.caption(tx(
                f"Source: {chosen_resource['title']} · {len(zarc_data):,} official rows · {len(dec_cols)} dekad columns. Catalogue update: {chosen_resource.get('last_modified') or 'not supplied'} · CC BY attribution.",
                f"Fonte: {chosen_resource['title']} · {len(zarc_data):,} registros oficiais · {len(dec_cols)} colunas de decêndio. Atualização do catálogo: {chosen_resource.get('last_modified') or 'não informada'}."
            ))
            zarc_crop_options = unique_values(zarc_data, crop_col)
            zarc_crop_choice = st.selectbox(tx("Crop", "Cultura"), zarc_crop_options, key="zarc_query_crop")
            after_crop = filter_zarc_rows(zarc_data, {"crop": zarc_crop_choice})
            uf_options = unique_values(after_crop, uf_col)
            zarc_uf_choice = st.selectbox(tx("State (UF)", "Estado (UF)"), uf_options, key="zarc_query_uf")
            after_uf = filter_zarc_rows(after_crop, {"uf": zarc_uf_choice})
            municipality_options = unique_values(after_uf, municipality_col)
            zarc_municipality_choice = st.selectbox(tx("Municipality", "Município"), municipality_options, key="zarc_query_municipality")
            after_municipality = filter_zarc_rows(after_uf, {"municipality": zarc_municipality_choice})
            c1,c2,c3=st.columns(3)
            soil_options = unique_values(after_municipality, soil_col)
            zarc_soil_choice = c1.selectbox(
                tx("Soil class / code", "Classe / código do solo"), soil_options,
                format_func=lambda value: {
                    "1": "1 · Arenoso", "2": "2 · Textura média", "3": "3 · Argiloso",
                    "11": "11 · AD1", "12": "12 · AD2", "13": "13 · AD3",
                    "14": "14 · AD4", "15": "15 · AD5", "16": "16 · AD6"
                }.get(str(value), str(value)), key="zarc_query_soil"
            )
            after_soil = filter_zarc_rows(after_municipality, {"soil": zarc_soil_choice})
            cycle_options = unique_values(after_soil, cycle_col)
            zarc_cycle_choice = c2.selectbox(
                tx("Cultivar cycle / group", "Ciclo / grupo de cultivar"), cycle_options,
                format_func=lambda value: {
                    "13": "13 · Perene", "19": "19 · Semiperene",
                    "20": "20 · Grupo I", "21": "21 · Grupo II",
                    "22": "22 · Grupo III", "24": "24 · Grupo IV",
                    "25": "25 · Grupo V", "26": "26 · Grupo VI"
                }.get(str(value), str(value)), key="zarc_query_cycle"
            )
            after_cycle = filter_zarc_rows(after_soil, {"cycle": zarc_cycle_choice})
            management_options = unique_values(after_cycle, management_col) if management_col else []
            zarc_management_choice = c3.selectbox(
                tx("Management", "Manejo"), management_options, key="zarc_query_management"
            ) if management_options else None
            after_management = filter_zarc_rows(after_cycle, {"management": zarc_management_choice})
            climate_options = unique_values(after_management, climate_col) if climate_col else []
            zarc_climate_choice = st.selectbox(
                tx("Climate group", "Grupo climático"), climate_options, key="zarc_query_climate"
            ) if climate_options else None
            matches = filter_zarc_rows(after_management, {"climate": zarc_climate_choice})
            st.metric(tx("Exact official records", "Registros oficiais encontrados"), f"{len(matches):,}")
            if matches.empty:
                st.warning(tx("No record matches this exact combination in the selected MAPA season file. Do not infer a planting window.", "Nenhum registro corresponde a essa combinação exata no arquivo MAPA selecionado. Não infira uma janela de plantio."))
            else:
                row_options = list(range(len(matches)))
                def _zarc_record_label(index):
                    row = matches.iloc[index]
                    portaria_col = find_column(matches, "Portaria")
                    portaria = str(row.get(portaria_col, "")) if portaria_col else ""
                    return f"Record {index + 1} · {portaria or tx('official record', 'registro oficial')}"
                selected_record_index = st.selectbox(
                    tx("Official record", "Registro oficial"), row_options,
                    format_func=_zarc_record_label, key="zarc_query_record"
                )
                selected_zarc_row = matches.iloc[int(selected_record_index)]
                dekad_rows = expand_decendios(selected_zarc_row, dec_cols)
                dekad_frame = pd.DataFrame(dekad_rows)
                if not dekad_frame.empty:
                    st.markdown("**" + tx("Official sowing windows by dekad", "Janelas oficiais de semeadura por decêndio") + "**")
                    st.dataframe(dekad_frame, use_container_width=True, hide_index=True)
                metadata_columns = {
                    "Crop": crop_col, "UF": uf_col, "Municipality": municipality_col,
                    "Soil code": soil_col, "Cultivar group / cycle": cycle_col,
                }
                for label, col in (("Management", management_col), ("Climate", climate_col), ("Ordinance", find_column(matches, "Portaria"))):
                    if col:
                        metadata_columns[label] = col
                official_record = {label: str(selected_zarc_row.get(col, "")) for label, col in metadata_columns.items()}
                official_record["Season dataset"] = chosen_resource["title"]
                official_record["Catalogue last modified"] = chosen_resource.get("last_modified", "")
                official_record["MAPA resource ID"] = chosen_resource.get("id", "")
                official_record["Recommended decendios"] = [
                    item for item in dekad_rows if item.get("Risco (%)") in (20, 30, 40)
                ]
                official_record["All decendios"] = dekad_rows
                official_record["Source URL"] = chosen_resource["url"]
                official_record["Source"] = "MAPA Dados Abertos — ZARC Tábua de Risco (official CSV)"
                if st.button(tx("Use this official ZARC record in the project", "Usar este registro oficial ZARC no projeto"), type="primary", key="zarc_use_official"):
                    st.session_state["zarc_reference"] = official_record
                    st.success(tx("Official MAPA record selected and attached to this project session.", "Registro oficial do MAPA selecionado e vinculado a esta sessão do projeto."))
                if st.session_state.get("zarc_reference", {}).get("Source URL") == chosen_resource["url"]:
                    st.caption(tx("Current project ZARC reference", "Referência ZARC atual do projeto"))
                    st.dataframe(pd.DataFrame([{
                        key: value for key, value in st.session_state["zarc_reference"].items()
                        if key not in ("Recommended decendios", "All decendios")
                    }]), use_container_width=True, hide_index=True)
        except Exception as exc:
            st.error(tx("Could not load or query the official MAPA ZARC dataset: ", "Não foi possível carregar ou consultar a base oficial ZARC do MAPA: ") + str(exc))
            st.markdown("[Open MAPA ZARC open-data portal](https://dados.agricultura.gov.br/dataset/tabua-de-risco-zoneamento-agricola-de-risco-climatico)")


        else:
            st.info(tx("Select at least one crop to analyze.", "Selecione ao menos uma cultura para analisar."))

with tab3:
    st.subheader(tx("Data sources and limitations", "Fontes de dados e limitações"))
    st.markdown(tx(
        "- **NASA POWER:** daily temperature, dew point, 2 m wind speed, precipitation and solar radiation; used as gridded weather inputs.\n- **FAO-56:** daily reference ET0 (Penman–Monteith), crop ETc (Kc × ET0) and a simplified root-zone bucket balance.\n- **ZARC/MAPA:** official season CSVs are downloaded from the MAPA open-data catalogue and filtered by municipality, crop, soil, cultivar cycle, management and climate; all 36 sowing dekads and source risk values are displayed.\n- The selected ZARC row is saved with the project and compared against the simulated sowing dekad; users must confirm that every farm-specific filter matches.\n- **MODIS MOD13Q1:** 16-day NDVI composites for the selected 2020–2025 period; queried live in batches that respect the ORNL request limit.\n- **Crop references:** indicative crop-cycle and seasonal water-need ranges from FAO and Embrapa publications.\n- **SMAP:** not yet connected in this public deployment; authenticated Earthdata access is still required.\n- Satellite pixels represent broader areas and do not replace field sampling.\n- The water balance is a simplified single-layer bucket, not the official ZARC SARRA model; it does not represent runoff, capillary rise, changing roots or calibrated field hydraulics.",
        "- **NASA POWER:** temperatura, ponto de orvalho, vento a 2 m, precipitação e radiação solar diários; usados como dados meteorológicos em grade.\n- **FAO-56:** ET0 diária pelo método Penman–Monteith, ETc da cultura (Kc × ET0) e balanço simplificado da zona radicular.\n- **ZARC/MAPA:** arquivos CSV oficiais da safra são baixados do catálogo de dados abertos do MAPA e filtrados por município, cultura, solo, ciclo de cultivar, manejo e clima; os 36 decêndios e os valores de risco da fonte são exibidos.\n- O registro ZARC selecionado é salvo com o projeto e comparado ao decêndio simulado; o usuário deve confirmar se todos os filtros correspondem à propriedade.\n- **MODIS MOD13Q1:** composições de NDVI a cada 16 dias no período selecionado entre 2020 e 2025; consultas divididas em lotes conforme o limite da ORNL.\n- **Referências das culturas:** faixas indicativas de ciclo e necessidade hídrica sazonal de publicações da FAO e da Embrapa.\n- **SMAP:** ainda não conectado nesta versão pública; exige autenticação Earthdata.\n- Pixels de satélite representam áreas mais amplas e não substituem amostragem de campo.\n- O balanço hídrico é um reservatório simplificado de uma camada, não o SARRA oficial do ZARC; não representa escoamento superficial, ascensão capilar, raízes variáveis ou hidráulica do solo calibrada."
    ))
    st.markdown("[NASA POWER Daily API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) · [FAO-56](https://www.fao.org/4/X0490E/X0490E00.htm) · [MAPA ZARC open data](https://dados.agricultura.gov.br/dataset/tabua-de-risco-zoneamento-agricola-de-risco-climatico) · [MAPA ZARC panel](https://mapa-indicadores.agricultura.gov.br/publico/extensions/Zarc/Zarc.html) · [MODIS/ORNL DAAC](https://modis.ornl.gov/) · [NASA SMAP](https://smap.jpl.nasa.gov/)")
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
    story.extend([Spacer(1, 16), Paragraph("Scientific note: this report summarizes historical environmental observations. NDVI is not a direct measure of yield or crop health. Rainfall totals alone are not a soil-water balance or crop water deficit estimate. Crop reference ranges are indicative and must be checked against cultivar, local ZARC calendar, soil tests, management and field observations.", styles["Italic"])])
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


with tab5:
    st.subheader(tx("Independent validation against weather-station observations", "Validação independente com observações de estações meteorológicas"))
    st.markdown(tx(
        "Upload a CSV containing daily observations from a traceable weather station. AGROVISION will align dates with NASA POWER and calculate paired error statistics. No station observations are bundled or fabricated.",
        "Envie um CSV com observações diárias de uma estação meteorológica identificável. O AGROVISION alinhará as datas com o NASA POWER e calculará estatísticas de erro pareadas. Nenhuma observação de estação é embutida ou inventada."
    ))
    st.warning(tx(
        "Use the same location, physical variable, unit and daily aggregation. Document station ID, coordinates, elevation, instrument, source and quality control. A nearby station is not automatically representative of the satellite/grid cell.",
        "Use o mesmo local, variável física, unidade e agregação diária. Documente ID da estação, coordenadas, altitude, instrumento, fonte e controle de qualidade. Uma estação próxima não representa automaticamente o pixel/célula de grade."
    ))
    if "climate" not in st.session_state or st.session_state.get("coords") != (lat, lon):
        st.info(tx("Load NASA POWER data in the Environmental dashboard first.", "Carregue primeiro os dados NASA POWER no Painel ambiental."))
    else:
        uploaded_station = st.file_uploader(
            tx("Station observations (CSV)", "Observações da estação (CSV)"),
            type=["csv"], key="station_validation_csv",
            help=tx("CSV must contain a date column and one observed-variable column.", "O CSV deve conter uma coluna de data e uma coluna da variável observada.")
        )
        if uploaded_station is not None:
            try:
                station = pd.read_csv(uploaded_station)
                if station.empty or len(station.columns) < 2:
                    raise ValueError("CSV must contain at least two columns.")
                date_col = st.selectbox(tx("Date column", "Coluna de data"), list(station.columns), key="validation_date_col")
                variable_map = {
                    "Air temperature (°C)": ("T2M", "°C"),
                    "Precipitation (mm/day)": ("PRECTOTCORR", "mm/day"),
                    "Solar radiation (kWh/m²/day)": ("ALLSKY_SFC_SW_DWN", "kWh/m²/day")
                }
                variable_label = st.selectbox(tx("Variable to validate", "Variável a validar"), list(variable_map), key="validation_variable")
                model_col, unit = variable_map[variable_label]
                obs_options = [c for c in station.columns if c != date_col]
                obs_col = st.selectbox(tx("Station observation column", "Coluna observada na estação"), obs_options, key="validation_obs_col")
                station_name = st.text_input(tx("Station name / identifier and source", "Nome/identificador da estação e fonte"), key="validation_station_name")
                if st.button(tx("Run independent validation", "Executar validação independente"), type="primary", key="run_station_validation"):
                    dates = pd.to_datetime(station[date_col], errors="coerce", utc=True).dt.tz_convert(None).dt.normalize()
                    observed = pd.Series(pd.to_numeric(station[obs_col], errors="coerce").values, index=dates).groupby(level=0).mean()
                    model = st.session_state["climate"][model_col].copy()
                    model.index = pd.to_datetime(model.index).normalize()
                    result = paired_validation_metrics(model, observed)
                    paired = result.pop("paired")
                    st.caption(f"{station_name.strip() or 'Station source not specified'} · {variable_label} · {unit}")
                    m1,m2,m3,m4=st.columns(4)
                    m1.metric("Paired days", result["n"])
                    m2.metric("Bias", f'{result["bias"]:.3f} {unit}')
                    m3.metric("MAE", f'{result["mae"]:.3f} {unit}')
                    m4.metric("RMSE", f'{result["rmse"]:.3f} {unit}')
                    if result["r_squared"] is not None:
                        st.metric("Coefficient of determination (R²)", f'{result["r_squared"]:.3f}')
                    else:
                        st.info(tx("R² is undefined because the station observations have zero variance.", "R² não está definido porque as observações da estação não apresentam variância."))
                    st.line_chart(paired.rename(columns={"model": "NASA POWER", "observed": "Weather station"}))
                    st.dataframe(paired.assign(Error=paired["model"]-paired["observed"]), use_container_width=True)
                    st.caption(tx(
                        "Bias = mean(POWER − station); MAE = mean absolute error; RMSE = root mean squared error; R² = 1 − SSE/SST. Missing pairs are excluded. These statistics describe this station, variable and period only; they are not a universal validation of NASA POWER or of crop predictions.",
                        "Viés = média(POWER − estação); MAE = erro absoluto médio; RMSE = raiz do erro quadrático médio; R² = 1 − SSE/SST. Pares ausentes são excluídos. Estas estatísticas descrevem somente esta estação, variável e período; não validam universalmente o NASA POWER nem previsões agrícolas."
                    ))
            except Exception as exc:
                st.error(tx("Could not process this CSV: ", "Não foi possível processar este CSV: ") + str(exc))
    st.markdown("**" + tx("Official independent validation resources", "Recursos oficiais de validação independente") + "**")
    st.markdown("- [NASA POWER DAV Validate / PRUVE](https://power.larc.nasa.gov/docs/services/api/validate/) — compare POWER with qualifying NOAA/BSRN/AERONET ground observations where available.")
    st.markdown("- [MAPA ZARC / SISZARC](https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/siszarc) — official planting windows by municipality, crop, soil water class and cultivar cycle.")
    st.markdown("- [FAO Irrigation and Drainage Paper 56](https://www.fao.org/4/X0490E/X0490E00.htm) — reference evapotranspiration and crop-coefficient methodology.")

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
                    saved_water = payload.get("water_balance")
                    if saved_water and saved_water.get("daily_rows"):
                        restored_water = pd.DataFrame(saved_water["daily_rows"])
                        restored_water["Date"] = pd.to_datetime(restored_water["Date"])
                        st.session_state["latest_water_balance"] = {
                            "crop": saved_water.get("crop"), "year": saved_water.get("year"),
                            "coords": (float(selected["latitude"]), float(selected["longitude"])),
                            "sowing_month": saved_water.get("sowing_month"),
                            "sowing_day": saved_water.get("sowing_day"),
                            "parameters": saved_water.get("parameters", {}),
                            "table": restored_water
                        }
                    else:
                        st.session_state.pop("latest_water_balance", None)
                    if payload.get("zarc_reference"):
                        st.session_state["zarc_reference"] = payload["zarc_reference"]
                    else:
                        st.session_state.pop("zarc_reference", None)
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
                "water_balance": (
                    {
                        "crop": st.session_state["latest_water_balance"]["crop"],
                        "year": st.session_state["latest_water_balance"]["year"],
                        "sowing_month": st.session_state["latest_water_balance"]["sowing_month"],
                        "sowing_day": st.session_state["latest_water_balance"].get("sowing_day"),
                        "parameters": st.session_state["latest_water_balance"]["parameters"],
                        "daily_rows": st.session_state["latest_water_balance"]["table"].assign(
                            Date=st.session_state["latest_water_balance"]["table"]["Date"].astype(str)
                        ).to_dict(orient="records")
                    } if st.session_state.get("latest_water_balance") else None
                ),
                "zarc_reference": st.session_state.get("zarc_reference"),
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
