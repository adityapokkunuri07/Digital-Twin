import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Digital Twin Engine"
    API_V1_STR: str = "/api"
    
    # Supabase Credentials (optional, triggers Mock DB mode if empty)
    # Using alias because frontend likely uses the NEXT_PUBLIC prefix.
    SUPABASE_URL: str = Field(default="", alias="NEXT_PUBLIC_SUPABASE_URL")
    SUPABASE_KEY: str = Field(default="", alias="NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY")
    
    # Gemini API Key
    GEMINI_API_KEY: str = ""
    
    # Obsidian Vault Export Destination (relative to project root)
    OBSIDIAN_VAULT_PATH: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
        "obsidian_vault"
    )
    
    # Embedding Configuration
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix=""
    )

settings = Settings()
