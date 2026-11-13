"""Brazil-focused GUMA Atlas reference catalog.

Coordinates are illustrative reference points, not official biome geometries.
"""
BIOMES = [
    {"name_pt":"Amazônia","name_en":"Amazonia","lat":-3.4653,"lon":-62.2159,
     "summary_pt":"Maior bioma brasileiro, com florestas tropicais, rios extensos e grande diversidade de ambientes. A sazonalidade hidrológica e as pressões de uso da terra variam regionalmente.",
     "summary_en":"Brazil's largest biome, with tropical forests, extensive rivers and highly diverse environments. Hydrological seasonality and land-use pressures vary regionally."},
    {"name_pt":"Caatinga","name_en":"Caatinga","lat":-9.4,"lon":-40.5,
     "summary_pt":"Bioma exclusivamente brasileiro, marcado por forte sazonalidade das chuvas, vegetação adaptada à semiaridez e grande diversidade de paisagens.",
     "summary_en":"A biome exclusive to Brazil, marked by strongly seasonal rainfall, vegetation adapted to semi-arid conditions and diverse landscapes."},
    {"name_pt":"Cerrado","name_en":"Cerrado","lat":-15.8,"lon":-47.9,
     "summary_pt":"Savana tropical com mosaico de formações campestres, savânicas e florestais; abriga importantes nascentes e áreas agrícolas.",
     "summary_en":"A tropical savanna mosaic of grassland, savanna and forest formations; it contains important headwaters and major agricultural areas."},
    {"name_pt":"Mata Atlântica","name_en":"Atlantic Forest","lat":-20.3,"lon":-42.5,
     "summary_pt":"Conjunto de formações florestais e ecossistemas associados ao longo da faixa atlântica, com elevada biodiversidade e intensa transformação histórica da paisagem.",
     "summary_en":"A set of forest formations and associated ecosystems along Brazil's Atlantic region, with high biodiversity and extensive historical landscape transformation."},
    {"name_pt":"Pampa","name_en":"Pampa","lat":-30.2,"lon":-54.3,
     "summary_pt":"Predominam campos naturais e paisagens campestres no extremo sul do Brasil; conservação e manejo de pastagens nativas são temas centrais.",
     "summary_en":"Natural grasslands and open landscapes dominate in southern Brazil; conservation and management of native grasslands are central themes."},
    {"name_pt":"Pantanal","name_en":"Pantanal","lat":-19.2,"lon":-56.6,
     "summary_pt":"Grande planície sazonalmente inundável, cuja dinâmica ecológica depende do pulso anual de cheias e secas.",
     "summary_en":"A vast seasonally flooded plain whose ecological dynamics depend on the annual flood-and-drought pulse."},
]

AGRICULTURAL_HUBS = [
    {"name_pt":"Sorriso · MT","name_en":"Sorriso · MT","lat":-12.542,"lon":-55.721,
     "context_pt":"Município de referência no norte de Mato Grosso, em região de produção de grãos.",
     "context_en":"Reference municipality in northern Mato Grosso, in a major grain-producing region."},
    {"name_pt":"Rio Verde · GO","name_en":"Rio Verde · GO","lat":-17.792,"lon":-50.919,
     "context_pt":"Polo agroindustrial do sudoeste goiano, com produção diversificada de grãos e proteína animal.",
     "context_en":"Agroindustrial hub in southwestern Goiás, with diversified grain and animal-protein production."},
    {"name_pt":"Luís Eduardo Magalhães · BA","name_en":"Luís Eduardo Magalhães · BA","lat":-12.096,"lon":-45.787,
     "context_pt":"Centro urbano e agrícola do oeste baiano, associado à produção mecanizada de grãos e fibras.",
     "context_en":"Urban and agricultural center in western Bahia, associated with mechanized grain and fiber production."},
    {"name_pt":"Petrolina · PE","name_en":"Petrolina · PE","lat":-9.389,"lon":-40.503,
     "context_pt":"Polo do Vale do São Francisco, conhecido pela fruticultura irrigada.",
     "context_en":"São Francisco Valley hub known for irrigated fruit production."},
    {"name_pt":"Cascavel · PR","name_en":"Cascavel · PR","lat":-24.955,"lon":-53.455,
     "context_pt":"Centro regional do oeste paranaense, em paisagem agrícola diversificada.",
     "context_en":"Regional center in western Paraná, in a diversified agricultural landscape."},
]


DATA_LAYERS = {
    "ana_bho_part1": {
        "name": "ANA Base Hidrográfica Ottocodificada (BHO), part 1",
        "source": "Agência Nacional de Águas e Saneamento Básico (ANA)",
        "status": "live_wms",
        "vintage_or_scale": "Multiscale reference dataset, 2012; part 1 covers Otto basins 1, 2 and 3",
        "limitations": "Not a complete national layer by itself; not real-time river flow or water availability.",
        "service_url": "https://portal1.snirh.gov.br/server/services/dados_abertos/Hidrografia_Parte_1/MapServer/WMSServer",
    },
    "icmbio_protected_areas": {
        "name": "Conservation units boundaries",
        "source": "ICMBio / INDE",
        "status": "linked_not_ingested",
        "vintage_or_scale": "Current WMS/WFS service catalog; dataset-specific dates must be checked per layer",
        "limitations": "Layer name, national coverage and current geometry vintage must be verified before rendering in-app.",
        "service_url": "https://geoservicos.inde.gov.br/geoserver/ICMBio/ows",
    },
    "ibge_biomes": {
        "name": "Biomes and Coastal-Marine System",
        "source": "IBGE",
        "status": "linked_not_ingested",
        "vintage_or_scale": "Official product compatible with 1:250,000 scale",
        "limitations": "Current in-app markers are illustrative points, not official polygon boundaries.",
        "service_url": "https://www.ibge.gov.br/geociencias/informacoes-ambientais/vegetacao/15842-biomas.html",
    },
    "mapbiomas_land_cover": {
        "name": "Annual land cover and land use",
        "source": "MapBiomas",
        "status": "linked_not_ingested",
        "vintage_or_scale": "Annual collections; consult platform for current collection and reference year",
        "limitations": "Not yet ingested as a native raster layer; collection and methodology must accompany analysis.",
        "service_url": "https://plataforma.brasil.mapbiomas.org/",
    },
}

def validate_atlas_catalog():
    if len(BIOMES) != 6:
        raise ValueError("The Brazilian terrestrial-biome catalog must contain six entries.")
    names = [item["name_pt"] for item in BIOMES]
    if len(names) != len(set(names)):
        raise ValueError("Biome names must be unique.")
    for item in BIOMES + AGRICULTURAL_HUBS:
        if not (-90 <= item["lat"] <= 90 and -180 <= item["lon"] <= 180):
            raise ValueError("Atlas coordinates must be valid geographic coordinates.")
        for key in ("name_pt", "name_en"):
            if not item.get(key):
                raise ValueError(f"Missing required atlas field: {key}")
    return True
