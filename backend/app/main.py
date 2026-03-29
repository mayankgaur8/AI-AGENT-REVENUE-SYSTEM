"""
Revenue-Generating AI Agent System
FastAPI Application Entry Point
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.config import settings
from app.db import init_db
from app.routes.agents import router as agents_router
from app.routes.leads import router as leads_router
from app.routes.proposals import router as proposals_router
from app.routes.outreach import router as outreach_router
from app.routes.revenue import router as revenue_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB and scheduler on startup."""
    logger.info("Starting Revenue AI Agent System...")
    await init_db()
    logger.info("Database initialized")

    # Setup daily scheduler (APScheduler)
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        from app.db import AsyncSessionLocal
        from app.agents.orchestrator import OrchestratorAgent

        scheduler = AsyncIOScheduler()

        async def run_daily_job():
            async with AsyncSessionLocal() as db:
                orchestrator = OrchestratorAgent()
                report = await orchestrator.run_daily(db=db, use_mock=True)
                logger.info(f"Scheduled daily run complete: {report['summary']}")

        # Run daily at 8:00 AM
        scheduler.add_job(
            run_daily_job,
            CronTrigger(hour=8, minute=0),
            id="daily_pipeline",
            name="Daily Revenue Pipeline",
        )
        scheduler.start()
        logger.info("Daily scheduler started (runs at 08:00)")
        app.state.scheduler = scheduler
    except Exception as e:
        logger.warning(f"Scheduler setup failed (non-critical): {e}")

    yield

    # Shutdown
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown(wait=False)
    logger.info("Revenue AI Agent System stopped")


app = FastAPI(
    title="Revenue AI Agent System",
    description="AI-powered freelance opportunity finder and proposal generator",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
allowed_origins = [
    origin for origin in {
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:5173",
        "https://ai-agent-revenue-system.vercel.app",
    }
    if origin
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(agents_router)
app.include_router(leads_router)
app.include_router(proposals_router)
app.include_router(outreach_router)
app.include_router(revenue_router)


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API docs."""
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Revenue AI Agent System"}


@app.get("/api/health")
async def api_health():
    """Health check reachable via the /api prefix (same path as frontend baseURL)."""
    return {"status": "ok", "service": "Revenue AI Agent System", "api_prefix": True}


@app.get("/api/config")
async def get_config():
    return {
        "candidate_name": settings.CANDIDATE_NAME,
        "candidate_skills": settings.CANDIDATE_SKILLS,
        "candidate_years": settings.CANDIDATE_YEARS,
        "ai_enabled": bool(settings.ANTHROPIC_API_KEY),
        "environment": settings.ENVIRONMENT,
    }


@app.get("/debug/routes", include_in_schema=False)
async def debug_routes():
    """List all registered routes — useful for verifying deployment."""
    routes = []
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            routes.append({
                "path": route.path,
                "methods": sorted(route.methods) if route.methods else [],
                "name": getattr(route, "name", ""),
            })
    return {"routes": sorted(routes, key=lambda r: r["path"]), "total": len(routes)}
