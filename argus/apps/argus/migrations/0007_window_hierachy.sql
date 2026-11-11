PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS window_hierarchy (
    label TEXT PRIMARY KEY,
    parent_label TEXT,
    is_parent BOOLEAN NOT NULL DEFAULT 0,
    FOREIGN KEY(parent_label) REFERENCES window_hierarchy(label) ON DELETE CASCADE
);
