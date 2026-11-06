PRAGMA user_version=2;

CREATE TABLE IF NOT EXISTS configurations (
    name TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    file TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS current_configuration (
    name TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    file TEXT NOT NULL,
    state TEXT DEFAULT 'idle' CHECK(state IN ('idle', 'loading', 'ready')),
    loaded_at DATETIME,
    FOREIGN KEY (name) REFERENCES configurations(name) ON DELETE CASCADE
);
