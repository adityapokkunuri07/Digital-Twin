import asyncio
import sys
from backend.app.core.config import settings
from backend.app.repositories.supabase_config_repo import SupabaseConfigRepository
from backend.app.services.embedding.gemini_embedder import GeminiEmbeddingService

async def test_integration():
    print(f"Loaded NEXT_PUBLIC_SUPABASE_URL: {'Yes' if settings.SUPABASE_URL else 'No'}")
    print(f"Loaded NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: {'Yes' if settings.SUPABASE_KEY else 'No'}")
    print(f"Loaded GEMINI_API_KEY: {'Yes' if settings.GEMINI_API_KEY else 'No'}")
    
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        print("ERROR: Supabase credentials missing from config.")
        sys.exit(1)
        
    if not settings.GEMINI_API_KEY:
        print("ERROR: Gemini API Key missing from config.")
        sys.exit(1)

    # 1. Test Supabase
    print("\n--- Testing Supabase Connection ---")
    try:
        repo = SupabaseConfigRepository(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        if repo.use_mock:
            print("ERROR: Supabase connection fell back to Mock mode. Check credentials or network.")
        else:
            # Try a simple query
            res = repo.client.table("expert_twin_configs").select("config_id").limit(1).execute()
            print("SUCCESS: Supabase connection successful!")
    except Exception as e:
        print(f"ERROR: Supabase connection failed: {e}")

    # 2. Test Gemini
    print("\n--- Testing Gemini Connection ---")
    try:
        embedder = GeminiEmbeddingService(settings.GEMINI_API_KEY)
        if embedder.use_fallback:
            print("ERROR: Gemini embedder fell back to mock mode. Check google-generativeai installation.")
        else:
            vec = embedder.get_embedding("Hello world, this is a test.")
            if vec and len(vec) == 768:
                print("SUCCESS: Gemini API connection successful! Successfully generated 768-dimensional embedding.")
            else:
                print(f"ERROR: Gemini API returned unexpected vector dimension: {len(vec) if vec else 0}")
    except Exception as e:
        print(f"ERROR: Gemini connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_integration())
