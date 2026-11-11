CREATE TABLE IF NOT EXISTS windows (
    parent_label TEXT PRIMARY KEY,
    is_main BOOLEAN,
    dockview_state JSON,
    updated_at INTEGER
);
