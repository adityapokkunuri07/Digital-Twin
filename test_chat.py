import httpx
import asyncio

async def test():
    async with httpx.AsyncClient() as client:
        # Get active sessions
        print("Getting active sessions...")
        res = await client.get("http://localhost:8000/api/pre-consult/queue/active")
        if res.status_code != 200:
            print("Failed to get active sessions:", res.text)
            return
        
        sessions = res.json()
        if not sessions:
            print("No active sessions.")
            return
            
        session_id = sessions[-1]["session_id"]
        print("Using session:", session_id)
        
        # Chat
        print("Sending message...")
        res2 = await client.post("http://localhost:8000/api/gateway/chat", json={
            "session_id": session_id,
            "message": "i have an stomach pain"
        })
        print(res2.json())

if __name__ == "__main__":
    asyncio.run(test())
