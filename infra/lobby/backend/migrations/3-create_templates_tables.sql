CREATE TABLE IF NOT EXISTS templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,

    name VARCHAR(255) NOT NULL,
    description TEXT,
    icon_url VARCHAR(512),

    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (group_id, name)
);

CREATE TABLE IF NOT EXISTS template_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL REFERENCES templates(id) ON DELETE CASCADE,

    version_tag VARCHAR(50) NOT NULL, -- SEMVER

    hcl_content TEXT,
    s3_assets_path VARCHAR(512),

    variables_schema JSONB NOT NULL DEFAULT '{}'::jsonb,

    changelog TEXT,
    created_by_user_id UUID,

    origin_project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (template_id, version_tag)
);
