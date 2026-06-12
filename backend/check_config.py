import asyncio
from uuid import UUID
from backend.app.api.dependencies import supabase_config_repo, provider
import json

async def main():
    provider.initialize()
    # Get the latest config
    res = supabase_config_repo.client.table("expert_configurations").select("*").order("created_at", desc=True).limit(1).execute()
    if not res.data:
        print("No configs found.")
        return
    
    config = res.data[0]
    print(f"Config ID: {config['config_id']}")
    print(f"Workflow Config: {json.dumps(config.get('workflow_config', {}), indent=2)}")

if __name__ == "__main__":
    asyncio.run(main())
