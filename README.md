# GUMA — Earth Intelligence

**GUMA is an Earth-intelligence platform connecting climate, Earth observation, agricultural systems and collaborative research.** Built for the NASA Space Apps Challenge 2026; scientific validation is in progress.

The name is inspired by Guma, the character in Jorge Amado's *Mar Morto*. Its visual identity draws on the sea, navigation and the horizon. This is an independent cultural inspiration, not an official association with the author or publisher. See [the GUMA brand system](docs/GUMA_BRAND.md).

## Institutional collaboration

The [GUMA Institutional Kit](docs/GUMA_INSTITUTIONAL_KIT.md) contains the project brief, technical architecture, scientific-validation pilot, partnership model, demonstration script, outreach templates and a proposed 90-day roadmap. All listed organizations are prospective contacts only; no partnership or endorsement is implied.

## Current capabilities

- Bilingual interface: English and Portuguese.
- Interactive study-area map with OpenStreetMap, Esri satellite imagery and topographic basemap layers (visual context only; no inferred farm boundary).
- **Global Earth Data Observatory:** global Sentinel-2 L2A scene discovery through the public Earth Search STAC API; NASA POWER daily global agroclimatology; NASA FIRMS NOAA-20 VIIRS global rolling 24-hour active-fire observations with optional WGS84 bounding-box filtering; and a separately labelled Brazil-only IBGE territorial reference. Includes CSV exports and explicit data-quality limitations.
- NASA POWER daily climate data for 2020–2025.
- MODIS/Terra MOD13Q1 16-day vegetation observations for a selectable year range (2020–2025), with pixel-reliability filtering.
- Annual climate summaries and rainfall/temperature anomalies relative to the 2020–2025 baseline.
- Annual MODIS/NDVI summaries with quality-screened observation counts and pixel-quality breakdown.
- Integrated evidence dashboard combining climate data coverage, vegetation indicators, current-coordinate water-balance scenario and selected official ZARC reference without inventing a composite suitability score.
- Crop-specific historical climate screening for maize, soybean and common bean, using a selected sowing month and complete daily crop-cycle windows.
- Daily FAO-56 Penman–Monteith ET0 estimates using NASA POWER temperature, dew point, wind and solar-radiation inputs plus user-entered elevation.
- A transparent single-layer root-zone water-balance scenario with crop-stage Kc, soil available water, effective root depth, depletion threshold, water stress and optional idealized supplemental irrigation.
- A ZARC/MAPA reference workflow for recording official municipality, cultivar group, soil class, risk level, sowing dekad and ordinance; official lookup remains user-confirmed rather than API-verified.
- Indicative crop-cycle durations and seasonal crop-water reference ranges sourced from FAO and Embrapa publications; no arbitrary crop ranking score.
- CSV export and an integrated PDF report covering climate coverage, annual MODIS/NDVI summaries, any current-coordinate FAO-56 scenario, selected MAPA ZARC record, sources and scientific limitations.
- Supabase email authentication and optional per-user project persistence.
- Saved projects include the queried climate and MODIS series plus any recorded FAO-56 water-balance run and ZARC reference, which can be restored in the app.



## GUMA Atlas — Brazil

The **GUMA Atlas** provides a first national geographic overview with selectable OpenStreetMap, Esri satellite and OpenTopoMap basemaps; filterable illustrative reference points for Brazil's six terrestrial biomes; and example agricultural reference hubs. These markers are not official biome polygons, administrative boundaries, farm boundaries or production rankings. The tab links to authoritative geospatial portals:

- **IBGE — Biomes and Coastal-Marine System:** official delimitation compatible with 1:250,000 scale. The six terrestrial biomes are Amazonia, Caatinga, Cerrado, Atlantic Forest, Pampa and Pantanal.
- **INPE — TerraBrasilis:** geospatial monitoring products including PRODES and DETER. Their purposes and update cycles differ; DETER alerts are not equivalent to annual PRODES rates.
- **MapBiomas:** annual land-cover and land-use mapping and thematic monitors.

The current in-app atlas uses basemap tiles and illustrative point references. Official thematic polygons and analytical overlays are planned as separately sourced layers and are not yet claimed as integrated. See [IBGE Biomes](https://www.ibge.gov.br/geociencias/informacoes-ambientais/vegetacao/15842-biomas.html), [INPE TerraBrasilis](https://www.terrabrasilis.dpi.inpe.br/) and [MapBiomas](https://brasil.mapbiomas.org/).

## Climate Watch

The **Climate Watch** tab is a global climate-indicator observatory, separate from the farm-scale screening tools. It retrieves four published monthly series:

- **NASA GISS GISTEMP v4:** global land-ocean temperature anomalies from 1880 onward, relative to 1951–1980. Monthly values and annual means are displayed separately.
- **NOAA Global Monitoring Laboratory — Mauna Loa:** monthly atmospheric CO₂ station observations in ppm; this is not a global marine-surface average.
- **NOAA Global Monitoring Laboratory — CH₄:** globally averaged monthly methane from the marine-surface sampling network, in ppb; recent observations are preliminary.
- **NOAA Global Monitoring Laboratory — N₂O:** globally averaged monthly nitrous oxide from the marine-surface sampling network, in ppb; the reliable series begins in 2001 and recent observations are preliminary.

Data are cached for 24 hours and can be manually refreshed. The dashboard shows retrieval time, latest observation dates, source links, reference baseline and interpretation limits. Publication latency is expected; the indicators are not real-time telemetry. Do not compare anomaly values with different reference periods as if they were identical.

Global sea-level and ocean-heat source references are exposed in the Climate Watch tab, but those datasets are not yet ingested into its plotted time series. The NASA PO.DAAC global sea-level indicator requires authenticated data access; GUMA does not silently substitute a different series. NOAA NCEI publishes monthly global ocean heat-content fields for 0–700 m and 0–2000 m, based on in-situ subsurface observations. A Brazil-specific national extremes atlas remains pending. The current Brazil/local panel calculates transparent hot-day, heavy-rain-day and consecutive-dry-spell indicators from the selected point's NASA POWER daily series; it is not an official national climate classification or a station observation.

Local extreme-indicator thresholds are user-adjustable and the annual summary reports valid-data counts. Missing precipitation dates break dry spells. These metrics are descriptive screening statistics, not official heatwave/drought definitions or causal attribution.\n\nParser and local-extreme regression tests: `python -m unittest discover -s tests -p "test_climate_watch.py"`.

## Run locally

Create a Python virtual environment, install dependencies with `pip install -r requirements.txt`, then start the app with `streamlit run app.py`.


- **Rotation Lab (Space Apps 2026 preparation):** compares historical NASA POWER climate windows across soybean-only, soybean→maize, and soybean→maize with a Brachiaria management overlay. The Brachiaria component is not simulated; the comparison does not predict yield, soil-carbon change, profitability, or water savings. Optional MODIS NDVI is displayed only as date-overlapping vegetation context, not crop identification. See [Rotation Lab method and limitations](docs/ROTATION_LAB.md).

## Data sources

- **NASA POWER Daily API:** daily near-surface temperature, daily maximum/minimum temperature, dew-point temperature, 2 m wind speed, corrected precipitation and solar radiation for the Agroclimatology community.
- **MODIS/Terra MOD13Q1 via ORNL DAAC:** 16-day vegetation-index composites and pixel-reliability data. The app first retrieves the available composite dates and splits the selected period into batches of no more than ten dates per point-subset request, respecting the ORNL service limit.

The MODIS endpoint is queried for the selected period. NDVI is computed from NIR and red reflectance using the ratio (NIR − red) / (NIR + red); the common reflectance scale factor cancels in this ratio. Only reliability flags 0 (good) and 1 (marginal) are retained for NDVI calculations.

SMAP is **not connected** in this deployment. Do not interpret any previous isolated SMAP sample as a field measurement.

## Scientific limitations

- NASA POWER and MODIS are gridded / satellite-derived products, not field sensors. A point query does not represent every part of a farm.
- NDVI is a vegetation-greenness indicator. It does not identify crop species, diagnose plant disease, or directly measure yield.
- Climate anomalies are calculated against the queried 2020–2025 period; this short baseline is not a formal climatological normal.
- Crop screening uses the midpoint of published indicative crop-cycle duration ranges to define a historical weather window. It does not model cultivar-specific phenology, yield, profitability or crop suitability.
- The water-balance module calculates FAO-56 reference ET0 and a simplified daily root-zone bucket. Rainfall is assumed to infiltrate until field capacity; runoff, capillary rise, lateral flow, changing root depth, salinity and measured soil hydraulic properties are not represented.
- Crop coefficients, crop-stage lengths, root depth, soil available water, initial storage, elevation and irrigation efficiency require local confirmation. Generic Kc values and soil defaults are illustrative starting values, not recommendations.
- The supplemental-irrigation option is an idealized threshold/refill scenario, not an irrigation prescription. The model is not the official ZARC SARRA method.
- FAO seasonal crop-water requirements are indicative evapotranspiration-based ranges under defined conditions. Comparing gross rainfall with those ranges is **not** a water-balance calculation.
- Crop cycle and water-need ranges vary by cultivar, region, sowing date and management. Local ZARC calendars, soil analysis, field observations and agronomist review remain necessary before planting decisions.
- Soil texture, fertility and irrigation context are user-entered assumptions.
- Validate any real-world decision with local soil tests, crop calendars, field observations and qualified agronomic advice.

## FAO-56 water balance and ZARC

The water-balance workflow uses daily NASA POWER inputs (T2M, T2M_MAX, T2M_MIN, T2MDEW, WS2M and ALLSKY_SFC_SW_DWN) to estimate reference evapotranspiration with FAO-56 Penman–Monteith. Crop ET is estimated with a user-configurable Kc curve across initial, development, mid-season and late-season stages. A one-layer root-zone bucket tracks total available water (TAW), readily available water (RAW), depletion, stress coefficient (Ks), estimated actual ET and an idealized supplemental-irrigation scenario.

The ZARC section retrieves official season CSV resources from the MAPA CKAN open-data catalogue (with a direct 2026/2027 fallback), filters the exact row dimensions and displays the 36 sowing dekads. It preserves the source risk values (20, 30, 40 and 0) and attaches the selected official row to the project. The water-balance sowing dekad is checked against the selected record; users must still confirm that the farm's municipality, cultivar group, soil class, management and climate match that row.

References: [MAPA ZARC open-data risk table](https://dados.agricultura.gov.br/dataset/tabua-de-risco-zoneamento-agricola-de-risco-climatico), [MAPA SISZARC](https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/siszarc), [FAO-56](https://www.fao.org/4/X0490E/X0490E00.htm), [FAO Penman–Monteith](https://www.fao.org/4/x0490e/x0490e06.htm), [MAPA ZARC/SISZARC](https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/siszarc), [MAPA soil available-water classes](https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/classificacao-de-solo).

## Scientific validation

The platform includes a station-observation validation workflow: upload a CSV with daily station data, select the date and observed-value columns, and compare it with NASA POWER using paired bias, MAE, RMSE and R². Missing pairs are excluded. This does not constitute universal validation; station provenance, distance, units, quality control and representativeness must be documented. See [the scientific validation protocol](docs/SCIENTIFIC_VALIDATION.md).

Official resources: [NASA POWER DAV Validate / PRUVE](https://power.larc.nasa.gov/docs/services/api/validate/), [MAPA SISZARC](https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/siszarc), and [FAO-56](https://www.fao.org/4/X0490E/X0490E00.htm).

## Crop-screening method

The crop analysis supports maize (grain), soybean and common bean (dry grain). For each selected crop, it uses the midpoint of the published indicative cycle-duration range as a representative window beginning on day one of the user-selected sowing month. Only complete windows with sufficient daily NASA POWER records are summarized. It reports historical cycle rainfall and mean air temperature by season, plus a median across available seasons. It does not rank crops or produce a recommendation.

Reference sources:
- [FAO — Crop Water Needs](https://www.fao.org/4/S2022E/s2022e07.htm): indicative crop-cycle durations, crop coefficients and seasonal water-need ranges.
- [Embrapa — Maize climate requirements](https://www.embrapa.br/web/agencia-de-informacao-tecnologica/cultivos/milho/pre-producao/caracteristicas-da-especie-e-relacoes-com-o-ambiente/relacoes-com-o-clima).
- [Embrapa — Soybean water requirements](https://www.embrapa.br/web/agencia-de-informacao-tecnologica/cultivos/soja/pre-producao/caracteristicas-da-especie-e-relacoes-com-o-ambiente/exigencias-climaticas/agua).
- [Embrapa — Common bean climate requirements](https://www.embrapa.br/web/agencia-de-informacao-tecnologica/cultivos/feijao/pre-producao/clima).

## GUMA Field Lab — community research notebook

Field Lab lets signed-in contributors publish a public research note with a hypothesis, management strategy, comparator, crop, Brazilian macroregion, season and optional contributor-reported metric values. The board supports crop/region/season filters and displays the notes with explicit "unverified community observation" status. It calculates a simple percentage difference only when both values are supplied and the reference is nonzero; this arithmetic is not a causal effect estimate.

Run `supabase/community_schema.sql` in Supabase SQL Editor to create the RLS-protected `field_lab_trials` table (the same migration also creates the Commons table). Browsing is public; publication requires email sign-in and explicit consent. Exact coordinates, personal data and raw daily records are not fields in the Field Lab table. Contributors must avoid sharing confidential or identifying information.

Field Lab now supports longitudinal follow-up entries linked to an original hypothesis: dated observations by season, stage (planting, development, harvest, post-harvest or follow-up), and comparison arm (strategy/comparator). Each update stores its own reported value, unit, method and notes, creating a chronological history without overwriting earlier observations. Updates are contributor-reported and are not automatically verified or statistically adjusted.\n\nField Lab is a hypothesis-sharing and evidence notebook, not a controlled-trial registry or peer-reviewed publication system. Contributor-reported values are not independently verified. Differences in soil, cultivar, management, weather, timing and measurement protocols can confound comparisons; do not infer causality or issue agronomic prescriptions from the board alone.

## GUMA Commons — opt-in community comparison\n\nThe Commons tab turns each loaded NASA POWER daily point series into a compact climate fingerprint: mean temperature, mean annual precipitation, annual hot-day frequency, and monthly temperature/rainfall rhythm. Signed-in users may explicitly publish this aggregate profile under a public alias and a broad Brazilian macroregion. Exact coordinates, email, farm name and raw daily records are not sent to the community table. The public board supports crop/season/region filters, a rainfall-versus-temperature climate-space plot, and a descriptive similarity distance. Similarity is not a crop-suitability, productivity or climate-risk score. Contributor labels are self-reported and not independently verified.\n\nTo enable it, run `supabase/community_schema.sql` in the same Supabase SQL Editor after the existing `supabase/schema.sql`. Publication is opt-in; browsing the board is public. Users should not enter identifying aliases or confidential farm information.\n\n## Supabase setup: save projects

Email authentication uses the Supabase Auth REST API. To enable saving and restoring projects:

1. Configure Streamlit Community Cloud → **Settings → Secrets** with the Supabase **Project URL** and **Publishable key**:

   ```toml
   SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
   SUPABASE_PUBLISHABLE_KEY = "sb_publishable_YOUR_KEY"
   ```

   Never put a Supabase Secret or service-role key in Streamlit secrets for this app or in GitHub.

2. Open the Supabase project's **SQL Editor**.
3. Copy and run the complete script in `supabase/schema.sql`.
4. In Supabase **Authentication → URL Configuration**, configure the deployed Streamlit URL as appropriate.
5. Confirm email sign-up / verification settings under **Authentication → Providers → Email**.

The SQL creates `public.farm_projects`, enables Row Level Security (RLS), and limits each signed-in user to their own rows. The app uses the signed-in user's access token for database requests. Visitor sessions cannot save projects.

Saved project payloads include the selected coordinates, user-entered farm context, climate time series and MODIS observations. These records are stored in the user's Supabase project; review your data-retention and privacy requirements before collecting real farm data.

## Deploy

Deploy this repository on Streamlit Community Cloud using `app.py` as the main file. Streamlit Community Cloud automatically rebuilds after commits to the connected GitHub branch.


## Agronomic Systems Library

The GUMA app includes an educational library explaining major agricultural production and management systems, including conventional tillage, no-till, crop rotation, succession, intercropping, ILP, ILF, IPF, ILPF, agroforestry, agroecological and organic production, irrigation, protected cultivation and hydroponics. See [the technical guide](docs/AGRONOMIC_SYSTEMS.md). The library distinguishes system types and describes operating logic, potential strengths, limitations and monitoring points; it is not an agronomic prescription.


## NASA Space Apps Challenge 2026 — primary direction

GUMA's primary challenge direction is **Challenge 02: Be An Earth System Trend Detective!** The dedicated [GUMA Trend Detective page](pages/01_Trend_Detective.py) introduces a transparent statistical workflow using NASA GISS GISTEMP v4 annual global temperature anomalies and user-supplied annual CSV series. The analysis uses Mann–Kendall and Sen's slope; see [the methodology and limitations](docs/GUMA_TREND_DETECTIVE.md).

Challenge 14, **The Earth Information Jukebox**, remains a possible complementary communication direction, not the primary product scope. GUMA is an independent project and does not claim NASA affiliation or endorsement.

The new page's original cartographic visual language is documented in [the GUMA visual direction](docs/GUMA_VISUAL_DIRECTION.md). It takes broad inspiration from Carybé's organic relationship between people and territory without copying any protected artwork.
