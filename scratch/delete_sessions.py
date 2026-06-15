import os
import asyncio
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv("backend/.env")

url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
key = os.environ.get("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY")

if not url or not key:
    print("Supabase credentials not found.")
    exit(1)

supabase: Client = create_client(url, key)

def delete_sessions():
    try:
        # Get all sessions
        res = supabase.table("pre_consultation_sessions").select("session_id").execute()
        if not res.data:
            print("No sessions found to delete.")
            return

        session_ids = [s["session_id"] for s in res.data]
        print(f"Found {len(session_ids)} sessions. Deleting...")

        # Delete all sessions
        for sid in session_ids:
            supabase.table("pre_consultation_sessions").delete().eq("session_id", sid).execute()
        
        print("All escalations and scheduled sessions have been deleted.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    delete_sessions()
