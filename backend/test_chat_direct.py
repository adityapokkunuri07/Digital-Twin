import asyncio
import sys
import traceback
from uuid import UUID

async def main():
    try:
        from backend.app.api.dependencies import get_preconsult_service, provider
        provider.initialize() # ensure singletons
        service = get_preconsult_service()
        
        # Get latest session from db directly
        res = service._repo.client.table("pre_consultation_sessions").select("*").order("created_at", desc=True).limit(1).execute()
        if not res.data:
            print("No sessions found.")
            return
            
        session = res.data[0]
        session_id = UUID(session["session_id"])
        print(f"Using Session ID: {session_id}")
        
        try:
            print("Calling process_chat_turn...")
            class MockBackgroundTasks:
                def add_task(self, *args, **kwargs):
                    pass
                    
            msg = "im suffering with frequent urination at night and also have sugar cravings this is becuase of diabetes ?? also im trying for pregnancy does this affect for conceiving??"
            res = await service.process_chat_turn(session_id, msg, MockBackgroundTasks())
            print("Chat Response:", res)
        except Exception as e:
            print("Chat Exception!")
            traceback.print_exc()

    except Exception as e:
        print("Setup Exception!")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
