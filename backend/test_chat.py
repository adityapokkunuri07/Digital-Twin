import asyncio
import json
from uuid import UUID
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        # Get active session from DB or queue
        print("Getting active sessions...")
        try:
            # We will just fetch a session directly from Supabase, or we can just create a new one
            # Call /start
            payload = {
                "patient_id": "33333333-3333-3333-3333-333333333333",
                "config_id": "11111111-1111-1111-1111-111111111111"
            }
            res = await client.post("http://127.0.0.1:8000/api/pre-consult/start", json=payload)
            if res.status_code == 200:
                print("Start:", res.json())
                session_id = res.json()["session_id"]
            else:
                print(f"Start Error {res.status_code}: {res.text}")
                return
            
            # Call /chat
            chat_payload = {
                "session_id": session_id,
                "message": "My temperature is 104 and my chest feels tight"
            }
            res = await client.post("http://127.0.0.1:8000/api/pre-consult/chat", json=chat_payload)
            if res.status_code == 200:
                print("Chat Response:", res.json())
            else:
                print(f"Error {res.status_code}: {res.text}")
        except Exception as e:
            print("HTTP Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
