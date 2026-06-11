-- =============================================================================
-- 03_hierarchy_and_skills.sql
-- Digital Twin — 5-Layer Hierarchy & Skills Mapping
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- Enum Types
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TYPE skill_type_enum AS ENUM ('Basic', 'Functional');

-- ─────────────────────────────────────────────────────────────────────────────
-- Layer 1: Hubs
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hubs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    description TEXT,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Layer 2: Domains
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS domains (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hub_id      UUID NOT NULL REFERENCES hubs(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    description TEXT,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Layer 3: Roles
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_id   UUID NOT NULL REFERENCES domains(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    description TEXT,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Layer 4: Workflows
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS workflows (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id     UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    description TEXT,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Layer 5: Tasks
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    description TEXT,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Skills Engine Node
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS skill_definitions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_name              TEXT NOT NULL UNIQUE,
    skill_type              skill_type_enum NOT NULL,
    is_active               BOOLEAN DEFAULT true,
    requires_human_approval BOOLEAN DEFAULT false,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workflow_skills (
    workflow_id                    UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    skill_id                       UUID NOT NULL REFERENCES skill_definitions(id) ON DELETE CASCADE,
    functional_context_description TEXT,
    PRIMARY KEY (workflow_id, skill_id)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Orchestration Tracking Tables
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS state_ledger (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id   UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    expert_id     UUID NOT NULL,
    current_state TEXT NOT NULL,
    updated_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS execution_logs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id  UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    task_id      UUID REFERENCES tasks(id) ON DELETE SET NULL,
    skill_id     UUID REFERENCES skill_definitions(id) ON DELETE SET NULL,
    expert_id    UUID NOT NULL,
    raw_payload  JSONB,
    status       TEXT,
    error_trace  TEXT,
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Remap Knowledge Hub Tables (expert_dna & master_cases)
-- ─────────────────────────────────────────────────────────────────────────────

-- 1. expert_dna modifications
ALTER TABLE expert_dna
    DROP COLUMN IF EXISTS industry;

ALTER TABLE expert_dna
    ADD COLUMN IF NOT EXISTS domain_id   UUID REFERENCES domains(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS role_id     UUID REFERENCES roles(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS workflow_id UUID REFERENCES workflows(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS task_id     UUID REFERENCES tasks(id) ON DELETE SET NULL;

-- Indexes for new expert_dna FKs
CREATE INDEX IF NOT EXISTS idx_dna_domain_id ON expert_dna(domain_id);
CREATE INDEX IF NOT EXISTS idx_dna_role_id ON expert_dna(role_id);
CREATE INDEX IF NOT EXISTS idx_dna_workflow_id ON expert_dna(workflow_id);
CREATE INDEX IF NOT EXISTS idx_dna_task_id ON expert_dna(task_id);

-- 2. master_cases modifications
ALTER TABLE master_cases
    ADD COLUMN IF NOT EXISTS domain_id   UUID REFERENCES domains(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS role_id     UUID REFERENCES roles(id) ON DELETE SET NULL;

-- Indexes for new master_cases FKs
CREATE INDEX IF NOT EXISTS idx_cases_domain_id ON master_cases(domain_id);
CREATE INDEX IF NOT EXISTS idx_cases_role_id ON master_cases(role_id);
