-- Enable vector and pg_trgm extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 1. Expert Twin Configuration Table
CREATE TABLE IF NOT EXISTS expert_twin_configs (
    config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id UUID NOT NULL,
    workflow_config JSONB NOT NULL,
    active_version VARCHAR(50) NOT NULL DEFAULT '1.0.0',
    is_feasible BOOLEAN NOT NULL DEFAULT TRUE,
    validation_errors TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Knowledge Chunks Table (Materialized path skeleton tree)
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_id UUID REFERENCES expert_twin_configs(config_id) ON DELETE CASCADE,
    order_index INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    parent_path VARCHAR(500) DEFAULT '', -- materialized path (e.g. 'intake.symptoms')
    tags TEXT[] DEFAULT '{}',
    synthetic_questions TEXT[] DEFAULT '{}',
    embedding vector(384), -- Local SentenceTransformer dimension
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT uq_config_order UNIQUE (config_id, order_index)
);

-- 3. Chain of Thought (CoT) Graph Mapping
CREATE TABLE IF NOT EXISTS cot_nodes (
    node_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_id UUID REFERENCES expert_twin_configs(config_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    node_type VARCHAR(50) NOT NULL, -- 'intake', 'evaluation', 'action'
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS cot_edges (
    edge_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_id UUID REFERENCES expert_twin_configs(config_id) ON DELETE CASCADE,
    source_node_id UUID REFERENCES cot_nodes(node_id) ON DELETE CASCADE,
    target_node_id UUID REFERENCES cot_nodes(node_id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL, -- 'requires', 'contradicts', 'related_to'
    UNIQUE(source_node_id, target_node_id)
);

-- 4. Active Sessions State Checkpointer
CREATE TABLE IF NOT EXISTS active_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    config_id UUID REFERENCES expert_twin_configs(config_id),
    current_node VARCHAR(100) NOT NULL DEFAULT 'start',
    graph_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_paused BOOLEAN NOT NULL DEFAULT FALSE,
    requires_review BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Execution Telemetry Ledger
CREATE TABLE IF NOT EXISTS execution_traces (
    trace_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES active_sessions(session_id) ON DELETE CASCADE,
    step_name VARCHAR(100) NOT NULL,
    prompt_used TEXT NOT NULL,
    response_generated TEXT NOT NULL,
    retrieved_chunk_ids UUID[] DEFAULT '{}',
    classification_score NUMERIC(5,4),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Indexes & Performance Optimization
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_config ON knowledge_chunks(config_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_embedding ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_content_trgm ON knowledge_chunks USING gin (content gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_active_sessions_conv ON active_sessions(conversation_id);

-- 7. Trigram Lexical Search Matching Function
CREATE OR REPLACE FUNCTION match_knowledge_chunks_lexical(
    query_text TEXT,
    match_threshold FLOAT,
    match_limit INT
)
RETURNS TABLE (
    chunk_id UUID,
    config_id UUID,
    order_index INT,
    title VARCHAR,
    content TEXT,
    parent_path VARCHAR,
    tags TEXT[],
    synthetic_questions TEXT[],
    lexical_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        kc.chunk_id,
        kc.config_id,
        kc.order_index,
        kc.title,
        kc.content,
        kc.parent_path,
        kc.tags,
        kc.synthetic_questions,
        similarity(kc.content, query_text)::FLOAT AS lexical_score
    FROM knowledge_chunks kc
    WHERE similarity(kc.content, query_text) > match_threshold
    ORDER BY lexical_score DESC
    LIMIT match_limit;
END;
$$ LANGUAGE plpgsql;
