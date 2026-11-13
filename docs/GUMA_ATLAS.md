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


## Official thematic layer integration status

The Atlas now exposes the ANA Base Hidrográfica Ottocodificada (BHO) part 1 as an optional live WMS overlay. The service describes a multiscale hydrographic network built from Brazilian systematic mapping, with connected river reaches and Otto-Pfafstetter drainage basins. Part 1 covers Otto basins 1, 2 and 3 only; it is not a complete national layer. Its documented reference vintage is 2012. It must not be interpreted as real-time river-flow monitoring or current water availability. Service metadata: https://portal1.snirh.gov.br/server/rest/services/dados_abertos/Hidrografia_Parte_1/MapServer?f=pjson

Other official datasets are linked but not rendered as map layers yet:
- **ICMBio / INDE protected areas:** WMS/WFS capabilities: https://geoservicos.inde.gov.br/geoserver/ICMBio/ows?service=wms&version=1.3.0&request=GetCapabilities and https://geoservicos.inde.gov.br/geoserver/ICMBio/ows?service=wfs&version=2.0.0&request=GetCapabilities. Verify layer names, national coverage and dataset date before adding an overlay.
- **IBGE biome boundaries:** authoritative product compatible with 1:250,000 scale: https://www.ibge.gov.br/geociencias/informacoes-ambientais/vegetacao/15842-biomas.html. Current biome points remain illustrative.
- **MapBiomas land cover:** annual maps and thematic products: https://plataforma.brasil.mapbiomas.org/. Native raster ingestion is pending; collection and reference year must be explicit.

The DATA_LAYERS catalog records source, integration status, vintage/scale and limitations.
