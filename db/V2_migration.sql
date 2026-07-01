-- Pre-Consultation Workflow Schema Migration V2
-- Addressing 4-Node Architecture, Zero-Trust Execution, and Immutable Snapshots

-- Enable pgvector if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Expert Workflows (Configuration Plane)
CREATE TABLE IF NOT EXISTS expert_workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_id UUID REFERENCES expert_twin_configs(config_id) ON DELETE CASCADE,
    expert_id VARCHAR(255) NOT NULL,
    workflow_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Workflow Tasks (Granular Steps)
CREATE TABLE IF NOT EXISTS workflow_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES expert_workflows(id) ON DELETE CASCADE,
    step_number INT NOT NULL,
    task_name VARCHAR(255) NOT NULL,
    node_alignment VARCHAR(50) NOT NULL,
    assigned_executor VARCHAR(50) NOT NULL DEFAULT 'TWIN',
    strategy_identifier VARCHAR(100),
    task_config JSONB NOT NULL DEFAULT '{}',
    UNIQUE (workflow_id, step_number)
);

-- 3. DELETED: journalist_knowledge_vault was a D1 copy-test violation.
-- It duplicated knowledge_chunks with a different embedding dimension (1536 vs 768).
-- If 1536-dim embeddings are needed, add a nullable column to knowledge_chunks.

-- 4. Entity Thresholds (renamed from journalist_entity_thresholds)
CREATE TABLE IF NOT EXISTS entity_thresholds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_id UUID REFERENCES expert_twin_configs(config_id) ON DELETE CASCADE,
    expert_id VARCHAR(255) NOT NULL,
    entity_name VARCHAR(100) NOT NULL,
    min_allowable_value NUMERIC,
    max_allowable_value NUMERIC,
    critical_escalation_triggers TEXT[],
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Update Sessions for Immutable Tracking
-- Note: 'status' enum might need to be modified in Postgres depending on existing setup
ALTER TABLE pre_consultation_sessions
    ADD COLUMN IF NOT EXISTS workflow_id UUID REFERENCES expert_workflows(id),
    ADD COLUMN IF NOT EXISTS current_step_index INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS assigned_actor VARCHAR(50) DEFAULT 'TWIN',
    ADD COLUMN IF NOT EXISTS extracted_telemetry JSONB DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS configuration_snapshot JSONB DEFAULT '{}'; -- Immutable Snapshot Fix!

-- 6. Indexes for Performance
CREATE INDEX IF NOT EXISTS idx_et_config ON entity_thresholds(config_id);
CREATE INDEX IF NOT EXISTS idx_wt_workflow ON workflow_tasks(workflow_id);

-- Disable RLS for development
ALTER TABLE expert_workflows DISABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_tasks DISABLE ROW LEVEL SECURITY;
ALTER TABLE entity_thresholds DISABLE ROW LEVEL SECURITY;
