import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Digital Twin Engine"
    API_V1_STR: str = "/api"
    
    # Supabase Credentials (optional, triggers Mock DB mode if empty)
    SUPABASE_URL: str = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "")
    
    # OpenAI & LLM (optional fallback models)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Obsidian Vault Export Destination
    OBSIDIAN_VAULT_PATH: str = os.getenv("OBSIDIAN_VAULT_PATH", "c:/Users/harin/Downloads/doctor/Digital-Twin/obsidian_vault")
    
    # Embedding Configuration
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    
    class Config:
        case_sensitive = True

settings = Settings()
