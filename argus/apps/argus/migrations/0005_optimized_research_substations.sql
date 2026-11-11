-- SQLite Database Optimization Script for Equipment Search
-- This script should be run once to set up FTS and indexes
PRAGMA user_version=5;


-- 1. Create FTS5 virtual table for substations
CREATE VIRTUAL TABLE IF NOT EXISTS substations_fts USING fts5(
  id,
  name,
  country,
  tso,
  content='substations',
  content_rowid='rowid',
  tokenize='porter unicode61'  -- Better tokenization for multi-language support
);

-- 2. Create triggers to keep FTS in sync with main table
CREATE TRIGGER IF NOT EXISTS substations_fts_insert 
AFTER INSERT ON substations BEGIN
  INSERT INTO substations_fts(rowid, id, name, country, tso)
  VALUES (new.rowid, new.id, new.name, new.country, new.tso);
END;

CREATE TRIGGER IF NOT EXISTS substations_fts_update 
AFTER UPDATE ON substations BEGIN
  UPDATE substations_fts 
  SET id = new.id, name = new.name, country = new.country, tso = new.tso
  WHERE rowid = new.rowid;
END;

CREATE TRIGGER IF NOT EXISTS substations_fts_delete 
AFTER DELETE ON substations BEGIN
  DELETE FROM substations_fts WHERE rowid = old.rowid;
END;

-- 3. Populate FTS table with existing data
INSERT OR IGNORE INTO substations_fts(rowid, id, name, country, tso)
SELECT rowid, id, name, country, tso FROM substations;

-- 4. Create FTS5 virtual table for voltage_levels
CREATE VIRTUAL TABLE IF NOT EXISTS voltage_levels_fts USING fts5(
  id,
  name,
  topology_kind,
  substation_id,
  content='voltage_levels',
  content_rowid='rowid',
  tokenize='porter unicode61'
);

-- 5. Create triggers for voltage_levels FTS
CREATE TRIGGER IF NOT EXISTS voltage_levels_fts_insert 
AFTER INSERT ON voltage_levels BEGIN
  INSERT INTO voltage_levels_fts(rowid, id, name, topology_kind, substation_id)
  VALUES (new.rowid, new.id, new.name, new.topology_kind, new.substation_id);
END;

CREATE TRIGGER IF NOT EXISTS voltage_levels_fts_update 
AFTER UPDATE ON voltage_levels BEGIN
  UPDATE voltage_levels_fts 
  SET id = new.id, name = new.name, topology_kind = new.topology_kind, substation_id = new.substation_id
  WHERE rowid = new.rowid;
END;

CREATE TRIGGER IF NOT EXISTS voltage_levels_fts_delete 
AFTER DELETE ON voltage_levels BEGIN
  DELETE FROM voltage_levels_fts WHERE rowid = old.rowid;
END;

-- 6. Populate voltage_levels FTS table
INSERT OR IGNORE INTO voltage_levels_fts(rowid, id, name, topology_kind, substation_id)
SELECT rowid, id, name, topology_kind, substation_id FROM voltage_levels;

-- 7. Create strategic indexes for common queries
-- Partial index for non-fictitious substations
CREATE INDEX IF NOT EXISTS idx_substations_fictitious 
ON substations(fictitious) 
WHERE fictitious = 0;

-- Composite index for country filtering
CREATE INDEX IF NOT EXISTS idx_substations_country_fictitious 
ON substations(country, fictitious) 
WHERE fictitious = 0;

-- Composite index for TSO filtering
CREATE INDEX IF NOT EXISTS idx_substations_tso_fictitious 
ON substations(tso, fictitious) 
WHERE fictitious = 0;

-- Index for voltage levels joins
CREATE INDEX IF NOT EXISTS idx_voltage_levels_substation_fictitious 
ON voltage_levels(substation_id, fictitious) 
WHERE fictitious = 0;

-- Index for voltage level sorting
CREATE INDEX IF NOT EXISTS idx_voltage_levels_nominal_v 
ON voltage_levels(nominal_v);

-- Covering index for main query
CREATE INDEX IF NOT EXISTS idx_substations_main_query 
ON substations(id, name, tso, geo_tags, country, fictitious) 
WHERE fictitious = 0;

-- 8. Analyze tables to update query planner statistics
ANALYZE substations;
ANALYZE voltage_levels;
ANALYZE substations_fts;
ANALYZE voltage_levels_fts;

-- 9. Optimize FTS index
INSERT INTO substations_fts(substations_fts) VALUES('optimize');
INSERT INTO voltage_levels_fts(voltage_levels_fts) VALUES('optimize');