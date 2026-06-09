import sys, os
sys.path.append(os.path.abspath('.'))
from backend.app.core.config import settings
from supabase import create_client
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
res = supabase.table('pre_consultation_sessions').select('*').eq('session_id', '4f3ece5d-edcf-4048-b40a-694a71c8b734').execute()
print(res.data)
