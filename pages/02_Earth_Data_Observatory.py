from datetime import date, timedelta

import pandas as pd
import streamlit as st

from guma_brand import apply_brand, render_brand_hero
from guma_earth_data import (
    load_ibge_states,
    load_nasa_firms_brazil_24h,
    search_sentinel2_scenes,
)

st.set_page_config(page_title="GUMA · Earth Data Observatory", page_icon="🌎", layout="wide")
apply_brand()
render_brand_hero()

st.markdown('<div class="guma-eyebrow">Observação da Terra · Dados abertos</div>', unsafe_allow_html=True)
st.title("Earth Data Observatory")
st.write(
    "Um ponto de encontro entre satélites, fogo, território e evidência. "
    "Cada camada mantém sua fonte, período, resolução e limitações explícitos."
)

tab_sat, tab_fire, tab_ibge, tab_method = st.tabs(
    ["Sentinel-2 · cenas", "NASA FIRMS · fogo", "IBGE · território", "Método e fontes"]
)

with tab_sat:
    st.subheader("Busca de cenas Sentinel-2 L2A")
    st.caption(
        "Pesquisa de metadados no catálogo STAC Earth Search. A busca usa um pequeno "
        "polígono retangular em torno do ponto escolhido; não representa limite de propriedade."
    )
    c1, c2, c3 = st.columns(3)
    lat = c1.number_input("Latitude", min_value=-90.0, max_value=90.0, value=-15.785, format="%.5f")
    lon = c2.number_input("Longitude", min_value=-180.0, max_value=180.0, value=-47.875, format="%.5f")
    cloud = c3.slider("Nuvens máximas na cena (%)", min_value=0, max_value=100, value=40)
    today = date.today()
    d1, d2 = st.columns(2)
    start = d1.date_input("Data inicial", value=today - timedelta(days=45), max_value=today)
    end = d2.date_input("Data final", value=today, min_value=start, max_value=today)
    if st.button("Pesquisar imagens de satélite", type="primary", key="guma_sentinel_search"):
        try:
            with st.spinner("Consultando catálogo Sentinel-2…"):
                scenes = search_sentinel2_scenes(lat, lon, start, end, cloud)
            st.session_state["guma_sentinel_scenes"] = scenes
            st.session_state["guma_sentinel_query"] = {
                "latitude": lat, "longitude": lon, "start": start.isoformat(),
                "end": end.isoformat(), "cloud_limit_pct": cloud,
            }
        except Exception as exc:
            st.error(f"Não foi possível consultar o catálogo Sentinel-2: {exc}")
    scenes = st.session_state.get("guma_sentinel_scenes")
    if isinstance(scenes, pd.DataFrame):
        query = st.session_state.get("guma_sentinel_query", {})
        st.caption(
            f"Consulta anterior: {query.get('start')} a {query.get('end')} · "
            f"centro {query.get('latitude')}, {query.get('longitude')}."
        )
        if scenes.empty:
            st.info("Nenhuma cena correspondeu aos filtros. Amplie o período ou o limite de nuvens.")
        else:
            st.metric("Cenas encontradas", len(scenes))
            st.dataframe(scenes, use_container_width=True, hide_index=True)
            st.download_button(
                "Baixar metadados CSV",
                scenes.to_csv(index=False).encode("utf-8"),
                file_name="guma_sentinel2_scenes.csv",
                mime="text/csv",
            )
            st.info(
                "A cobertura de nuvens exibida é a estimativa da cena/tile, não a fração de nuvens "
                "dentro de um talhão. Esta página ainda não calcula NDVI/EVI/NDMI em pixels."
            )
    st.caption("Fonte: Element 84 Earth Search · Sentinel-2 L2A · catálogo STAC.")
    st.markdown("[Abrir catálogo Earth Search](https://earth-search.aws.element84.com/v1)")

with tab_fire:
    st.subheader("Detecções recentes de fogo — NOAA-20 VIIRS")
    st.write(
        "Consulta ao arquivo South America 24h do NASA FIRMS. A filtragem abaixo usa "
        "um retângulo aproximado do Brasil, não a malha oficial das fronteiras."
    )
    if st.button("Atualizar focos de calor", type="primary", key="guma_firms_refresh"):
        try:
            with st.spinner("Obtendo arquivo NASA FIRMS…"):
                fires, source_url = load_nasa_firms_brazil_24h()
            st.session_state["guma_fires"] = fires
            st.session_state["guma_fires_source"] = source_url
        except Exception as exc:
            st.error(f"Não foi possível consultar NASA FIRMS: {exc}")
    fires = st.session_state.get("guma_fires")
    if isinstance(fires, pd.DataFrame):
        a, b = st.columns(2)
        a.metric("Detecções no recorte aproximado do Brasil", len(fires))
        if "frp" in fires.columns:
            frp = pd.to_numeric(fires["frp"], errors="coerce")
            b.metric("Potência radiativa somada (MW)", f"{frp.sum():,.1f}" if frp.notna().any() else "—")
        if not fires.empty:
            st.map(fires[["latitude", "longitude"]], size=8)
            keep = [c for c in ["acquired_at_utc", "latitude", "longitude", "confidence", "frp", "bright_ti4", "satellite"] if c in fires.columns]
            st.dataframe(fires[keep].head(500), use_container_width=True, hide_index=True)
            st.download_button(
                "Baixar detecções CSV",
                fires.to_csv(index=False).encode("utf-8"),
                file_name="guma_nasa_firms_brazil_24h.csv",
                mime="text/csv",
            )
        else:
            st.info("Nenhuma detecção apareceu dentro do recorte geográfico aproximado nesta consulta.")
        st.caption("Arquivo: " + str(st.session_state.get("guma_fires_source", "")))
    st.markdown("[NASA FIRMS — Fire Information for Resource Management System](https://firms.modaps.eosdis.nasa.gov/)")

with tab_ibge:
    st.subheader("Referência territorial oficial")
    st.write("Códigos e nomes das unidades da Federação obtidos diretamente da API de Localidades do IBGE.")
    if st.button("Carregar unidades da Federação", key="guma_ibge_states"):
        try:
            with st.spinner("Consultando IBGE…"):
                st.session_state["guma_ibge_states"] = load_ibge_states()
        except Exception as exc:
            st.error(f"Não foi possível consultar o IBGE: {exc}")
    states = st.session_state.get("guma_ibge_states")
    if isinstance(states, pd.DataFrame):
        st.metric("Unidades da Federação", len(states))
        st.dataframe(states, use_container_width=True, hide_index=True)
        st.download_button(
            "Baixar códigos estaduais CSV",
            states.to_csv(index=False).encode("utf-8"),
            file_name="guma_ibge_uf.csv",
            mime="text/csv",
        )
    st.markdown("[API de Localidades do IBGE](https://servicodados.ibge.gov.br/api/docs/localidades)")

with tab_method:
    st.subheader("Proveniência e limitações")
    st.markdown(
        """
        - **Sentinel-2:** metadados de cenas L2A; nuvens são percentuais do tile, não do polígono.
        - **NASA FIRMS:** detecções de fogo ativas por satélite; um foco não equivale automaticamente
          a incêndio confirmado, área queimada ou causa identificada.
        - **IBGE:** códigos oficiais de unidades da Federação; população, área e malhas serão
          incorporadas em uma próxima etapa após validação dos agregados e seus metadados.
        - **Sem inferência causal:** coincidência espacial ou temporal não demonstra causalidade.
        - **Sem limite cadastral:** os polígonos desta página são apenas janelas de busca.
        """
    )
    st.markdown("[NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) · [Earth Search](https://earth-search.aws.element84.com/) · [IBGE](https://www.ibge.gov.br/)")
