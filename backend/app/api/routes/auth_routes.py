from fastapi import APIRouter, HTTPException, status
from supabase import create_client, Client
from backend.app.core.config import settings
from backend.app.api.schemas.auth_schemas import RegisterRequest, LoginRequest, AuthResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

# We'll use the Supabase client directly for this simple auth flow
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

@router.post("/register", response_model=AuthResponse)
async def register_patient(payload: RegisterRequest):
    """Register a new patient into the patients table."""
    try:
        # Check if exists
        existing = supabase.table("patients").select("*").eq("email", payload.email).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Email already registered")

        # In a real app, hash the password. For simulation, we store as-is or simple hash.
        record = {
            "email": payload.email,
            "password_hash": payload.password, # Plaintext for simulation purposes
            "full_name": payload.full_name
        }
        res = supabase.table("patients").insert(record).execute()
        
        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to create patient")
            
        data = res.data[0]
        return AuthResponse(
            patient_id=data["patient_id"],
            full_name=data["full_name"],
            email=data["email"],
            message="Registration successful"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login", response_model=AuthResponse)
async def login_patient(payload: LoginRequest):
    """Authenticate a patient."""
    try:
        res = supabase.table("patients").select("*").eq("email", payload.email).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Patient not found")
            
        patient = res.data[0]
        if patient["password_hash"] != payload.password:
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
        return AuthResponse(
            patient_id=patient["patient_id"],
            full_name=patient["full_name"],
            email=patient["email"],
            message="Login successful"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
