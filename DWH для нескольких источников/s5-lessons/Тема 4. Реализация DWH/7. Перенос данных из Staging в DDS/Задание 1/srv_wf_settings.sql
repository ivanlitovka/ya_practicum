CREATE TABLE IF NOT EXISTS dds.srv_wf_settings (
    id SERIAL PRIMARY KEY,
    workflow_key VARCHAR NOT NULL UNIQUE,
    workflow_settings JSONB NOT NULL
);