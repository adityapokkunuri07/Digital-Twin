-- =============================================================================
-- 04_seed_domains_and_roles.sql
-- Digital Twin Platform — Seed Data for 3 Unified Twins
-- =============================================================================
-- Run this AFTER 03_hierarchy_and_skills.sql
--
-- Seeds the 5-layer hierarchy with:
--   1 Hub  → Digital Twin Platform
--   3 Domains → Healthcare | IT | Education
--   3 Roles   → Doctor | Project Manager | Tutor
--   Starter Workflows + Tasks per Role
--   Starter Skill Definitions (Basic + Functional) per Domain
--
-- IMPORTANT: UUIDs are hardcoded so application adapters can reference them
-- via environment variables or config without an extra lookup query.
-- =============================================================================


-- ─────────────────────────────────────────────────────────────────────────────
-- Layer 1: Hub
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO hubs (id, name, description)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Digital Twin Platform',
    'The unified root hub for all domain-specific AI expert twins.'
)
ON CONFLICT (id) DO NOTHING;


-- ─────────────────────────────────────────────────────────────────────────────
-- Layer 2: Domains
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO domains (id, hub_id, name, description)
VALUES
    (
        '10000000-0000-0000-0000-000000000001',
        '00000000-0000-0000-0000-000000000001',
        'Healthcare',
        'Clinical decision support and patient care domain.'
    ),
    (
        '10000000-0000-0000-0000-000000000002',
        '00000000-0000-0000-0000-000000000001',
        'IT',
        'Software project management and engineering domain.'
    ),
    (
        '10000000-0000-0000-0000-000000000003',
        '00000000-0000-0000-0000-000000000001',
        'Education',
        'Personalised learning and academic tutoring domain.'
    )
ON CONFLICT (id) DO NOTHING;


-- ─────────────────────────────────────────────────────────────────────────────
-- Layer 3: Roles
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO roles (id, domain_id, name, description)
VALUES
    (
        '20000000-0000-0000-0000-000000000001',
        '10000000-0000-0000-0000-000000000001',
        'Doctor',
        'Clinical physician responsible for diagnosis and treatment decisions.'
    ),
    (
        '20000000-0000-0000-0000-000000000002',
        '10000000-0000-0000-0000-000000000002',
        'Project Manager',
        'Leads delivery of software projects using Agile/SDLC methodologies.'
    ),
    (
        '20000000-0000-0000-0000-000000000003',
        '10000000-0000-0000-0000-000000000003',
        'Tutor',
        'Expert educator who guides learners using Socratic questioning.'
    )
ON CONFLICT (id) DO NOTHING;


-- ─────────────────────────────────────────────────────────────────────────────
-- Layer 4: Workflows
-- ─────────────────────────────────────────────────────────────────────────────

-- Healthcare — Doctor Workflows
INSERT INTO workflows (id, role_id, name, description)
VALUES
    (
        '30000000-0000-0000-0000-000000000001',
        '20000000-0000-0000-0000-000000000001',
        'Patient Consultation',
        'End-to-end clinical consultation from intake to treatment recommendation.'
    ),
    (
        '30000000-0000-0000-0000-000000000002',
        '20000000-0000-0000-0000-000000000001',
        'Diagnostic Analysis',
        'Interpretation of lab reports, imaging, and diagnostic data.'
    )
ON CONFLICT (id) DO NOTHING;

-- IT — Project Manager Workflows
INSERT INTO workflows (id, role_id, name, description)
VALUES
    (
        '30000000-0000-0000-0000-000000000003',
        '20000000-0000-0000-0000-000000000002',
        'Sprint Planning',
        'Backlog refinement, capacity planning, and sprint goal setting.'
    ),
    (
        '30000000-0000-0000-0000-000000000004',
        '20000000-0000-0000-0000-000000000002',
        'Risk & Escalation Management',
        'Identifying blockers, managing stakeholder escalations, and mitigation plans.'
    )
ON CONFLICT (id) DO NOTHING;

-- Education — Tutor Workflows
INSERT INTO workflows (id, role_id, name, description)
VALUES
    (
        '30000000-0000-0000-0000-000000000005',
        '20000000-0000-0000-0000-000000000003',
        'Concept Explanation Session',
        'Structured explanation of a complex concept using the Feynman technique.'
    ),
    (
        '30000000-0000-0000-0000-000000000006',
        '20000000-0000-0000-0000-000000000003',
        'Assessment & Feedback',
        'Evaluating learner submissions and providing formative feedback.'
    )
ON CONFLICT (id) DO NOTHING;


-- ─────────────────────────────────────────────────────────────────────────────
-- Layer 5: Tasks
-- ─────────────────────────────────────────────────────────────────────────────

-- Healthcare Tasks
INSERT INTO tasks (id, workflow_id, name, description)
VALUES
    ('40000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000001', 'Collect Patient History',        'Gather presenting complaints, medical history, and current medications.'),
    ('40000000-0000-0000-0000-000000000002', '30000000-0000-0000-0000-000000000001', 'Order Investigations',           'Prescribe appropriate lab tests or imaging based on differential diagnosis.'),
    ('40000000-0000-0000-0000-000000000003', '30000000-0000-0000-0000-000000000001', 'Formulate Treatment Plan',       'Synthesise findings into a clinical decision and document the plan.'),
    ('40000000-0000-0000-0000-000000000004', '30000000-0000-0000-0000-000000000002', 'Analyse Diagnostic Reports',     'Interpret lab values, imaging results, and flag critical findings.'),
    ('40000000-0000-0000-0000-000000000005', '30000000-0000-0000-0000-000000000002', 'Generate Differential Diagnosis','Produce a ranked list of possible diagnoses with confidence scores.')
ON CONFLICT (id) DO NOTHING;

-- IT Tasks
INSERT INTO tasks (id, workflow_id, name, description)
VALUES
    ('40000000-0000-0000-0000-000000000006', '30000000-0000-0000-0000-000000000003', 'Groom Backlog',                  'Review and prioritise user stories with the product owner.'),
    ('40000000-0000-0000-0000-000000000007', '30000000-0000-0000-0000-000000000003', 'Assign Story Points',            'Facilitate team estimation using planning poker.'),
    ('40000000-0000-0000-0000-000000000008', '30000000-0000-0000-0000-000000000003', 'Set Sprint Goal',                'Define the sprint objective and acceptance criteria.'),
    ('40000000-0000-0000-0000-000000000009', '30000000-0000-0000-0000-000000000004', 'Identify Blockers',              'Surface impediments from daily standups and track to resolution.'),
    ('40000000-0000-0000-0000-000000000010', '30000000-0000-0000-0000-000000000004', 'Escalate to Stakeholders',       'Prepare escalation brief with timeline impact and proposed remediation.')
ON CONFLICT (id) DO NOTHING;

-- Education Tasks
INSERT INTO tasks (id, workflow_id, name, description)
VALUES
    ('40000000-0000-0000-0000-000000000011', '30000000-0000-0000-0000-000000000005', 'Diagnose Knowledge Gap',         'Identify what the learner already knows via diagnostic questions.'),
    ('40000000-0000-0000-0000-000000000012', '30000000-0000-0000-0000-000000000005', 'Scaffold Explanation',           'Break the concept into layers, using analogies and Socratic prompts.'),
    ('40000000-0000-0000-0000-000000000013', '30000000-0000-0000-0000-000000000005', 'Check for Understanding',        'Pose a mastery check question before closing the session.'),
    ('40000000-0000-0000-0000-000000000014', '30000000-0000-0000-0000-000000000006', 'Review Submission',              'Analyse the learner submission against the rubric criteria.'),
    ('40000000-0000-0000-0000-000000000015', '30000000-0000-0000-0000-000000000006', 'Deliver Formative Feedback',     'Provide specific, actionable feedback guiding the next iteration.')
ON CONFLICT (id) DO NOTHING;


-- ─────────────────────────────────────────────────────────────────────────────
-- Skills Engine: Skill Definitions
-- ─────────────────────────────────────────────────────────────────────────────

-- Basic Skills (cross-domain, reusable)
INSERT INTO skill_definitions (id, skill_name, skill_type, is_active, requires_human_approval)
VALUES
    ('50000000-0000-0000-0000-000000000001', 'RAG Knowledge Retrieval',      'Basic',      true, false),
    ('50000000-0000-0000-0000-000000000002', 'Structured Data Extraction',   'Basic',      true, false),
    ('50000000-0000-0000-0000-000000000003', 'Document Ingestion',           'Basic',      true, false),
    ('50000000-0000-0000-0000-000000000004', 'Confidence Score Evaluation',  'Basic',      true, false),
    ('50000000-0000-0000-0000-000000000005', 'Human Escalation Trigger',     'Basic',      true, true)
ON CONFLICT (id) DO NOTHING;

-- Functional Skills — Healthcare
INSERT INTO skill_definitions (id, skill_name, skill_type, is_active, requires_human_approval)
VALUES
    ('50000000-0000-0000-0000-000000000010', 'Clinical Decision Synthesis',       'Functional', true, true),
    ('50000000-0000-0000-0000-000000000011', 'Differential Diagnosis Generation', 'Functional', true, true),
    ('50000000-0000-0000-0000-000000000012', 'Lab Report Interpretation',         'Functional', true, false)
ON CONFLICT (id) DO NOTHING;

-- Functional Skills — IT
INSERT INTO skill_definitions (id, skill_name, skill_type, is_active, requires_human_approval)
VALUES
    ('50000000-0000-0000-0000-000000000020', 'Sprint Capacity Calculation',       'Functional', true, false),
    ('50000000-0000-0000-0000-000000000021', 'Risk Impact Assessment',            'Functional', true, false),
    ('50000000-0000-0000-0000-000000000022', 'Stakeholder Escalation Drafting',   'Functional', true, true)
ON CONFLICT (id) DO NOTHING;

-- Functional Skills — Education
INSERT INTO skill_definitions (id, skill_name, skill_type, is_active, requires_human_approval)
VALUES
    ('50000000-0000-0000-0000-000000000030', 'Knowledge Gap Diagnosis',           'Functional', true, false),
    ('50000000-0000-0000-0000-000000000031', 'Socratic Prompt Generation',        'Functional', true, false),
    ('50000000-0000-0000-0000-000000000032', 'Rubric-Based Assessment',           'Functional', true, false)
ON CONFLICT (id) DO NOTHING;


-- ─────────────────────────────────────────────────────────────────────────────
-- workflow_skills: Map Skills to Workflows with Functional Context
-- ─────────────────────────────────────────────────────────────────────────────

-- Healthcare: Patient Consultation
INSERT INTO workflow_skills (workflow_id, skill_id, functional_context_description)
VALUES
    ('30000000-0000-0000-0000-000000000001', '50000000-0000-0000-0000-000000000001', 'Retrieve verified clinical decisions from the Doctor DNA vault relevant to the patient scenario.'),
    ('30000000-0000-0000-0000-000000000001', '50000000-0000-0000-0000-000000000010', 'Synthesise patient history and investigation results into a clinical decision with reasoning.'),
    ('30000000-0000-0000-0000-000000000001', '50000000-0000-0000-0000-000000000005', 'If confidence < 0.70, escalate the case to a human physician for review.')
ON CONFLICT (workflow_id, skill_id) DO NOTHING;

-- Healthcare: Diagnostic Analysis
INSERT INTO workflow_skills (workflow_id, skill_id, functional_context_description)
VALUES
    ('30000000-0000-0000-0000-000000000002', '50000000-0000-0000-0000-000000000011', 'Generate a ranked differential diagnosis based on lab and imaging data.'),
    ('30000000-0000-0000-0000-000000000002', '50000000-0000-0000-0000-000000000012', 'Interpret abnormal lab values and flag critical results requiring immediate action.')
ON CONFLICT (workflow_id, skill_id) DO NOTHING;

-- IT: Sprint Planning
INSERT INTO workflow_skills (workflow_id, skill_id, functional_context_description)
VALUES
    ('30000000-0000-0000-0000-000000000003', '50000000-0000-0000-0000-000000000001', 'Retrieve relevant past sprint decisions and PM strategies from the IT DNA vault.'),
    ('30000000-0000-0000-0000-000000000003', '50000000-0000-0000-0000-000000000020', 'Calculate team velocity and available capacity to determine sprint scope.')
ON CONFLICT (workflow_id, skill_id) DO NOTHING;

-- IT: Risk & Escalation Management
INSERT INTO workflow_skills (workflow_id, skill_id, functional_context_description)
VALUES
    ('30000000-0000-0000-0000-000000000004', '50000000-0000-0000-0000-000000000021', 'Assess the timeline and delivery risk of each identified blocker.'),
    ('30000000-0000-0000-0000-000000000004', '50000000-0000-0000-0000-000000000022', 'Draft a concise stakeholder escalation note with impact analysis and recommended action.')
ON CONFLICT (workflow_id, skill_id) DO NOTHING;

-- Education: Concept Explanation Session
INSERT INTO workflow_skills (workflow_id, skill_id, functional_context_description)
VALUES
    ('30000000-0000-0000-0000-000000000005', '50000000-0000-0000-0000-000000000030', 'Identify the specific sub-concept the learner is struggling with before scaffolding begins.'),
    ('30000000-0000-0000-0000-000000000005', '50000000-0000-0000-0000-000000000031', 'Generate Socratic questions that guide the learner to discover the answer independently.')
ON CONFLICT (workflow_id, skill_id) DO NOTHING;

-- Education: Assessment & Feedback
INSERT INTO workflow_skills (workflow_id, skill_id, functional_context_description)
VALUES
    ('30000000-0000-0000-0000-000000000006', '50000000-0000-0000-0000-000000000001', 'Retrieve relevant rubric benchmarks and past tutor feedback patterns from the Education DNA vault.'),
    ('30000000-0000-0000-0000-000000000006', '50000000-0000-0000-0000-000000000032', 'Evaluate the learner submission against the defined rubric and produce a formative feedback report.')
ON CONFLICT (workflow_id, skill_id) DO NOTHING;
