import os
from supabase import create_client, Client
from dotenv import load_dotenv
from backend.app.core.config import settings

load_dotenv()

class SupabaseService:
    def __init__(self):
        url: str = settings.SUPABASE_URL
        key: str = settings.SUPABASE_KEY
        if not url or not key:
            print("Warning: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not found in environment.")
            self.client = None
        else:
            from supabase.client import ClientOptions
            options = ClientOptions(postgrest_client_timeout=5, storage_client_timeout=5)
            self.client: Client = create_client(url, key, options=options)

    def insert_chunks(self, chunks: list[dict]):
        if not self.client: return
        return self.client.table("document_chunks").insert(chunks).execute()

    def semantic_search(self, embedding: list[float], limit: int = 5):
        if not self.client: return []
        response = self.client.rpc("match_chunks", {
            "query_embedding": embedding,
            "match_threshold": 0.5,
            "match_count": limit
        }).execute()
        return response.data

    def insert_expert_dna(self, data: dict):
        """Final commit of expert-verified logic into the production vault."""
        if not self.client: return
        return self.client.table("expert_dna").insert(data).execute()

    def expert_vault_search(
        self,
        embedding: list[float],
        domain_id: str | None = None,
        workflow_id: str | None = None,
        limit: int = 1,
    ):
        """
        High-purity search against verified expert logic only.

        Args:
            embedding:    Query vector from EmbeddingService.
            domain_id:    Optional FK from the `domains` table. When provided,
                          restricts results to a single domain (e.g., Healthcare).
                          This is the primary isolation mechanism between twins.
            workflow_id:  Optional FK from the `workflows` table.
            limit:        Max results to return.
        """
        if not self.client: return []

        # Always call the 5-param overload to avoid Supabase PGRST203 ambiguity
        rpc_params = {
            "query_embedding": embedding,
            "match_threshold": 0.40,
            "match_count": limit,
            "p_domain_id": domain_id,
            "p_workflow_id": workflow_id,
        }

        response = self.client.rpc("match_expert_dna", rpc_params).execute()
        return response.data

    def insert_chat_audit_log(self, data: dict):
        """Logs the LangGraph chat execution trace to the database."""
        if not self.client: return
        return self.client.table("chat_audit_logs").insert(data).execute()

    def get_count(self, table: str) -> int:
        """Returns the total row count for a given table."""
        if not self.client: return 0
        try:
            # We use a select with head=True to just get the count
            response = self.client.table(table).select("*", count="exact").limit(0).execute()
            return response.count if response.count is not None else 0
        except Exception as e:
            print(f"Error fetching count for {table}: {e}")
            return 0

    def upload_document(self, file_bytes: bytes, file_path: str, bucket_name: str) -> dict:
        """Uploads a file to a Supabase Storage bucket. Returns dict with 'path' or 'error'."""
        if not self.client:
            return {"error": "Supabase client not initialized"}
        try:
            # Overwrite if exists
            res = self.client.storage.from_(bucket_name).upload(
                path=file_path,
                file=file_bytes,
                file_options={"upsert": "true"}
            )
            return {"path": file_path}
        except Exception as e:
            return {"error": str(e)}

    def list_documents(self, prefix: str, bucket_name: str) -> list:
        """Lists files in a Supabase Storage bucket under a specific prefix (folder)."""
        if not self.client:
            return []
        try:
            res = self.client.storage.from_(bucket_name).list(path=prefix)
            return res
        except Exception as e:
            print(f"[SupabaseService] list_documents error: {e}")
            return []

