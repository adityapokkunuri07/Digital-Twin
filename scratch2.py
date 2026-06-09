import asyncio
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

supabase = create_client(supabase_url, supabase_key)

try:
    res = supabase.table("appointments").select("*").execute()
    print("Appointments:", res.data)
except Exception as e:
    print("Error:", e)
