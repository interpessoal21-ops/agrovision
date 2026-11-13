# Rotation Lab — prototype method and limitations

## Purpose
The Rotation Lab adds a transparent comparison of crop-sequence weather windows to AGROVISION. It is an exploratory decision-support prototype, not a calibrated crop model or a planting recommendation.

## Scenarios
- A: soybean main-season window; the remainder is not modeled as a cover crop.
- B: soybean followed by a second-season maize window.
- C: the same cash-crop windows as B, with Brachiaria shown only as a management overlay. Brachiaria growth, water use, biomass and soil effects are not simulated.

The cycle lengths use rounded midpoints of the indicative ranges already documented in `app.py`: soybean 135–150 days and maize 125–180 days. These are not cultivar-specific calendars.

## Inputs and calculations
- NASA POWER daily precipitation and near-surface air temperature for complete crop windows.
- Optional MODIS/Terra MOD13Q1 NDVI observations overlapping each window, with the existing app's quality-screened data.
- User-entered local context (soil texture, fertility and water regime) is displayed but is not treated as a measured hydraulic property.

Only complete windows with at least 95% non-missing precipitation and temperature records are retained. Rainfall is summed over each crop window; temperature is averaged. MODIS NDVI is averaged over available overlapping composites. Sequence summaries aggregate crop-window rainfall and average temperature by season.

## Critical interpretation
- Rainfall is not effective rainfall and is not a soil-water balance.
- MODIS NDVI is regional/pixel vegetation context, not crop identification.
- No yield, profit, soil-carbon, soil-health, biomass or water-saving benefit is predicted.
- Scenario C does not simulate Brachiaria.
- No scenario receives a composite score or automated recommendation.
- Check the exact current MAPA ZARC combination for municipality, crop, cultivar group, soil class, management and sowing dekad before any real-world use.

## Next validation steps
1. Unit-test date windows, missing records and aggregation.
2. Compare POWER variables with quality-controlled station observations where available.
3. Review crop-cycle assumptions with an agronomist and replace generic cycle lengths with locally justified cultivar/management values.
4. Obtain laboratory soil properties before using a root-zone water balance in rotation comparisons.
5. Compare the interpretation against multi-season field records before claiming agronomic performance.

## Data provenance
- NASA POWER Daily API: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
- MODIS/Terra MOD13Q1 via ORNL DAAC: https://modis.ornl.gov/data/modis_webservice.html
- FAO-56: https://www.fao.org/4/X0490E/X0490E00.htm
- MAPA ZARC: https://dados.agricultura.gov.br/dataset/tabua-de-risco-zoneamento-agricola-de-risco-climatico
- Embrapa crop and production-system references: https://www.embrapa.br/
