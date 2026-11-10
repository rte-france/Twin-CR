CREATE TABLE IF NOT EXISTS project_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    name VARCHAR(255) NOT NULL,
    is_directory BOOLEAN DEFAULT FALSE,

    s3_object_key VARCHAR(1024),

    parent_id UUID REFERENCES project_files(id) ON DELETE CASCADE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_project_files_project_id ON project_files (project_id);
CREATE INDEX IF NOT EXISTS idx_project_files_parent_id ON project_files (parent_id);


CREATE TABLE IF NOT EXISTS file_roles (
    user_id UUID NOT NULL,
    file_id UUID NOT NULL REFERENCES project_files(id) ON DELETE CASCADE,

    role VARCHAR(255) NOT NULL, -- Ex: 'viewer', 'commenter', 'editor'

    PRIMARY KEY (user_id, file_id)
);
