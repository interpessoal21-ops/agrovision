# AGROVISION — Scientific validation protocol

**Status:** validation workflow implemented; scientific validation results are not yet established.

## 1. Scope and claims

AGROVISION currently summarizes historical environmental observations and provides an initial crop-specific climate screen for maize, soybean and common bean. It must not claim calibrated yield prediction, crop suitability, irrigation prescription, or validated rotation optimization.

The application separates:
- **Data verification:** completeness, units, temporal coverage, geolocation and quality flags.
- **Environmental-data validation:** comparison of NASA POWER against independent ground observations.
- **Agronomic-model validation:** comparison of model outputs against independent field observations, which has not yet been performed.

## 2. NASA POWER validation

The new Scientific validation tab accepts a user-supplied CSV with daily station observations. It aligns observations by calendar date and calculates:
- Bias = mean(POWER − station)
- MAE = mean absolute error
- RMSE = square root of mean squared error
- R² = 1 − SSE/SST (only when station observations have non-zero variance)
- Number of paired observations

Missing pairs are excluded, not imputed. The workflow requires at least three valid pairs. This is a transparent local comparison, not a universal validation. Record station identifier, coordinates, elevation, instrument, source, quality-control procedure, period and distance from the requested point. Match the variable, units and daily aggregation before interpreting metrics.

NASA's official DAV Validate / PRUVE service can independently identify qualifying surface stations and report bias, RMSE, slope, intercept and R². Coverage is not guaranteed for every parameter or location; station gaps and representativeness must be reported:
https://power.larc.nasa.gov/docs/services/api/validate/

## 3. Agronomic validation roadmap

### Stage A — ZARC compatibility
Use the current MAPA ZARC/SISZARC publications for the selected municipality, crop, cultivar cycle, soil water-availability class, management/climate group and season. Do not infer a planting window from month-of-year averages. Store publication/portaria, crop, UF, municipality, soil class, cultivar group, risk level (20/30/40%) and source date with every lookup.
Official sources:
- https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/siszarc
- https://mapa-indicadores.agricultura.gov.br/publico/extensions/Zarc/Zarc.html
- https://dados.agricultura.gov.br/dataset/tabua-de-risco-zoneamento-agricola-de-risco-climatico

### Stage B — Water balance (implemented as an exploratory module)

The application now calculates daily FAO-56 reference evapotranspiration (ET0) with the Penman–Monteith equation from NASA POWER T2M, T2M_MAX, T2M_MIN, T2MDEW, WS2M and ALLSKY_SFC_SW_DWN. Solar radiation is converted from kWh/m²/day to MJ/m²/day. User-entered site elevation and selected latitude are used for atmospheric pressure and extraterrestrial/clear-sky radiation terms. Missing required weather inputs are not imputed; a season is excluded if the required daily values are incomplete.

Crop evapotranspiration is estimated as ETc = Kc × ET0 using a user-configurable four-stage Kc curve (initial, development, mid-season and late-season). Generic FAO-56 Table 12 reference Kc values are offered as editable starting points, not cultivar-specific recommendations. The stage durations are illustrative proportions unless replaced with local crop/cultivar phenology.

A one-layer root-zone bucket tracks total available water (TAW = available water × effective root depth), readily available water (RAW = p × TAW), depletion and the FAO stress coefficient Ks. It reports potential ETc, estimated actual ETa, water deficit, depletion and an idealized supplemental-irrigation trigger/refill scenario. Soil available water, effective rooting depth, p, initial storage and irrigation efficiency are explicit user inputs. The allowed 34–184 mm/m available-water range corresponds to the MAPA-published 0.34–1.84 mm/cm interval; users should derive the actual value from their soil analysis / official ZARC calculator rather than use the placeholder default.

**Important simplifications:** precipitation is treated as infiltrating until field capacity; runoff is not separately modeled. The current model omits capillary rise, lateral flow, salinity, changing root depth, layered soil, measured hydraulic properties and crop-specific stress response. The irrigation trigger is a scenario, not an irrigation prescription. This is not the official ZARC SARRA model and has not been calibrated against field observations.

The ZARC section links to the current MAPA SISZARC and risk-indication panel. It allows a user to transcribe the official municipality/crop/cultivar/soil/risk/dekadal result and checks crop + sowing-dekad consistency with the water-balance scenario. It does not query an official API or independently verify the transcribed publication. MAPA explains that ZARC evaluates climate, soil water availability and crop phenology, and publishes soil available-water classes; those local details must be confirmed before interpreting the scenario.

References:
- Allen et al. (1998), FAO Irrigation and Drainage Paper 56: https://www.fao.org/4/X0490E/X0490E00.htm
- FAO-56 crop coefficient tables (Chapter 6): https://www.fao.org/4/X0490E/x0490e0b.htm
- FAO Penman–Monteith method: https://www.fao.org/4/x0490e/x0490e06.htm
- MAPA ZARC/SISZARC: https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/siszarc
- MAPA soil available-water classes: https://www.gov.br/agricultura/pt-br/assuntos/riscos-seguro/programa-nacional-de-zoneamento-agricola-de-risco-climatico/classificacao-de-solo

### Stage C — Field validation
Build a versioned, independent dataset with observed planting/harvest dates, cultivar, management, soil test, irrigation, weather, phenology and measured yield. Split by location and year (not random rows) into calibration and holdout sets to avoid spatial/temporal leakage. Report sample size, missingness, bias, MAE, RMSE, R² and uncertainty intervals by crop, region and season. Compare against a simple baseline. Do not publish performance claims until holdout results are reproducible.

### Stage D — Rotation-system validation
Evaluate multi-season sequences with measured soil indicators and field outcomes. Include cover-crop residue, nitrogen inputs/removal, pest/disease pressure, water balance and operational constraints. Compare against local conventional practice and report uncertainty. A crop rotation recommendation requires multi-year field evidence.

## 4. Current automated tests

The tests/test_validation.py suite checks validation metrics. The tests/test_agronomy.py suite checks FAO-56 ET0 behavior, Kc curve length/stages, water-bucket bounds and irrigation-trigger behavior. These are software unit tests; they are not field validation or proof of agronomic accuracy.

GitHub Actions compiles the application and runs these tests on pushes and pull requests.

## 5. Release gates

Do not label AGROVISION scientifically validated until:
1. Source data and station provenance are traceable.
2. Data-quality checks and unit tests pass.
3. NASA POWER validation is reported by variable, station, location and period.
4. ZARC lookups match current official publications.
5. Water-balance calculations are benchmarked against published FAO-56 worked examples.
6. Crop/rotation outputs are evaluated against independent field observations and holdout data.
7. Limitations, parameter versions and uncertainty are visible to users.
