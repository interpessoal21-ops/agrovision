# GUMA Data Architecture — first operational integrations

## Principles

1. Every observation keeps its source, source URL, source identifier, units, period, retrieval time and quality notes.
2. Raw measurements are distinct from derived indicators and interpretation.
3. No missing observation is replaced with a fabricated zero.
4. Spatial search windows are not cadastral boundaries.
5. Satellite tile cloud cover is not the same as cloud share inside a field polygon.
6. A satellite active-fire detection is not automatically a confirmed fire perimeter or cause.
7. The NASA Space Apps Challenge 02 trend-analysis work remains the analytical priority.

## Connectors available in the ChatGPT work environment

### Firecrawl / Alexandria

Successfully tested:
- Element 84 Earth Search: Sentinel-2 L2A scene availability and scene search.
- NASA FIRMS: NOAA-20 VIIRS South America active-fire records, 24-hour file.
- IBGE service-data provider: documented capabilities for localities, SIDRA aggregates and territorial meshes. Calls returned HTTP 503/504 during the first test; retry through the direct public API from the deployed app.

The Firecrawl connector is available to the assistant, not automatically to the public Streamlit runtime. The app page therefore uses documented public endpoints directly and does not expose Firecrawl credentials.

### MotherDuck

The account connection is active. Databases discovered: `my_db` and shared `sample_data`. Both currently return zero tables/views. A read-only query confirms the `my_db` database connection.

No schema or tables have been created. MotherDuck write actions require separate confirmation. A proposed schema is staged in `sql/001_guma_core_schema.sql`.

## Implemented app integrations

- `guma_earth_data.py`: validated helpers for Sentinel-2 STAC scene discovery, NASA FIRMS NOAA-20 VIIRS CSV loading and IBGE state-locality lookup.
- `pages/02_Earth_Data_Observatory.py`: branded Streamlit page with scene search, active-fire observations, state-code lookup, CSV exports and limitations.

## Data products tested

### Sentinel-2 / Earth Search
A discovery window over a small Cerrado-area polygon (15.785° S, 47.875° W) for 2026-10-01 to 2026-11-14 returned 51 tile-level scene matches across the available collection. A scene search returned 24 matches, five shown, with tile cloud cover. The scene counts are per MGRS tile, so one acquisition may appear more than once when the search intersects tile edges.

This test validates metadata discovery only. Field-level NDVI/EVI/NDMI pixel calculations have not yet been validated in the connector workflow.

### NASA FIRMS
The South America NOAA-20 VIIRS 24-hour file returned 100 records on the first page, with publication ID and SHA-256 metadata. This is a paginated publication; a page of 100 is not the total count for South America. The app applies a coarse Brazil bounding-box filter and explicitly warns that this is not a precise national boundary.

### IBGE
The Alexandria provider was unavailable during initial live calls (HTTP 503/504). The public IBGE Localities endpoint is used in the app for state codes. Population aggregates, municipal area and territorial meshes remain planned until live schema and coverage validation.

## MotherDuck schema proposal

See `sql/001_guma_core_schema.sql`. It defines:
- source registry;
- IBGE territorial units;
- time-series indicator observations;
- satellite scene metadata;
- active-fire detections;
- scientific evidence records.

The SQL is a proposal only and has not been executed.

## Next scientific milestones

1. Validate the public IBGE API calls and metadata for municipal population / GDP.
2. Ingest a small, cited pilot table into MotherDuck after the user approves the schema.
3. Validate field-level Sentinel-2 vegetation-index calculations with cloud masking and an independent reference.
4. Add temporal trend analysis with Mann–Kendall and Sen slope, documenting autocorrelation and multiple-testing limitations.
5. Add MapBiomas annual land-cover statistics and INPE PRODES/DETER products as separate, clearly labelled datasets.
