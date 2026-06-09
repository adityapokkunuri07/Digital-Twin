import sys, os
sys.path.append(os.path.abspath('.'))
from backend.app.core.config import settings
from supabase import create_client
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
res = supabase.table('patients').select('*').execute()
print(res.data)
