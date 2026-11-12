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

### Stage B — Water balance
Implement FAO-56 reference evapotranspiration (FAO Penman–Monteith) only when all required meteorological variables and units are available and quality checked. Apply crop coefficients (Kc) by growth stage, rooting depth and depletion fraction, and a documented soil-water capacity. Maintain a daily root-zone water balance with effective rainfall, irrigation, runoff/drainage assumptions and stress coefficient. Never equate gross rainfall with effective rainfall or crop water use.
Reference:
- Allen et al. (1998), FAO Irrigation and Drainage Paper 56: https://www.fao.org/4/X0490E/X0490E00.htm

### Stage C — Field validation
Build a versioned, independent dataset with observed planting/harvest dates, cultivar, management, soil test, irrigation, weather, phenology and measured yield. Split by location and year (not random rows) into calibration and holdout sets to avoid spatial/temporal leakage. Report sample size, missingness, bias, MAE, RMSE, R² and uncertainty intervals by crop, region and season. Compare against a simple baseline. Do not publish performance claims until holdout results are reproducible.

### Stage D — Rotation-system validation
Evaluate multi-season sequences with measured soil indicators and field outcomes. Include cover-crop residue, nitrogen inputs/removal, pest/disease pressure, water balance and operational constraints. Compare against local conventional practice and report uncertainty. A crop rotation recommendation requires multi-year field evidence.

## 4. Current automated tests

The tests/test_validation.py suite checks perfect agreement, positive bias/missing-pair handling and the minimum paired sample requirement. These are software unit tests for metric calculations; they are not agronomic validation.

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
