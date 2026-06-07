import os
import logging
import httpx
import asyncpg
from arq.connections import RedisSettings
from backend.app.services.saga_orchestrator import SagaOrchestrator

logger = logging.getLogger("ArqWorker")

# Configurations
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
DATABASE_URL = os.getenv("DATABASE_POOLER_URL", "postgresql://postgres:postgres@localhost:6543/postgres")

async def on_startup(ctx):
    """Initializes asyncpg connection pool and httpx client for the worker."""
    logger.info("Initializing worker resources...")
    ctx['http_client'] = httpx.AsyncClient(timeout=10.0)
    ctx['db_pool'] = await asyncpg.create_pool(
        dsn=DATABASE_URL,
        min_size=2,
        max_size=10
    )
    logger.info("Worker pool connected to DB on transaction port 6543.")

async def on_shutdown(ctx):
    """Cleans up worker resources on shutdown."""
    logger.info("Closing worker resources...")
    if ctx.get('http_client'):
        await ctx['http_client'].aclose()
    if ctx.get('db_pool'):
        await ctx['db_pool'].close()
    logger.info("Worker shutdown complete.")

async def execute_booking_saga_task(ctx, session_id: str, preferred_date: str, time_slot: str) -> str:
    """Consumes the task, instantiates the SagaOrchestrator, and executes it."""
    db_pool = ctx['db_pool']
    http_client = ctx['http_client']
    
    logger.info(f"Starting booking saga for session {session_id} on {preferred_date} at {time_slot}...")
    orchestrator = SagaOrchestrator(db_pool=db_pool, http_client=http_client)
    
    status = await orchestrator.run(session_id, preferred_date, time_slot)
    logger.info(f"Finished booking saga for session {session_id} with status: {status}")
    return status

class WorkerSettings:
    functions = [execute_booking_saga_task]
    redis_settings = RedisSettings(host=REDIS_HOST, port=REDIS_PORT)
    on_startup = on_startup
    on_shutdown = on_shutdown
    concurrency = 50
