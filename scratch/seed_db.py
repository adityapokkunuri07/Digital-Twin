import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv("backend/.env")

url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
key = os.environ.get("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY")
supabase: Client = create_client(url, key)

# 2. doctor_workflows
supabase.table("doctor_workflows").upsert({
    "id": "22222222-2222-2222-2222-222222222222",
    "config_id": "11111111-1111-1111-1111-111111111111",
    "doctor_id": "dr_sterling",
    "workflow_name": "Initial Cardiac Consult"
}).execute()

# 3. workflow_tasks
# Check if exists first to avoid unique constraint issues if running multiple times
res = supabase.table("workflow_tasks").select("*").eq("workflow_id", "22222222-2222-2222-2222-222222222222").eq("step_number", 1).execute()
if not res.data:
    supabase.table("workflow_tasks").insert({
        "workflow_id": "22222222-2222-2222-2222-222222222222",
        "step_number": 1,
        "task_name": "Assess Chest Pain",
        "node_alignment": "data_gathering",
        "strategy_identifier": "SYMPTOM_PARSER",
        "task_config": {"required_variables": ["chest_pain_severity", "fever"]}
    }).execute()

# 4. thresholds
# Delete old thresholds to ensure clean state
supabase.table("journalist_entity_thresholds").delete().eq("config_id", "11111111-1111-1111-1111-111111111111").execute()
supabase.table("journalist_entity_thresholds").insert({
    "config_id": "11111111-1111-1111-1111-111111111111",
    "doctor_id": "dr_sterling",
    "entity_name": "fever",
    "max_allowable_value": 103.0,
    "critical_escalation_triggers": ["unbearable pain", "passing out"]
}).execute()

print("Database successfully seeded for testing.")
