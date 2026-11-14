CREATE SCHEMA IF NOT EXISTS guma;
CREATE TABLE IF NOT EXISTS guma.source_registry (
 source_id VARCHAR PRIMARY KEY, source_name VARCHAR NOT NULL, provider VARCHAR NOT NULL,
 dataset_name VARCHAR NOT NULL, endpoint_url VARCHAR, license_name VARCHAR, citation_text VARCHAR,
 update_cadence VARCHAR, spatial_resolution VARCHAR, temporal_coverage VARCHAR,
 geographic_coverage VARCHAR DEFAULT 'global', accessed_at TIMESTAMPTZ,
 source_status VARCHAR DEFAULT 'catalogued'
);
CREATE TABLE IF NOT EXISTS guma.geographic_units (
 geography_id VARCHAR PRIMARY KEY, geography_code VARCHAR NOT NULL, country_iso3 VARCHAR,
 admin_level VARCHAR NOT NULL, unit_name VARCHAR NOT NULL, parent_geography_id VARCHAR,
 region_name VARCHAR, area_km2 DOUBLE, centroid_lon DOUBLE, centroid_lat DOUBLE,
 valid_from DATE, valid_to DATE, source_id VARCHAR, observed_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS guma.indicator_observations (
 observation_id VARCHAR PRIMARY KEY, source_id VARCHAR NOT NULL, geography_id VARCHAR,
 geography_code VARCHAR, country_iso3 VARCHAR, indicator_code VARCHAR NOT NULL,
 indicator_name VARCHAR NOT NULL, period_start DATE NOT NULL, period_end DATE,
 value DOUBLE, unit VARCHAR, reference_period VARCHAR, quality_flag VARCHAR,
 source_record_id VARCHAR, source_url VARCHAR, observed_at TIMESTAMPTZ NOT NULL, raw_payload JSON
);
CREATE TABLE IF NOT EXISTS guma.satellite_scenes (
 scene_id VARCHAR PRIMARY KEY, source_id VARCHAR NOT NULL, collection_name VARCHAR NOT NULL,
 platform VARCHAR, acquired_at TIMESTAMPTZ NOT NULL, tile_id VARCHAR, cloud_cover_pct DOUBLE,
 geometry_geojson JSON, item_url VARCHAR, observed_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS guma.fire_detections (
 detection_id VARCHAR PRIMARY KEY, source_id VARCHAR NOT NULL, acquired_at TIMESTAMPTZ NOT NULL,
 latitude DOUBLE NOT NULL, longitude DOUBLE NOT NULL, country_iso3 VARCHAR, satellite VARCHAR,
 instrument VARCHAR, confidence VARCHAR, fire_radiative_power_mw DOUBLE,
 brightness_temperature_k DOUBLE, publication_id VARCHAR, source_url VARCHAR,
 observed_at TIMESTAMPTZ NOT NULL, raw_payload JSON
);
CREATE TABLE IF NOT EXISTS guma.evidence_records (
 evidence_id VARCHAR PRIMARY KEY, source_id VARCHAR NOT NULL, title VARCHAR NOT NULL,
 authors VARCHAR, publication_year INTEGER, doi VARCHAR, url VARCHAR, evidence_type VARCHAR,
 geographic_scope VARCHAR DEFAULT 'global', summary VARCHAR, supports_claim BOOLEAN,
 contradicts_claim BOOLEAN, reviewed_at TIMESTAMPTZ, notes VARCHAR
);
CREATE TABLE IF NOT EXISTS guma.data_ingestion_log (
 ingestion_id VARCHAR PRIMARY KEY, source_id VARCHAR NOT NULL, dataset_name VARCHAR NOT NULL,
 started_at TIMESTAMPTZ NOT NULL, completed_at TIMESTAMPTZ, status VARCHAR NOT NULL,
 records_read BIGINT DEFAULT 0, records_written BIGINT DEFAULT 0,
 checksum_sha256 VARCHAR, error_message VARCHAR
);
INSERT INTO guma.source_registry
(source_id,source_name,provider,dataset_name,endpoint_url,citation_text,update_cadence,geographic_coverage,source_status)
VALUES
('earth-search-sentinel2-l2a','Earth Search Sentinel-2 L2A','Element 84','Sentinel-2 Collection 1 Level-2A','https://earth-search.aws.element84.com/v1','Element 84 Earth Search STAC API','Per satellite acquisition','global','catalogued'),
('nasa-firms-noaa20-viirs-global','NASA FIRMS NOAA-20 VIIRS C2 Global','NASA','NOAA-20 VIIRS global active fire detections','https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_7d.csv','NASA FIRMS','Rolling 7-day file','global','catalogued'),
('ibge-localidades','IBGE API de Localidades','IBGE','Brazilian state and municipality geography','https://servicodados.ibge.gov.br/api/v1/localidades/estados','IBGE API de Localidades','As published by IBGE','Brazil','catalogued')
ON CONFLICT (source_id) DO NOTHING;
