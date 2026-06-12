import asyncio
from uuid import UUID
from backend.app.api.dependencies import hybrid_rag_engine, provider

async def main():
    provider.initialize()
    # Find the config ID from latest session
    from backend.app.api.dependencies import supabase_preconsult_repo
    res = supabase_preconsult_repo.client.table("pre_consultation_sessions").select("*").order("created_at", desc=True).limit(1).execute()
    if not res.data:
        print("No sessions.")
        return
    session = res.data[0]
    config_id = UUID(session["config_id"])
    
    print(f"Testing search for config: {config_id}")
    query = "Vital Signs Blood Pressure"
    context, selected, rejected = await hybrid_rag_engine.retrieve_context(config_id, query)
    
    print("Selected Chunks:", len(selected))
    if selected:
        print("Top score:", selected[0].get("combined_score"))

if __name__ == "__main__":
    asyncio.run(main())
