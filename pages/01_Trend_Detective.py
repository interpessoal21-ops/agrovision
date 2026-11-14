import io
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st
from guma_brand import apply_brand, render_brand_hero

from agrovision_trends import analyze_annual_series

st.set_page_config(page_title="GUMA · Trend Detective", page_icon="🌍", layout="wide")

apply_brand()
render_brand_hero()

st.caption("GUMA · Earth Intelligence · Beyond the horizon.")
st.markdown('<div class="note"><b>Scientific scope.</b> This experience currently analyzes annual global GISTEMP temperature anomalies or a user-supplied annual series. It is an analytical prototype, not an operational climate-attribution system or a local forecast.</div>', unsafe_allow_html=True)

@st.cache_data(ttl=86400, show_spinner=False)
def load_gistemp():
    url = "https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv"
    response = requests.get(url, timeout=45)
    response.raise_for_status()
    response.encoding = "utf-8"
    if not response.text or "<html" in response.text[:500].lower():
        raise ValueError("NASA returned an HTML page instead of the GISTEMP CSV. Check the data endpoint or network availability.")
    # NASA's current GISTEMP CSV has a descriptive title on line 1 and
    # the actual column header on line 2. Skip the title before parsing.
    frame = pd.read_csv(
        io.StringIO(response.text),
        skiprows=1,
        skipinitialspace=True,
        na_values=["***", "*** "],
    )
    frame.columns = [str(c).strip().lstrip("\ufeff") for c in frame.columns]
    if "Year" not in frame.columns:
        preview = " | ".join(str(x) for x in frame.columns[:8])
        raise ValueError(f"NASA GISTEMP schema not recognized after skipping its title row. Columns received: {preview}")
    frame["Year"] = pd.to_numeric(frame["Year"], errors="coerce")
    # J-D is NASA's published annual mean anomaly. Prefer it over averaging
    # months, which would otherwise admit incomplete current-year records.
    if "J-D" in frame.columns:
        frame["J-D"] = pd.to_numeric(frame["J-D"], errors="coerce")
        annual = frame[["Year", "J-D"]].dropna().rename(columns={"Year": "year", "J-D": "value"})
    else:
        month_columns = [m for m in ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"] if m in frame.columns]
        if len(month_columns) != 12:
            raise ValueError("NASA GISTEMP data has neither the annual J-D column nor all twelve monthly columns.")
        for col in month_columns:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
        annual = frame[["Year", *month_columns]].dropna(subset=["Year"]).copy()
        annual["value"] = frame[month_columns].where(frame[month_columns] > -90).mean(axis=1)
        annual = annual.dropna(subset=["value"]).rename(columns={"Year": "year"})
    annual["year"] = annual["year"].astype(int)
    annual["value"] = pd.to_numeric(annual["value"], errors="coerce")
    annual = annual.dropna(subset=["year", "value"]).sort_values("year")
    annual = annual[annual["value"].between(-5, 5)]
    if len(annual) < 8:
        raise ValueError(f"NASA GISTEMP returned only {len(annual)} usable annual observations.")
    return annual[["year", "value"]].reset_index(drop=True)

st.subheader("Choose an evidence stream")
source = st.radio("Dataset", ["NASA GISTEMP · Global annual temperature anomaly", "Upload annual CSV"], horizontal=True)
frame = None
source_label = source
if source.startswith("NASA"):
    if st.button("Retrieve latest NASA GISTEMP series", type="primary"):
        st.session_state["guma_trend_load"] = True
    if st.session_state.get("guma_trend_load"):
        try:
            with st.spinner("Retrieving and checking NASA GISTEMP data…"):
                frame = load_gistemp()
            st.success(f"Loaded {len(frame)} annual observations from {int(frame.year.min())} to {int(frame.year.max())}.")
        except Exception as exc:
            st.error(f"NASA data could not be loaded: {exc}")
else:
    uploaded = st.file_uploader("Upload CSV with one annual observation per row", type=["csv"])
    if uploaded:
        try:
            raw = pd.read_csv(uploaded)
            st.write("Preview", raw.head())
            year_col = st.selectbox("Year column", raw.columns)
            value_col = st.selectbox("Indicator column", [c for c in raw.columns if c != year_col])
            frame = raw[[year_col, value_col]].rename(columns={year_col:"year", value_col:"value"})
            source_label = f"User upload · {uploaded.name}"
        except Exception as exc:
            st.error(f"Could not read CSV: {exc}")

if frame is not None:
    frame["year"] = pd.to_numeric(frame["year"], errors="coerce")
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.dropna().sort_values("year")
    min_year, max_year = int(frame.year.min()), int(frame.year.max())
    if min_year < max_year:
        left, right = st.columns(2)
        start_year = left.number_input("First year", min_value=min_year, max_value=max_year, value=max(min_year, max_year-50), step=1)
        end_year = right.number_input("Last year", min_value=min_year, max_value=max_year, value=max_year, step=1)
        selected = frame[(frame.year >= start_year) & (frame.year <= end_year)].copy()
        if len(selected) >= 8:
            try:
                result = analyze_annual_series(selected.year.tolist(), selected.value.tolist())
                a,b,c,d = st.columns(4)
                a.metric("Sen's slope", f'{result["sen_slope_per_year"]:.4f} / year')
                b.metric("Mann–Kendall τ", f'{result["tau"]:.3f}')
                c.metric("p-value", f'{result["p_value"]:.4g}')
                d.metric("Valid years", str(result["n"]))
                st.markdown("### The signal")
                st.markdown(f'**Direction:** {result["direction"]}.  **Statistically significant at α = 0.05:** {"Yes" if result["significant_at_alpha"] else "No"}.')
                st.line_chart(selected.set_index("year")["value"], height=360)
                st.caption(f'Sen slope: {result["sen_slope_per_year"]:.5f} indicator units per year · Kendall τ: {result["tau"]:.3f} · two-sided p = {result["p_value"]:.5g}')
                with st.expander("Method and interpretation"):
                    st.write("Mann–Kendall is a non-parametric test for a monotonic trend. Sen’s slope is the median of all pairwise slopes. Ties are included in the Mann–Kendall variance correction.")
                    st.write("The test assumes observations are independent. Serial autocorrelation can inflate significance; this prototype does not yet apply an autocorrelation correction, seasonal Mann–Kendall, or field-specific uncertainty model.")
                    st.write("A statistically significant trend is not proof of causation. Check data provenance, coverage, measurement changes, temporal dependence and physical context before drawing conclusions.")
            except ValueError as exc:
                st.warning(str(exc))
        else:
            st.info("Select a window with at least eight valid annual observations.")
    else:
        st.warning("The dataset needs at least two distinct years.")

st.divider()
st.subheader("Roadmap for the challenge")
st.markdown("""
- **Now:** global annual temperature trend and transparent analysis of annual CSV series.
- **Next:** spatial comparison and gridded Earth-observation products, with source/version metadata.
- **Validation:** autocorrelation-aware inference, uncertainty intervals, independent replication and domain review.
- **Communication:** annotated timelines, maps and accessible explanations that separate observations, statistics and interpretation.
""")
st.caption("NASA GISS GISTEMP v4 · Global land-ocean temperature index · Monthly anomalies relative to 1951–1980. GUMA retrieval time (UTC): " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"))
st.markdown("[NASA GISTEMP data and documentation](https://data.giss.nasa.gov/gistemp/) · [Challenge 02](https://www.spaceappschallenge.org/2026/challenges/)")
