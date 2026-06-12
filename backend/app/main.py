"""
FastAPI Application Entry Point.

Assembles the application, registers middleware, and mounts route modules.
The ServiceProvider is initialized at startup to create all singletons.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import traceback

from backend.app.core.config import settings
from backend.app.core.middleware import PIISanitizationMiddleware
from backend.app.api.dependencies import provider

# Route modules
from backend.app.api.routes.config_routes import router as config_router
from backend.app.api.routes.session_routes import router as session_router
from backend.app.api.routes.preconsult_routes import router as preconsult_router
from backend.app.api.routes.auth_routes import router as auth_router
from backend.app.api.routes.workflow_runtime import router as workflow_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Zero-Trust PII Sanitization Middleware
app.add_middleware(PIISanitizationMiddleware)

# Register domain-specific route modules
app.include_router(config_router, prefix=settings.API_V1_STR)
app.include_router(session_router, prefix=settings.API_V1_STR)
app.include_router(preconsult_router, prefix=settings.API_V1_STR)
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(workflow_router, prefix=settings.API_V1_STR)


@app.on_event("startup")
async def startup_event():
    """Initialize the DI container singletons at application startup."""
    provider.initialize()


@app.get("/")
def read_root():
    return {"message": "Digital Twin Engine active. Version 1.0.0"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    with open("error_trace.log", "w") as f:
        f.write(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error. Stack trace dumped to error_trace.log"}
    )
