-- Pre-Consultation Workflow Schema Migration

-- 1. Enums
CREATE TYPE pre_consultation_status AS ENUM (
    'GATHERING', 
    'SYNTHESIZING', 
    'SYNTHESIZING_PARTIAL', 
    'PENDING_REVIEW', 
    'ALIGNING', 
    'BOOKED', 
    'CLOSED'
);

CREATE TYPE sender_type AS ENUM (
    'PATIENT', 
    'AI_DOCTOR', 
    'AI_COORDINATOR'
);

CREATE TYPE appointment_status AS ENUM (
    'SCHEDULED', 
    'CONFIRMED', 
    'CANCELLED', 
    'COMPLETED'
);

-- 2. Tables
CREATE TABLE IF NOT EXISTS pre_consultation_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(patient_id) ON DELETE CASCADE,
    config_id UUID REFERENCES expert_twin_configs(config_id) ON DELETE CASCADE,
    status pre_consultation_status NOT NULL DEFAULT 'GATHERING',
    current_confidence_score NUMERIC(5,4) NOT NULL DEFAULT 0.0000,
    turn_count INT NOT NULL DEFAULT 0,
    current_extracted_entities JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS interaction_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES pre_consultation_sessions(session_id) ON DELETE CASCADE,
    sender sender_type NOT NULL,
    message_text TEXT NOT NULL,
    extracted_entities JSONB DEFAULT '{}'::jsonb,
    turn_index INT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pre_consult_summaries (
    summary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES pre_consultation_sessions(session_id) ON DELETE CASCADE,
    structured_clinical_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    summary_embedding vector(768), -- Matches Gemini embedding dimension
    doctor_review_notes TEXT,
    order_index INT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_session_order UNIQUE (session_id, order_index),
    CONSTRAINT uq_session_summary UNIQUE (session_id) -- One summary per session
);

CREATE TABLE IF NOT EXISTS appointments (
    appointment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(patient_id) ON DELETE CASCADE,
    session_id UUID REFERENCES pre_consultation_sessions(session_id) ON DELETE CASCADE,
    doctor_id UUID NOT NULL,
    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
    status appointment_status NOT NULL DEFAULT 'SCHEDULED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Indexes
CREATE INDEX IF NOT EXISTS idx_preconsult_sessions_patient ON pre_consultation_sessions(patient_id);
CREATE INDEX IF NOT EXISTS idx_interaction_logs_session ON interaction_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_preconsult_summaries_session ON pre_consult_summaries(session_id);
CREATE INDEX IF NOT EXISTS idx_preconsult_summaries_embedding ON pre_consult_summaries USING hnsw (summary_embedding vector_cosine_ops);


-- 4. Atomic RPC for State Sync & Summary Insertion
CREATE OR REPLACE FUNCTION atomic_insert_summary_and_update_state(
    p_session_id UUID,
    p_structured_data JSONB,
    p_summary_embedding vector(768)
)
RETURNS void AS $$
DECLARE
    next_idx INT;
    current_status pre_consultation_status;
BEGIN
    -- Explicit row-level lock on the session row
    SELECT status INTO current_status FROM pre_consultation_sessions 
    WHERE session_id = p_session_id FOR UPDATE;

    -- Phantom Double-Insert Protection: Validate state UNDER the lock
    IF current_status NOT IN ('SYNTHESIZING', 'SYNTHESIZING_PARTIAL') THEN
        -- Another thread/node already synthesized this session. Silently abort.
        RETURN;
    END IF;

    -- Calculate next order index safely under the lock
    SELECT COALESCE(MAX(order_index), 0) + 1
    INTO next_idx
    FROM pre_consult_summaries
    WHERE session_id = p_session_id;

    -- Transactional block for both operations
    INSERT INTO pre_consult_summaries (session_id, structured_clinical_data, summary_embedding, order_index)
    VALUES (p_session_id, p_structured_data, p_summary_embedding, next_idx);

    UPDATE pre_consultation_sessions
    SET status = 'PENDING_REVIEW', updated_at = NOW()
    WHERE session_id = p_session_id;
END;
$$ LANGUAGE plpgsql;

-- 5. Disable RLS for development
ALTER TABLE pre_consultation_sessions DISABLE ROW LEVEL SECURITY;

--- VERTICAL: HEALTHCARE ---
-- 5. Appointments Table (For Booking Saga)
CREATE TABLE IF NOT EXISTS appointments (
    appointment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(patient_id),
    session_id UUID REFERENCES pre_consultation_sessions(session_id),
    expert_id UUID NOT NULL,
    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) DEFAULT 'SCHEDULED', -- SCHEDULED, COMPLETED, CANCELLED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure a doctor can't be double booked at the exact same time
    UNIQUE (expert_id, scheduled_time)
);
CREATE INDEX IF NOT EXISTS idx_appointments_patient ON appointments(patient_id);
ALTER TABLE appointments DISABLE ROW LEVEL SECURITY;
ALTER TABLE interaction_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE pre_consult_summaries DISABLE ROW LEVEL SECURITY;
