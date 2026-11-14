import io
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st

from agrovision_trends import analyze_annual_series

st.set_page_config(page_title="GUMA · Trend Detective", page_icon="🌍", layout="wide")

st.markdown("""
<style>
:root{--ink:#091722;--ocean:#15364A;--teal:#24C8B5;--lime:#B9F36B;--amber:#F0B66A;--paper:#F0F5F3;--muted:#A9BEC5}
.stApp{background:radial-gradient(ellipse at 88% 0%,rgba(36,200,181,.14),transparent 32%),radial-gradient(ellipse at 4% 38%,rgba(185,243,107,.07),transparent 30%),linear-gradient(180deg,#102638 0%,#091722 620px);color:var(--paper)}
[data-testid="stAppViewContainer"],[data-testid="stMain"],[data-testid="stMainBlockContainer"]{background:transparent}
.block-container{max-width:1440px;padding-top:2rem}
h1,h2,h3,p,label,.stMarkdown{color:var(--paper)}
[data-testid="stCaptionContainer"],.stCaption{color:var(--muted)!important}
[data-testid="stMetric"]{background:linear-gradient(145deg,#153044,#102638);border:1px solid #29495A;padding:1rem;border-radius:16px}
[data-testid="stMetricLabel"],[data-testid="stMetricValue"]{color:var(--paper)!important}
[data-baseweb="input"],[data-baseweb="select"]>div,[data-testid="stFileUploader"]{background:#102638;color:var(--paper)}
div.stButton>button{background:#153044;color:var(--paper);border:1px solid #31566A;border-radius:12px}
div.stButton>button[kind="primary"]{background:linear-gradient(105deg,#147F7A,#24AFA5);color:#071923}
.guma-hero{padding:2rem 2.2rem;border:1px solid #31566A;border-radius:24px;background:radial-gradient(circle at 85% 15%,rgba(36,200,181,.22),transparent 25%),linear-gradient(120deg,#091722,#153D50);margin-bottom:1.4rem}
.guma-eyebrow{color:#F0B66A;letter-spacing:.18em;font-size:.72rem;font-weight:800}
.guma-title{font-size:clamp(2rem,5vw,3.7rem);font-weight:850;letter-spacing:-.05em;line-height:1.05;margin:.7rem 0}
.guma-title span{color:#B9F36B}
.guma-copy{color:#C3D4D8;max-width:850px;font-size:1.05rem;line-height:1.6}
.guma-art{float:right;width:min(30%,230px);margin:-.5rem 0 0 1rem}
.note{background:#102F3D;border-left:4px solid #24C8B5;padding:.9rem 1rem;border-radius:0 12px 12px 0;color:#C9E2E0}
@media(max-width:700px){.guma-hero{padding:1.3rem}.guma-art{width:110px}}
</style>
<div class="guma-hero">
<svg class="guma-art" viewBox="0 0 220 190" role="img" aria-label="Original abstract cartographic illustration">
<path d="M18 105C38 24 105 13 150 47s58 86 27 116-95 19-127-7S5 134 18 105Z" fill="none" stroke="#24C8B5" stroke-width="2"/>
<path d="M35 105c24-49 63-62 93-42s40 56 18 78-62 27-91 7-35-21-20-43Z" fill="none" stroke="#B9F36B" stroke-width="2"/>
<path d="M15 132c35-23 57-22 82-2s52 21 99-11M22 151c31-19 52-17 76 0s51 14 82-7" fill="none" stroke="#F0F5F3" stroke-width="3" stroke-linecap="round"/>
<path d="M78 25c-9 32-3 50 18 68s26 42 12 77" fill="none" stroke="#F0B66A" stroke-width="2" stroke-dasharray="4 5"/>
<circle cx="157" cy="43" r="5" fill="#F0B66A"/><circle cx="49" cy="73" r="4" fill="#24C8B5"/>
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
    frame = pd.read_csv(io.StringIO(response.text), skipinitialspace=True)
    frame.columns = [str(c).strip().lstrip("\ufeff") for c in frame.columns]
    if "Year" not in frame.columns:
        raise ValueError("NASA GISTEMP response did not contain the expected Year column.")
    month_columns = [m for m in ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"] if m in frame.columns]
    if len(month_columns) != 12:
        raise ValueError("NASA GISTEMP monthly schema changed; expected all twelve month columns.")
    for col in ["Year", *month_columns]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    annual = frame[["Year", *month_columns]].dropna(subset=["Year"]).copy()
    annual["annual_anomaly_c"] = annual[month_columns].where(annual[month_columns] > -90).mean(axis=1)
    annual = annual.dropna(subset=["annual_anomaly_c"])
    return annual[["Year", "annual_anomaly_c"]].rename(columns={"Year":"year", "annual_anomaly_c":"value"})

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
