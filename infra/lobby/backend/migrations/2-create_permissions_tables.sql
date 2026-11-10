CREATE TABLE IF NOT EXISTS permissions_graph (
    object_namespace VARCHAR(50) NOT NULL,
    object_id UUID NOT NULL,
    relation VARCHAR(50) NOT NULL,
    subject_namespace VARCHAR(50) NOT NULL,
    subject_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (object_namespace, object_id, relation, subject_namespace, subject_id)
);

CREATE INDEX IF NOT EXISTS idx_pg_object ON permissions_graph(object_namespace, object_id);
CREATE INDEX IF NOT EXISTS idx_pg_subject ON permissions_graph(subject_namespace, subject_id);
