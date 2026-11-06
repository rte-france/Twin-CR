PRAGMA user_version=3;

CREATE TABLE IF NOT EXISTS substations (
    id         VARCHAR PRIMARY KEY,
    name       VARCHAR,
    tso        VARCHAR,
    geo_tags   VARCHAR,
    country    VARCHAR,
    fictitious BOOLEAN
)
