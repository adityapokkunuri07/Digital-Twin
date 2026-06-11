# 🧠 Skills & Knowledge Framework: Architectural File Map

If you want to extract or port the system that dynamically maps human knowledge (`expert_dna`) to executable tasks (`blueprints`) and skills, you will need to look at the following files in the codebase. 

I've categorized them by layer so you know exactly what each file does in the pipeline.

---

## 1. Database Schema Layer (Supabase / PostgreSQL)
These files define the relational tables and the seed data required to make the framework run.
- [NEW] [16_knowledge_framework.sql](file:///d:/season_1_dt/sql_schemas/16_knowledge_framework.sql)
  - **Purpose:** Defines the core tables: `expert_dna` (raw rules), `knowledge_hub` (parsed step-by-step logic), and `task_blueprints` (compiled JSON execution payloads).
- [MODIFY] [03_hierarchy_and_skills.sql](file:///d:/season_1_dt/sql_schemas/03_hierarchy_and_skills.sql)
  - **Purpose:** Defines the taxonomy tables: `tasks`, `workflows`, and `skill_definitions` (the available tools the LLM can use).
- [MODIFY] [17_task_output_format.sql](file:///d:/season_1_dt/sql_schemas/17_task_output_format.sql)
  - **Purpose:** Adds the `output_format` constraint column to the tasks table.
- [NEW] [04_seed_domains_and_roles.sql](file:///d:/season_1_dt/sql_schemas/04_seed_domains_and_roles.sql) & [12_seed_it_workflow_tasks.sql](file:///d:/season_1_dt/sql_schemas/12_seed_it_workflow_tasks.sql)
  - **Purpose:** Seeds the initial data, roles, and IT workflow tasks (e.g., "Generate Briefs") so the LLM knows what to map to.

---

## 2. Backend Services Layer (Python)
These are the core engines that handle the actual data processing, calling the LLMs, and assembling the logic.
- [NEW] [knowledge_ingestion.py](file:///d:/season_1_dt/backend/app/services/knowledge_ingestion.py)
  - **Purpose:** The "Parser Engine". It takes raw, unstructured rules from `expert_dna`, sends them to `gpt-4o-mini`, and asks it to map those rules to specific `tasks` and `required_actions` (skills). It then saves the output to `knowledge_hub`.
- [NEW] [task_assembler.py](file:///d:/season_1_dt/backend/app/services/task_assembler.py)
  - **Purpose:** The "Compiler Engine". When a task is requested, this script pulls all the matched rules from `knowledge_hub`, bundles them up into an array, attaches the required skills, and generates the final JSON `task_blueprint`.

---

## 3. Backend API & Orchestration Layer (Python)
These are the FastAPI endpoints that trigger the engines and serve data to the frontend.
- [MODIFY] [chat.py](file:///d:/season_1_dt/backend/app/api/chat.py)
  - **Purpose:** The primary orchestrator. When the user sends a chat message, it:
    1. Matches the request to a task (e.g., "Generate Briefs").
    2. Calls `knowledge_ingestion.py` to parse the rules.
    3. Calls `task_assembler.py` to get the blueprint.
    4. *Injects* the blueprint's rules and skills directly into the LLM system prompt before executing the chat completion.
- [MODIFY] [workflow_runtime.py](file:///d:/season_1_dt/backend/app/api/workflow_runtime.py)
  - **Purpose:** Contains the `GET /api/workflows/knowledge-proofs` endpoint. This is the API that the Twin Brain UI uses to fetch the parsed rules and blueprints to display the visual graph.

---

## 4. Skills Library Layer (Python)
Once the blueprint maps a rule to a `required_action` (like `SKL_IT_STAKEHOLDER_COMM.task_generate_briefs`), the LLM needs to be able to execute it. This folder contains all the callable python functions.
- [MODIFY] `backend/app/skills/functional/it/stakeholder_comm.py` (and the entire `backend/app/skills/` directory)
  - **Purpose:** These are the actual Python functions wrapped with `@tool` decorators that the LLM uses to take action (e.g. generating the DOCX, sending an email).

---

## 5. Identity & Context Layer (Python)
- [MODIFY] [base_adapter.py](file:///d:/season_1_dt/backend/app/adapters/base_adapter.py) & [domain_router.py](file:///d:/season_1_dt/backend/app/adapters/domain_router.py)
  - **Purpose:** The adapter pattern ensures that the system always knows which `expert_id`, `domain`, and `role` is currently active, so it pulls the correct rules for the correct user.

---

## 6. Frontend Visualization Layer (Next.js / React)
- [MODIFY] [page.js](file:///d:/season_1_dt/frontend/src/app/skills/page.js)
  - **Purpose:** The Next.js routing page where the visualization is hosted.
- [MODIFY] [KnowledgeProofsViewer.js](file:///d:/season_1_dt/frontend/src/components/skills/KnowledgeProofsViewer.js)
  - **Purpose:** This is the "Digital Twin Brain & Blueprint Assembly" UI component you shared in your screenshot. It fetches data from `workflow_runtime.py` and renders the flow from Task -> Expert Knowledge -> Skill Selection.
