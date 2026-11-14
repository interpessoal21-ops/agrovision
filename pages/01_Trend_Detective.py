import io
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st

from agrovision_trends import analyze_annual_series

st.set_page_config(page_title="GUMA · Trend Detective", page_icon="🌍", layout="wide")

st.markdown("""
<style>
:root{--paper:#F1E8D5;--paper2:#E6D9BF;--ink:#18272B;--blue:#2457A6;--red:#D85B3D;--leaf:#63764B;--gold:#D4A64A;--muted:#68716C}
.stApp{background:var(--paper);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,sans-serif}
[data-testid="stAppViewContainer"],[data-testid="stMain"],[data-testid="stMainBlockContainer"]{background:transparent}
.block-container{max-width:1440px;padding-top:2rem}
h1,h2,h3,p,label,.stMarkdown{color:var(--ink)}
[data-testid="stCaptionContainer"],.stCaption{color:var(--muted)!important}
[data-testid="stMetric"]{background:#E6DDCB;border:1px solid #C9BDA7;padding:1rem;border-radius:3px;box-shadow:3px 3px 0 #D7C9B1}
[data-testid="stMetricLabel"],[data-testid="stMetricValue"]{color:var(--ink)!important}
[data-baseweb="input"],[data-baseweb="select"]>div,[data-testid="stFileUploader"]{background:#FFFDF7;color:var(--ink)}
div.stButton>button{background:#E5D8C1;color:var(--ink);border:1px solid #A99D89;border-radius:2px;font-weight:800}
div.stButton>button[kind="primary"]{background:var(--red);color:#FFF8ED;border-color:#B7472F;box-shadow:3px 3px 0 var(--ink)}
.guma-hero{padding:2rem 2.2rem;border:1px solid var(--ink);border-radius:3px;background:var(--ink);color:var(--paper);margin-bottom:1.4rem;box-shadow:8px 8px 0 var(--red);overflow:hidden}
.guma-eyebrow{color:#E17A5B;letter-spacing:.18em;font-size:.72rem;font-weight:900}
.guma-title{font-size:clamp(2rem,5vw,3.7rem);font-weight:900;letter-spacing:-.05em;line-height:1.05;margin:.7rem 0}
.guma-title span{color:#E2B75F}
.guma-copy{color:#E3D9C8;max-width:850px;font-size:1.05rem;line-height:1.6}
.guma-art{float:right;width:min(30%,230px);margin:-.5rem 0 0 1rem}
.note{background:#E8DDC9;border-left:5px solid var(--red);padding:.9rem 1rem;border-radius:0;color:var(--ink)}
hr{border-color:#C9BDA7!important}
@media(max-width:700px){.guma-hero{padding:1.3rem;box-shadow:4px 4px 0 var(--red)}.guma-art{width:110px}}
</style>
<div class="guma-hero">
<svg class="guma-art" viewBox="0 0 220 190" role="img" aria-label="Original abstract cartographic illustration">
<path d="M18 105C38 24 105 13 150 47s58 86 27 116-95 19-127-7S5 134 18 105Z" fill="none" stroke="#D85B3D" stroke-width="2"/>
<path d="M35 105c24-49 63-62 93-42s40 56 18 78-62 27-91 7-35-21-20-43Z" fill="none" stroke="#E2B75F" stroke-width="2"/>
<path d="M15 132c35-23 57-22 82-2s52 21 99-11M22 151c31-19 52-17 76 0s51 14 82-7" fill="none" stroke="#F1E8D5" stroke-width="3" stroke-linecap="round"/>
<path d="M78 25c-9 32-3 50 18 68s26 42 12 77" fill="none" stroke="#2457A6" stroke-width="2" stroke-dasharray="4 5"/>
<circle cx="157" cy="43" r="5" fill="#2457A6"/><circle cx="49" cy="73" r="4" fill="#D85B3D"/>
</svg>
<div class="guma-eyebrow">NASA SPACE APPS CHALLENGE 2026 · CHALLENGE 02</div>
<div class="guma-title">GUMA <span>Trend Detective</span></div>
<div class="guma-copy">Read the fingerprints of a changing Earth. Explore long-term environmental signals, test monotonic trends and distinguish statistical evidence from interpretation.</div>
</div>
""", unsafe_allow_html=True)

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
    frame.columns = [str(c).strip().lstrip("\\ufeff") for c in frame.columns]
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
