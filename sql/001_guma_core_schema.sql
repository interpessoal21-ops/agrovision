-- GUMA core data model for MotherDuck / DuckDB.
-- Review and execute only after confirming the target database.
-- All timestamps are UTC. Preserve raw source identifiers and provenance.

CREATE SCHEMA IF NOT EXISTS guma;

CREATE TABLE IF NOT EXISTS guma.source_registry (
    source_id VARCHAR PRIMARY KEY,
    source_name VARCHAR NOT NULL,
    provider VARCHAR NOT NULL,
    dataset_name VARCHAR NOT NULL,
    endpoint_url VARCHAR,
    license_name VARCHAR,
    citation_text VARCHAR,
    update_cadence VARCHAR,
    spatial_resolution VARCHAR,
    temporal_coverage VARCHAR,
    accessed_at TIMESTAMPTZ,
    source_status VARCHAR DEFAULT 'catalogued'
);

CREATE TABLE IF NOT EXISTS guma.territorial_units (
    ibge_code VARCHAR PRIMARY KEY,
    unit_level VARCHAR NOT NULL,
    unit_name VARCHAR NOT NULL,
    uf_code VARCHAR,
    uf_name VARCHAR,
    region_name VARCHAR,
    area_km2 DOUBLE,
    centroid_lon DOUBLE,
    centroid_lat DOUBLE,
    valid_from DATE,
    valid_to DATE,
    source_id VARCHAR REFERENCES guma.source_registry(source_id),
    observed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS guma.indicator_observations (
    observation_id VARCHAR PRIMARY KEY,
    source_id VARCHAR NOT NULL REFERENCES guma.source_registry(source_id),
    geography_code VARCHAR,
    indicator_code VARCHAR NOT NULL,
    indicator_name VARCHAR NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE,
    value DOUBLE,
    unit VARCHAR,
    reference_period VARCHAR,
    quality_flag VARCHAR,
    source_record_id VARCHAR,
    source_url VARCHAR,
    observed_at TIMESTAMPTZ NOT NULL,
    raw_payload JSON
);

CREATE TABLE IF NOT EXISTS guma.satellite_scenes (
    scene_id VARCHAR PRIMARY KEY,
    source_id VARCHAR NOT NULL REFERENCES guma.source_registry(source_id),
    collection_name VARCHAR NOT NULL,
    platform VARCHAR,
    acquired_at TIMESTAMPTZ NOT NULL,
    tile_id VARCHAR,
    cloud_cover_pct DOUBLE,
    geometry_geojson JSON,
    item_url VARCHAR,
    observed_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS guma.fire_detections (
    detection_id VARCHAR PRIMARY KEY,
    source_id VARCHAR NOT NULL REFERENCES guma.source_registry(source_id),
    acquired_at TIMESTAMPTZ NOT NULL,
    latitude DOUBLE NOT NULL,
    longitude DOUBLE NOT NULL,
    satellite VARCHAR,
    instrument VARCHAR,
    confidence VARCHAR,
    fire_radiative_power_mw DOUBLE,
    brightness_temperature_k DOUBLE,
    publication_id VARCHAR,
    source_url VARCHAR,
    observed_at TIMESTAMPTZ NOT NULL,
    raw_payload JSON
);

CREATE TABLE IF NOT EXISTS guma.evidence_records (
    evidence_id VARCHAR PRIMARY KEY,
    source_id VARCHAR NOT NULL REFERENCES guma.source_registry(source_id),
    title VARCHAR NOT NULL,
    authors VARCHAR,
    publication_year INTEGER,
    doi VARCHAR,
    url VARCHAR,
    evidence_type VARCHAR,
    summary VARCHAR,
    supports_claim BOOLEAN,
    contradicts_claim BOOLEAN,
    reviewed_at TIMESTAMPTZ,
    notes VARCHAR
);

CREATE INDEX IF NOT EXISTS idx_indicator_geo_period
    ON guma.indicator_observations (geography_code, indicator_code, period_start);
CREATE INDEX IF NOT EXISTS idx_fire_time
    ON guma.fire_detections (acquired_at);
CREATE INDEX IF NOT EXISTS idx_fire_location
    ON guma.fire_detections (latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_scene_time
    ON guma.satellite_scenes (acquired_at);
