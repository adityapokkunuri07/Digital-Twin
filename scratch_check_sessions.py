import sys, os
sys.path.append(os.path.abspath('.'))
from backend.app.core.config import settings
from supabase import create_client
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
res = supabase.table('pre_consultation_sessions').select('session_id, status, created_at').order('created_at', desc=True).limit(3).execute()
print(res.data)
