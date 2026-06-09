import asyncio
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
from backend.app.core.config import settings
from supabase import create_client

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

try:
    res = supabase.table("appointments").select("*, patients(full_name, email)").execute()
    print("Success:", res.data)
except Exception as e:
    print("Error:", e)
