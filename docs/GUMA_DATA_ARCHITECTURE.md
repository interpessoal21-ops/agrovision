# GUMA Global Data Architecture

## Product scope
GUMA is a global Earth intelligence platform. Brazil is an important regional use case and pilot context, never the geographic limit. Global datasets and schemas support WGS84 coordinates, country ISO-3 identifiers, global/admin geographic hierarchies, and explicit source coverage metadata.

## Data governance
1. Every observation keeps source, URL, identifier, units, period, retrieval time and quality notes.
2. Raw measurements are distinct from derived indicators and interpretation.
3. Missing observations are never replaced with fabricated zeros.
4. Search windows are not cadastral or administrative boundaries.
5. Satellite tile cloud cover is not cloud share inside a field polygon.
6. An active-fire detection is not automatically a confirmed fire perimeter or cause.
7. Global coverage is the default schema scope; national datasets declare their actual coverage.
8. Timestamps are UTC unless source metadata states otherwise.

## Integrations
- Element 84 Earth Search: global Sentinel-2 L2A STAC discovery.
- NASA FIRMS: global NOAA-20 VIIRS rolling 7-day CSV. Static file endpoint is public; FIRMS area API is separate and requires a free MAP_KEY.
- IBGE: Brazil-only localities source, explicitly scoped.
- Firecrawl is available to the assistant, not automatically to the public Streamlit runtime; app calls public endpoints directly without connector credentials.

## MotherDuck
The connected account database contains schema guma with source registry, global geographic units, indicator observations, satellite scenes, fire detections, scientific evidence and ingestion logs. Seeded sources distinguish global Sentinel-2 and FIRMS from Brazil-only IBGE.

## App integrations
- guma_earth_data.py: global Sentinel-2 scene search, global FIRMS 7-day observations with optional WGS84 bounding-box filtering, Brazil-only IBGE state lookup.
- pages/02_Earth_Data_Observatory.py: global satellite scene search, global fire map/table/download, custom spatial window and explicitly national IBGE tab.

## Scientific limitations
- Sentinel-2 currently returns scene metadata, not pixel-derived vegetation indices.
- Tile cloud percentage is not a parcel-level cloud mask.
- FIRMS hotspots do not independently establish burned area, fire perimeter or cause.
- Custom bounding boxes are not administrative boundaries.
- IBGE is not a global source.

## Next milestones
1. Add global country/admin boundaries with version/license metadata.
2. Add global climate reanalysis and station observations with resolution distinctions.
3. Add global land-cover products; regional products such as MapBiomas and PRODES remain labelled complements.
4. Ingest validated global observations into MotherDuck with idempotent keys, source hashes and ingestion logs.
5. Validate pixel-level Sentinel-2 indices with cloud masking and independent references.
6. Continue Challenge 02 trend detection, documenting autocorrelation, multiple testing, missingness and uncertainty.
