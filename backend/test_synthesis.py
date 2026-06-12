import asyncio
from uuid import UUID
from backend.app.api.dependencies import provider

async def test_synth():
    provider.initialize()
    
    # Get the latest session that is SYNTHESIZING
    res = provider.session_repo.client.table("pre_consultation_sessions").select("*").eq("status", "SYNTHESIZING").order("created_at", desc=True).limit(1).execute()
    if not res.data:
        print("No SYNTHESIZING session found.")
        return
        
    session_id = UUID(res.data[0]["session_id"])
    print(f"Testing synthesis for session: {session_id}")
    
    try:
        await provider._orchestrator.execute_synthesis_subgraph(session_id, False, "Completed Workflow")
        print("Done.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_synth())
