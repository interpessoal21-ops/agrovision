# GUMA Institutional Kit
## Institutional brief, technical architecture, demonstration and outreach

**Version:** 1.0  
**Status:** preparation material for exploratory conversations. GUMA has no confirmed institutional, academic or commercial partners unless a written agreement is separately documented.

---

## 1. Executive brief

### GUMA — Earth Intelligence
**Beyond the horizon.**

GUMA is an early-stage, bilingual geospatial and environmental intelligence platform that brings together Earth-observation products, climate indicators, territorial context and collaborative research. Its current demonstrator connects daily NASA POWER climate data, MODIS/Terra vegetation observations, climate indicators and exploratory agricultural workflows.

The platform is being developed as an open, reproducible and transparent research-oriented system. Its ambition is to make environmental evidence easier to explore while preserving the provenance, uncertainty, resolution and limitations of every dataset.

### The problem we are addressing

Environmental and agricultural decisions often require information scattered across different portals, formats, spatial scales and update cycles. A map, a climate series and a vegetation indicator may describe different things and should not be treated as interchangeable evidence.

GUMA aims to provide a coherent workspace in which users can:
- explore a territory and its environmental context;
- inspect climate and vegetation observations with source attribution;
- compare historical conditions without disguising uncertainty;
- document hypotheses and community-contributed observations;
- identify where additional measurements, validation or expert review are needed.

### What GUMA is — and is not

GUMA is currently a research and demonstration platform. It is not an operational early-warning service, a certified agronomic decision system, a calibrated yield model, a substitute for field measurement, or an official government data portal. It does not claim institutional endorsement.

---

## 2. Current demonstrator

Capabilities implemented in the development branch should be checked against the live deployment before every external presentation.

| Area | Current capability | Important boundary |
|---|---|---|
| Earth Observatory | Study-area selection and integrated entry point | Map layers provide context; they do not delineate property boundaries |
| Climate data | NASA POWER daily climate series | Gridded estimates, not local station measurements |
| Vegetation | MODIS/Terra MOD13Q1 NDVI with quality filtering | NDVI is not crop identification, disease diagnosis or yield |
| Climate Watch | Global temperature and greenhouse-gas indicator series | Publication latency; not real-time telemetry |
| Local extremes | Descriptive hot-day, heavy-rain and dry-spell indicators | Not official heatwave or drought classifications |
| Agricultural screening | Historical crop-window and water-balance exploration | Not a calibrated crop model or agronomic prescription |
| Rotation Lab | Historical climate-window comparison of illustrative scenarios | No yield, profit, carbon or water-saving prediction |
| GUMA Commons | Opt-in, aggregated climate fingerprints | Contributor labels are self-reported |
| Field Lab | Community hypothesis notes and longitudinal updates | Contributions are unverified; not a controlled-trial registry |
| Partnerships & Alliances | Prospecting framework and institutional opportunity map | Listed organizations are prospects, not partners |

**Deployment discipline:** the GitHub development branch and public Streamlit deployment may differ. Confirm the deployed commit and run the live demonstration checklist before describing a capability as publicly available.

---

## 3. Technical architecture

### Data and evidence flow

1. **Source layer:** official APIs, data portals and documented scientific datasets.
2. **Ingestion layer:** request, parse, cache and validate data; preserve source identifiers and retrieval dates.
3. **Quality layer:** apply product-specific quality flags, missing-data checks, valid ranges and completeness thresholds.
4. **Analysis layer:** calculate transparent indicators and exploratory summaries; avoid unsupported composite scores.
5. **Presentation layer:** maps, time series, tables, source links and explicit interpretation limits.
6. **Collaboration layer:** optional authenticated user projects and opt-in community contributions, with access controls.
7. **Validation layer:** compare gridded products with independent station observations and document representativeness.

### Current technology

- Python and Streamlit for the application.
- NASA POWER Daily API for gridded meteorological variables.
- MODIS/Terra MOD13Q1 accessed through ORNL DAAC for vegetation-index observations.
- Supabase Auth and PostgreSQL with Row Level Security for optional accounts, projects and community records.
- GitHub for source control, tests and CI workflows.

### Proposed architecture improvements

- Create a versioned source registry: provider, dataset, variable, license, spatial resolution, temporal coverage, update cadence, API endpoint and known uncertainty.
- Add a normalized geospatial data catalog and explicit coordinate reference system handling.
- Separate ingestion, processing, validation and UI modules further as the number of datasets grows.
- Add reproducible data snapshots and dataset-version metadata to exported reports.
- Introduce automated data freshness checks and source outage reporting.
- Maintain a documented security, privacy, backup and retention policy before expanding user data collection.

---

## 4. Scientific integrity and validation plan

### Immediate validation pilot

**Proposed pilot:** compare NASA POWER daily precipitation and temperature against quality-controlled observations from one or more INMET stations in a clearly defined study area and period.

Protocol:
1. Select a territory and stations with documented coordinates, elevation, instruments and observation period.
2. Confirm variable definitions, units, time zone, missing-value codes and quality-control procedures.
3. Match dates and compare only valid paired observations.
4. Report sample size, bias, MAE, RMSE and R² where statistically appropriate.
5. Examine distance and elevation differences and seasonal performance.
6. Publish limitations and avoid generalizing one station comparison to all of Brazil.

A validation result is specific to the station, variable, period and spatial representativeness tested. It is not universal validation of NASA POWER or GUMA.

### Additional research questions

- How do gridded precipitation estimates compare with station observations during intense rainfall?
- How does MODIS NDVI behave across different land-cover types and seasons?
- Which open datasets can add land-cover change, fire, water and biodiversity context?
- How can uncertainty be communicated to non-specialist users without hiding methodological detail?

### Evidence policy

Every operational indicator should display:
- dataset and provider;
- observation period and retrieval time;
- units and spatial/temporal resolution;
- quality filtering and missing-data treatment;
- calculation method and reference baseline;
- uncertainty, known limitations and intended use.

Do not describe a prototype screening result as a forecast, diagnosis, official classification or recommendation.

---

## 5. Partnership model

GUMA should seek specific contributions rather than generic endorsement.

| Partner profile | Potential contribution | Possible GUMA contribution |
|---|---|---|
| Public research and space agencies | Earth-observation expertise, datasets, technical review | Reproducible integrations, documented use cases and educational demonstrators |
| Meteorological and hydrological agencies | Station observations, metadata and monitoring expertise | Transparent comparison tools and station-vs-grid validation reports |
| Universities and research groups | Principal investigators, peer review, student projects and methods | Open research software, reproducible notebooks and data visualization |
| Agricultural research institutions | Crop, soil, agroclimatology and field expertise | Exploratory workflows and structured research hypotheses |
| Environmental organizations | Land-cover, forest, fire, water and biodiversity knowledge | Interoperable views and source-attributed territorial analysis |
| Private technology and geospatial companies | Cloud credits, APIs, compute, tooling and engineering mentorship | Demonstration use cases, testing and documented technical feedback |
| Cooperatives and producers | Field context, pilot sites and feedback | Transparent monitoring tools and co-designed research questions |
| Innovation and funding programs | Grants, challenge programs, incubation and R&D support | Defined work packages, milestones and measurable deliverables |

### Priority outreach sequence

1. **Scientific and data foundations:** INPE, INMET, Embrapa, CEMADEN, universities and research groups.
2. **Territorial and environmental layers:** MapBiomas, MMA/INDE and relevant public data providers.
3. **Applied research and infrastructure:** EMBRAPII units, research centers and private geospatial/cloud providers.
4. **Funding and innovation:** FINEP, state research foundations, CONFAP networks, open-innovation programs and eligible accelerators.

These are prospective pathways, not evidence of an active call, eligibility or willingness to collaborate. Check official rules and current opportunities before applying.

---

## 6. Demonstration script (7–10 minutes)

**0:00–1:00 — Why GUMA exists**  
Explain the fragmentation of environmental information and the need to distinguish observation, inference and uncertainty.

**1:00–2:30 — Earth Observatory**  
Choose a study area. Explain the map as geographic context, not a property boundary or measurement.

**2:30–4:00 — Climate and vegetation**  
Show a NASA POWER climate series and a MODIS NDVI summary. Point out the observation period, source, quality filtering and limitations.

**4:00–5:30 — Climate Watch**  
Show global climate indicators and distinguish the latest published observation from real-time conditions.

**5:30–7:00 — Research workflows**  
Show Rotation Lab, Field Lab or Commons. Explain that scenario comparisons and community records are exploratory and do not establish causality.

**7:00–8:30 — Validation and partnerships**  
Present the station-comparison pilot and identify the specific expertise or dataset sought from the institution.

**8:30–10:00 — Concrete request**  
Ask for one next step: a technical conversation, methodological review, data-product guidance or a narrowly scoped pilot.

### Demo readiness checklist

- [ ] Confirm the live app is running and identify its deployed commit.
- [ ] Use a preselected study area with known, successfully loaded data.
- [ ] Check that source links and latest observation dates render.
- [ ] Test the internet connection and fallback behavior.
- [ ] Avoid showing secrets, personal records or confidential coordinates.
- [ ] Clearly label roadmap features as planned, not operational.
- [ ] Have screenshots or a short recorded walkthrough available as backup.

---

## 7. First-contact message templates

### A. Public research or data institution

**Subject:** Exploratory technical conversation — GUMA Earth Intelligence

Hello,

I am developing GUMA — Earth Intelligence, an independent research-oriented platform that brings together Earth-observation products, climate indicators, geospatial context and exploratory environmental and agricultural workflows.

The current demonstrator uses public NASA POWER climate data and MODIS/Terra vegetation observations. We are working to strengthen data provenance, scientific validation and the integration of authoritative Brazilian datasets.

I would like to ask whether your team could point me to the most appropriate technical documentation, data specialists or research group for an exploratory conversation about [specific dataset, method or research question].

At this stage, I am not presenting an established partnership or requesting institutional endorsement. The immediate goal is to learn, validate the technical approach and identify a small, well-defined pilot.

I can share the demonstrator, technical brief and validation protocol in advance.

Thank you for your time.

Best regards,  
GUMA — Earth Intelligence

### B. University or research group

**Subject:** Research collaboration inquiry — geospatial and environmental data demonstrator

Hello,

I am developing GUMA — Earth Intelligence, a platform for exploring climate, Earth observation and territorial data. I am looking for a research group interested in reviewing a small, reproducible validation study.

A first candidate is a comparison of NASA POWER daily climate estimates with quality-controlled observations from selected meteorological stations, documenting paired sample size, bias, MAE, RMSE, R² where appropriate, and spatial representativeness.

I would value a conversation about methodological supervision, a student research project or a limited pilot. GUMA is an early-stage demonstrator; I do not claim that the platform or its models are scientifically validated as a whole.

Would this topic fit the scope of your group?

Best regards,  
GUMA — Earth Intelligence

### C. Private technology or innovation organization

**Subject:** Technical introduction — GUMA Earth Intelligence

Hello,

I am developing GUMA — Earth Intelligence, an early-stage platform connecting Earth observation, climate data and environmental research workflows.

I am exploring potential technical support in [cloud infrastructure / geospatial tooling / data engineering / mentorship / pilot access]. The goal is to improve reliability, reproducibility and responsible use of public environmental datasets.

I would appreciate guidance on relevant open-innovation programs, developer resources or a suitable technical contact. I can provide a short demonstration and a clearly scoped list of needs.

This is an exploratory approach; no commercial agreement or partnership is implied.

Best regards,  
GUMA — Earth Intelligence

---

## 8. First 90 days: proposed roadmap

| Period | Deliverable | Evidence of completion |
|---|---|---|
| Days 1–15 | Institutional brief, source registry and demo checklist | Versioned docs and repeatable demo |
| Days 16–30 | Select pilot territory and station dataset | Documented station metadata and data-quality checks |
| Days 31–45 | Run first station-vs-grid comparison | Reproducible notebook/report with metrics and limitations |
| Days 46–60 | Request independent methodological review | Written feedback and tracked issues |
| Days 61–75 | Improve one integration based on review | Tested code and updated provenance |
| Days 76–90 | Prepare eligible pilot or funding proposal | Defined partner roles, budget assumptions and milestones |

Progress should be measured by evidence: validated data flows, reproducible results, independent feedback and working integrations — not by the number of logos displayed.

---

## 9. Governance, privacy and intellectual property

Before a formal collaboration:
- define scope, deliverables, responsibilities and maintenance;
- document dataset licenses, attribution and redistribution restrictions;
- agree on code ownership, licensing, publication rights and any background IP;
- define data protection, consent, retention, access controls and incident response;
- do not publish exact farm coordinates, personal data or confidential operational records without a lawful basis and explicit safeguards;
- distinguish public datasets, user contributions and partner-provided data;
- obtain written authorization before using partner names or logos;
- never imply endorsement, certification or formal affiliation without written permission.

---

## 10. Reference links

- [NASA POWER](https://power.larc.nasa.gov/)
- [NASA Earthdata](https://www.earthdata.nasa.gov/)
- [INPE Data Portal](https://data.inpe.br/)
- [INMET meteorological station map](https://portal.inmet.gov.br/servicos/mapa-de-esta%C3%A7%C3%B5es-meteorol%C3%B3gicas)
- [Embrapa](https://www.embrapa.br/)
- [CEMADEN](https://www.gov.br/cemaden/pt-br)
- [MapBiomas Brazil](https://brasil.mapbiomas.org/)
- [MMA interactive maps and INDE](https://www.gov.br/mma/pt-br/acesso-a-informacao/informacoes-ambientais/mapas-interativos)
- [EMBRAPII](https://embrapii.org.br/)
- [FINEP](https://www.finep.gov.br/)
- [FAPESP cooperation agreements](https://www.fapesp.br/acordos/)
- [Petrobras Open Innovation](https://petrobras.com.br/inovacao-e-tecnologia/inovacao-aberta)

---

**Contact and authorship:** complete with the project's chosen public contact channel before distributing this document externally. Do not invent a personal or institutional email address.
