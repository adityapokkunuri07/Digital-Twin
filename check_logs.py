import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("backend/.env")

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("No env vars")
    sys.exit(1)

client = create_client(url, key)
res = client.table("interaction_logs").select("*").execute()
print(f"Total logs: {len(res.data)}")
print(res.data)
