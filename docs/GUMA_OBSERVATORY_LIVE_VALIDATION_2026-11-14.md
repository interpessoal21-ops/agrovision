# GUMA — Earth Data Observatory live validation

**Validation date:** 2026-11-14  
**Public application:** https://agrovision-mnxorykmgeisybvcnufu2q.streamlit.app/  
**Page:** Earth Data Observatory  
**Execution mode:** live browser interaction against the published Streamlit application  
**Status:** 3 source queries returned data; 1 source query failed at the provider connection layer.

## Published page / deployment check

- The public `Earth Data Observatory` page loaded.
- The earlier `ImportError` was no longer present.
- All five tabs rendered: Sentinel-2 global search, NASA FIRMS global fire, NASA POWER climate, IBGE Brazil, Methods & sources.

## 1. Sentinel-2 — successful

- **Provider/catalogue:** Element 84 Earth Search STAC
- **Collection:** `sentinel-2-c1-l2a`
- **Query geometry:** point-centred rectangular search window around latitude `-15.8`, longitude `-47.0`; app implementation uses ±0.08°.
- **Date window:** 2026-10-01 through 2026-11-14
- **Maximum tile cloud cover:** 40%
- **Returned matches:** 5
- **Returned tile:** `MGRS-23LKC` in all five rows
- **Important limitation:** these are catalogue scene/tile matches and scene-level cloud estimates, not field-level cloud cover or pixel-derived NDVI/EVI/NDMI.

| Scene ID | Acquisition UTC | Platform | Tile cloud cover |
|---|---|---|---:|
| S2C_T23LKC_20261104T132228_L2A | 2026-11-04 13:26:39 | sentinel-2c | 33.609894% |
| S2B_T23LKC_20261020T132612_L2A | 2026-10-20 13:26:43 | sentinel-2b | 6.682612% |
| S2A_T23LKC_20261017T132243_L2A | 2026-10-17 13:26:54 | sentinel-2a | 8.828856% |
| S2B_T23LKC_20261010T132231_L2A | 2026-10-10 13:26:43 | sentinel-2b | 3.450320% |
| S2A_T23LKC_20261007T132245_L2A | 2026-10-07 13:26:55 | sentinel-2a | 0.001338% |

- **Source endpoint:** https://earth-search.aws.element84.com/v1/search
- **Collection/item provenance:** https://earth-search.aws.element84.com/v1/collections/sentinel-2-c1-l2a/items/
- **Interface source link:** Element 84 Earth Search STAC.

## 2. NASA FIRMS — successful

- **Provider/product:** NASA FIRMS, NOAA-20 VIIRS, rolling global 24-hour CSV.
- **Geographic filter:** custom WGS84 bounding box:
  - West: -48.0°
  - South: -16.5°
  - East: -46.0°
  - North: -15.0°
- **Returned detections in selected box:** 2
- **Acquisition UTC range:** 2026-11-13 17:02:00 through 2026-11-14 04:10:00.
- **Columns displayed:** `acquired_at_utc`, `latitude`, `longitude`, `confidence`, `frp`, `bright_ti4`, `satellite`.

| Acquired at UTC | Latitude | Longitude | Confidence | FRP (MW) | Brightness TI4 | Satellite |
|---|---:|---:|---|---:|---:|---|
| 2026-11-14 04:10:00 | -15.56716 | -47.85581 | nominal | 1.31 | 304.31 | N20 |
| 2026-11-13 17:02:00 | -15.36162 | -47.35870 | nominal | 4.64 | 344.79 | N20 |

- **Source endpoint:** https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_24h.csv
- **Interpretation caveat:** an active-fire detection is a thermal anomaly observation, not automatically a confirmed fire perimeter, burned area, cause, or impact estimate.
- **Scope caveat:** the two detections are the rows inside the selected bounding box, not the global total.

## 3. NASA POWER — successful

- **Provider/community:** NASA POWER, Agroclimatology (`AG`).
- **Coordinates:** latitude -15.8°, longitude -47.0°.
- **Date window:** 2026-10-10 through 2026-11-09.
- **Temporal resolution:** daily.
- **Valid rows:** 31.
- **Displayed metrics:** mean `T2M` = 28.1 °C; accumulated `PRECTOTCORR` = 136.8 mm.
- **Returned parameters:** `T2M`, `T2M_MAX`, `T2M_MIN`, `T2MDEW`, `WS2M`, `PRECTOTCORR`, `ALLSKY_SFC_SW_DWN`.
- **Retrieved at UTC:** 2026-11-14T15:37:23.375656+00:00.
- **Source endpoint:** https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M%2CT2M_MAX%2CT2M_MIN%2CT2MDEW%2CWS2M%2CPRECTOTCORR%2CALLSKY_SFC_SW_DWN&community=AG&longitude=-47.0&latitude=-15.8&start=20261010&end=20261109&format=JSON
- **Spatial limitation shown in app:** meteorological grid approximately 0.5° × 0.625°; solar grid approximately 1° × 1°. Not field-scale or station observations.
- **Metadata issue to fix:** the provenance JSON in the live page returned an empty `units` object (`{}`) even though the UI displays metric units for temperature and precipitation. The parameter-unit dictionary should be populated from authoritative NASA POWER parameter metadata and tested before the presentation.

## 4. IBGE — attempted, failed at connection

- **Provider:** IBGE Localities API.
- **Requested dataset:** Brazilian federative units (states).
- **Source endpoint:** https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome
- **Interface action:** `Load Brazilian state codes`, attempted twice.
- **Result:** no rows returned.
- **Exact failure:** HTTPS connection timeout to `servicodados.ibge.gov.br:443`; request timeout reported by the application was 30 seconds.
- **No data was fabricated or substituted.**
- **Interpretation:** the public app and tab work, but this live source query is not validated. This may be a transient provider/network egress problem; the current evidence does not distinguish those causes.

## Overall acceptance status

| Check | Result |
|---|---|
| Published Observatory page loads | PASS |
| Previous ImportError resolved in public app | PASS |
| Sentinel-2 query via interface | PASS — 5 matches |
| NASA FIRMS query via interface | PASS — 2 detections in selected bbox |
| NASA POWER query via interface | PASS — 31 daily rows |
| IBGE query via interface | FAIL — provider connection timeout |
| NASA POWER provenance unit dictionary | NEEDS FIX |
| Full Observatory acceptance | NOT YET PASSED |

## Next corrective actions

1. Diagnose IBGE connectivity from Streamlit Cloud and add a transparent retry/fallback strategy only if it preserves source provenance.
2. Populate and test NASA POWER parameter units in provenance metadata.
3. Re-run the IBGE and POWER checks after the code changes.
4. Only then mark the Observatory accepted for the Space Apps presentation.

**Scientific integrity rule:** source unavailability, empty search results, and zero detections must remain distinct states. Do not replace missing data with plausible-looking values.
