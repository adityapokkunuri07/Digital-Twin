-- =============================================================================
-- 17_task_output_format.sql
-- Digital Twin — Add custom output formatting per task
-- =============================================================================

-- 1. Add the column
ALTER TABLE tasks 
ADD COLUMN IF NOT EXISTS output_format TEXT;

-- 2. Seed the output format for the 'Generate Briefs' task
UPDATE tasks 
SET output_format = '- Architectural Assessment
- Critical Violations & Risks (based on your rules)
- Mandatory Remediation Steps'
WHERE name = 'Generate Briefs';
