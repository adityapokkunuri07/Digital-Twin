import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv("backend/.env")

url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
key = os.environ.get("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY")

supabase: Client = create_client(url, key)

res = supabase.table("doctor_workflows").select("*").execute()
print(f"doctor_workflows: {res.data}")
