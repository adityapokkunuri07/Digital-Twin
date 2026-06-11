-- 16_knowledge_framework.sql
-- Creates the foundational tables for the Unified Digital Twin Knowledge & Skills Mapping Framework

-- Table to store extracted knowledge steps from the expert
CREATE TABLE IF NOT EXISTS knowledge_hub (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    expert_id UUID NOT NULL,
    task_boundary VARCHAR(255) NOT NULL, -- e.g., 'T1_Document_Validation'
    execution_order INT NOT NULL,
    rule_text TEXT NOT NULL,
    required_action VARCHAR(255) NOT NULL, -- The tag used for skill binding, e.g., 'extract_text'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table to store the assembled templates for fast execution
CREATE TABLE IF NOT EXISTS task_blueprints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id VARCHAR(255) NOT NULL UNIQUE,
    payload_template JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS (Row Level Security) if not already enabled globally
ALTER TABLE knowledge_hub ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_blueprints ENABLE ROW LEVEL SECURITY;

-- Add basic policies (example for authenticated users)
CREATE POLICY "Allow authenticated read access for knowledge_hub" 
    ON knowledge_hub FOR SELECT TO authenticated USING (true);
    
CREATE POLICY "Allow authenticated read access for task_blueprints" 
    ON task_blueprints FOR SELECT TO authenticated USING (true);
