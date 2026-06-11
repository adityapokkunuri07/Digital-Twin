-- =============================================================================
-- 12_seed_it_workflow_tasks.sql
-- Digital Twin — Seed IT Workflows and Tasks (Auto-Generated UUIDs)
-- =============================================================================
-- Uses gen_random_uuid() — the database generates real UUIDs.
-- References parent rows by NAME lookup instead of hardcoded UUIDs.
-- Safe to re-run — uses ON CONFLICT guards.
-- =============================================================================


-- ─────────────────────────────────────────────────────────────────────────────
-- 1. SEED WORKFLOWS (reference role by name)
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO workflows (id, role_id, name, description)
VALUES
  (
    gen_random_uuid(),
    (SELECT id FROM roles WHERE name = 'Project Manager' LIMIT 1),
    'Architecture Drift Detection',
    'Scans codebase to detect architectural deviations, rogue dependencies, and rule violations.'
  ),
  (
    gen_random_uuid(),
    (SELECT id FROM roles WHERE name = 'Project Manager' LIMIT 1),
    'Blast Radius Simulation',
    'Analyzes Git PR diffs and models downstream blast radius and infrastructure loads.'
  ),
  (
    gen_random_uuid(),
    (SELECT id FROM roles WHERE name = 'Project Manager' LIMIT 1),
    'Stakeholder Communication',
    'Tailors technical decisions into custom persona briefs and dispatches them via DOCX & SMTP.'
  )
ON CONFLICT (id) DO NOTHING;


-- ─────────────────────────────────────────────────────────────────────────────
-- 2. SEED DRIFT DETECTOR TASKS (reference workflow by name)
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO tasks (id, workflow_id, name, step_order, execution_mode, is_enabled)
VALUES
  (gen_random_uuid(), (SELECT id FROM workflows WHERE name = 'Architecture Drift Detection'), 'Resolve Repository',         1, 'ai_auto', true),
  (gen_random_uuid(), (SELECT id FROM workflows WHERE name = 'Architecture Drift Detection'), 'Clone & Snapshot',            2, 'ai_auto', true),
  (gen_random_uuid(), (SELECT id FROM workflows WHERE name = 'Architecture Drift Detection'), 'Load Architecture Rules',     3, 'ai_auto', true),
  (gen_random_uuid(), (SELECT id FROM workflows WHERE name = 'Architecture Drift Detection'), 'Scan Code',                   4, 'ai_auto', true),
  (gen_random_uuid(), (SELECT id FROM workflows WHERE name = 'Architecture Drift Detection'), 'Audit Config Files',          5, 'ai_auto', true),
  (gen_random_uuid(), (SELECT id FROM workflows WHERE name = 'Architecture Drift Detection'), 'Generate Violation Report',   6, 'ai_auto', true),
  (gen_random_uuid(), (SELECT id FROM workflows WHERE name = 'Architecture Drift Detection'), 'Post Report',                 7, 'ai_auto', true)
ON CONFLICT (id) DO NOTHING;


-- ─────────────────────────────────────────────────────────────────────────────
-- 3. SEED BLAST RADIUS SIMULATOR TASKS
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO tasks (id, workflow_id, name, step_order, execution_mode, is_enabled)
VALUES
  (gen_random_uuid(), (SELECT id FROM workflows WHERE name = 'Blast Radius Simulation'), 'Read PR Data',            1, 'ai_auto', true),
  (gen_random_uuid(), (SELECT id FROM workflows WHERE name = 'Blast Radius Simulation'), 'Parse Code Diffs',        2, 'ai_auto', true),
  (gen_random_uuid(), (SELECT id FROM workflows WHERE name = 'Blast Radius Simulation'), 'Profile Infrastructure',  3, 'ai_auto', true),
  (gen_random_uuid(), (SELECT id FROM workflows WHERE name = 'Blast Radius Simulation'), 'Simulate Risks',          4, 'ai_auto', true),
  (gen_random_uuid(), (SELECT id FROM workflows WHERE name = 'Blast Radius Simulation'), 'Post GitHub Comment',     5, 'ai_auto', true),
  (gen_random_uuid(), (SELECT id FROM workflows WHERE name = 'Blast Radius Simulation'), 'Save Simulation Report',  6, 'ai_auto', true)
ON CONFLICT (id) DO NOTHING;


-- ─────────────────────────────────────────────────────────────────────────────
-- 4. SEED COMMS TWIN TASKS (Expert Review defaults to 'human_only')
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO tasks (id, workflow_id, name, step_order, execution_mode, is_enabled)
VALUES
  (gen_random_uuid(), (SELECT id FROM workflows WHERE name = 'Stakeholder Communication'), 'Save Technical Decision',    1, 'ai_auto',    true),
  (gen_random_uuid(), (SELECT id FROM workflows WHERE name = 'Stakeholder Communication'), 'Assemble Persona Context',   2, 'ai_auto',    true),
  (gen_random_uuid(), (SELECT id FROM workflows WHERE name = 'Stakeholder Communication'), 'Generate Briefs',            3, 'ai_auto',    true),
  (gen_random_uuid(), (SELECT id FROM workflows WHERE name = 'Stakeholder Communication'), 'Expert Review',              4, 'human_only', true),
  (gen_random_uuid(), (SELECT id FROM workflows WHERE name = 'Stakeholder Communication'), 'Package DOCX Document',      5, 'ai_auto',    true),
  (gen_random_uuid(), (SELECT id FROM workflows WHERE name = 'Stakeholder Communication'), 'Dispatch Emails',            6, 'ai_auto',    true)
ON CONFLICT (id) DO NOTHING;
