import streamlit as st
from guma_brand import apply_brand, render_brand_hero, sidebar_brand
import pandas as pd
from agrovision_validation import paired_validation_metrics
from agrovision_modis import parse_modis_subset, calculate_ndvi_from_reflectance
from agrovision_http import get_with_retries
from agrovision_quality import climate_quality_report, modis_quality_report
from agrovision_agronomy import fao56_reference_et0, crop_coefficient_curve, simulate_root_zone_balance
from agrovision_rotation import ROTATION_SCENARIOS, compare_rotation_scenarios, scenario_disclosure
from agrovision_zarc import list_zarc_resources, load_zarc_csv, find_column, unique_values, filter_zarc_rows, decendio_columns, expand_decendios, crop_matches_app_crop
from agrovision_climate import summarize_local_extremes
from agrovision_commons import build_climate_fingerprint, comparison_distance
from agrovision_fieldlab import ALLOWED_CROPS, ALLOWED_REGIONS, ALLOWED_METRICS, ALLOWED_STAGES, validate_trial_record, validate_trial_update, relative_difference
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

st.set_page_config(page_title="GUMA — Earth Intelligence", page_icon="🌊", layout="wide")

apply_brand()
render_brand_hero()

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
    st.markdown(sidebar_brand(), unsafe_allow_html=True)
    st.selectbox("Language / Idioma", ["English", "Português"], key="agrovision_language")

auth_mode = st.session_state.get("agrovision_auth_mode")
if auth_mode not in ("guest", "email"):
    st.markdown("### " + tx("Welcome to GUMA", "Bem-vindo ao GUMA"))
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
            submitted = st.form_submit_button(tx("Sign in", "Entrar"), width="stretch", disabled=not email_enabled)
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
            create_account = st.form_submit_button(tx("Create account", "Criar conta"), width="stretch", disabled=not email_enabled)
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
    if st.button(tx("Continue as visitor →", "Continuar como visitante →"), type="primary", width="stretch"):
        st.session_state["agrovision_auth_mode"] = "guest"
        st.rerun()
    st.caption(tx("Visitor access does not require registration. Email authentication will become available after the project owner configures Supabase.", "O acesso de visitante não exige cadastro. A autenticação por e-mail depende da configuração do Supabase pelo responsável pelo projeto."))
    st.stop()

with st.sidebar:
    if st.session_state.get("agrovision_auth_mode") == "email":
        st.caption(f"Signed in as {st.session_state.get('agrovision_user_email', 'user')}")
    else:
        st.caption(tx("Browsing as a visitor", "Navegando como visitante"))
    if st.button(tx("Sign out / Exit", "Sair da conta"), width="stretch"):
        for key in ("agrovision_auth_mode", "agrovision_access_token", "agrovision_user_email", "climate", "modis", "coords"):
            st.session_state.pop(key, None)
        st.rerun()

@st.cache_data(ttl=3600, max_entries=8, show_spinner=False)
def get_nasa_power(lat, lon):
    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    params = {"parameters":"T2M,T2M_MAX,T2M_MIN,T2MDEW,WS2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN","community":"AG","longitude":lon,"latitude":lat,"start":"20200101","end":"20251231","format":"JSON"}
    response = get_with_retries(url, params=params, timeout=90, attempts=3, backoff_seconds=1.5)
    response.raise_for_status()
    values = response.json()["properties"]["parameter"]
    frame = pd.DataFrame(values).apply(pd.to_numeric, errors="coerce")
    frame.index = pd.to_datetime(frame.index, format="%Y%m%d")
    # NASA POWER uses -999 as a missing-value sentinel; convert it to NaN
    # while keeping the climate columns numeric for aggregation and charts.
    return frame.mask(frame == -999)

@st.cache_data(ttl=86400, max_entries=4, show_spinner=False)
def get_modis(lat, lon, start_year=2020, end_year=2025):
    """Retrieve MOD13Q1 observations in batches of at most ten composites.

    ORNL DAAC's point-subset endpoint limits each request to ten MODIS dates.
    The dates endpoint is used to obtain the actual available composite dates.
    """
    api_root = "https://modis.ornl.gov/rst/api/v1/MOD13Q1"
    common = {"latitude": lat, "longitude": lon}
    dates_response = get_with_retries(
        f"{api_root}/dates",
        params=common,
        timeout=60,
        attempts=3
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
    date_batches = [
        selected_dates[offset:offset + 10]
        for offset in range(0, len(selected_dates), 10)
    ]

    def fetch_batch(date_batch):
        params = {
            **common,
            "startDate": date_batch[0],
            "endDate": date_batch[-1],
            "kmAboveBelow": 0,
            "kmLeftRight": 0
        }
        response = get_with_retries(
            f"{api_root}/subset",
            params=params,
            timeout=90,
            attempts=4,
            backoff_seconds=2
        )
        return parse_modis_subset(response.json())

    # Fetch a few independent date windows concurrently. This reduces the
    # first-load wait without increasing pressure on ORNL excessively.
    records = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        for batch_records in executor.map(fetch_batch, date_batches):
            for day, bands in batch_records.items():
                records.setdefault(day, {}).update(bands)
    rows = []
    for day, bands in records.items():
        nir = bands.get("250m_16_days_NIR_reflectance")
        red = bands.get("250m_16_days_red_reflectance")
        quality = bands.get("250m_16_days_pixel_reliability")
        ndvi = calculate_ndvi_from_reflectance(nir, red, quality)
        rows.append({
            "Date": pd.Timestamp(day),
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

with st.sidebar:
    st.header(tx("Study area", "Área de estudo"))
    st.caption(tx("Enter the coordinates of the area you want to investigate.", "Informe as coordenadas da área que deseja investigar."))
    if st.button(tx("📍 Use Rio Verde, GO pilot", "📍 Usar piloto de Rio Verde, GO"), width="stretch", help=tx("Loads the municipal-seat coordinates as a demonstration study point. Replace them with farm coordinates for local analysis.", "Carrega as coordenadas da sede municipal como ponto de demonstração. Substitua pelas coordenadas da propriedade para análise local.")):
        st.session_state["lat_value"] = -17.79
        st.session_state["lon_value"] = -50.91
        st.session_state["elevation_m"] = 748.0
        st.rerun()
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

tab_home, tab_atlas, tab_help, tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab_rotation, tab_climate, tab_commons, tab_fieldlab, tab_partners, tab_systems, tab_trend, tab_earthdata = st.tabs([
    tx("🌐 00 · Earth Observatory", "🌐 00 · Observatório da Terra"),
    tx("🗺️ 01 · GUMA Atlas", "🗺️ 01 · Atlas GUMA"),
    tx("👋 02 · Start here", "👋 02 · Comece aqui"),
    tx("🛰️ 03 · Earth data", "🛰️ 03 · Dados da Terra"),
    tx("🌱 04 · Crop intelligence", "🌱 04 · Inteligência agrícola"),
    tx("📚 05 · Data & methods", "📚 05 · Dados e métodos"),
    tx("🗂️ 06 · Workspace", "🗂️ 06 · Projetos"),
    tx("🧪 07 · Validation", "🧪 07 · Validação"),
    tx("📖 08 · Knowledge", "📖 08 · Conhecimento"),
    tx("📊 09 · Evidence", "📊 09 · Evidências"),
    tx("🌾 10 · Rotation Lab", "🌾 10 · Rotação de culturas"),
    tx("🌍 11 · Climate Watch", "🌍 11 · Monitoramento climático"),
    tx("🧬 12 · Commons", "🧬 12 · Comunidade"),
    tx("🔬 13 · Field Lab", "🔬 13 · Laboratório de Campo"),
    tx("🤝 14 · Partnerships", "🤝 14 · Alianças"),
    tx("🌾 15 · Agronomic Systems", "🌾 15 · Sistemas agronômicos"),
    tx("📈 16 · Trend Detective", "📈 16 · Detetive de Tendências"),
    tx("🛰️ 17 · Earth Data Observatory", "🛰️ 17 · Observatório de Dados da Terra")
], on_change="rerun", key="guma_main_tabs")

if tab_trend.open:
    with tab_trend:
        st.markdown("### GUMA Trend Detective")
        st.caption(tx("NASA Space Apps Challenge 2026 · Challenge 02", "NASA Space Apps Challenge 2026 · Desafio 02"))
        st.write(tx("Open the dedicated trend-analysis workspace to test long-term environmental signals with the Mann–Kendall test and Sen’s slope.", "Abra o ambiente dedicado de análise de tendências para testar sinais ambientais de longo prazo com o teste de Mann–Kendall e a inclinação de Sen."))
        if st.button(tx("Open Trend Detective", "Abrir Detetive de Tendências"), type="primary", key="open_guma_trend_page"):
            st.switch_page("pages/01_Trend_Detective.py")

if tab_earthdata.open:
    with tab_earthdata:
        st.markdown("### GUMA Earth Data Observatory")
        st.caption(tx("Sentinel-2 · NASA FIRMS · IBGE", "Sentinel-2 · NASA FIRMS · IBGE"))
        st.write(tx("Explore satellite scene metadata, recent active-fire detections and official Brazilian territorial codes, with source provenance and quality limitations.", "Explore metadados de cenas de satélite, detecções recentes de fogo e códigos territoriais oficiais do Brasil, com procedência e limitações de qualidade."))
        if st.button(tx("Open Earth Data Observatory", "Abrir Observatório de Dados da Terra"), type="primary", key="open_guma_earth_data_page"):
            st.switch_page("pages/02_Earth_Data_Observatory.py")


if tab6.open:
    with tab6:
        st.header(tx("GUMA Knowledge", "Conhecimento GUMA"))
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
            "Start with the explanation, open the primary reference, and then return to the relevant GUMA tool. Each material is educational: verify the source, date, geographic scope and assumptions before using information in a real-world decision.",
            "Comece pela explicação, abra a referência primária e depois volte à ferramenta correspondente do GUMA. Os materiais são educativos: confira fonte, data, abrangência geográfica e hipóteses antes de usar a informação em uma decisão real."
        ))
        st.caption(tx(
            "Editorial library · Foundational references, not a live news feed. New research and official updates are reviewed separately.",
            "Biblioteca editorial · Referências fundamentais, não um feed de notícias em tempo real. Novas pesquisas e atualizações oficiais são verificadas separadamente."
        ))
    
if tab7.open:
    with tab7:
        st.header(tx("Integrated evidence dashboard", "Painel integrado de evidências"))
        st.write(tx("A consolidated view of climate, vegetation, crop-water and official zoning evidence attached to this study area.", "Uma visão consolidada das evidências de clima, vegetação, balanço hídrico e zoneamento oficial desta área."))
        st.info(tx("No composite suitability score or planting recommendation is calculated. Missing evidence is shown explicitly.", "Nenhuma pontuação geral de aptidão ou recomendação de plantio é calculada. As evidências ausentes são identificadas."))
        current_coords = (float(lat), float(lon))
        climate_ready = "climate" in st.session_state and st.session_state.get("coords") == current_coords
        if climate_ready:
            climate_evidence = st.session_state["climate"]
            indicators = [("NASA POWER · T2M", climate_evidence["T2M"], "°C"), ("NASA POWER · PRECTOTCORR", climate_evidence["PRECTOTCORR"], "mm"), ("NASA POWER · ALLSKY_SFC_SW_DWN", climate_evidence["ALLSKY_SFC_SW_DWN"], "kWh/m²/day")]
            rows = []
            for label, series, unit in indicators:
                valid = series.dropna()
                value = valid.mean() if "T2M" in label or "ALLSKY" in label else valid.sum()
                rows.append({"Indicator": label, "Valid records": len(valid), "Coverage (%)": round(100*len(valid)/max(1,len(series)),1), "Summary": f"{value:.2f} {unit}" if len(valid) else "No valid values"})
            st.subheader(tx("Climate evidence", "Evidências climáticas"))
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
        else:
            st.warning(tx("Load environmental data for the selected coordinates first.", "Carregue primeiro os dados ambientais das coordenadas selecionadas."))
        vegetation = st.session_state.get("modis", pd.DataFrame())
        if climate_ready and not vegetation.empty:
            usable = vegetation.dropna(subset=["NDVI"])
            st.subheader(tx("MODIS vegetation evidence", "Evidências de vegetação MODIS"))
            if not usable.empty:
                v1, v2, v3 = st.columns(3)
                v1.metric(tx("Usable composites", "Composições válidas"), len(usable))
                v2.metric(tx("Mean NDVI", "NDVI médio"), f"{usable['NDVI'].mean():.3f}")
                v3.metric(tx("Period", "Período"), str(pd.to_datetime(usable["Date"]).dt.year.min()) + "–" + str(pd.to_datetime(usable["Date"]).dt.year.max()))
            else:
                st.warning(tx("No usable quality-screened NDVI observations.", "Nenhuma observação NDVI passou pelo filtro de qualidade."))
        else:
            st.caption(tx("No MODIS series is attached to the current study coordinates.", "Não há série MODIS vinculada às coordenadas atuais."))
        saved_balance = st.session_state.get("latest_water_balance")
        if saved_balance and saved_balance.get("coords") == current_coords and saved_balance.get("table") is not None:
            balance_table = saved_balance["table"]
            st.subheader(tx("Exploratory FAO-56 crop-water scenario", "Cenário exploratório de balanço hídrico FAO-56"))
            a, b, c, d = st.columns(4)
            a.metric(tx("Crop", "Cultura"), str(saved_balance.get("crop", "—")))
            b.metric(tx("Season", "Safra"), str(saved_balance.get("year", "—")))
            c.metric("ETc", f"{balance_table['ETc potential (mm)'].sum():.1f} mm")
            d.metric("ETa", f"{balance_table['ETa actual estimate (mm)'].sum():.1f} mm")
            st.caption(tx("User-entered parameters; simplified one-layer bucket; not calibrated or an irrigation prescription.", "Parâmetros informados pelo usuário; reservatório simplificado de uma camada; não calibrado nem prescrição de irrigação."))
        else:
            st.caption(tx("No water-balance run is attached for the current coordinates.", "Nenhuma simulação de balanço hídrico está vinculada às coordenadas atuais."))
        zarc_evidence = st.session_state.get("zarc_reference")
        if zarc_evidence:
            st.subheader(tx("Official MAPA ZARC reference", "Referência oficial ZARC/MAPA"))
            zarc_keys = ("Crop", "UF", "Municipality", "Soil code", "Cultivar group / cycle", "Management", "Climate", "Ordinance", "Season dataset")
            zarc_rows = [{"Field": key, "Value": zarc_evidence.get(key, "")} for key in zarc_keys if zarc_evidence.get(key, "")]
            if zarc_rows:
                st.dataframe(pd.DataFrame(zarc_rows), width="stretch", hide_index=True)
            st.markdown("[Open official MAPA source](" + str(zarc_evidence.get("Source URL", "https://dados.agricultura.gov.br/dataset/tabua-de-risco-zoneamento-agricola-de-risco-climatico")) + ")")
        else:
            st.caption(tx("No official ZARC row has been attached yet.", "Nenhum registro oficial ZARC foi vinculado ainda."))
        st.divider()
        st.subheader(tx("Evidence still needed", "Evidências ainda necessárias"))
        st.markdown(tx("- Exact farm boundary and representative satellite pixel.\n- Laboratory soil analysis and measured root-zone properties.\n- Confirmed cultivar, cycle, management and current ZARC ordinance.\n- Comparison with a quality-controlled local weather station.\n- Field validation of the water-balance scenario.", "- Limite exato da propriedade e pixel de satélite representativo.\n- Análise laboratorial do solo e propriedades medidas da zona radicular.\n- Cultivar, ciclo, manejo e portaria ZARC vigente confirmados.\n- Comparação com estação meteorológica local controlada.\n- Validação do balanço hídrico em campo."))
        st.caption(tx("Evidence summary only — not a calibrated agronomic decision-support system.", "Apenas resumo de evidências — não é um sistema calibrado de apoio à decisão agronômica."))
    
if tab_help.open:
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
            st.warning("These are user-provided context values. GUMA does not measure soil texture or fertility from NASA data.")
    
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
            st.markdown("**GUMA can help you:**")
            st.markdown("- Explore climate indicators for a selected location.\n- View satellite-derived vegetation observations.\n- Compare historical climate during representative cycles of maize, soybean and common bean.\n- Review the reference ranges and assumptions behind each crop screen.")
        with right:
            st.markdown("**GUMA does not currently:**")
            st.markdown("- Measure soil properties directly.\n- Reproduce the full official ZARC/SARRA model.\n- Predict crop yield or farm profit.\n- Provide a certified planting or irrigation recommendation.\n- Display SMAP data in this public deployment.")
        st.caption("GUMA · " + tx("First-visit guide · Agricultural climate analysis", "Guia inicial · Análise climática agrícola"))
    
if tab1.open:
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
        if st.button(tx("🛰️ Load environmental data", "🛰️ Carregar dados ambientais"), type="primary", width="stretch"):
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
        
        
@st.cache_data(ttl=86400, max_entries=1, show_spinner=False)
def get_climate_watch_data():
    from agrovision_climate import fetch_climate_watch
    return fetch_climate_watch()

if tab_home.open:
    with tab_home:
        st.markdown("""
        <div style="padding:1.65rem 1.8rem;border:1px solid #C9BDA7;border-radius:20px;
          background:radial-gradient(circle at 90% 8%,rgba(36,200,181,.18),transparent 30%),
          radial-gradient(circle at 4% 100%,rgba(185,243,107,.09),transparent 35%),
          linear-gradient(115deg,#18272B,#2457A6 68%,#63764B);margin:.3rem 0 1rem 0">
          <div style="color:#D85B3D;font-size:.7rem;letter-spacing:.2em;font-weight:800">GUMA · EARTH INTELLIGENCE PLATFORM</div>
          <h1 style="color:#F1E8D5;margin:.35rem 0 .45rem 0;font-size:2.15rem">Observe the Earth. Understand the signals.</h1>
          <p style="color:#C3D4D8;margin:0;max-width:900px;line-height:1.6">A connected workspace for planetary change, territorial evidence and agricultural systems — from global climate signals to a selected study point.</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("**" + tx("THE OBSERVATORY", "O OBSERVATÓRIO") + "**")
        st.caption(tx("One platform, four connected domains. Start with a territory, follow the environmental signals, and inspect the evidence behind each interpretation.",
                     "Uma plataforma, quatro domínios conectados. Comece por um território, acompanhe os sinais ambientais e examine as evidências por trás de cada interpretação."))
        d1,d2,d3,d4=st.columns(4)
        d1.metric(tx("Territory", "Território"), f"{lat:.3f}, {lon:.3f}", tx("Selected study point", "Ponto de estudo selecionado"))
        climate_loaded = "climate" in st.session_state and st.session_state.get("coords") == (lat,lon)
        vegetation_loaded = climate_loaded and not st.session_state.get("modis", pd.DataFrame()).empty
        d2.metric(tx("Climate data", "Dados climáticos"), tx("Loaded", "Carregados") if climate_loaded else tx("Not loaded", "Não carregados"))
        d3.metric("MODIS NDVI", tx("Available", "Disponível") if vegetation_loaded else tx("Not loaded", "Não carregado"))
        d4.metric(tx("Global observatory", "Observatório global"), tx("On demand", "Sob demanda"), tx("NASA · NOAA", "NASA · NOAA"))
        st.divider()
        st.subheader(tx("Explore the Earth", "Explore a Terra"))
        map_left,map_right=st.columns([1.55,1])
        with map_left:
            st.caption(tx("Select a point to connect the platform's local analysis to a territory. Use the layer control to switch between street, satellite and topographic views.",
                         "Selecione um ponto para conectar a análise local da plataforma a um território. Use o controle de camadas para alternar entre mapa de ruas, satélite e topografia."))
            map_center = [st.session_state.get("lat_value", -15.8), st.session_state.get("lon_value", -47.0)]
            study_map = folium.Map(location=map_center, zoom_start=5, control_scale=True, tiles="OpenStreetMap")
            folium.TileLayer(tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", attr="Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community", name="Satellite imagery", overlay=False, control=True).add_to(study_map)
            folium.TileLayer(tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}", attr="Tiles © Esri — National Geographic, Esri, Garmin, HERE, UNEP-WCMC, USGS, NASA, ESA, METI, NRCAN, GEBCO, NOAA, increment P Corp.", name="Topographic map", overlay=False, control=True).add_to(study_map)
            folium.LayerControl(collapsed=True).add_to(study_map)
            folium.CircleMarker(location=map_center, radius=8, color="#D85B3D", weight=3, fill=True, fill_color="#E2B75F", fill_opacity=.9, tooltip="Current study area").add_to(study_map)
            map_event = st_folium(study_map, height=390, use_container_width=True, returned_objects=["last_clicked"], key="guma_observatory_map")
            if map_event and map_event.get("last_clicked"):
                clicked_lat = round(float(map_event["last_clicked"]["lat"]),4)
                clicked_lon = round(float(map_event["last_clicked"]["lng"]),4)
                clicked_point=(clicked_lat,clicked_lon)
                if clicked_point != st.session_state.get("last_map_click"):
                    st.session_state["last_map_click"]=clicked_point
                    # Apply map selections before the sidebar number_input widgets
                    # are instantiated on the next rerun.
                    st.session_state["pending_study_coords"]=(clicked_lat,clicked_lon)
                    st.rerun()
        with map_right:
            st.markdown("**" + tx("A connected Earth system", "Um sistema terrestre conectado") + "**")
            with st.container(border=True):
                st.markdown("**01 · " + tx("Climate intelligence", "Inteligência climática") + "**")
                st.caption(tx("Global temperature, greenhouse gases and local climate extremes.", "Temperatura global, gases de efeito estufa e extremos climáticos locais."))
            with st.container(border=True):
                st.markdown("**02 · " + tx("Earth observation", "Observação da Terra") + "**")
                st.caption(tx("Satellite-derived vegetation signals and environmental context.", "Sinais de vegetação derivados de satélite e contexto ambiental."))
            with st.container(border=True):
                st.markdown("**03 · " + tx("Agricultural intelligence", "Inteligência agrícola") + "**")
                st.caption(tx("Crop windows, water balance, rotation scenarios and official references.", "Janelas de cultivo, balanço hídrico, cenários de rotação e referências oficiais."))
            with st.container(border=True):
                st.markdown("**04 · " + tx("Research commons", "Pesquisa colaborativa") + "**")
                st.caption(tx("Transparent methods, validation, shared observations and field hypotheses.", "Métodos transparentes, validação, observações compartilhadas e hipóteses de campo."))
        st.divider()
        st.subheader(tx("Global climate pulse", "Pulso climático global"))
        st.caption(tx("Load the latest available NASA and NOAA monthly series. Publication dates differ by dataset; these are not real-time measurements.",
                     "Carregue as séries mensais mais recentes disponíveis da NASA e NOAA. As datas de publicação variam por base; não são medições em tempo real."))
        if st.button(tx("Retrieve global indicators", "Consultar indicadores globais"), type="primary", key="home_global_climate"):
            try:
                with st.spinner(tx("Retrieving NASA and NOAA datasets…", "Consultando bases da NASA e NOAA…")):
                    st.session_state["guma_global_climate"] = get_climate_watch_data()
                st.success(tx("Global indicators updated.", "Indicadores globais atualizados."))
            except Exception as exc:
                st.warning(tx("Global indicators could not be retrieved: ", "Não foi possível consultar os indicadores globais: ") + str(exc))
        global_data = st.session_state.get("guma_global_climate")
        if global_data:
            t=global_data["temperature"]; c=global_data["co2"]; m=global_data["ch4"]; n=global_data["n2o"]
            if all(not x.empty for x in (t,c,m,n)):
                last_t,last_c,last_m,last_n=t.iloc[-1],c.iloc[-1],m.iloc[-1],n.iloc[-1]
                g1,g2,g3,g4=st.columns(4)
                g1.metric(tx("Global temperature anomaly","Anomalia da temperatura global"),f"{last_t['Anomaly_C']:+.2f} °C",tx("vs 1951–1980","vs. 1951–1980"))
                g2.metric("CO₂ · Mauna Loa",f"{last_c['CO2_ppm']:.1f} ppm",f"{last_c['Date']:%b %Y}")
                g3.metric("CH₄ · NOAA",f"{last_m['CH4_ppb']:.1f} ppb",f"{last_m['Date']:%b %Y}")
                g4.metric("N₂O · NOAA",f"{last_n['N2O_ppb']:.2f} ppb",f"{last_n['Date']:%b %Y}")
                st.caption(tx(f"Retrieved {global_data['retrieved_at']:%Y-%m-%d %H:%M UTC}. Open Climate Watch for full time series, methodology and local extreme indicators.",
                              f"Consulta em {global_data['retrieved_at']:%d/%m/%Y %H:%M UTC}. Abra Monitoramento climático para séries completas, metodologia e indicadores locais de extremos."))
                annual=t.assign(Year=t["Date"].dt.year).groupby("Year")["Anomaly_C"].mean()
                st.area_chart(annual.rename("Annual global temperature anomaly (°C)"),height=210)
            else:
                st.warning(tx("At least one climate dataset has no usable observations.", "Pelo menos uma série climática não possui observações utilizáveis."))
        else:
            st.info(tx("No global climate snapshot has been requested in this session yet.", "Nenhum retrato climático global foi solicitado nesta sessão."))
        st.divider()
        st.subheader(tx("Platform modules", "Módulos da plataforma"))
        module_cards=[
          ("🌍","Climate Watch",tx("Planetary warming, greenhouse gases and local extremes.","Aquecimento global, gases de efeito estufa e extremos locais."),"10"),
          ("🛰️",tx("Earth data","Dados da Terra"),tx("NASA POWER climate series and MODIS vegetation observations.","Séries climáticas NASA POWER e observações de vegetação MODIS."),"02"),
          ("🌱",tx("Crop intelligence","Inteligência agrícola"),tx("Crop-specific climate screening, FAO-56 water balance and ZARC references.","Análise climática por cultura, balanço hídrico FAO-56 e referências ZARC."),"03"),
          ("🌾","Rotation Lab",tx("Compare transparent historical crop-window scenarios.","Compare cenários históricos transparentes de janelas de cultivo."),"09"),
          ("📚",tx("Knowledge","Conhecimento"),tx("Methods, scientific references and data interpretation.","Métodos, referências científicas e interpretação de dados."),"07"),
          ("🧪",tx("Validation & Field Lab","Validação e Laboratório de Campo"),tx("Compare station observations and document field hypotheses.","Compare observações de estações e documente hipóteses de campo."),"06 / 12"),
          ("🧬","GUMA Commons",tx("Opt-in climate fingerprints and community comparisons.","Assinaturas climáticas voluntárias e comparações comunitárias."),"11"),
          ("🗂️",tx("Workspace","Área de trabalho"),tx("Save and retrieve studies linked to your account.","Salve e recupere estudos vinculados à sua conta."),"05"),
        ]
        for start in range(0,len(module_cards),4):
            cols=st.columns(4)
            for col,item in zip(cols,module_cards[start:start+4]):
                with col:
                    with st.container(border=True):
                        st.markdown(f"### {item[0]} {item[1]}")
                        st.caption(item[2])
                        st.caption(tx("MODULE","MÓDULO")+" "+item[3])
        st.subheader(tx("Beyond agriculture · Earth systems roadmap", "Além da agricultura · Roteiro dos sistemas terrestres"))
        roadmap = [
          ("🌊", tx("Oceans & cryosphere", "Oceanos e criosfera"), tx("Sea level, ocean heat, sea-surface conditions, glaciers and ice sheets.", "Nível do mar, calor oceânico, condições da superfície do mar, geleiras e mantos de gelo."), tx("Planned · source integration and uncertainty review", "Planejado · integração das fontes e revisão de incertezas")),
          ("🌳", tx("Forests, biodiversity & fire", "Florestas, biodiversidade e fogo"), tx("Forest cover, restoration, habitat context, fire scars and ecosystem change.", "Cobertura florestal, restauração, contexto de habitats, cicatrizes de fogo e mudanças ecossistêmicas."), tx("Planned · Brazilian public datasets first", "Planejado · prioridade às bases públicas brasileiras")),
          ("🗺️", tx("Land use & territorial change", "Uso do solo e transformação territorial"), tx("Annual land-cover transitions, agriculture, pasture, mining and urban expansion.", "Transições anuais de cobertura, agricultura, pastagem, mineração e expansão urbana."), tx("Planned · MapBiomas / INPE pathways", "Planejado · integração MapBiomas / INPE")),
          ("💧", tx("Water & environmental risk", "Água e risco ambiental"), tx("River basins, water availability, floods, droughts, landslides and observation networks.", "Bacias hidrográficas, disponibilidade hídrica, enchentes, secas, deslizamentos e redes de observação."), tx("Planned · ANA / CEMADEN pathways", "Planejado · integração ANA / CEMADEN")),
        ]
        for row in roadmap:
            with st.container(border=True):
                c1,c2=st.columns([1,4])
                c1.markdown(f"### {row[0]} {row[1]}")
                c2.write(row[2])
                c2.caption(row[3])
        st.caption(tx("Roadmap only: these layers are not represented as integrated datasets until ingestion, provenance, licensing and quality checks are implemented.",
                      "Apenas roteiro: essas camadas não são apresentadas como bases integradas até que ingestão, proveniência, licenciamento e controle de qualidade sejam implementados."))
        st.caption(tx("Scientific transparency: GUMA distinguishes observed datasets, derived indicators, exploratory scenarios and user-provided context. No output on this page is a calibrated yield forecast or agronomic prescription.",
                      "Transparência científica: GUMA distingue bases observadas, indicadores derivados, cenários exploratórios e contexto informado pelo usuário. Nenhum resultado desta página é previsão calibrada de produtividade ou prescrição agronômica."))
    
if tab_partners.open:
    with tab_partners:
        st.markdown("""
        <div style="padding:1.55rem 1.8rem;border:1px solid #C9BDA7;border-radius:18px;
          background:radial-gradient(circle at 92% 8%,rgba(36,200,181,.18),transparent 30%),
          linear-gradient(115deg,#18272B,#15364A 70%,#155568);margin:.3rem 0 1rem 0">
          <div style="color:#D85B3D;font-size:.7rem;letter-spacing:.2em;font-weight:800">GUMA · ECOSYSTEM DEVELOPMENT</div>
          <h1 style="color:#F1E8D5;margin:.3rem 0">PARTNERSHIPS & ALLIANCES</h1>
          <p style="color:#C3D4D8;margin:0">Build the network behind better Earth intelligence — science, public data, infrastructure, field validation and responsible innovation.</p>
        </div>
        """, unsafe_allow_html=True)
        st.write(tx("This is a prospecting map, not a list of confirmed partners. Every organization below is an independent institution or initiative; no endorsement, agreement or active relationship with GUMA is implied.",
                    "Este é um mapa de prospecção, não uma lista de parceiros confirmados. Cada organização ou iniciativa abaixo é independente; não implica endosso, acordo ou relacionamento ativo com a GUMA."))
        p1,p2,p3,p4=st.columns(4)
        p1.metric(tx("Public-data pathways","Caminhos de dados públicos"),"6+")
        p2.metric(tx("Research & funding routes","Rotas de pesquisa e fomento"),"5+")
        p3.metric(tx("Private innovation routes","Rotas de inovação privada"),"3+")
        p4.metric(tx("Priority","Prioridade"),tx("Evidence first","Evidência primeiro"))
        st.divider()
        st.subheader(tx("How alliances can strengthen GUMA","Como alianças podem fortalecer a GUMA"))
        st.markdown(tx(
          """- **Data & APIs:** authoritative datasets, documented access, metadata and update cadence.
    - **Scientific review:** independent review of methods, uncertainty, validation and reproducibility.
    - **Field pilots:** compare satellite and gridded products with stations, farms, watersheds and field observations.
    - **Compute & technology:** geospatial infrastructure, cloud credits, GIS, AI and engineering support.
    - **Funding & institutional support:** grants, research agreements, innovation calls and student/researcher networks.
    - **Distribution & adoption:** connect outputs to cooperatives, public managers, researchers and producers.""",
          """- **Dados e APIs:** bases confiáveis, acesso documentado, metadados e frequência de atualização.
    - **Revisão científica:** avaliação independente de métodos, incertezas, validação e reprodutibilidade.
    - **Pilotos de campo:** comparar satélites e produtos em grade com estações, propriedades, bacias e observações de campo.
    - **Computação e tecnologia:** infraestrutura geoespacial, créditos de nuvem, SIG, IA e apoio de engenharia.
    - **Fomento e apoio institucional:** editais, acordos de pesquisa, chamadas de inovação e redes de estudantes/pesquisadores.
    - **Distribuição e adoção:** conectar resultados a cooperativas, gestores públicos, pesquisadores e produtores."""
        ))
        partners = [
          {"name":"INPE","kind":"Public science & data","priority":"A · Strategic","fit":"Earth observation, land-cover monitoring, fire, deforestation and satellite products.","ask":"Technical dialogue, public datasets, methodological references and possible research collaboration.","offer":"A transparent integration layer, reproducible workflows, documented use cases and feedback on data usability.","url":"https://www.gov.br/inpe/pt-br","label":"Official institute"},
          {"name":"INMET","kind":"Public data & validation","priority":"A · Strategic","fit":"Meteorological station observations and AgroMet context for Brazilian agricultural territories.","ask":"Documented access to station observations, metadata, quality flags and validation guidance.","offer":"Comparative dashboards, station-vs-grid validation notebooks and clear attribution.","url":"https://portal.inmet.gov.br/","label":"Official service"},
          {"name":"EMBRAPA","kind":"Applied agricultural research","priority":"A · Strategic","fit":"Crop science, soil, agroclimatology, production systems and applied validation.","ask":"Scientific review, crop-calendar expertise, research questions and potential field pilot partners.","offer":"Exploratory geospatial tools, transparent climate screening and collaborative research prototypes.","url":"https://www.embrapa.br/","label":"Research institution"},
          {"name":"CEMADEN","kind":"Public risk monitoring","priority":"B · High value","fit":"Rainfall, hydrology, geotechnical monitoring and disaster-risk observation networks.","ask":"Methods, station/network metadata and opportunities to compare environmental signals with risk observations.","offer":"Territorial visualizations and reproducible analysis of climate extremes, with limitations explicit.","url":"https://www.gov.br/cemaden/pt-br","label":"Public monitoring"},
          {"name":"MMA · INDE","kind":"Public geospatial infrastructure","priority":"A · Strategic","fit":"Catalogued geospatial data on biodiversity, forests, water, climate and territorial policy.","ask":"Discovery of authoritative layers, metadata standards, services and licensing guidance.","offer":"Interoperable map views, source attribution and accessible territorial synthesis.","url":"https://www.gov.br/mma/pt-br/acesso-a-informacao/informacoes-ambientais/mapas-interativos","label":"Public data ecosystem"},
          {"name":"MapBiomas","kind":"Research network & open data","priority":"A · Strategic","fit":"Annual land-cover/use, agriculture, pasture, fire, water, mining and soil-carbon datasets.","ask":"Use guidance, technical documentation, network contacts and potential research collaboration.","offer":"New interfaces for exploring public layers and cross-domain analysis with transparent citations.","url":"https://brasil.mapbiomas.org/","label":"Multi-institutional network"},
          {"name":"FINEP · COOPERAMAIS","kind":"Public innovation funding","priority":"B · Eligibility-dependent","fit":"Funding pathways for technology development in family farming, agroindustry, digital transformation and climate resilience.","ask":"Eligibility guidance and a qualified institutional/company/cooperative consortium if a matching call is open.","offer":"A defined technical work package, measurable deliverables and transparent prototype evidence.","url":"https://www.finep.gov.br/l/1060720","label":"Funding call · check rules"},
          {"name":"FAPESP / CONFAP / State FAPs","kind":"Research funding & networks","priority":"B · Eligibility-dependent","fit":"Research grants, cooperation agreements and state-level science/innovation ecosystems.","ask":"Academic host, principal investigator, research plan and fit with current calls.","offer":"Open, reproducible software and a research platform that can support a funded project.","url":"https://www.fapesp.br/acordos/","label":"Funding & cooperation"},
          {"name":"EMBRAPII","kind":"Industry–research collaboration","priority":"B · Eligibility-dependent","fit":"Applied R&D through accredited research units and business partners.","ask":"Identify a suitable accredited unit and company challenge with a defined R&D scope.","offer":"Problem framing, geospatial prototype and a route to validate an applied solution.","url":"https://embrapii.org.br/","label":"Innovation ecosystem"},
          {"name":"Petrobras · Open Innovation","kind":"Private-sector innovation","priority":"B · Challenge-dependent","fit":"Open innovation, technology transfer, solution acquisition and collaborative development; potentially relevant to ocean, climate, energy and geospatial monitoring.","ask":"Track published challenges and assess fit before submitting a proposal; no standing GUMA invitation is assumed.","offer":"A focused demonstrator for environmental monitoring or territorial intelligence with measurable technical criteria.","url":"https://petrobras.com.br/inovacao-e-tecnologia/inovacao-aberta","label":"Open innovation portal"},
          {"name":"Agtech Innovation","kind":"Private-sector ecosystem","priority":"B · Program-dependent","fit":"Corporate innovation programs, startup connections and farmer-centered technology adoption.","ask":"Explore program fit, introductions to agribusiness partners and pilot opportunities when calls are open.","offer":"A research-led geospatial prototype for climate risk, crop systems and territorial intelligence.","url":"https://www.pwc.com.br/pt/consultoria/agtech-innovation-en/programs.html","label":"Innovation programs"},
        ]
        categories = [tx("All prospects","Todas as possibilidades"),"Public science & data","Applied agricultural research","Public risk monitoring","Public geospatial infrastructure","Research network & open data","Public innovation funding","Research funding & networks","Industry–research collaboration","Private-sector innovation","Private-sector ecosystem","Public data & validation"]
        chosen = st.selectbox(tx("Filter the alliance landscape","Filtrar o mapa de alianças"),categories,key="guma_partner_filter")
        visible = partners if chosen == categories[0] else [x for x in partners if x["kind"] == chosen]
        partner_pt = {
          "INPE":("Ciência e dados públicos","Observação da Terra, monitoramento do uso do solo, fogo, desmatamento e produtos de satélite.","Diálogo técnico, bases públicas, referências metodológicas e possível colaboração de pesquisa.","Uma camada transparente de integração, fluxos reproduzíveis, casos de uso documentados e retorno sobre a usabilidade dos dados.","Instituto oficial"),
          "INMET":("Dados públicos e validação","Observações de estações meteorológicas e contexto AgroMet para territórios agrícolas brasileiros.","Acesso documentado a observações, metadados, indicadores de qualidade e orientação para validação.","Painéis comparativos, cadernos de validação estação versus grade e atribuição clara das fontes.","Serviço oficial"),
          "EMBRAPA":("Pesquisa agrícola aplicada","Ciência das culturas, solos, agrometeorologia, sistemas produtivos e validação aplicada.","Revisão científica, conhecimento de calendários agrícolas, perguntas de pesquisa e possíveis pilotos de campo.","Ferramentas geoespaciais exploratórias, triagem climática transparente e protótipos colaborativos de pesquisa.","Instituição de pesquisa"),
          "CEMADEN":("Monitoramento público de riscos","Chuva, hidrologia, monitoramento geotécnico e redes de observação de riscos e desastres.","Métodos, metadados das redes e oportunidades para comparar sinais ambientais com observações de risco.","Visualizações territoriais e análises reproduzíveis de extremos climáticos, com limitações explícitas.","Monitoramento público"),
          "MMA · INDE":("Infraestrutura geoespacial pública","Dados geoespaciais catalogados sobre biodiversidade, florestas, água, clima e políticas territoriais.","Identificação de camadas oficiais, metadados, padrões de serviços e orientação sobre licenças.","Visualizações interoperáveis, atribuição de fontes e síntese territorial acessível.","Ecossistema de dados públicos"),
          "MapBiomas":("Rede de pesquisa e dados abertos","Bases anuais de cobertura e uso da terra, agricultura, pastagem, fogo, água, mineração e carbono no solo.","Orientação de uso, documentação técnica, contatos da rede e possível colaboração de pesquisa.","Novas interfaces para explorar camadas públicas e análises entre domínios com citações transparentes.","Rede multi-institucional"),
          "FINEP · COOPERAMAIS":("Fomento público à inovação","Caminhos de financiamento para tecnologia na agricultura familiar, agroindústria, transformação digital e resiliência climática.","Orientação sobre elegibilidade e eventual consórcio qualificado entre instituição, empresa e cooperativa, se houver chamada compatível.","Um pacote técnico definido, entregáveis mensuráveis e evidências transparentes do protótipo.","Edital · conferir regras"),
          "FAPESP / CONFAP / State FAPs":("Fomento e redes de pesquisa","Auxílios à pesquisa, acordos de cooperação e ecossistemas estaduais de ciência e inovação.","Instituição anfitriã, pesquisador responsável, plano de pesquisa e aderência a chamadas vigentes.","Software aberto e reproduzível e uma plataforma de pesquisa para apoiar um projeto financiado.","Fomento e cooperação"),
          "EMBRAPII":("Colaboração indústria–pesquisa","P&D aplicado por meio de unidades de pesquisa credenciadas e empresas parceiras.","Identificar unidade credenciada adequada e desafio empresarial com escopo de P&D definido.","Formulação do problema, protótipo geoespacial e caminho para validar uma solução aplicada.","Ecossistema de inovação"),
          "Petrobras · Open Innovation":("Inovação do setor privado","Inovação aberta, transferência de tecnologia, aquisição de soluções e desenvolvimento colaborativo; potencialmente relevante para oceano, clima, energia e monitoramento geoespacial.","Acompanhar desafios publicados e avaliar aderência antes de submeter proposta; não se presume convite permanente à GUMA.","Um demonstrador focado em monitoramento ambiental ou inteligência territorial com critérios técnicos mensuráveis.","Portal de inovação aberta"),
          "Agtech Innovation":("Ecossistema privado","Programas de inovação corporativa, conexões entre startups e adoção de tecnologia centrada no produtor.","Explorar aderência a programas, conexões com parceiros do agronegócio e oportunidades de piloto quando houver chamadas.","Um protótipo geoespacial orientado por pesquisa para risco climático, sistemas agrícolas e inteligência territorial.","Programas de inovação")
        }
        for item in visible:
            pt = partner_pt.get(item["name"], ())
            with st.expander(f"{item['name']}  ·  {item['priority']}"):
                st.caption(tx(item["kind"],pt[0] if pt else item["kind"])+" · "+tx(item["label"],pt[4] if pt else item["label"]))
                st.write("**"+tx("Why it matters","Por que importa")+":** "+tx(item["fit"],pt[1] if pt else item["fit"]))
                st.write("**"+tx("What GUMA could seek","O que a GUMA poderia buscar")+":** "+tx(item["ask"],pt[2] if pt else item["ask"]))
                st.write("**"+tx("What GUMA could contribute","O que a GUMA poderia oferecer")+":** "+tx(item["offer"],pt[3] if pt else item["offer"]))
                st.markdown(f"[{tx('Official website / initiative','Site ou iniciativa oficial')}]({item['url']})")
        st.divider()
        st.subheader(tx("A realistic partnership sequence","Uma sequência realista de aproximação"))
        sequence=[
          ("01","Prepare the evidence pack","Preparar o pacote de evidências","One-page overview, architecture, live demo, methods, data sources, limitations, roadmap and a specific ask.","Apresentação de uma página, arquitetura, demonstração, métodos, fontes, limitações, roteiro e um pedido específico."),
          ("02","Start with research and data stewards","Começar por pesquisa e gestores de dados","Prioritize INPE, INMET, Embrapa, MapBiomas and a university lab for technical conversations and validation.","Priorizar INPE, INMET, Embrapa, MapBiomas e um laboratório universitário para conversas técnicas e validação."),
          ("03","Build one small validation pilot","Construir um piloto pequeno de validação","Choose one territory, compare NASA POWER with nearby station data, document gaps and publish reproducible results.","Escolher um território, comparar NASA POWER com estações próximas, documentar lacunas e publicar resultados reproduzíveis."),
          ("04","Approach innovation and funding routes","Buscar inovação e fomento","Only after a credible pilot, approach EMBRAPII, FINEP, state FAPs and private innovation programs with a defined work package.","Depois de um piloto confiável, procurar EMBRAPII, FINEP, FAPs estaduais e programas privados com um pacote de trabalho definido."),
          ("05","Formalize governance before scaling","Formalizar governança antes de escalar","Agree on data licensing, attribution, privacy, IP, publication rights, maintenance and responsibilities in writing.","Definir por escrito licenças de dados, atribuição, privacidade, propriedade intelectual, direitos de publicação, manutenção e responsabilidades.")
        ]
        for n,en,pt,detail,detail_pt in sequence:
            with st.container(border=True):
                st.markdown(f"**{n} · {tx(en,pt)}**")
                st.caption(tx(detail,detail_pt))
        st.info(tx("Important eligibility note: several funding mechanisms require an eligible company, university, accredited research unit, cooperative or formal consortium. GUMA should not assume it can apply as an individual project. Confirm the current call rules and legal applicant before investing time in an application.",
                   "Atenção à elegibilidade: diversos mecanismos exigem empresa, universidade, unidade de pesquisa credenciada, cooperativa ou consórcio formal. A GUMA não deve presumir que pode se candidatar como projeto individual. Confirme as regras do edital e a entidade proponente antes de preparar uma submissão."))
        st.subheader(tx("Near-term action plan","Plano de ação imediato"))
        st.markdown(tx(
          """1. Publish a concise technical brief and a 90-second demo.
    2. Create a source register with license, API, spatial resolution, temporal coverage and known limitations.
    3. Invite one university/research group to review the climate and NDVI methods.
    4. Design a Brazilian pilot that compares gridded climate data with INMET station observations.
    5. Keep a public log of contacts, proposals and actual agreements — never display a prospect as a partner before written confirmation.""",
          """1. Publicar uma apresentação técnica curta e uma demonstração de 90 segundos.
    2. Criar um inventário de fontes com licença, API, resolução espacial, cobertura temporal e limitações conhecidas.
    3. Convidar um grupo universitário/de pesquisa para revisar os métodos climáticos e de NDVI.
    4. Desenhar um piloto brasileiro que compare dados climáticos em grade com observações de estações do INMET.
    5. Manter um registro público de contatos, propostas e acordos reais — nunca apresentar um prospect como parceiro antes de confirmação formal."""
        ))
        st.caption(tx("Prospecting status: all entries are uncontacted opportunities unless explicitly updated by the project team. Program availability and eligibility can change; verify each official source before applying.",
                      "Status de prospecção: todas as entradas são oportunidades ainda não contatadas, salvo atualização explícita pela equipe. Disponibilidade e elegibilidade podem mudar; verifique cada fonte oficial antes de se candidatar."))
    
if tab_climate.open:
    with tab_climate:
        st.markdown("""
        <div style="padding:1.6rem 1.8rem;border:1px solid #4b3940;border-radius:18px;
          background:radial-gradient(circle at 90% 10%,rgba(226,91,66,.22),transparent 28%),
          linear-gradient(115deg,#101c2a,#1d2632 60%,#342329);margin:.3rem 0 1rem 0">
          <div style="color:#ffb18e;font-size:.72rem;letter-spacing:.18em;font-weight:800">PLANETARY SIGNALS · EARTH SYSTEM</div>
          <h1 style="color:#f4f0ed;margin:.25rem 0">CLIMATE WATCH</h1>
          <p style="color:#d0d9df;margin:0">Monitoramento de indicadores do sistema climático e suas implicações para a agricultura.</p>
        </div>
        """, unsafe_allow_html=True)
        st.write(tx(
            "A source-traceable observatory of long-term global change. Values are updated when their providers publish new observations; this is not a real-time sensor feed.",
            "Um observatório rastreável da mudança climática de longo prazo. Os valores são atualizados quando as instituições publicam novas observações; isto não é um fluxo de sensores em tempo real."
        ))
        if st.button(tx("↻ Load / update climate indicators", "↻ Carregar / atualizar indicadores climáticos"), type="primary"):
            get_climate_watch_data.clear()
            try:
                with st.spinner(tx("Retrieving NASA and NOAA climate series…", "Consultando séries climáticas da NASA e NOAA…")):
                    st.session_state["guma_global_climate"] = get_climate_watch_data()
                st.success(tx("Climate indicators updated.", "Indicadores climáticos atualizados."))
            except Exception as exc:
                st.warning(tx("Could not update climate indicators: ", "Não foi possível atualizar os indicadores climáticos: ") + str(exc))
    
        climate_watch = st.session_state.get("guma_global_climate")
        if climate_watch is None:
            st.info(tx(
                "Climate data are loaded on demand to keep the main application responsive. Select Load / update climate indicators to retrieve the latest NASA and NOAA series.",
                "Os dados climáticos são carregados sob demanda para manter o aplicativo responsivo. Selecione Carregar / atualizar indicadores climáticos para consultar as séries mais recentes da NASA e NOAA."
            ))
        else:
            try:
                temperature = climate_watch["temperature"].copy()
                co2 = climate_watch["co2"].copy()
                ch4 = climate_watch["ch4"].copy()
                n2o = climate_watch["n2o"].copy()
                if any(series.empty for series in (temperature, co2, ch4, n2o)):
                    st.warning(tx("At least one source returned no usable observations. Check availability and retry.", "Pelo menos uma fonte não retornou observações utilizáveis. Confira a disponibilidade e tente novamente."))
                else:
                    latest_temp = temperature.iloc[-1]
                    latest_co2 = co2.iloc[-1]
                    latest_ch4 = ch4.iloc[-1]
                    latest_n2o = n2o.iloc[-1]
                    annual = temperature.assign(Year=temperature["Date"].dt.year).groupby("Year")["Anomaly_C"].mean()
                    annual = annual[annual.index >= 1880]
                    previous_co2 = co2[co2["Date"] <= latest_co2["Date"] - pd.DateOffset(years=1)]
                    co2_delta = (latest_co2["CO2_ppm"] - previous_co2.iloc[-1]["CO2_ppm"]) if not previous_co2.empty else None
                    prev_ch4=ch4[ch4["Date"]<=latest_ch4["Date"]-pd.DateOffset(years=1)]
                    prev_n2o=n2o[n2o["Date"]<=latest_n2o["Date"]-pd.DateOffset(years=1)]
                    ch4_delta=latest_ch4["CH4_ppb"]-prev_ch4.iloc[-1]["CH4_ppb"] if not prev_ch4.empty else None
                    n2o_delta=latest_n2o["N2O_ppb"]-prev_n2o.iloc[-1]["N2O_ppb"] if not prev_n2o.empty else None
                    m1,m2,m3,m4=st.columns(4)
                    m1.metric(tx("Global temperature anomaly","Anomalia da temperatura global"),f"{latest_temp['Anomaly_C']:+.2f} °C",tx("vs 1951–1980","vs. 1951–1980"))
                    m2.metric(tx("Mauna Loa CO₂","CO₂ em Mauna Loa"),f"{latest_co2['CO2_ppm']:.1f} ppm",f"{co2_delta:+.1f} ppm" if co2_delta is not None else None)
                    m3.metric(tx("Global methane · CH₄","Metano global · CH₄"),f"{latest_ch4['CH4_ppb']:.1f} ppb",f"{ch4_delta:+.1f} ppb" if ch4_delta is not None else None)
                    m4.metric(tx("Global nitrous oxide · N₂O","Óxido nitroso global · N₂O"),f"{latest_n2o['N2O_ppb']:.2f} ppb",f"{n2o_delta:+.2f} ppb" if n2o_delta is not None else None)
                    st.caption(tx(
                        f"Latest observations: temperature {latest_temp['Date']:%b %Y}; CO₂ {latest_co2['Date']:%b %Y}; CH₄ {latest_ch4['Date']:%b %Y}; N₂O {latest_n2o['Date']:%b %Y}. Retrieved {climate_watch['retrieved_at']:%Y-%m-%d %H:%M UTC}.",
                        f"Últimas observações: temperatura {latest_temp['Date']:%m/%Y}; CO₂ {latest_co2['Date']:%m/%Y}; CH₄ {latest_ch4['Date']:%m/%Y}; N₂O {latest_n2o['Date']:%m/%Y}. Consulta em {climate_watch['retrieved_at']:%d/%m/%Y %H:%M UTC}."
                    ))
                    st.divider()
                    left, right = st.columns([1.25, 1])
                    with left:
                        st.subheader(tx("Global temperature anomaly", "Anomalia da temperatura global"))
                        st.line_chart(temperature.set_index("Date")[["Anomaly_C"]], height=300)
                        st.caption(tx(
                            "Monthly global land-ocean temperature anomaly in °C relative to 1951–1980. Monthly values fluctuate; use annual means to discuss long-term trends.",
                            "Anomalia mensal global de temperatura sobre continentes e oceanos, em °C, relativa a 1951–1980. Valores mensais oscilam; use médias anuais para discutir tendências de longo prazo."
                        ))
                    with right:
                        st.subheader(tx("Atmospheric CO₂ · Mauna Loa", "CO₂ atmosférico · Mauna Loa"))
                        st.line_chart(co2.set_index("Date")[["CO2_ppm"]], height=300)
                        st.caption(tx(
                            "Monthly mean CO₂ measured at Mauna Loa, Hawaii. This is a long-running station record, not a global spatial average.",
                            "Média mensal de CO₂ medida em Mauna Loa, Havaí. É uma série de uma estação de monitoramento, não uma média espacial global."
                        ))
                    gas_left,gas_right=st.columns(2)
                    with gas_left:
                        st.subheader(tx("Global atmospheric methane · CH₄","Metano atmosférico global · CH₄"))
                        st.line_chart(ch4.set_index("Date")[["CH4_ppb"]],height=260)
                        st.caption(tx("NOAA global marine-surface monthly means. Recent observations are preliminary and may be revised.","Médias mensais globais da rede de superfície marinha da NOAA. Observações recentes são preliminares e podem ser revisadas."))
                    with gas_right:
                        st.subheader(tx("Global atmospheric nitrous oxide · N₂O","Óxido nitroso atmosférico global · N₂O"))
                        st.line_chart(n2o.set_index("Date")[["N2O_ppb"]],height=260)
                        st.caption(tx("NOAA global marine-surface monthly means. The reliable series begins in 2001.","Médias mensais globais da rede de superfície marinha da NOAA. A série confiável começa em 2001."))
                    st.subheader(tx("Annual temperature signal", "Sinal anual de temperatura"))
                    annual_frame = annual.rename("Annual anomaly (°C)").to_frame()
                    st.area_chart(annual_frame, height=260)
                    st.caption(tx(
                        "Annual means are calculated here from the monthly NASA values. The reference baseline remains 1951–1980; this is not the pre-industrial (1850–1900) reference used in many 1.5°C assessments.",
                        "As médias anuais são calculadas aqui a partir dos valores mensais da NASA. A referência continua sendo 1951–1980; não é a linha de base pré-industrial (1850–1900) usada em muitas avaliações do limite de 1,5 °C."
                    ))
                    st.divider()
                    st.subheader(tx("Why this matters for agriculture", "Por que isso importa para a agricultura"))
                    a, b = st.columns(2)
                    with a:
                        st.markdown("**" + tx("Heat exposure", "Exposição ao calor") + "**")
                        st.write(tx(
                            "Rising background temperatures can increase the frequency and intensity of heat stress during sensitive crop stages. Local exposure must be assessed with regional daily data and crop calendars.",
                            "O aumento da temperatura de fundo pode elevar a frequência e a intensidade do estresse térmico em fases sensíveis das culturas. A exposição local precisa ser avaliada com dados diários regionais e calendários agrícolas."
                        ))
                        st.markdown("**" + tx("Water and rainfall variability", "Água e variabilidade das chuvas") + "**")
                        st.write(tx(
                            "Changes in evaporation demand and rainfall patterns can affect soil-water balance, sowing windows and drought or excess-rain risk. Global indicators do not determine conditions on an individual farm.",
                            "Mudanças na demanda evaporativa e nos padrões de chuva podem afetar o balanço hídrico do solo, janelas de semeadura e riscos de seca ou excesso de chuva. Indicadores globais não determinam as condições de uma propriedade específica."
                        ))
                    with b:
                        st.markdown("**" + tx("Greenhouse gases", "Gases de efeito estufa") + "**")
                        st.write(tx(
                            "CO₂ is a major long-lived greenhouse gas. The Mauna Loa series is an atmospheric measurement record; it does not by itself attribute a particular local drought, flood or crop loss.",
                            "O CO₂ é um importante gás de efeito estufa de longa permanência. A série de Mauna Loa é um registro de medição atmosférica; isoladamente, não atribui uma seca, enchente ou perda agrícola local."
                        ))
                        st.markdown("**" + tx("Next GUMA connection", "Próxima conexão no GUMA") + "**")
                        st.write(tx(
                            "The next analytical layer is to compare regional heat and rainfall extremes with crop calendars, NASA POWER histories, MODIS vegetation signals and official Brazilian datasets.",
                            "A próxima camada analítica é cruzar extremos regionais de calor e chuva com calendários agrícolas, históricos NASA POWER, sinais de vegetação MODIS e bases oficiais brasileiras."
                        ))
                    st.divider()
                    st.subheader(tx("Brazil · Local climate extremes", "Brasil · Extremos climáticos locais"))
                    st.write(tx(
                        "A location-level screening layer based on the NASA POWER daily series already loaded for the selected study point. Thresholds below are transparent indicators, not official heatwave or drought classifications.",
                        "Uma camada de triagem para o ponto de estudo selecionado, baseada na série diária NASA POWER já carregada. Os limites abaixo são indicadores transparentes, não classificações oficiais de onda de calor ou seca."
                    ))
                    local_climate = st.session_state.get("climate")
                    local_coords = st.session_state.get("coords")
                    if local_climate is not None and local_coords == (lat, lon):
                        hcol, rcol, dcol = st.columns(3)
                        hot_threshold = hcol.number_input(tx("Hot day threshold · Tmax (°C)", "Limite de dia quente · Tmax (°C)"), min_value=25.0, max_value=45.0, value=35.0, step=1.0, key="cw_hot_threshold")
                        rain_threshold = rcol.number_input(tx("Heavy-rain day (mm/day)", "Chuva intensa (mm/dia)"), min_value=10.0, max_value=150.0, value=50.0, step=5.0, key="cw_rain_threshold")
                        dry_threshold = dcol.number_input(tx("Dry day threshold (mm/day)", "Limite de dia seco (mm/dia)"), min_value=0.0, max_value=5.0, value=1.0, step=0.5, key="cw_dry_threshold")
                        try:
                            local_extremes = summarize_local_extremes(
                                local_climate, hot_day_c=float(hot_threshold),
                                heavy_rain_mm=float(rain_threshold), dry_day_mm=float(dry_threshold)
                            )
                            if not local_extremes.empty:
                                latest_year = local_extremes.iloc[-1]
                                e1, e2, e3 = st.columns(3)
                                e1.metric(tx("Hot days in latest year", "Dias quentes no último ano"), int(latest_year["Hot days (Tmax threshold)"]))
                                e2.metric(tx("Heavy-rain days in latest year", "Dias de chuva intensa no último ano"), int(latest_year["Heavy-rain days"]))
                                e3.metric(tx("Longest dry spell", "Maior sequência seca"), f"{int(latest_year['Longest dry spell (days)'])} d")
                                st.line_chart(local_extremes.set_index("Year")[[
                                    "Hot days (Tmax threshold)", "Heavy-rain days"
                                ]], height=260)
                                st.dataframe(local_extremes, width="stretch", hide_index=True)
                                st.caption(tx(
                                    f"Selected point: {lat:.4f}, {lon:.4f}. Latest year in the loaded NASA POWER record: {int(latest_year['Year'])}. Dry days are consecutive valid daily precipitation values below the selected threshold; missing dates break a spell.",
                                    f"Ponto selecionado: {lat:.4f}, {lon:.4f}. Último ano disponível na série NASA POWER: {int(latest_year['Year'])}. Dias secos são valores diários válidos de precipitação abaixo do limite escolhido; datas ausentes interrompem a sequência."
                                ))
                        except Exception as local_exc:
                            st.warning(tx("Could not calculate local indicators: ", "Não foi possível calcular os indicadores locais: ") + str(local_exc))
                    else:
                        st.info(tx(
                            "Load the environmental data for your selected study area in the Environmental dashboard tab to calculate local indicators here.",
                            "Carregue os dados ambientais da área escolhida na aba Painel ambiental para calcular os indicadores locais aqui."
                        ))
                    st.markdown(
                        "**" + tx("Ocean system references", "Referências do sistema oceânico") + "**\n"
                        "- [NASA Global Mean Sea Level — current indicator and methodology](https://sealevel.nasa.gov/understanding-sea-level/key-indicators/global-mean-sea-level/)\n"
                        "- [NOAA NCEI — monthly global ocean heat content, 0–700 m and 0–2000 m](https://www.ncei.noaa.gov/access/global-ocean-heat-content/monthly_analysis.html)"
                    )
                    st.caption(tx(
                        "Sea-level and ocean-heat datasets are linked as authoritative references but are not yet ingested into GUMA's plotted time series. NOAA's ocean-heat product uses in-situ subsurface observations and a documented climatological reference; its monthly fields have spatial-data and sampling uncertainty.",
                        "As bases de nível do mar e calor oceânico estão indicadas como referências oficiais, mas ainda não foram ingeridas nas séries gráficas do GUMA. O produto de calor oceânico da NOAA usa observações subsuperficiais in situ e uma referência climatológica documentada; seus campos mensais possuem incertezas espaciais e de amostragem."
                    ))
                    st.subheader(tx("Data provenance & update policy", "Proveniência dos dados e política de atualização"))
                    source_rows = [
                        {"Indicator": "Global temperature anomaly", "Provider": "NASA GISS", "Dataset": "GISTEMP v4", "Baseline": "1951–1980", "Frequency": "Monthly"},
                        {"Indicator": "Atmospheric CO₂", "Provider": "NOAA GML", "Dataset": "Mauna Loa monthly mean", "Baseline": "Station record", "Frequency": "Monthly"},
                        {"Indicator": "Atmospheric CH₄", "Provider": "NOAA GML", "Dataset": "Global marine-surface mean", "Baseline": "Global network", "Frequency": "Monthly"},
                        {"Indicator": "Atmospheric N₂O", "Provider": "NOAA GML", "Dataset": "Global marine-surface mean", "Baseline": "Global network", "Frequency": "Monthly"},
                    ]
                    st.dataframe(pd.DataFrame(source_rows), width="stretch", hide_index=True)
                    st.markdown(
                        "- [NASA GISTEMP v4 — data and methodology](https://data.giss.nasa.gov/gistemp/)\n"
                        "- [NASA GISTEMP source documentation](https://data.giss.nasa.gov/gistemp/sources/gistemp.html)\n"
                        "- [NOAA Global Monitoring Laboratory — CO₂ trends](https://gml.noaa.gov/ccgg/trends/)\\n"
                        "- [NOAA global methane trends and methods](https://gml.noaa.gov/ccgg/trends_ch4/)\\n"
                        "- [NOAA global nitrous oxide trends and methods](https://gml.noaa.gov/ccgg/trends_n2o/)"
                    )
                    with st.expander(tx("Scientific interpretation and limitations", "Interpretação científica e limitações")):
                        st.markdown(tx(
                            "- NASA GISTEMP is an estimate of global surface temperature change, not a direct thermometer reading at every location.\n- Monthly anomalies are not the same as annual means or absolute global mean temperature.\n- GISTEMP uses a 1951–1980 baseline; do not compare its anomaly directly with indicators using 1850–1900 without a documented conversion.\n- Mauna Loa CO₂ is a station record and has seasonal variation; it is not the global marine-surface average.\n- NOAA CH₄ and N₂O are globally averaged monthly means from a marine-surface network; recent observations are preliminary and may be revised.\n- These indicators describe global context only; they do not establish local climate impacts or agricultural causation.\n- Global sea level, ocean heat, ice sheets and a Brazil-specific climate-extremes atlas are not yet integrated.",
                            "- O NASA GISTEMP estima a mudança da temperatura superficial global; não é uma leitura direta de termômetro em cada local.\n- Anomalias mensais não são equivalentes a médias anuais nem à temperatura média global absoluta.\n- O GISTEMP usa a referência 1951–1980; não compare diretamente sua anomalia com indicadores baseados em 1850–1900 sem conversão documentada.\n- CO₂ de Mauna Loa é uma série de estação e apresenta variação sazonal; não é a média global da superfície oceânica.\n- CH₄ e N₂O da NOAA são médias mensais globais de uma rede de superfície marinha; observações recentes são preliminares e podem ser revisadas.\n- Esses indicadores descrevem o contexto global, mas não demonstram impactos climáticos locais nem causalidade agrícola.\n- Nível do mar, calor oceânico, mantos de gelo e atlas brasileiro de extremos climáticos ainda não estão integrados."
                        ))
        
            except Exception as exc:
                st.error(tx("Climate Watch could not retrieve the source datasets: ", "O Observatório climático não conseguiu consultar as bases: ") + str(exc))
                st.info(tx(
                    "Try again later. The dashboard does not replace missing live observations with invented or hard-coded values.",
                    "Tente novamente mais tarde. O painel não substitui observações indisponíveis por números inventados ou fixos."
                ))
    
    if "climate" in st.session_state and st.session_state.get("coords") == (lat, lon):
            climate = st.session_state["climate"]
            with st.expander(tx("🔎 Automatic data-quality checks", "🔎 Verificações automáticas de qualidade dos dados"), expanded=False):
                climate_qc = climate_quality_report(climate)
                q1, q2, q3, q4 = st.columns(4)
                q1.metric(tx("Daily coverage", "Cobertura diária"), f"{climate_qc['coverage_pct']:.1f}%")
                q2.metric(tx("Missing values", "Valores ausentes"), climate_qc["missing_cells"])
                q3.metric(tx("Duplicate dates", "Datas duplicadas"), climate_qc["duplicate_dates"])
                q4.metric(tx("Out-of-range values", "Valores fora da faixa"), climate_qc["out_of_range_cells"])
                st.caption(tx(
                    f"Period: {climate_qc['start_date']} to {climate_qc['end_date']} · {climate_qc['observed_days']} observed dates of {climate_qc['expected_days']} expected calendar days.",
                    f"Período: {climate_qc['start_date']} a {climate_qc['end_date']} · {climate_qc['observed_days']} datas observadas de {climate_qc['expected_days']} dias corridos esperados."
                ))
                if climate_qc["duplicate_dates"] or climate_qc["missing_cells"] or climate_qc["out_of_range_cells"] or climate_qc["missing_dates"]:
                    st.warning(tx(
                        "The checks found gaps or values that deserve review. Original observations are preserved; no automatic correction or imputation was applied.",
                        "As verificações encontraram lacunas ou valores que merecem revisão. As observações originais foram preservadas; não houve correção ou imputação automática."
                    ))
                else:
                    st.success(tx("No basic completeness or range issue was detected in the loaded climate table.", "Nenhum problema básico de completude ou faixa foi detectado na tabela climática carregada."))
                st.dataframe(pd.DataFrame(climate_qc["variables"]), width="stretch", hide_index=True)
                modis_qc = modis_quality_report(st.session_state.get("modis", pd.DataFrame()))
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric(tx("MODIS observations", "Observações MODIS"), modis_qc["rows"])
                m2.metric(tx("Usable NDVI", "NDVI utilizável"), modis_qc["valid_ndvi"])
                m3.metric(tx("Invalid NDVI", "NDVI inválido"), modis_qc["invalid_ndvi"])
                m4.metric(tx("Poor/unknown QA", "QA ruim/desconhecida"), modis_qc["poor_or_unknown_quality"])
                m5.metric(tx("Duplicate dates", "Datas duplicadas"), modis_qc["duplicate_dates"])
                st.caption(tx(
                    "MODIS QA is reported separately from climate completeness. NDVI values outside [-1, 1] are flagged, not silently clipped.",
                    "A QA do MODIS é informada separadamente da completude climática. Valores de NDVI fora de [-1, 1] são sinalizados, não limitados silenciosamente."
                ))
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
                st.dataframe(modis[["Date", "NDVI", "Quality label"]], width="stretch", hide_index=True)
                valid_modis = modis.dropna(subset=["NDVI"]).copy()
                if not valid_modis.empty:
                    valid_modis["Year"] = pd.to_datetime(valid_modis["Date"]).dt.year
                    annual_ndvi = valid_modis.groupby("Year")["NDVI"].agg(Observations="count", Mean="mean", Minimum="min", Maximum="max").reset_index()
                    st.markdown("**" + tx("Interannual vegetation summary", "Resumo interanual da vegetação") + "**")
                    st.dataframe(annual_ndvi.round({"Mean": 3, "Minimum": 3, "Maximum": 3}), width="stretch", hide_index=True)
                    st.caption(tx("Annual means summarize quality-screened 16-day observations. They are not crop classification, phenology or yield estimates.", "As médias anuais resumem observações de 16 dias com qualidade aceita. Não são classificação de cultura, fenologia ou estimativa de produtividade."))
                    st.bar_chart(modis["Quality label"].fillna("Unknown").value_counts())
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
            end = start + pd.Timedelta(cycle_days - 1, unit="D")
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

if tab2.open:
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
                    st.dataframe(display_summary, width="stretch", hide_index=True)
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
                    st.dataframe(season_view, width="stretch", hide_index=True)
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
                        candidate_end = candidate_start + pd.Timedelta(cycle_days - 1, unit="D")
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
                                end = start + pd.Timedelta(cycle_days - 1, unit="D")
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
                            st.dataframe(balance, width="stretch", hide_index=True)
                            st.download_button(
                                tx("Download daily water-balance CSV", "Baixar CSV do balanço hídrico diário"),
                                balance.to_csv(index=False).encode("utf-8"),
                                file_name=f"guma_water_balance_{water_crop.lower().replace(' ','_')}_{water_year}.csv",
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
            @st.cache_data(ttl=3600, max_entries=1, show_spinner=False)
            def _cached_zarc_resources():
                return list_zarc_resources()
    
            @st.cache_data(ttl=3600, max_entries=1, show_spinner=False)
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
                        st.dataframe(dekad_frame, width="stretch", hide_index=True)
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
                        }]), width="stretch", hide_index=True)
            except Exception as exc:
                st.error(tx("Could not load or query the official MAPA ZARC dataset: ", "Não foi possível carregar ou consultar a base oficial ZARC do MAPA: ") + str(exc))
                st.markdown("[Open MAPA ZARC open-data portal](https://dados.agricultura.gov.br/dataset/tabua-de-risco-zoneamento-agricola-de-risco-climatico)")
    
    
            else:
                st.info(tx("Select at least one crop to analyze.", "Selecione ao menos uma cultura para analisar."))
    
if tab3.open:
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


def fetch_community_snapshots():
    base_url, public_key, _ = supabase_settings()
    if not base_url or not public_key:
        return []
    headers = {"apikey": public_key}
    access_token = st.session_state.get("agrovision_access_token", "")
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    response = requests.get(
        f"{base_url}/rest/v1/community_snapshots?select=id,display_alias,macroregion,crop,season,metrics,source_metadata,created_at&published=eq.true&order=created_at.desc&limit=300",
        headers=headers, timeout=25
    )
    if not response.ok:
        raise RuntimeError(f"Community board unavailable (HTTP {response.status_code}): {response.text[:250]}")
    return response.json()


def publish_community_snapshot(alias, macroregion, crop, season, metrics):
    base_url, headers = supabase_rest_headers()
    if not headers:
        raise RuntimeError("Sign in with an email account to publish a comparison. Visitor access can browse only.")
    response = requests.post(
        f"{base_url}/rest/v1/community_snapshots",
        headers=headers,
        json={
            "display_alias": alias.strip(),
            "macroregion": macroregion,
            "crop": crop,
            "season": season,
            "metrics": metrics,
            "source_metadata": {
                "provider": "NASA POWER",
                "method": "Daily point-series aggregate",
                "period_start": metrics.get("period_start"),
                "period_end": metrics.get("period_end"),
                "shared_at": datetime.now(timezone.utc).isoformat()
            },
            "published": True
        },
        timeout=25
    )
    if not response.ok:
        raise RuntimeError(f"Publishing failed (HTTP {response.status_code}): {response.text[:250]}")
    return response.json()


def fetch_field_lab_trials():
    base_url, public_key, _ = supabase_settings()
    if not base_url or not public_key:
        return []
    headers = {"apikey": public_key}
    access_token = st.session_state.get("agrovision_access_token", "")
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    response = requests.get(
        f"{base_url}/rest/v1/field_lab_trials?select=id,title,display_alias,macroregion,crop,season,hypothesis,strategy,comparator,metric,unit,baseline_value,alternative_value,notes,status,created_at&published=eq.true&order=created_at.desc&limit=300",
        headers=headers, timeout=25
    )
    if not response.ok:
        raise RuntimeError(f"Field Lab board unavailable (HTTP {response.status_code}): {response.text[:250]}")
    return response.json()


def publish_field_lab_trial(record):
    base_url, headers = supabase_rest_headers()
    if not headers:
        raise RuntimeError("Sign in with an email account to publish a Field Lab record.")
    response = requests.post(
        f"{base_url}/rest/v1/field_lab_trials",
        headers=headers,
        json=record,
        timeout=25
    )
    if not response.ok:
        raise RuntimeError(f"Field Lab publication failed (HTTP {response.status_code}): {response.text[:250]}")
    return response.json()


def fetch_field_lab_updates():
    base_url, public_key, _ = supabase_settings()
    if not base_url or not public_key:
        return []
    headers = {"apikey": public_key}
    access_token = st.session_state.get("agrovision_access_token", "")
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    response = requests.get(
        f"{base_url}/rest/v1/field_lab_updates?select=id,trial_id,display_alias,season,observation_date,stage,arm,observed_value,unit,method,notes,created_at&published=eq.true&order=observation_date.asc&limit=2000",
        headers=headers, timeout=25
    )
    if not response.ok:
        raise RuntimeError(f"Field Lab timeline unavailable (HTTP {response.status_code}): {response.text[:250]}")
    return response.json()


def publish_field_lab_update(record):
    base_url, headers = supabase_rest_headers()
    if not headers:
        raise RuntimeError("Sign in with an email account to publish a follow-up.")
    response = requests.post(
        f"{base_url}/rest/v1/field_lab_updates",
        headers=headers,
        json=record,
        timeout=25
    )
    if not response.ok:
        raise RuntimeError(f"Field Lab follow-up failed (HTTP {response.status_code}): {response.text[:250]}")
    return response.json()

@st.cache_data(ttl=3600, max_entries=4, show_spinner=False)
def build_pdf_report(climate_frame, vegetation_frame, latitude, longitude, water_balance=None, zarc_reference=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=38, leftMargin=38, topMargin=38, bottomMargin=38)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("GUMA — Earth intelligence assessment", styles["Title"]),
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
    if water_balance and water_balance.get("table") is not None and not water_balance["table"].empty:
        wb = water_balance["table"]
        story.extend([Spacer(1, 12), Paragraph("Crop-water scenario — exploratory FAO-56 balance", styles["Heading2"])])
        water_rows = [
            ["Scenario field", "Value"],
            ["Crop / season", f"{water_balance.get('crop', 'Not recorded')} / {water_balance.get('year', 'Not recorded')}"],
            ["Daily steps", str(len(wb))],
            ["Accumulated ET0", f"{wb['ET0 FAO-56 (mm)'].sum():.1f} mm"],
            ["Potential ETc", f"{wb['ETc potential (mm)'].sum():.1f} mm"],
            ["Estimated actual ETa", f"{wb['ETa actual estimate (mm)'].sum():.1f} mm"],
            ["Cycle precipitation", f"{wb['Precipitation (mm)'].sum():.1f} mm"],
            ["Days with modeled stress", str(int((wb['Stress coefficient Ks'] < 0.999).sum()))],
            ["Net irrigation scenario", f"{wb['Net irrigation (mm)'].sum():.1f} mm"],
        ]
        water_table = Table(water_rows, colWidths=[270, 180])
        water_table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#164b35")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("GRID", (0,0), (-1,-1), .4, colors.HexColor("#cbd5ce")), ("PADDING", (0,0), (-1,-1), 6)]))
        story.append(water_table)
    else:
        story.extend([Spacer(1, 8), Paragraph("No current-coordinate water-balance scenario was attached.", styles["Normal"])])
    story.extend([Spacer(1, 12), Paragraph("Official MAPA ZARC reference", styles["Heading2"])])
    if zarc_reference:
        zarc_rows = [["Field", "Selected official record"]]
        for key in ("Crop", "UF", "Municipality", "Soil code", "Cultivar group / cycle", "Management", "Climate", "Ordinance", "Season dataset"):
            value = zarc_reference.get(key)
            if value not in (None, ""):
                zarc_rows.append([key, str(value)])
        zarc_table = Table(zarc_rows, colWidths=[170, 280])
        zarc_table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#164b35")), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("GRID", (0,0), (-1,-1), .4, colors.HexColor("#cbd5ce")), ("PADDING", (0,0), (-1,-1), 5)]))
        story.append(zarc_table)
        story.append(Paragraph("Official source: " + str(zarc_reference.get("Source URL", "MAPA ZARC open-data portal")), styles["Normal"]))
    else:
        story.append(Paragraph("No official MAPA ZARC row was attached to this project.", styles["Normal"]))

    story.extend([Spacer(1, 16), Paragraph("Scientific note: this report summarizes historical environmental observations. NDVI is not a direct measure of yield or crop health. Rainfall totals alone are not a soil-water balance or crop water deficit estimate. Crop reference ranges are indicative and must be checked against cultivar, local ZARC calendar, soil tests, management and field observations.", styles["Italic"])])
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


if tab5.open:
    with tab5:
        st.subheader(tx("Independent validation against weather-station observations", "Validação independente com observações de estações meteorológicas"))
        st.markdown(tx(
            "Upload a CSV containing daily observations from a traceable weather station. GUMA will align dates with NASA POWER and calculate paired error statistics. No station observations are bundled or fabricated.",
            "Envie um CSV com observações diárias de uma estação meteorológica identificável. O GUMA alinhará as datas com o NASA POWER e calculará estatísticas de erro pareadas. Nenhuma observação de estação é embutida ou inventada."
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
                        st.dataframe(paired.assign(Error=paired["model"]-paired["observed"]), width="stretch")
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
    
if tab4.open:
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
                st.dataframe(pd.DataFrame([{k: row.get(k) for k in ("project_name", "latitude", "longitude", "created_at")} for row in saved]), width="stretch", hide_index=True)
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
                st.download_button(tx("Download climate CSV", "Baixar CSV climático"), csv_frame.to_csv().encode("utf-8"), file_name="guma_nasa_power.csv", mime="text/csv", width="stretch")
                if not modis_for_export.empty:
                    st.download_button(tx("Download MODIS CSV", "Baixar CSV do MODIS"), modis_for_export.to_csv(index=False).encode("utf-8"), file_name="guma_modis_ndvi.csv", mime="text/csv", width="stretch")
            with export_col2:
                water_for_export = st.session_state.get("latest_water_balance")
                if water_for_export and water_for_export.get("coords") != (float(lat), float(lon)):
                    water_for_export = None
                pdf_bytes = build_pdf_report(
                    climate_for_export, modis_for_export, lat, lon,
                    water_balance=water_for_export,
                    zarc_reference=st.session_state.get("zarc_reference")
                )
                st.download_button(tx("Download PDF report", "Baixar relatório PDF"), pdf_bytes, file_name="guma_report.pdf", mime="application/pdf", width="stretch")
            with export_col3:
                if st.button(tx("Save project to account", "Salvar projeto na conta"), width="stretch"):
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
        

if tab_rotation.open:
    with tab_rotation:
        st.header(tx("Crop Rotation Lab", "Laboratório de rotação de culturas"))
        st.write(tx(
            "Compare historical climate exposure across transparent soybean-based crop sequences. This is a screening tool, not a yield forecast or planting recommendation.",
            "Compare a exposição climática histórica em sequências de cultivo baseadas em soja. Esta é uma ferramenta de triagem, não uma previsão de produtividade ou recomendação de plantio."
        ))
        st.info(tx(
            "NASA POWER daily climate and quality-screened MODIS observations are used when loaded for the current coordinates. Soil texture, fertility and water regime below are local inputs; they are not measured by NASA.",
            "São usados dados climáticos diários NASA POWER e observações MODIS filtradas por qualidade quando carregados para as coordenadas atuais. Textura, fertilidade e regime hídrico são dados locais informados pelo usuário; não são medidos pela NASA."
        ))
        if "climate" not in st.session_state or st.session_state.get("coords") != (float(lat), float(lon)):
            st.warning(tx(
                "Load environmental data in the Environmental dashboard first. The Rotation Lab uses the same selected coordinates.",
                "Carregue primeiro os dados ambientais no Painel ambiental. O Laboratório de rotação usa as mesmas coordenadas selecionadas."
            ))
        else:
            rotation_month = st.selectbox(
                tx("Main-season sowing month", "Mês de semeadura da safra principal"),
                list(range(1, 13)), index=9, format_func=lambda m: tx(
                    ["January","February","March","April","May","June","July","August","September","October","November","December"][m-1],
                    ["Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"][m-1]
                ), key="rotation_sowing_month"
            )
            scenario_names = list(ROTATION_SCENARIOS)
            selected_scenarios = st.multiselect(
                tx("Scenarios to compare", "Cenários para comparar"),
                scenario_names, default=scenario_names, key="rotation_scenarios"
            )
            st.markdown("**" + tx("Local farm context", "Contexto local da propriedade") + "**")
            c1, c2, c3 = st.columns(3)
            c1.metric(tx("Soil texture", "Textura do solo"), str(soil))
            c2.metric(tx("Soil fertility", "Fertilidade do solo"), str(fertility))
            c3.metric(tx("Water regime", "Regime hídrico"), str(irrigation))
            st.caption(tx(
                "These local inputs are recorded as context only. They are not converted into measured available-water capacity or soil-health scores.",
                "Esses dados locais são registrados apenas como contexto. Não são convertidos em capacidade de água disponível medida nem em índices de saúde do solo."
            ))
            if not selected_scenarios:
                st.warning(tx("Select at least one scenario.", "Selecione pelo menos um cenário."))
            else:
                try:
                    rotation_detail, rotation_summary = compare_rotation_scenarios(
                        st.session_state["climate"],
                        st.session_state.get("modis", pd.DataFrame()),
                        rotation_month,
                        selected_scenarios
                    )
                    if rotation_detail.empty:
                        st.warning(tx(
                            "No complete crop-sequence windows were available for this month and historical period. Try another sowing month or load a longer dataset.",
                            "Não há janelas completas de sequência de cultivo para este mês e período histórico. Tente outro mês ou carregue uma série mais longa."
                        ))
                    else:
                        st.subheader(tx("Scenario comparison", "Comparação dos cenários"))
                        st.dataframe(rotation_summary, width="stretch", hide_index=True)
                        chart_data = rotation_summary.set_index("Scenario")[["Median daily rainfall (mm/day)"]]
                        st.bar_chart(chart_data)
                        st.caption(tx(
                            "Daily rainfall rate helps compare sequences of different modeled durations. Total sequence rainfall and duration are also shown; neither is effective rainfall, crop water requirement, nor water saved by a rotation.",
                            "A taxa diária de chuva ajuda a comparar sequências com durações modeladas diferentes. A chuva total e a duração também são exibidas; nenhuma delas representa chuva efetiva, necessidade hídrica da cultura ou economia de água pela rotação."
                        ))
                        st.subheader(tx("Crop-window evidence", "Evidências por janela de cultivo"))
                        st.dataframe(rotation_detail, width="stretch", hide_index=True)
                        st.download_button(
                            tx("Download rotation comparison CSV", "Baixar comparação de rotação em CSV"),
                            rotation_detail.to_csv(index=False).encode("utf-8"),
                            file_name="guma_rotation_windows.csv",
                            mime="text/csv"
                        )
                except Exception as exc:
                    st.error(tx("Could not calculate the rotation comparison: ", "Não foi possível calcular a comparação de rotação: ") + str(exc))
        with st.expander(tx("Method, assumptions and scientific limitations", "Método, hipóteses e limitações científicas"), expanded=True):
            st.markdown("\n".join("- " + item for item in scenario_disclosure()))
            st.markdown(
                "[Rotation Lab methodology and validation plan](https://github.com/interpessoal21-ops/agrovision/blob/spaceapps-2026-rotation-lab/docs/ROTATION_LAB.md)"
            )
    
if tab_commons.open:
    with tab_commons:
        st.header("GUMA COMMONS")
        st.caption(tx(
            "A collaborative climate atlas built from opt-in, anonymized aggregate fingerprints — not a leaderboard.",
            "Um atlas climático colaborativo construído com assinaturas agregadas e compartilhadas voluntariamente — não um placar de produtores."
        ))
        st.markdown("""
        <div class="section-note">
          <strong>CLIMATE FINGERPRINT / ASSINATURA CLIMÁTICA</strong><br>
          Each contribution turns a daily climate series into a compact profile of heat, rainfall and seasonal rhythm.
          Compare places and crop contexts without publishing farm coordinates, names or raw daily records.
        </div>
        """, unsafe_allow_html=True)
        current_climate = st.session_state.get("climate")
        current_coords = st.session_state.get("coords")
        current_latlon = (float(lat), float(lon))
        fingerprint = None
        if current_climate is not None and current_coords == current_latlon:
            try:
                fingerprint = build_climate_fingerprint(current_climate)
            except Exception as exc:
                st.warning(tx("Could not build this climate fingerprint: ", "Não foi possível montar a assinatura climática: ") + str(exc))
        else:
            st.info(tx(
                "Load NASA POWER data for your selected point in the Environmental dashboard to create a fingerprint.",
                "Carregue os dados NASA POWER do ponto escolhido no Painel ambiental para criar uma assinatura."
            ))
        if fingerprint:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric(tx("Mean temperature", "Temperatura média"), f"{fingerprint['mean_temp_c']:.1f} °C")
            m2.metric(tx("Mean annual rainfall", "Chuva anual média"), f"{fingerprint['annual_precipitation_mm']:.0f} mm")
            m3.metric(tx("Hot days ≥35 °C / year", "Dias ≥35 °C / ano"), f"{fingerprint['hot_days_35c_per_year']:.1f}")
            m4.metric(tx("Valid daily records", "Registros diários válidos"), f"{fingerprint['valid_days']:,}")
            monthly = pd.DataFrame({
                "Month": list(range(1, 13)),
                "Mean temperature (°C)": [fingerprint["monthly_temperature_c"].get(str(i)) for i in range(1,13)],
                "Mean daily precipitation (mm)": [fingerprint["monthly_precipitation_mm_day"].get(str(i)) for i in range(1,13)]
            }).set_index("Month")
            left, right = st.columns(2)
            with left:
                st.markdown("**THERMAL RHYTHM / RITMO TÉRMICO**")
                st.line_chart(monthly[["Mean temperature (°C)"]], height=220)
            with right:
                st.markdown("**RAIN SIGNATURE / ASSINATURA DE CHUVA**")
                st.bar_chart(monthly[["Mean daily precipitation (mm)"]], height=220)
            st.caption(tx(
                f"Aggregate period: {fingerprint['period_start']} to {fingerprint['period_end']}. Monthly precipitation is the mean daily value for each calendar month, not a monthly total.",
                f"Período agregado: {fingerprint['period_start']} a {fingerprint['period_end']}. A precipitação mensal exibida é a média diária de cada mês do calendário, não o total mensal."
            ))
        st.divider()
        st.subheader(tx("Publish a climate fingerprint", "Compartilhe uma assinatura climática"))
        st.warning(tx(
            "Publishing is optional and public. Your alias, broad macroregion, crop, season and aggregate indicators will be visible to other users. Exact coordinates, email, farm name and raw daily data are not sent.",
            "A publicação é opcional e pública. Seu apelido, macrorregião, cultura, safra e indicadores agregados ficarão visíveis a outros usuários. Coordenadas exatas, e-mail, nome da fazenda e dados diários brutos não são enviados."
        ))
        if st.session_state.get("agrovision_auth_mode") == "email":
            with st.form("commons_publish_form"):
                alias = st.text_input(tx("Public alias (not your email)", "Apelido público (não use seu e-mail)"), max_chars=32, placeholder="AgroLab-01")
                macroregion = st.selectbox(tx("Macroregion", "Macrorregião"), ["Norte","Nordeste","Centro-Oeste","Sudeste","Sul"])
                crop = st.selectbox(tx("Main crop context", "Cultura de referência"), ["Soja","Milho","Feijão","Café","Cana-de-açúcar","Algodão","Arroz","Trigo","Mandioca","Sistema diversificado","Outro"])
                season = st.selectbox(tx("Season / reference year", "Safra / ano de referência"), ["2020–2025","2023–2025","2025","2024","2023","2022","2021","2020"])
                consent = st.checkbox(tx("I understand this aggregate profile will be publicly visible.", "Entendo que esta assinatura agregada ficará visível publicamente."), value=False)
                submitted = st.form_submit_button(tx("Publish my fingerprint", "Publicar minha assinatura"), type="primary", disabled=not bool(fingerprint))
            if submitted:
                if not alias.strip() or len(alias.strip()) < 2:
                    st.error(tx("Choose an alias with at least 2 characters.", "Escolha um apelido com pelo menos 2 caracteres."))
                elif not consent:
                    st.error(tx("Explicit consent is required before publishing.", "É necessário consentimento explícito para publicar."))
                else:
                    try:
                        publish_community_snapshot(alias, macroregion, crop, season, fingerprint)
                        st.success(tx("Your climate fingerprint is now on the Commons board.", "Sua assinatura climática já está no mural Commons."))
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))
        else:
            st.info(tx("Sign in to publish. Visitors can explore the public comparison board.", "Entre na sua conta para publicar. Visitantes podem explorar o mural público."))
        st.divider()
        st.subheader(tx("Community comparison field", "Campo de comparação comunitária"))
        st.write(tx(
            "Filter public fingerprints by crop and season. The similarity distance compares mean temperature, mean annual precipitation and hot-day frequency using fixed scales. Lower means more similar; it is not a suitability, productivity or risk score.",
            "Filtre assinaturas públicas por cultura e safra. A distância de similaridade compara temperatura média, precipitação anual média e frequência de dias quentes, com escalas fixas. Quanto menor, mais semelhantes; não é nota de aptidão, produtividade ou risco."
        ))
        try:
            snapshots = fetch_community_snapshots()
            if snapshots:
                board = pd.DataFrame([{
                    "Alias": row.get("display_alias",""),
                    "Macroregion": row.get("macroregion",""),
                    "Crop": row.get("crop",""),
                    "Season": row.get("season",""),
                    "Mean temp (°C)": (row.get("metrics") or {}).get("mean_temp_c"),
                    "Mean annual rain (mm)": (row.get("metrics") or {}).get("annual_precipitation_mm"),
                    "Hot days ≥35 °C/year": (row.get("metrics") or {}).get("hot_days_35c_per_year"),
                    "Created": str(row.get("created_at",""))[:10],
                    "_metrics": row.get("metrics") or {}
                } for row in snapshots])
                f1, f2, f3 = st.columns(3)
                crops = ["All"] + sorted(board["Crop"].dropna().unique().tolist())
                seasons = ["All"] + sorted(board["Season"].dropna().unique().tolist())
                regions = ["All"] + sorted(board["Macroregion"].dropna().unique().tolist())
                crop_filter = f1.selectbox(tx("Crop filter","Filtrar cultura"),crops)
                season_filter = f2.selectbox(tx("Season filter","Filtrar safra"),seasons)
                region_filter = f3.selectbox(tx("Region filter","Filtrar região"),regions)
                filtered = board.copy()
                if crop_filter != "All": filtered = filtered[filtered["Crop"] == crop_filter]
                if season_filter != "All": filtered = filtered[filtered["Season"] == season_filter]
                if region_filter != "All": filtered = filtered[filtered["Macroregion"] == region_filter]
                if fingerprint is not None and not filtered.empty:
                    filtered = filtered.copy()
                    filtered["Similarity distance ↓"] = filtered["_metrics"].apply(lambda item: comparison_distance(fingerprint,item) if all(k in item for k in ("mean_temp_c","annual_precipitation_mm","hot_days_35c_per_year")) else float("nan"))
                    filtered = filtered.sort_values("Similarity distance ↓", na_position="last")
                display_cols = ["Alias","Macroregion","Crop","Season","Mean temp (°C)","Mean annual rain (mm)","Hot days ≥35 °C/year","Created"]
                if "Similarity distance ↓" in filtered.columns: display_cols.append("Similarity distance ↓")
                if filtered.empty:
                    st.info(tx("No public fingerprints match these filters yet. Be the first to contribute.", "Ainda não há assinaturas públicas com esses filtros. Você pode ser o primeiro a contribuir."))
                else:
                    st.dataframe(filtered[display_cols], width="stretch", hide_index=True)
                    if fingerprint is not None and "Similarity distance ↓" in filtered.columns:
                        st.caption(tx("The top rows are the closest climate fingerprints under this descriptive three-variable comparison — not the best places to farm.", "As primeiras linhas são as assinaturas climaticamente mais próximas nesta comparação descritiva de três variáveis — não os melhores lugares para plantar."))
                    if len(filtered) >= 2:
                        st.markdown("**COMMUNITY CLIMATE SPACE / ESPAÇO CLIMÁTICO COMUNITÁRIO**")
                        st.scatter_chart(filtered, x="Mean annual rain (mm)", y="Mean temp (°C)", color="Macroregion", size="Hot days ≥35 °C/year")
            else:
                st.info(tx("The public board is empty. Publish an opt-in fingerprint to start the shared atlas.", "O mural público está vazio. Publique uma assinatura voluntária para iniciar o atlas coletivo."))
        except Exception as exc:
            st.warning(tx("The community board needs the Supabase Commons migration. Run supabase/community_schema.sql in the Supabase SQL Editor. Details: ", "O mural comunitário precisa da migração Supabase Commons. Execute supabase/community_schema.sql no SQL Editor do Supabase. Detalhes: ") + str(exc))
        st.caption(tx(
            "Method note: profiles summarize a gridded NASA POWER point series. User-selected macroregion and crop are labels supplied by contributors, not independently verified farm boundaries or crop observations. Similarity is descriptive only.",
            "Nota metodológica: as assinaturas resumem uma série pontual em grade do NASA POWER. Macrorregião e cultura são rótulos informados pelos participantes, não limites de fazenda ou observações de cultura verificados independentemente. A similaridade é apenas descritiva."
        ))
    
    
if tab_fieldlab.open:
    with tab_fieldlab:
        st.header("GUMA FIELD LAB")
        st.caption(tx(
            "A public notebook for agricultural hypotheses, field comparisons and shared evidence.",
            "Um caderno público de hipóteses agrícolas, comparações de campo e evidências compartilhadas."
        ))
        st.markdown("""
        <div class="section-note">
          <strong>FROM QUESTION TO EVIDENCE / DA PERGUNTA À EVIDÊNCIA</strong><br>
          Propose a comparison, describe the management contrast, record the metric and inspect what other contributors have reported.
          Field Lab entries are community research notes — not controlled trials unless the contributor documents that design.
        </div>
        """, unsafe_allow_html=True)
        st.warning(tx(
            "Do not publish exact farm locations, personal data, confidential business information or identifiable third-party information. Values and study descriptions are contributor-reported and are not independently verified.",
            "Não publique localização exata de propriedades, dados pessoais, informações comerciais confidenciais ou dados identificáveis de terceiros. Valores e descrições são informados pelos participantes e não passam por verificação independente."
        ))
        st.subheader(tx("Design a field question", "Desenhe uma pergunta de campo"))
        if st.session_state.get("agrovision_auth_mode") == "email":
            with st.form("fieldlab_publish_form"):
                title = st.text_input(tx("Study title", "Título do estudo"), max_chars=90, placeholder="Cobertura do solo e milho safrinha")
                alias = st.text_input(tx("Public alias", "Apelido público"), max_chars=32, placeholder="Campo-07")
                c1,c2,c3 = st.columns(3)
                region = c1.selectbox(tx("Macroregion", "Macrorregião"), list(ALLOWED_REGIONS))
                crop = c2.selectbox(tx("Crop", "Cultura"), list(ALLOWED_CROPS))
                season = c3.text_input(tx("Season / year", "Safra / ano"), max_chars=20, value="2025/26")
                hypothesis = st.text_area(tx("What do you expect to happen, and why?", "O que você espera que aconteça e por quê?"), max_chars=700, placeholder=tx("Example: soil cover may reduce exposure to high temperatures and rainfall variability.", "Exemplo: a cobertura do solo pode reduzir a exposição a temperaturas elevadas e à irregularidade das chuvas."))
                strategy = st.text_area(tx("Strategy / treatment", "Estratégia / tratamento"), max_chars=500, placeholder=tx("Describe the management practice or intervention.", "Descreva a prática de manejo ou intervenção."))
                comparator = st.text_area(tx("Comparator / reference", "Comparador / referência"), max_chars=500, placeholder=tx("Describe the reference condition.", "Descreva a condição de referência."))
                c4,c5,c6 = st.columns(3)
                metric = c4.selectbox(tx("Metric", "Indicador"), list(ALLOWED_METRICS))
                unit = c5.text_input(tx("Unit", "Unidade"), max_chars=24, value="sacas/ha")
                baseline = c6.text_input(tx("Reference value (optional)", "Valor de referência (opcional)"), placeholder="80")
                alternative = st.text_input(tx("Alternative value (optional)", "Valor da estratégia (opcional)"), placeholder="84")
                notes = st.text_area(tx("Method, period and limitations", "Método, período e limitações"), max_chars=1000)
                consent = st.checkbox(tx("I consent to publishing this research note publicly under my alias.", "Autorizo a publicação pública desta nota de pesquisa sob meu apelido."), value=False)
                submitted = st.form_submit_button(tx("Publish research note", "Publicar nota de pesquisa"), type="primary")
            if submitted:
                try:
                    record = validate_trial_record({
                        "title":title,"display_alias":alias,"macroregion":region,"crop":crop,
                        "season":season,"hypothesis":hypothesis,"strategy":strategy,
                        "comparator":comparator,"metric":metric,"unit":unit,
                        "baseline_value":baseline if baseline.strip() else None,
                        "alternative_value":alternative if alternative.strip() else None,
                        "notes":notes
                    })
                    if not consent:
                        raise ValueError(tx("Explicit consent is required.", "É necessário consentimento explícito."))
                    publish_field_lab_trial(record)
                    st.success(tx("Research note published to the Field Lab.", "Nota de pesquisa publicada no Field Lab."))
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        else:
            st.info(tx("Sign in with your email account to publish. Public research notes can be explored below without signing in.", "Entre com sua conta de e-mail para publicar. As notas públicas podem ser exploradas abaixo sem entrar na conta."))
        st.divider()
        st.subheader(tx("Explore community experiments", "Explore experimentos da comunidade"))
        try:
            trials = fetch_field_lab_trials()
            try:
                updates = fetch_field_lab_updates()
                updates_frame = pd.DataFrame(updates)
            except Exception as update_exc:
                updates_frame = pd.DataFrame()
                st.warning(tx("The longitudinal timeline needs the latest Supabase migration. ", "A linha do tempo precisa da migração mais recente do Supabase.") + str(update_exc))
            if not trials:
                st.info(tx("No public field notes yet. The first contribution will open this research notebook.", "Ainda não há notas públicas de campo. A primeira contribuição abrirá este caderno de pesquisa."))
            else:
                frame = pd.DataFrame(trials)
                f1,f2,f3 = st.columns(3)
                crop_filter = f1.selectbox(tx("Crop", "Cultura"), ["All"] + sorted(frame["crop"].dropna().unique().tolist()), key="fl_crop")
                region_filter = f2.selectbox(tx("Macroregion", "Macrorregião"), ["All"] + sorted(frame["macroregion"].dropna().unique().tolist()), key="fl_region")
                season_filter = f3.selectbox(tx("Season", "Safra"), ["All"] + sorted(frame["season"].dropna().unique().tolist()), key="fl_season")
                filtered = frame.copy()
                if crop_filter != "All": filtered = filtered[filtered["crop"] == crop_filter]
                if region_filter != "All": filtered = filtered[filtered["macroregion"] == region_filter]
                if season_filter != "All": filtered = filtered[filtered["season"] == season_filter]
                if filtered.empty:
                    st.info(tx("No records match these filters.", "Nenhum registro corresponde a esses filtros."))
                else:
                    for _, trial in filtered.iterrows():
                        with st.expander(f"{trial['title']} · {trial['crop']} · {trial['macroregion']}"):
                            st.caption(f"{trial['display_alias']} · {trial['season']} · {trial['status']}")
                            st.markdown("**" + tx("Hypothesis", "Hipótese") + "**")
                            st.write(trial["hypothesis"])
                            left,right = st.columns(2)
                            with left:
                                st.markdown("**" + tx("Strategy", "Estratégia") + "**")
                                st.write(trial["strategy"])
                            with right:
                                st.markdown("**" + tx("Comparator", "Comparador") + "**")
                                st.write(trial["comparator"])
                            st.write(f"**{tx('Metric','Indicador')}:** {trial['metric']} ({trial['unit']})")
                            base,alt = trial.get("baseline_value"),trial.get("alternative_value")
                            if pd.notna(base) and pd.notna(alt):
                                delta = relative_difference(base,alt)
                                st.metric(tx("Contributor-reported difference", "Diferença informada pelo participante"), f"{delta:+.2f}%" if delta is not None else tx("Not calculable", "Não calculável"), help=tx("Descriptive arithmetic only; not a causal effect or verified result.", "Apenas cálculo descritivo; não é efeito causal nem resultado verificado."))
                                st.caption(f"{tx('Reference','Referência')}: {base:g} · {tx('Alternative','Alternativa')}: {alt:g} {trial['unit']}")
                            if trial.get("notes"):
                                st.caption(trial["notes"])
                            st.caption(tx("Community observation · unverified contributor report", "Observação comunitária · relato não verificado"))
    
                            st.markdown("#### " + tx("Season-by-season timeline", "Linha do tempo por safra"))
                            if not updates_frame.empty:
                                history = updates_frame[updates_frame["trial_id"] == trial["id"]].sort_values(["observation_date", "created_at"])
                            else:
                                history = pd.DataFrame()
                            if history.empty:
                                st.caption(tx("No follow-up observations recorded yet.", "Ainda não há observações de acompanhamento."))
                            else:
                                for _, item in history.iterrows():
                                    st.markdown(
                                        f"**{item['season']} · {item['stage']} · {item['arm']}** — "
                                        f"{item['observed_value']:g} {item['unit']}"
                                    )
                                    st.caption(
                                        f"{item['observation_date']} · {item['display_alias']} · "
                                        f"{item['method']}"
                                    )
                                    if item.get("notes"):
                                        st.caption(item["notes"])
                            if st.session_state.get("agrovision_auth_mode") == "email":
                                with st.form(f"fieldlab_followup_{trial['id']}"):
                                    st.markdown("**" + tx("Add a follow-up observation", "Adicionar observação de acompanhamento") + "**")
                                    u1,u2,u3 = st.columns(3)
                                    follow_alias = u1.text_input(tx("Public alias", "Apelido público"), max_chars=32, key=f"fl_alias_{trial['id']}")
                                    follow_season = u2.text_input(tx("Season", "Safra"), max_chars=20, key=f"fl_season_{trial['id']}", value=str(trial["season"]))
                                    follow_date = u3.date_input(tx("Observation date", "Data da observação"), value=datetime.now().date(), key=f"fl_date_{trial['id']}", max_value=datetime.now().date())
                                    u4,u5,u6 = st.columns(3)
                                    follow_stage = u4.selectbox(tx("Stage", "Etapa"), list(ALLOWED_STAGES), key=f"fl_stage_{trial['id']}")
                                    follow_arm = u5.selectbox(tx("Comparison arm", "Grupo de comparação"), ["Estratégia", "Comparador", "Outro"], key=f"fl_arm_{trial['id']}")
                                    follow_value = u6.text_input(tx("Observed value", "Valor observado"), key=f"fl_value_{trial['id']}")
                                    follow_method = st.text_input(tx("Measurement method / protocol", "Método de medição / protocolo"), max_chars=500, key=f"fl_method_{trial['id']}")
                                    follow_notes = st.text_area(tx("Context and limitations", "Contexto e limitações"), max_chars=1000, key=f"fl_notes_{trial['id']}")
                                    follow_consent = st.checkbox(tx("I consent to publishing this follow-up publicly.", "Autorizo a publicação pública deste acompanhamento."), key=f"fl_consent_{trial['id']}")
                                    follow_submit = st.form_submit_button(tx("Add to timeline", "Adicionar à linha do tempo"))
                                if follow_submit:
                                    try:
                                        follow_record = validate_trial_update({
                                            "trial_id": str(trial["id"]),
                                            "display_alias": follow_alias,
                                            "season": follow_season,
                                            "observation_date": follow_date.isoformat(),
                                            "stage": follow_stage,
                                            "arm": follow_arm,
                                            "observed_value": follow_value,
                                            "unit": str(trial["unit"]),
                                            "method": follow_method,
                                            "notes": follow_notes
                                        })
                                        if not follow_consent:
                                            raise ValueError(tx("Explicit consent is required.", "É necessário consentimento explícito."))
                                        publish_field_lab_update(follow_record)
                                        st.success(tx("Follow-up added to the experiment timeline.", "Acompanhamento adicionado à linha do tempo do experimento."))
                                        st.rerun()
                                    except Exception as follow_exc:
                                        st.error(str(follow_exc))
        except Exception as exc:
            st.warning(tx("The Field Lab database migration is required. Run supabase/community_schema.sql in Supabase SQL Editor. Details: ", "A migração do Field Lab é necessária. Execute supabase/community_schema.sql no SQL Editor do Supabase. Detalhes: ") + str(exc))
        st.caption(tx(
            "Interpretation rule: comparisons are descriptive. Different soils, cultivars, dates, input rates, measurement protocols and weather can confound comparisons. Do not infer causality or recommend management from community entries alone.",
            "Regra de interpretação: as comparações são descritivas. Solos, cultivares, datas, doses de insumos, protocolos de medição e clima diferentes podem confundir os resultados. Não infira causalidade nem recomende manejo apenas com registros comunitários."
        ))
    
st.divider()
st.caption("GUMA · Crop-specific climate screening · Research and validation in progress")



if tab_atlas.open:
    with tab_atlas:
        from agrovision_atlas import BIOMES, AGRICULTURAL_HUBS, validate_atlas_catalog
        validate_atlas_catalog()
        st.header(tx("GUMA Atlas · Brazil", "GUMA Atlas · Brasil"))
        st.write(tx(
            "Explore Brazil through biome reference points, agricultural hubs and selectable geographic basemaps. This is a first national overview, designed to connect environmental and agricultural layers as the atlas evolves.",
            "Explore o Brasil por pontos de referência dos biomas, polos agrícolas e mapas-base geográficos selecionáveis. Esta é uma primeira visão nacional, criada para conectar camadas ambientais e agrícolas à medida que o atlas evolui."
        ))
        st.markdown(
            '<div class="section-note"><strong>GEOGRAPHIC CONTEXT, NOT A BOUNDARY PRODUCT</strong><br>Biome markers are illustrative reference locations, not official biome polygons, farm boundaries or administrative limits. Use the linked IBGE geospatial product for authoritative biome boundaries.</div>',
            unsafe_allow_html=True
        )
        selected_biomes = st.multiselect(
            tx("Biome reference points", "Pontos de referência dos biomas"),
            options=[b["name_pt"] for b in BIOMES],
            default=[b["name_pt"] for b in BIOMES],
            key="guma_atlas_biomes"
        )
        show_hubs = st.checkbox(tx("Show agricultural reference hubs", "Mostrar polos agrícolas de referência"), value=True, key="guma_atlas_hubs")
        show_hydrography = st.checkbox(tx("Show ANA hydrography network (BHO)", "Mostrar rede hidrográfica da ANA (BHO)"), value=False, key="guma_atlas_hydrography")
        map_center = [-14.2, -51.9]
        atlas_map = folium.Map(location=map_center, zoom_start=4, tiles=None, control_scale=True, prefer_canvas=True)
        folium.TileLayer(
            tiles="OpenStreetMap", name=tx("Street map", "Mapa de ruas"),
            overlay=False, control=True
        ).add_to(atlas_map)
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Tiles © Esri", name=tx("Satellite imagery", "Imagem de satélite"),
            overlay=False, control=True
        ).add_to(atlas_map)
        folium.TileLayer(
            tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
            attr="Map data: © OpenStreetMap contributors, SRTM | Map style: © OpenTopoMap",
            name=tx("Topography", "Topografia"), overlay=False, control=True
        ).add_to(atlas_map)
        biome_layer = folium.FeatureGroup(name=tx("Biome reference points", "Pontos de referência dos biomas"), show=True)
        for biome in BIOMES:
            if biome["name_pt"] not in selected_biomes:
                continue
            label = biome["name_pt"] if st.session_state.get("agrovision_language") == "Português" else biome["name_en"]
            summary = biome["summary_pt"] if st.session_state.get("agrovision_language") == "Português" else biome["summary_en"]
            folium.CircleMarker(
                location=[biome["lat"], biome["lon"]], radius=9,
                color="#D85B3D", weight=2, fill=True, fill_color="#E2B75F",
                fill_opacity=0.88,
                tooltip=label,
                popup=folium.Popup(f"<b>{label}</b><br>{summary}<br><small>Illustrative reference point · IBGE biome source linked below</small>", max_width=300)
            ).add_to(biome_layer)
        biome_layer.add_to(atlas_map)
        if show_hydrography:
            folium.raster_layers.WmsTileLayer(
                url="https://portal1.snirh.gov.br/server/services/dados_abertos/Hidrografia_Parte_1/MapServer/WMSServer",
                layers="0",
                name=tx("ANA · Hydrography (BHO, part 1)", "ANA · Hidrografia (BHO, parte 1)"),
                fmt="image/png", transparent=True, version="1.3.0",
                attr="ANA · Base Hidrográfica Ottocodificada Multiescalas 2012",
                overlay=True, control=True, show=True
            ).add_to(atlas_map)
        if show_hubs:
            hub_layer = folium.FeatureGroup(name=tx("Agricultural reference hubs", "Polos agrícolas de referência"), show=True)
            for hub in AGRICULTURAL_HUBS:
                label = hub["name_pt"] if st.session_state.get("agrovision_language") == "Português" else hub["name_en"]
                context = hub["context_pt"] if st.session_state.get("agrovision_language") == "Português" else hub["context_en"]
                folium.Marker(
                    location=[hub["lat"], hub["lon"]],
                    tooltip=label,
                    popup=folium.Popup(f"<b>{label}</b><br>{context}<br><small>Reference city; not a production ranking.</small>", max_width=300),
                    icon=folium.Icon(color="green", icon="leaf", prefix="fa")
                ).add_to(hub_layer)
            hub_layer.add_to(atlas_map)
        folium.LayerControl(collapsed=False).add_to(atlas_map)
        st_folium(atlas_map, width=None, height=610, key="guma_brazil_atlas_map", returned_objects=[])
        st.caption(tx(
            "Basemaps are visual context. Satellite tiles are not a current land-cover classification. The ANA BHO part 1 overlay is a 2012 reference hydrography network, not real-time river flow or water availability.",
            "Os mapas-base oferecem contexto visual. As imagens de satélite não são uma classificação atual de uso da terra. A camada BHO parte 1 da ANA é uma rede hidrográfica de referência de 2012, não um dado de vazão ou disponibilidade hídrica em tempo real."
        ))
        st.subheader(tx("Brazil's six terrestrial biomes", "Os seis biomas terrestres brasileiros"))
        biome_cols = st.columns(3)
        for index, biome in enumerate(BIOMES):
            title = biome["name_pt"] if st.session_state.get("agrovision_language") == "Português" else biome["name_en"]
            summary = biome["summary_pt"] if st.session_state.get("agrovision_language") == "Português" else biome["summary_en"]
            with biome_cols[index % 3]:
                with st.container(border=True):
                    st.markdown(f"**{title}**")
                    st.write(summary)
        st.divider()
        st.subheader(tx("Connect to authoritative geospatial data", "Acesse dados geoespaciais de referência"))
        source_cols = st.columns(3)
        with source_cols[0]:
            st.markdown("**IBGE · Biomes**")
            st.write(tx("Official biome and coastal-marine system delimitation, compatible with 1:250,000 scale.", "Delimitação oficial dos biomas e do sistema costeiro-marinho, compatível com a escala 1:250.000."))
            st.markdown("[IBGE · Biomas](https://www.ibge.gov.br/geociencias/informacoes-ambientais/vegetacao/15842-biomas.html)")
        with source_cols[1]:
            st.markdown("**INPE · TerraBrasilis**")
            st.write(tx("PRODES, DETER and vegetation monitoring geospatial services. Their indicators have different purposes and update cycles.", "Serviços geoespaciais do PRODES, DETER e monitoramento da vegetação. Os indicadores têm objetivos e ciclos de atualização diferentes."))
            st.markdown("[TerraBrasilis](https://www.terrabrasilis.dpi.inpe.br/)")
        with source_cols[2]:
            st.markdown("**MapBiomas**")
            st.write(tx("Annual land-cover and land-use maps, historical series and thematic monitors.", "Mapas anuais de cobertura e uso da terra, séries históricas e monitores temáticos."))
            st.markdown("[MapBiomas Brasil](https://brasil.mapbiomas.org/)")
        st.subheader(tx("Official data services and layer status", "Serviços oficiais e situação das camadas"))
        st.markdown("""
    - **ANA · Hydrography:** BHO multiscale 2012 is available as an optional live WMS overlay (part 1 only). [Service metadata](https://portal1.snirh.gov.br/server/rest/services/dados_abertos/Hidrografia_Parte_1/MapServer?f=pjson)
    - **ICMBio · Protected areas:** official WMS/WFS services are linked for GIS use; not rendered here until layer names and national coverage are verified. [WMS capabilities](https://geoservicos.inde.gov.br/geoserver/ICMBio/ows?service=wms&version=1.3.0&request=GetCapabilities) · [WFS capabilities](https://geoservicos.inde.gov.br/geoserver/ICMBio/ows?service=wfs&version=2.0.0&request=GetCapabilities)
    - **IBGE · Biomes:** official boundary product compatible with 1:250,000; current map still uses illustrative points. [IBGE product](https://www.ibge.gov.br/geociencias/informacoes-ambientais/vegetacao/15842-biomas.html)
    - **MapBiomas · Land cover:** annual maps and thematic products are available; native raster ingestion is pending. [MapBiomas platform](https://plataforma.brasil.mapbiomas.org/)
    """)
        st.info(tx(
            "The Atlas distinguishes live map overlays from authoritative datasets that are linked but not yet ingested. Every future layer must carry source, dataset vintage, scale/resolution, license, update cadence and quality notes. ANA BHO part 1 is a 2012 reference dataset, not real-time monitoring.",
            "O Atlas diferencia camadas exibidas ao vivo de bases oficiais apenas vinculadas, ainda não incorporadas. Toda camada deverá informar fonte, versão/data, escala/resolução, licença, frequência de atualização e notas de qualidade. A parte 1 da BHO da ANA é uma base de referência de 2012, não monitoramento em tempo real."
        ))
    
    
if tab_systems.open:
    with tab_systems:
        from agrovision_systems import AGRONOMIC_SYSTEMS, validate_catalog
        st.header(tx("Agronomic Systems Library", "Biblioteca de Sistemas Agronômicos"))
        st.write(tx(
            "Explore how major farming and management systems are organized, how they operate, and what determines their performance.",
            "Explore como os principais sistemas de produção e manejo são organizados, como funcionam e quais fatores condicionam seus resultados."
        ))
        st.markdown(
            '<div class="section-note">Educational reference · Context-specific management · Not an agronomic prescription</div>',
            unsafe_allow_html=True
        )
        validate_catalog()
        categories = sorted({item["category"] for item in AGRONOMIC_SYSTEMS})
        category_labels = {item["category"]: (item["category_pt"] if st.session_state.get("agrovision_language") == "Português" else item["category"]) for item in AGRONOMIC_SYSTEMS}
        category_keys = ["All categories"] + categories
        category_options = [tx("All categories", "Todas as categorias")] + [category_labels[key] for key in categories]
        selected_category_label = st.selectbox(tx("Explore by category", "Explorar por categoria"), category_options, key="guma_system_category")
        selected_category = None if selected_category_label == category_options[0] else next(key for key in categories if category_labels[key] == selected_category_label)
        search_term = st.text_input(tx("Search systems", "Buscar sistemas"), placeholder=tx("Example: no-till, ILPF, irrigation...", "Ex.: plantio direto, ILPF, irrigação..."), key="guma_system_search").strip().casefold()
        filtered_systems = [
            item for item in AGRONOMIC_SYSTEMS
            if (selected_category is None or item["category"] == selected_category)
            and (not search_term or search_term in " ".join(str(value) for value in item.values()).casefold())
        ]
        st.caption(tx(f"{len(filtered_systems)} systems in this view · {len(AGRONOMIC_SYSTEMS)} in the library", f"{len(filtered_systems)} sistemas nesta visualização · {len(AGRONOMIC_SYSTEMS)} na biblioteca"))
        if not filtered_systems:
            st.info(tx("No systems match this search. Try another term.", "Nenhum sistema corresponde à busca. Tente outro termo."))
        for system in filtered_systems:
            title = system["pt"] if st.session_state.get("agrovision_language") == "Português" else system["name"]
            category = system["category_pt"] if st.session_state.get("agrovision_language") == "Português" else system["category"]
            with st.expander(f"{title} · {category}", expanded=False):
                how = system["how_pt"] if st.session_state.get("agrovision_language") == "Português" else system["how"]
                flow = system["flow_pt"] if st.session_state.get("agrovision_language") == "Português" else system["flow"]
                strengths = system["strengths_pt"] if st.session_state.get("agrovision_language") == "Português" else system["strengths"]
                limits = system["limits_pt"] if st.session_state.get("agrovision_language") == "Português" else system["limits"]
                watch = system["watch_pt"] if st.session_state.get("agrovision_language") == "Português" else system["watch"]
                st.markdown("**" + tx("How it works", "Como funciona") + "**")
                st.write(how)
                st.markdown("**" + tx("Typical operating sequence", "Sequência típica de funcionamento") + "**")
                st.info(flow)
                left, right = st.columns(2)
                with left:
                    st.markdown("**" + tx("Potential strengths", "Potenciais vantagens") + "**")
                    st.write(strengths)
                with right:
                    st.markdown("**" + tx("Limitations and trade-offs", "Limitações e contrapartidas") + "**")
                    st.write(limits)
                st.markdown("**" + tx("What to monitor", "O que monitorar") + "**")
                st.caption(watch)
        st.divider()
        st.subheader(tx("How to interpret this library", "Como interpretar esta biblioteca"))
        st.write(tx(
            "These entries describe different levels of a farming system. No-till is a soil-management approach; rotation and succession describe crop sequences; ILP/ILPF and agroforestry integrate production components; irrigation describes water supply. They can be combined, but they are not synonyms.",
            "As entradas descrevem níveis diferentes de um sistema agrícola. Plantio direto é uma abordagem de manejo do solo; rotação e sucessão descrevem sequências de culturas; ILP/ILPF e SAF integram componentes produtivos; irrigação descreve o suprimento de água. Eles podem ser combinados, mas não são sinônimos."
        ))
        st.caption(tx(
            "Suitability depends on local soil, climate, topography, water, crop, machinery, labor, market and regulation. Potential benefits are conditional, not guaranteed.",
            "A adequação depende de solo, clima, relevo, água, cultura, máquinas, mão de obra, mercado e legislação locais. Benefícios potenciais são condicionais, não garantidos."
        ))
        st.markdown("[Technical references and methodology](https://github.com/interpessoal21-ops/agrovision/blob/spaceapps-2026-rotation-lab/docs/AGRONOMIC_SYSTEMS.md)")
    