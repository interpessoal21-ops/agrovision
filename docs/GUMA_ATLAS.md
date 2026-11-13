# GUMA Atlas — Brazil

## Scope of the first release

The Brazil Atlas is an exploratory geographic interface that combines selectable basemaps with two point-reference overlays:

1. Six illustrative biome reference locations, corresponding to the six terrestrial biomes recognized by IBGE.
2. Selected agricultural reference hubs to help orient the user to major agricultural regions.

Basemaps currently available in the app:
- OpenStreetMap street map.
- Esri World Imagery satellite basemap.
- OpenTopoMap topographic basemap.

## Important geographic limitation

The biome coordinates are illustrative reference points. They are not official biome boundaries, polygons, centroids calculated from official geometries, municipal limits, farm boundaries or a spatial classification. The agricultural hubs are examples, not a complete directory, production ranking or evidence of output. Satellite basemaps are visual context and are not a current land-cover classification.

The first release links users to authoritative sources rather than pretending their thematic datasets are already integrated as live analytical layers:

- IBGE's *Biomas e Sistema Costeiro-Marinho do Brasil*, compatible with 1:250,000 scale: https://www.ibge.gov.br/geociencias/informacoes-ambientais/vegetacao/15842-biomas.html
- INPE TerraBrasilis, for PRODES, DETER and vegetation monitoring: https://www.terrabrasilis.dpi.inpe.br/
- MapBiomas, for annual land-cover and land-use mapping and thematic monitors: https://brasil.mapbiomas.org/

PRODES and DETER must not be conflated: they have distinct purposes and update cycles. The INPE portal describes its products as geographic monitoring information; the presence of a mapped change does not by itself determine its legality.

## Next technical stages

Before adding official analytical overlays, each layer must have:
- A verified service endpoint and layer identifier.
- Source institution, dataset version and retrieval date.
- Spatial reference system, scale or pixel resolution.
- Temporal coverage and update frequency.
- License and attribution requirements.
- Quality-control and interpretation notes.
- A graceful unavailable-data state and tests for parsing and geometry validity.

Candidate layers: official biome polygons, protected areas, hydrography, elevation, land cover, fire scars, vegetation suppression and agricultural production. Integrations should be incremental and must preserve provenance.
