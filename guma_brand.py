"""GUMA brand system — Brazilian territorial cartography.

The visual language follows the supplied GUMA identity board: warm paper,
deep Atlantic blues, ochre sun, terracotta, coastal silhouettes and flowing
topographic/wave lines. All vector artwork here is original.
"""
import html
import streamlit as st

PAPER = "#E8D9C4"
INK = "#16272D"
OCEAN = "#1D5367"
NAVY = "#0D384D"
GOLD = "#D79320"
SKY = "#6A8F9B"
TERRACOTTA = "#AC5C22"
MUTED = "#586664"

BRAND_CSS = """
<style>
:root{
 --guma-paper:#E8D9C4;--guma-paper-light:#F3E8D5;--guma-ink:#16272D;
 --guma-ocean:#1D5367;--guma-navy:#0D384D;--guma-gold:#D79320;
 --guma-sky:#6A8F9B;--guma-terracotta:#AC5C22;--guma-muted:#586664;
 --guma-border:#C5B69F;--guma-panel:#F4E9D7;
}
.stApp{background:var(--guma-paper);color:var(--guma-ink);font-family:Georgia,"Palatino Linotype",serif}
[data-testid="stAppViewContainer"],[data-testid="stMain"],[data-testid="stMainBlockContainer"]{background:transparent}
[data-testid="stSidebar"]{background:#E2D2BA;border-right:1px solid var(--guma-border)}
[data-testid="stHeader"]{background:rgba(232,217,196,.94)}
.block-container{padding-top:1.25rem;padding-bottom:3rem;max-width:1500px}
h1,h2,h3,h4,h5,h6,p,li,label,.stMarkdown,[data-testid="stCaptionContainer"]{color:var(--guma-ink)}
h1,h2,h3{font-family:Georgia,"Palatino Linotype",serif}
[data-testid="stCaptionContainer"],.stCaption,small{color:var(--guma-muted)!important}
a{color:var(--guma-ocean)!important;text-decoration-thickness:1px}
.guma-hero{position:relative;overflow:hidden;min-height:310px;margin:.2rem 0 1.7rem;border:1px solid #BDAE97;background:var(--guma-paper);box-shadow:7px 7px 0 var(--guma-ocean)}
.guma-hero svg{display:block;width:100%;height:auto;min-height:310px}
.guma-hero__copy{position:absolute;left:35%;top:17%;width:43%;text-align:center}
.guma-hero__wordmark{font-family:"Trebuchet MS",Arial,sans-serif;font-size:clamp(2.6rem,6vw,5.4rem);font-weight:1000;letter-spacing:-.075em;line-height:.92;color:var(--guma-ink)}
.guma-hero__descriptor{font-family:Arial,sans-serif;font-size:clamp(.55rem,1.15vw,.9rem);font-weight:800;letter-spacing:.24em;margin-top:.5rem;color:var(--guma-ink)}
.guma-hero__tagline{font-family:Georgia,serif;font-style:italic;font-size:clamp(.8rem,1.7vw,1.25rem);line-height:1.25;margin-top:1.1rem;color:var(--guma-navy)}
.guma-hero__rule{width:42%;height:5px;margin:.65rem auto 0;background:var(--guma-gold);border-radius:50%;transform:rotate(-2deg)}
.guma-sidebar-brand{display:flex;align-items:center;gap:10px;padding:8px 2px 18px}
.guma-sidebar-brand svg{width:46px;height:46px;flex:0 0 46px}
.guma-sidebar-brand strong{font-family:"Trebuchet MS",Arial,sans-serif;color:var(--guma-ink);font-size:1.25rem;letter-spacing:.08em}
.guma-sidebar-brand small{display:block;color:var(--guma-ocean)!important;font-family:Arial,sans-serif;font-size:.56rem;letter-spacing:.13em;font-weight:800}
.guma-eyebrow{font-family:Arial,sans-serif;color:var(--guma-terracotta);font-size:.7rem;font-weight:900;letter-spacing:.17em;text-transform:uppercase}
.guma-note,.section-note,.note{padding:.9rem 1rem;border-left:5px solid var(--guma-terracotta);background:#E1D1B8;color:var(--guma-ink);margin:.5rem 0 1rem}
.step-card{background:var(--guma-panel);border:1px solid var(--guma-border);border-radius:2px;padding:1rem;min-height:142px;box-shadow:3px 3px 0 #D6C5AA}
.step-number{display:inline-flex;width:30px;height:30px;align-items:center;justify-content:center;background:#D6C5AA;color:var(--guma-ocean);font-weight:900;margin-bottom:.55rem}
.step-card strong{display:block;color:var(--guma-ink);margin-bottom:.3rem}
.step-card span{color:var(--guma-muted);font-size:.88rem;line-height:1.4}
div[data-testid="stTabs"] button{color:#586664;font-weight:750}
div[data-testid="stTabs"] button[aria-selected="true"]{color:var(--guma-terracotta);border-bottom-color:var(--guma-terracotta)}
[data-baseweb="input"],[data-baseweb="textarea"],[data-baseweb="select"]>div,[data-testid="stDateInput"] input,[data-testid="stNumberInput"] input{background:#FFF9EF!important;color:var(--guma-ink)!important;border-color:#BDAE97!important}
input,textarea{color:var(--guma-ink)!important}
[data-baseweb="popover"],[data-baseweb="menu"],[role="listbox"]{background:#FFF9EF!important;color:var(--guma-ink)!important}
[data-testid="stDataFrame"],[data-testid="stTable"]{background:#FFF9EF;border:1px solid var(--guma-border);border-radius:2px}
[data-testid="stMetric"]{background:#E1D1B8;border:1px solid var(--guma-border);padding:1rem;border-radius:2px;box-shadow:3px 3px 0 #D6C5AA}
[data-testid="stMetricLabel"],[data-testid="stMetricValue"],[data-testid="stMetricDelta"]{color:var(--guma-ink)!important}
[data-testid="stAlert"]{background:#E5D5BD;color:var(--guma-ink);border:1px solid var(--guma-border)}
div.stButton>button{border-radius:2px;font-weight:800;color:var(--guma-ink);background:#E4D4BC;border:1px solid #A99A82;transition:all .16s ease}
div.stButton>button[kind="primary"],.stFormSubmitButton>button{background:var(--guma-terracotta);color:#FFF5E8;border:1px solid #8F481D;box-shadow:3px 3px 0 var(--guma-ink);font-weight:850}
div.stButton>button:hover{border-color:var(--guma-ocean);color:var(--guma-ocean);transform:translate(-1px,-1px)}
div.stButton>button[kind="primary"]:hover{color:#FFF5E8;background:#91471E}
hr{border-color:#C5B69F!important}
:focus-visible{outline:3px solid var(--guma-gold)!important;outline-offset:3px}
[data-testid="stSidebar"] a,[data-testid="stMain"] a{font-weight:650}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;transition:none!important;animation:none!important}}
@media(max-width:700px){
 .guma-hero{min-height:185px;box-shadow:4px 4px 0 var(--guma-ocean)}
 .guma-hero svg{min-height:185px}
 .guma-hero__copy{left:31%;top:18%;width:48%}
 .guma-hero__wordmark{font-size:2.2rem}
 .guma-hero__descriptor{font-size:.45rem;letter-spacing:.12em}
 .guma-hero__tagline{font-size:.72rem;margin-top:.55rem}
 .guma-hero__rule{height:3px}
}
</style>
"""

HERO_SVG = """
<div class="guma-hero" role="img" aria-label="GUMA — Território, Clima e Futuro. Do campo ao mar, com o Brasil no horizonte.">
<svg viewBox="0 0 1200 470" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
<defs>
 <linearGradient id="gumaSea" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#1D5367"/><stop offset="1" stop-color="#0D384D"/></linearGradient>
 <pattern id="gumaPaper" width="34" height="34" patternUnits="userSpaceOnUse"><path d="M0 8 Q12 3 24 9 T48 8M-8 28 Q8 22 18 28 T42 27" fill="none" stroke="#C7B69C" stroke-width=".6" opacity=".34"/></pattern>
</defs>
<rect width="1200" height="470" fill="#E8D9C4"/><rect width="1200" height="470" fill="url(#gumaPaper)"/>
<!-- Sun and emblem -->
<circle cx="188" cy="185" r="126" fill="#D79320"/>
<path d="M65 194C76 91 157 44 240 77c66 26 91 102 68 163-25 65-104 95-178 66-49-19-72-61-65-112Z" fill="#1D5367"/>
<path d="M67 233c49-40 98-43 145-13 48 31 91 25 137-14v74c-46 45-100 52-151 23-47-26-86-26-131 5Z" fill="#0D384D"/>
<path d="M45 300c54-27 100-29 147-7 52 24 100 21 153-16M45 337c55-26 100-27 149-6 52 22 99 17 152-19" fill="none" stroke="#E8D9C4" stroke-width="13"/>
<!-- Figure with broad hat and staff -->
<path d="M114 159q51-34 103-7l-15 19q-43-15-83 8Z" fill="#16272D"/>
<path d="M127 164q34-14 74-4l-6 20q-35-5-65 10Z" fill="#E8D9C4"/>
<path d="M147 184l-9 48 27 29 33-12-9-48Z" fill="#16272D"/>
<path d="M167 228l-42 62 37 11 44-59Z" fill="#E8D9C4"/>
<path d="M222 75l76 254" stroke="#16272D" stroke-width="7" stroke-linecap="round"/>
<!-- chapel silhouette -->
<path d="M235 206h58v75h-58zM249 186l15-24 15 24v20h-30zM258 161v-13h12v13" fill="#E8D9C4"/>
<path d="M254 230h9v17h-9zm17 0h9v17h-9z" fill="#1D5367"/>
<!-- Coastal palms and chapel on right -->
<path d="M1015 0q-22 68-5 150m-3-119q-73-45-104-22 49 2 85 42-63-7-96 30 56-19 105 2-39 24-50 60 39-29 62-53 14 44 47 68-17-54-23-93 52 21 87 15-53-30-91-37 50-19 77-57-65 26-102 53Z" fill="#16272D"/>
<path d="M1070 190h95v115h-95zM1092 190v-32l24-34 24 34v32" fill="#F3E8D5" stroke="#16272D" stroke-width="8"/>
<path d="M1110 248h17v57h-17zM1141 218h13v22h-13z" fill="#16272D"/>
<!-- boats and sea -->
<path d="M810 332q110-30 215 5t175 0v85H770Z" fill="url(#gumaSea)"/>
<path d="M820 363q95-27 183 2t180 1M810 391q98-25 190 1t177-1" fill="none" stroke="#E8D9C4" stroke-width="8"/>
<path d="M880 319l36-48v48zM922 320l25-35v35z" fill="#F3E8D5"/>
<path d="M870 321h84l-12 12h-61z" fill="#16272D"/>
<!-- warm landforms -->
<path d="M1000 322q75-60 125-12t75 6v102h-200Z" fill="#AC5C22"/>
<path d="M1017 355q75-40 128 1t75 0" fill="none" stroke="#D79320" stroke-width="17"/>
<!-- bottom cartographic waves -->
<path d="M0 421q120-45 242-5t244 4 246-4 240 8 228-6v52H0Z" fill="#0D384D"/>
<path d="M0 442q133-34 253 5t248-2 242-3 231 6 226-5" fill="none" stroke="#1D5367" stroke-width="12"/>
<path d="M0 457q131-24 252 11t247-3 244-2 231 4 226-4" fill="none" stroke="#D79320" stroke-width="7"/>
</svg>
<div class="guma-hero__copy">
 <div class="guma-hero__wordmark">GUMA</div>
 <div class="guma-hero__descriptor">TERRITÓRIO • CLIMA • FUTURO</div>
 <div class="guma-hero__tagline">Do campo ao mar,<br/>com o Brasil no horizonte.</div>
 <div class="guma-hero__rule"></div>
</div>
</div>
"""

def apply_brand():
    st.markdown(BRAND_CSS, unsafe_allow_html=True)

def render_brand_hero():
    st.markdown(HERO_SVG, unsafe_allow_html=True)

def sidebar_brand():
    return '''
    <div class="guma-sidebar-brand">
      <svg viewBox="0 0 64 64" role="img" aria-label="GUMA">
        <circle cx="29" cy="28" r="25" fill="#D79320"/>
        <path d="M5 30C12 6 39 -1 53 17s8 36-12 42S4 50 5 30Z" fill="#1D5367"/>
        <path d="M7 39q14-10 26-1t25-2v13q-17 13-31 3T7 55Z" fill="#0D384D"/>
        <path d="M7 48q15-8 27 0t24-1" stroke="#E8D9C4" stroke-width="4" fill="none"/>
        <path d="M26 9l14 46" stroke="#16272D" stroke-width="3"/>
        <path d="M12 22q13-10 26-2l-4 6q-10-3-20 3Z" fill="#16272D"/>
      </svg>
      <div><strong>GUMA</strong><small>TERRITÓRIO • CLIMA • FUTURO</small></div>
    </div>
    '''
