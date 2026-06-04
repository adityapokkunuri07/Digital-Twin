-- Sample Data for Testing the Digital Twin Engine
-- This script injects mock Expert Twin Configuration, Knowledge Chunks, CoT Nodes, and CoT Edges.
-- Designed to test the ingestion, RAG, and orchestration workflows without needing the AI Journalist.

-- Use fixed UUIDs for easy referencing
-- config_id: '11111111-1111-1111-1111-111111111111'
-- doctor_id: '22222222-2222-2222-2222-222222222222'

-- 1. Insert Expert Twin Configuration
INSERT INTO expert_twin_configs (config_id, doctor_id, workflow_config, active_version, is_feasible)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    '22222222-2222-2222-2222-222222222222',
    '{
        "steps": [
            {
                "id": "step_1",
                "name": "Intake Vitals",
                "inputs": ["temperature", "blood_pressure_systolic", "blood_pressure_diastolic", "chest_pain"],
                "outputs": ["evaluation_done"],
                "dependencies": []
            }
        ]
    }'::jsonb,
    '1.0.0',
    TRUE
) ON CONFLICT (config_id) DO NOTHING;

-- 2. Insert Knowledge Chunks
-- Note: In a real system, the 'embedding' column would be populated with 768-dimensional vectors. 
-- We skip populating embeddings here for simplicity, allowing lexical/trigram search to work, or the system to mock it.
INSERT INTO knowledge_chunks (chunk_id, config_id, order_index, title, content, parent_path, tags, synthetic_questions)
VALUES 
(
    '33333333-3333-3333-3333-333333333331',
    '11111111-1111-1111-1111-111111111111',
    0,
    'Temperature Guideline',
    'Verify temperature vitals. Normal is 98.6. Severe fever is >= 103.0.',
    'temp_guideline',
    '{"fever", "vitals"}',
    '{"What is normal temperature?", "When is fever severe?"}'
),
(
    '33333333-3333-3333-3333-333333333332',
    '11111111-1111-1111-1111-111111111111',
    1,
    'Cardiac Guideline',
    'Chest pain is a critical symptom. Evaluate immediately for acute coronary syndrome.',
    'cardiac_guideline',
    '{"chest_pain", "cardiac", "emergency"}',
    '{"How to handle chest pain?"}'
) ON CONFLICT ON CONSTRAINT uq_config_order DO NOTHING;

-- 3. Insert CoT Nodes
INSERT INTO cot_nodes (node_id, config_id, title, node_type, content, metadata)
VALUES
(
    '44444444-4444-4444-4444-444444444441',
    '11111111-1111-1111-1111-111111111111',
    'Gather Vitals',
    'intake',
    'First, we must gather the patients temperature and blood pressure to establish a baseline.',
    '{"unlearned": false}'::jsonb
),
(
    '44444444-4444-4444-4444-444444444442',
    '11111111-1111-1111-1111-111111111111',
    'Fever Assessment',
    'evaluation',
    'If the temperature is 103 or higher, it is an extreme fever requiring immediate medical intercept.',
    '{"unlearned": false}'::jsonb
),
(
    '44444444-4444-4444-4444-444444444443',
    '11111111-1111-1111-1111-111111111111',
    'Cardiac Assessment',
    'evaluation',
    'If the patient reports chest pain, halt the process and route to a cardiologist.',
    '{"unlearned": false}'::jsonb
) ON CONFLICT (node_id) DO NOTHING;

-- 4. Insert CoT Edges
INSERT INTO cot_edges (edge_id, config_id, source_node_id, target_node_id, relationship_type)
VALUES
(
    '55555555-5555-5555-5555-555555555551',
    '11111111-1111-1111-1111-111111111111',
    '44444444-4444-4444-4444-444444444441',
    '44444444-4444-4444-4444-444444444442',
    'requires'
),
(
    '55555555-5555-5555-5555-555555555552',
    '11111111-1111-1111-1111-111111111111',
    '44444444-4444-4444-4444-444444444441',
    '44444444-4444-4444-4444-444444444443',
    'related_to'
) ON CONFLICT (edge_id) DO NOTHING;
