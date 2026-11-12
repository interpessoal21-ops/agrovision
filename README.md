# AGROVISION

**Early-stage agricultural climate-screening platform using NASA Earth-observation data and published crop references.** Built for the NASA Space Apps Challenge 2026; scientific validation is in progress.

## Current capabilities

- Bilingual interface: English and Portuguese.
- Interactive study-area map with latitude/longitude input.
- NASA POWER daily climate data for 2020–2025.
- MODIS/Terra MOD13Q1 16-day vegetation observations for a selectable year range (2020–2025), with pixel-reliability filtering.
- Annual climate summaries and rainfall/temperature anomalies relative to the 2020–2025 baseline.
- Crop-specific historical climate screening for maize, soybean and common bean, using a selected sowing month and complete daily crop-cycle windows.
- Indicative crop-cycle durations and seasonal crop-water reference ranges sourced from FAO and Embrapa publications; no arbitrary crop ranking score.
- CSV export and PDF environmental report.
- Supabase email authentication and optional per-user project persistence.
- Saved projects include the queried climate and MODIS series and can be restored in the app.

## Run locally

Create a Python virtual environment, install dependencies with `pip install -r requirements.txt`, then start the app with `streamlit run app.py`.

## Data sources

- **NASA POWER Daily API:** daily near-surface air temperature, precipitation and solar radiation for the Agroclimatology community.
- **MODIS/Terra MOD13Q1 via ORNL DAAC:** 16-day vegetation-index composites and pixel-reliability data. The app first retrieves the available composite dates and splits the selected period into batches of no more than ten dates per point-subset request, respecting the ORNL service limit.

The MODIS endpoint is queried for the selected period. NDVI is computed from NIR and red reflectance using the ratio (NIR − red) / (NIR + red); the common reflectance scale factor cancels in this ratio. Only reliability flags 0 (good) and 1 (marginal) are retained for NDVI calculations.

SMAP is **not connected** in this deployment. Do not interpret any previous isolated SMAP sample as a field measurement.

## Scientific limitations

- NASA POWER and MODIS are gridded / satellite-derived products, not field sensors. A point query does not represent every part of a farm.
- NDVI is a vegetation-greenness indicator. It does not identify crop species, diagnose plant disease, or directly measure yield.
- Climate anomalies are calculated against the queried 2020–2025 period; this short baseline is not a formal climatological normal.
- Crop screening uses the midpoint of published indicative crop-cycle duration ranges to define a historical weather window. It reports observed precipitation and temperature; it does not model phenology, effective rainfall, evapotranspiration, soil-water storage, irrigation demand, yield, profitability, or crop suitability.
- FAO seasonal crop-water requirements are indicative evapotranspiration-based ranges under defined conditions. Comparing gross rainfall with those ranges is **not** a water-balance calculation.
- Crop cycle and water-need ranges vary by cultivar, region, sowing date and management. Local ZARC calendars, soil analysis, field observations and agronomist review remain necessary before planting decisions.
- Soil texture, fertility and irrigation context are user-entered assumptions.
- Validate any real-world decision with local soil tests, crop calendars, field observations and qualified agronomic advice.

## Scientific validation\n\nThe platform includes a station-observation validation workflow: upload a CSV with daily station data, select the date and observed-value columns, and compare it with NASA POWER using paired bias, MAE, RMSE and R². Missing pairs are excluded. This does not constitute universal validation; station provenance, distance, units, quality control and representativeness must be documented. See [the scientific validation protocol](docs/SCIENTIFIC_VALIDATION.md).\n\nOfficial resources: [NASA POWER DAV Validate / PRUVE](https://power.larc.nasa.gov/docs/services/api/validate/), [MAPA SISZARC](https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/siszarc), and [FAO-56](https://www.fao.org/4/X0490E/X0490E00.htm).\n\n## Crop-screening method

The crop analysis supports maize (grain), soybean and common bean (dry grain). For each selected crop, it uses the midpoint of the published indicative cycle-duration range as a representative window beginning on day one of the user-selected sowing month. Only complete windows with sufficient daily NASA POWER records are summarized. It reports historical cycle rainfall and mean air temperature by season, plus a median across available seasons. It does not rank crops or produce a recommendation.

Reference sources:
- [FAO — Crop Water Needs](https://www.fao.org/4/S2022E/s2022e07.htm): indicative crop-cycle durations, crop coefficients and seasonal water-need ranges.
- [Embrapa — Maize climate requirements](https://www.embrapa.br/web/agencia-de-informacao-tecnologica/cultivos/milho/pre-producao/caracteristicas-da-especie-e-relacoes-com-o-ambiente/relacoes-com-o-clima).
- [Embrapa — Soybean water requirements](https://www.embrapa.br/web/agencia-de-informacao-tecnologica/cultivos/soja/pre-producao/caracteristicas-da-especie-e-relacoes-com-o-ambiente/exigencias-climaticas/agua).
- [Embrapa — Common bean climate requirements](https://www.embrapa.br/web/agencia-de-informacao-tecnologica/cultivos/feijao/pre-producao/clima).

## Supabase setup: save projects

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
