import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
from backend.app.core.config import settings
from supabase import create_client

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

try:
    res = supabase.table("pre_consultation_sessions").select("session_id, status").eq("session_id", "9acf054d-0683-4627-a5a3-18187d4e157a").execute()
    print("Session Status:", res.data)
except Exception as e:
    print("Error:", e)
