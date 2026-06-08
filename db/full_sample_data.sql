-- =============================================================================
-- FULL SAMPLE DATA — Digital Twin (Cardiologist: Dr. Meera Sharma)
-- =============================================================================
-- Fixed UUIDs for easy cross-referencing:
--   doctor_id  : 22222222-2222-2222-2222-222222222222
--   config_id  : 11111111-1111-1111-1111-111111111111
--   patient_1  : aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa001
--   patient_2  : aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa002
-- =============================================================================

-- ─────────────────────────────────────────────
-- 0. PATIENTS TABLE (create if not exists)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS patients (
    patient_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
ALTER TABLE patients DISABLE ROW LEVEL SECURITY;

INSERT INTO patients (patient_id, email, password_hash, full_name)
VALUES
(
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa001',
    'rahul.kapoor@example.com',
    'demo1234',
    'Rahul Kapoor'
),
(
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa002',
    'priya.nair@example.com',
    'demo1234',
    'Priya Nair'
)
ON CONFLICT (patient_id) DO NOTHING;

-- ─────────────────────────────────────────────
-- 1. EXPERT TWIN CONFIG (Dr. Meera Sharma — Cardiologist)
-- ─────────────────────────────────────────────
INSERT INTO expert_twin_configs (config_id, doctor_id, workflow_config, active_version, is_feasible)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    '22222222-2222-2222-2222-222222222222',
    '{
        "doctor_name": "Dr. Meera Sharma",
        "specialty": "Cardiology",
        "steps": [
            {
                "id": "step_1",
                "name": "Intake Vitals",
                "inputs": ["temperature", "blood_pressure_systolic", "blood_pressure_diastolic", "chest_pain"],
                "outputs": ["vitals_collected"],
                "dependencies": []
            },
            {
                "id": "step_2",
                "name": "Symptom Deep-Dive",
                "inputs": ["chest_pain_duration", "chest_pain_location", "shortness_of_breath", "palpitations"],
                "outputs": ["symptoms_profiled"],
                "dependencies": ["step_1"]
            },
            {
                "id": "step_3",
                "name": "Risk Stratification",
                "inputs": ["smoking_history", "diabetes", "family_cardiac_history", "bmi"],
                "outputs": ["risk_score"],
                "dependencies": ["step_2"]
            },
            {
                "id": "step_4",
                "name": "Recommendation",
                "inputs": [],
                "outputs": ["action_plan"],
                "dependencies": ["step_3"]
            }
        ]
    }'::jsonb,
    '1.0.0',
    TRUE
) ON CONFLICT (config_id) DO NOTHING;

-- ─────────────────────────────────────────────
-- 2. KNOWLEDGE CHUNKS (Clinical Guidelines)
-- ─────────────────────────────────────────────
INSERT INTO knowledge_chunks (chunk_id, config_id, order_index, title, content, parent_path, tags, synthetic_questions)
VALUES
(
    '33333333-3333-3333-3333-333333333301',
    '11111111-1111-1111-1111-111111111111',
    0,
    'Blood Pressure Classification',
    'Blood pressure classification per ACC/AHA 2017 guidelines: Normal <120/80 mmHg. Elevated 120-129/<80. Stage 1 HTN 130-139/80-89. Stage 2 HTN >=140/>=90. Hypertensive crisis >180/>120 — requires immediate evaluation.',
    'vitals.blood_pressure',
    '{"hypertension", "vitals", "blood_pressure"}',
    '{"What is normal blood pressure?", "When is blood pressure considered a crisis?", "What are the stages of hypertension?"}'
),
(
    '33333333-3333-3333-3333-333333333302',
    '11111111-1111-1111-1111-111111111111',
    1,
    'Chest Pain Differential Diagnosis',
    'Chest pain differentials: Acute Coronary Syndrome (crushing substernal pain radiating to left arm/jaw, diaphoresis), Pulmonary Embolism (pleuritic pain, dyspnea, tachycardia), Pericarditis (sharp pain worse when lying down, relieved by leaning forward), GERD (burning retrosternal pain after meals). Always rule out ACS first.',
    'symptoms.chest_pain',
    '{"chest_pain", "ACS", "differential_diagnosis", "emergency"}',
    '{"What are the causes of chest pain?", "How to differentiate cardiac vs non-cardiac chest pain?"}'
),
(
    '33333333-3333-3333-3333-333333333303',
    '11111111-1111-1111-1111-111111111111',
    2,
    'Temperature and Cardiac Risk',
    'Fever (>100.4°F/38°C) in cardiac patients may indicate endocarditis, pericarditis, or post-MI Dressler syndrome. Severe fever >=103°F warrants immediate blood cultures and echocardiography. Normal body temperature is 98.6°F (37°C).',
    'vitals.temperature',
    '{"fever", "endocarditis", "vitals", "temperature"}',
    '{"What is normal temperature?", "Why is fever dangerous in cardiac patients?"}'
),
(
    '33333333-3333-3333-3333-333333333304',
    '11111111-1111-1111-1111-111111111111',
    3,
    'Cardiac Risk Factors — ASCVD Assessment',
    'Major ASCVD risk factors: Age (M>=45, F>=55), smoking, diabetes mellitus, hypertension, dyslipidemia (LDL>190), family history of premature CAD (1st degree M<55, F<65), obesity (BMI>=30). 10-year ASCVD risk: Low <5%, Borderline 5-7.5%, Intermediate 7.5-20%, High >20%.',
    'risk_assessment.ascvd',
    '{"risk_factors", "ASCVD", "smoking", "diabetes", "family_history"}',
    '{"What are cardiac risk factors?", "How is ASCVD risk calculated?"}'
),
(
    '33333333-3333-3333-3333-333333333305',
    '11111111-1111-1111-1111-111111111111',
    4,
    'Troponin Interpretation',
    'High-sensitivity cardiac troponin (hs-cTn) is the gold standard biomarker for myocardial injury. Values above the 99th percentile URL with a rise/fall pattern indicate acute MI. Serial measurements at 0h and 3h are recommended. Delta >20% is significant.',
    'diagnostics.troponin',
    '{"troponin", "biomarker", "MI", "diagnostics"}',
    '{"What does elevated troponin mean?", "How to interpret serial troponin?"}'
),
(
    '33333333-3333-3333-3333-333333333306',
    '11111111-1111-1111-1111-111111111111',
    5,
    'ECG Interpretation Basics',
    'Key ECG findings: ST-elevation in contiguous leads suggests STEMI — activate cath lab. ST-depression or T-wave inversion may indicate NSTEMI or ischemia. New LBBB in setting of chest pain is a STEMI equivalent. Always correlate with clinical picture.',
    'diagnostics.ecg',
    '{"ECG", "STEMI", "NSTEMI", "ischemia"}',
    '{"What does ST elevation mean?", "When to activate the cath lab?"}'
),
(
    '33333333-3333-3333-3333-333333333307',
    '11111111-1111-1111-1111-111111111111',
    6,
    'Medication Protocol — Antiplatelet Therapy',
    'For confirmed ACS: Aspirin 325mg loading then 81mg daily. Dual antiplatelet (DAPT) with P2Y12 inhibitor (clopidogrel 600mg load or ticagrelor 180mg load). Continue DAPT for 12 months post-ACS. PPI co-prescription if GI risk factors present.',
    'treatment.medications',
    '{"aspirin", "clopidogrel", "DAPT", "ACS", "treatment"}',
    '{"What medications for ACS?", "How long to continue dual antiplatelet therapy?"}'
),
(
    '33333333-3333-3333-3333-333333333308',
    '11111111-1111-1111-1111-111111111111',
    7,
    'When to Refer — Escalation Protocol',
    'Immediate cardiology referral criteria: Troponin positive with dynamic changes, STEMI on ECG, hemodynamic instability (SBP<90), new heart failure symptoms, syncope with structural heart disease. Urgent (24-48h): new murmur, uncontrolled HTN despite 3 drugs, recurrent chest pain.',
    'workflow.escalation',
    '{"referral", "escalation", "emergency", "STEMI"}',
    '{"When should a patient be referred to cardiology?", "What are emergency cardiac criteria?"}'
)
ON CONFLICT ON CONSTRAINT uq_config_order DO NOTHING;

-- ─────────────────────────────────────────────
-- 3. COT NODES (Chain-of-Thought Reasoning Graph)
-- ─────────────────────────────────────────────
INSERT INTO cot_nodes (node_id, config_id, title, node_type, content, metadata)
VALUES
(
    '44444444-4444-4444-4444-444444444401',
    '11111111-1111-1111-1111-111111111111',
    'Gather Vitals',
    'intake',
    'First collect the patient''s temperature, blood pressure (systolic and diastolic), and ask about chest pain. These baseline vitals determine the urgency pathway.',
    '{"priority": "high", "max_retries": 3}'::jsonb
),
(
    '44444444-4444-4444-4444-444444444402',
    '11111111-1111-1111-1111-111111111111',
    'Symptom Profiling',
    'intake',
    'If chest pain is reported, determine: duration (acute <24h vs chronic), location (substernal, left-sided, diffuse), radiation (arm, jaw, back), and associated symptoms (diaphoresis, dyspnea, nausea, palpitations).',
    '{"priority": "high"}'::jsonb
),
(
    '44444444-4444-4444-4444-444444444403',
    '11111111-1111-1111-1111-111111111111',
    'Blood Pressure Evaluation',
    'evaluation',
    'Classify BP per ACC/AHA guidelines. If systolic >=180 or diastolic >=120, flag as hypertensive crisis. If systolic >=140 or diastolic >=90, flag Stage 2 HTN requiring medication review.',
    '{"threshold_systolic": 180, "threshold_diastolic": 120}'::jsonb
),
(
    '44444444-4444-4444-4444-444444444404',
    '11111111-1111-1111-1111-111111111111',
    'Fever Assessment',
    'evaluation',
    'Temperature >=103°F is a severe fever in cardiac patients. Consider endocarditis or pericarditis. Recommend blood cultures and echocardiography. Temperature 100.4-103°F warrants monitoring.',
    '{"fever_threshold": 103.0}'::jsonb
),
(
    '44444444-4444-4444-4444-444444444405',
    '11111111-1111-1111-1111-111111111111',
    'ACS Risk Stratification',
    'evaluation',
    'Apply HEART score: History (0-2), ECG (0-2), Age (0-2), Risk factors (0-2), Troponin (0-2). Score 0-3: low risk (outpatient). Score 4-6: moderate (observation). Score 7-10: high risk (aggressive intervention).',
    '{"scoring_system": "HEART"}'::jsonb
),
(
    '44444444-4444-4444-4444-444444444406',
    '11111111-1111-1111-1111-111111111111',
    'Cardiac Emergency Escalation',
    'action',
    'If any of: chest pain with ST-elevation, troponin positive, hemodynamic instability — immediately halt auto-pilot, freeze session, and route to human cardiologist for intercept.',
    '{"action_type": "escalate", "freeze_session": true}'::jsonb
),
(
    '44444444-4444-4444-4444-444444444407',
    '11111111-1111-1111-1111-111111111111',
    'Treatment Plan Dispatch',
    'action',
    'For stable patients: generate lifestyle recommendations (diet, exercise, smoking cessation), medication adjustments, and follow-up scheduling. Provide patient education materials.',
    '{"action_type": "treat", "follow_up_days": 14}'::jsonb
)
ON CONFLICT (node_id) DO NOTHING;

-- ─────────────────────────────────────────────
-- 4. COT EDGES (Reasoning Flow Connections)
-- ─────────────────────────────────────────────
INSERT INTO cot_edges (edge_id, config_id, source_node_id, target_node_id, relationship_type)
VALUES
-- Gather Vitals → BP Evaluation
('55555555-5555-5555-5555-555555555501', '11111111-1111-1111-1111-111111111111',
 '44444444-4444-4444-4444-444444444401', '44444444-4444-4444-4444-444444444403', 'requires'),
-- Gather Vitals → Fever Assessment
('55555555-5555-5555-5555-555555555502', '11111111-1111-1111-1111-111111111111',
 '44444444-4444-4444-4444-444444444401', '44444444-4444-4444-4444-444444444404', 'requires'),
-- Gather Vitals → Symptom Profiling
('55555555-5555-5555-5555-555555555503', '11111111-1111-1111-1111-111111111111',
 '44444444-4444-4444-4444-444444444401', '44444444-4444-4444-4444-444444444402', 'requires'),
-- Symptom Profiling → ACS Risk Stratification
('55555555-5555-5555-5555-555555555504', '11111111-1111-1111-1111-111111111111',
 '44444444-4444-4444-4444-444444444402', '44444444-4444-4444-4444-444444444405', 'requires'),
-- BP Evaluation → ACS Risk (hypertension is a risk factor)
('55555555-5555-5555-5555-555555555505', '11111111-1111-1111-1111-111111111111',
 '44444444-4444-4444-4444-444444444403', '44444444-4444-4444-4444-444444444405', 'related_to'),
-- ACS Risk → Emergency Escalation
('55555555-5555-5555-5555-555555555506', '11111111-1111-1111-1111-111111111111',
 '44444444-4444-4444-4444-444444444405', '44444444-4444-4444-4444-444444444406', 'requires'),
-- ACS Risk → Treatment Plan (if stable)
('55555555-5555-5555-5555-555555555507', '11111111-1111-1111-1111-111111111111',
 '44444444-4444-4444-4444-444444444405', '44444444-4444-4444-4444-444444444407', 'related_to'),
-- Fever → Emergency Escalation (severe fever in cardiac patients)
('55555555-5555-5555-5555-555555555508', '11111111-1111-1111-1111-111111111111',
 '44444444-4444-4444-4444-444444444404', '44444444-4444-4444-4444-444444444406', 'related_to')
ON CONFLICT (edge_id) DO NOTHING;

-- ─────────────────────────────────────────────
-- 5. PRE-CONSULTATION SESSIONS
-- ─────────────────────────────────────────────
-- Session 1: Rahul — completed flow (chest pain concern)
INSERT INTO pre_consultation_sessions (session_id, patient_id, config_id, status, current_confidence_score, turn_count, current_extracted_entities)
VALUES
(
    'cccccccc-cccc-cccc-cccc-cccccccccc01',
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa001',
    '11111111-1111-1111-1111-111111111111',
    'BOOKED',
    0.9200,
    5,
    '{
        "chief_complaint": "intermittent chest tightness for 3 days",
        "temperature": 98.4,
        "blood_pressure_systolic": 148,
        "blood_pressure_diastolic": 92,
        "chest_pain": true,
        "chest_pain_duration": "3 days",
        "chest_pain_location": "substernal",
        "shortness_of_breath": true,
        "palpitations": false,
        "smoking_history": "10 pack-years, quit 2 years ago",
        "diabetes": false,
        "family_cardiac_history": "father had MI at age 52"
    }'::jsonb
),
-- Session 2: Priya — still in GATHERING phase
(
    'cccccccc-cccc-cccc-cccc-cccccccccc02',
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa002',
    '11111111-1111-1111-1111-111111111111',
    'GATHERING',
    0.3500,
    2,
    '{
        "chief_complaint": "occasional dizziness and racing heart",
        "temperature": 99.1,
        "palpitations": true
    }'::jsonb
)
ON CONFLICT (session_id) DO NOTHING;

-- ─────────────────────────────────────────────
-- 6. INTERACTION LOGS (Chat History)
-- ─────────────────────────────────────────────
-- Session 1 (Rahul) — 5 turns
INSERT INTO interaction_logs (log_id, session_id, sender, message_text, extracted_entities, turn_index)
VALUES
(
    'dddddddd-dddd-dddd-dddd-dddddddddd01',
    'cccccccc-cccc-cccc-cccc-cccccccccc01',
    'AI_DOCTOR',
    'Hello, I am Dr. Sharma''s digital assistant. I''ll help prepare for your consultation. Could you describe what brings you in today?',
    '{}'::jsonb, 0
),
(
    'dddddddd-dddd-dddd-dddd-dddddddddd02',
    'cccccccc-cccc-cccc-cccc-cccccccccc01',
    'PATIENT',
    'I have been having chest tightness on and off for the past 3 days. It feels like pressure in the center of my chest, especially when I climb stairs.',
    '{"chest_pain": true, "chest_pain_duration": "3 days", "chest_pain_location": "substernal"}'::jsonb, 1
),
(
    'dddddddd-dddd-dddd-dddd-dddddddddd03',
    'cccccccc-cccc-cccc-cccc-cccccccccc01',
    'AI_DOCTOR',
    'Thank you for sharing that. Substernal chest tightness with exertion is important to evaluate. Could you provide your current vitals — temperature and blood pressure? Also, do you experience shortness of breath or palpitations?',
    '{}'::jsonb, 2
),
(
    'dddddddd-dddd-dddd-dddd-dddddddddd04',
    'cccccccc-cccc-cccc-cccc-cccccccccc01',
    'PATIENT',
    'My temperature is 98.4. Blood pressure is 148/92. Yes I do get short of breath but no palpitations. My father had a heart attack at 52. I used to smoke for 10 years but quit 2 years ago.',
    '{"temperature": 98.4, "blood_pressure_systolic": 148, "blood_pressure_diastolic": 92, "shortness_of_breath": true, "palpitations": false, "family_cardiac_history": "father MI at 52", "smoking_history": "10 pack-years, quit 2y"}'::jsonb, 3
),
(
    'dddddddd-dddd-dddd-dddd-dddddddddd05',
    'cccccccc-cccc-cccc-cccc-cccccccccc01',
    'AI_DOCTOR',
    'Based on the information gathered: substernal chest tightness with exertion, Stage 2 hypertension (148/92), exertional dyspnea, significant family history, and past smoking — I am flagging this for priority evaluation with Dr. Sharma. I recommend an ECG and troponin panel at your visit. I will schedule your appointment now.',
    '{}'::jsonb, 4
),
-- Session 2 (Priya) — 2 turns so far
(
    'dddddddd-dddd-dddd-dddd-dddddddddd06',
    'cccccccc-cccc-cccc-cccc-cccccccccc02',
    'AI_DOCTOR',
    'Hello, I am Dr. Sharma''s digital assistant. What symptoms are you experiencing today?',
    '{}'::jsonb, 0
),
(
    'dddddddd-dddd-dddd-dddd-dddddddddd07',
    'cccccccc-cccc-cccc-cccc-cccccccccc02',
    'PATIENT',
    'I feel dizzy sometimes and my heart races. Temperature is 99.1.',
    '{"palpitations": true, "temperature": 99.1}'::jsonb, 1
)
ON CONFLICT (log_id) DO NOTHING;

-- ─────────────────────────────────────────────
-- 7. PRE-CONSULT SUMMARIES (Session 1 — completed)
-- ─────────────────────────────────────────────
INSERT INTO pre_consult_summaries (summary_id, session_id, structured_clinical_data, doctor_review_notes, order_index)
VALUES (
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeee01',
    'cccccccc-cccc-cccc-cccc-cccccccccc01',
    '{
        "patient_name": "Rahul Kapoor",
        "age": 45,
        "chief_complaint": "Intermittent substernal chest tightness x3 days, worse with exertion",
        "vitals": {
            "temperature_f": 98.4,
            "bp_systolic": 148,
            "bp_diastolic": 92,
            "bp_classification": "Stage 2 Hypertension"
        },
        "symptoms": {
            "chest_pain": true,
            "chest_pain_character": "pressure/tightness",
            "chest_pain_location": "substernal",
            "chest_pain_trigger": "exertion (climbing stairs)",
            "shortness_of_breath": true,
            "palpitations": false,
            "diaphoresis": false
        },
        "risk_factors": {
            "smoking": "10 pack-year history, quit 2 years ago",
            "diabetes": false,
            "family_history": "Father — MI at age 52",
            "hypertension": true
        },
        "ai_assessment": {
            "risk_level": "INTERMEDIATE-HIGH",
            "preliminary_differentials": ["Stable Angina", "Unstable Angina", "Hypertensive Heart Disease"],
            "recommended_workup": ["12-lead ECG", "hs-Troponin (0h and 3h)", "Lipid panel", "HbA1c", "Chest X-ray"],
            "urgency": "Priority — schedule within 24-48 hours"
        }
    }'::jsonb,
    NULL,
    1
) ON CONFLICT ON CONSTRAINT uq_session_summary DO NOTHING;

-- ─────────────────────────────────────────────
-- 8. APPOINTMENTS
-- ─────────────────────────────────────────────
INSERT INTO appointments (appointment_id, patient_id, session_id, doctor_id, scheduled_time, status)
VALUES (
    'ffffffff-ffff-ffff-ffff-ffffffffffff',
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaa001',
    'cccccccc-cccc-cccc-cccc-cccccccccc01',
    '22222222-2222-2222-2222-222222222222',
    '2026-06-10T10:30:00+05:30',
    'SCHEDULED'
) ON CONFLICT (appointment_id) DO NOTHING;

-- ─────────────────────────────────────────────
-- 9. ACTIVE SESSIONS (Live orchestrator session for Rahul)
-- ─────────────────────────────────────────────
INSERT INTO active_sessions (session_id, conversation_id, config_id, current_node, graph_state, is_paused, requires_review)
VALUES (
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb01',
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb99',
    '11111111-1111-1111-1111-111111111111',
    'action_dispatch',
    '{
        "session_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb01",
        "conversation_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb99",
        "config_id": "11111111-1111-1111-1111-111111111111",
        "current_node": "action_dispatch",
        "user_query": "temperature is 98.4, bp is 148/92, I have chest pain",
        "gathered_data": {
            "temperature": 98.4,
            "blood_pressure_systolic": 148,
            "blood_pressure_diastolic": 92,
            "chest_pain": true
        },
        "retrieved_context": "Blood pressure 148/92 is Stage 2 HTN per ACC/AHA. Chest pain with hypertension warrants ACS workup.",
        "output_message": "Clinical parameters verified. BP classified as Stage 2 Hypertension. Chest pain noted. Guideline Recommendation: Evaluate for ACS, order ECG and troponin.",
        "requires_review": false,
        "is_paused": false,
        "classification_score": 0.87,
        "history": []
    }'::jsonb,
    FALSE,
    FALSE
) ON CONFLICT (session_id) DO NOTHING;

-- ─────────────────────────────────────────────
-- 10. EXECUTION TRACES (Telemetry for the above session)
-- ─────────────────────────────────────────────
INSERT INTO execution_traces (trace_id, session_id, step_name, prompt_used, response_generated, retrieved_chunk_ids, classification_score)
VALUES
(
    '99999999-9999-9999-9999-999999999901',
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb01',
    'data_gathering',
    'My temperature is 98.4 and blood pressure is 148/92',
    'Thank you. I have recorded your temperature (98.4°F — normal) and blood pressure (148/92 — Stage 2 Hypertension). Do you have any chest pain or other symptoms?',
    ARRAY['33333333-3333-3333-3333-333333333301'::UUID, '33333333-3333-3333-3333-333333333303'::UUID],
    0.82
),
(
    '99999999-9999-9999-9999-999999999902',
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbb01',
    'action_dispatch',
    'yes I have chest pain',
    'Clinical parameters verified against guidelines. BP classified as Stage 2 Hypertension. Chest pain noted — recommend ECG and troponin panel. Guideline: Always rule out ACS first in chest pain patients.',
    ARRAY['33333333-3333-3333-3333-333333333301'::UUID, '33333333-3333-3333-3333-333333333302'::UUID],
    0.87
)
ON CONFLICT (trace_id) DO NOTHING;
