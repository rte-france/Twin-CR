PRAGMA user_version=4;

CREATE TABLE IF NOT EXISTS voltage_levels (
    id                 VARCHAR PRIMARY KEY,
    name               VARCHAR,
    substation_id      VARCHAR,
    nominal_v          DOUBLE,
    high_voltage_limit DOUBLE,
    low_voltage_limit  DOUBLE,
    fictitious         BOOLEAN,
    topology_kind      VARCHAR,
    FOREIGN KEY (substation_id) REFERENCES substations (id)
)
