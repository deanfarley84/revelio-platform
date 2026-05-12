import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler

from app.core.config import settings
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.middleware import RequestContextMiddleware
from app.core.rate_limit import limiter
from app.api.routes import auth, diagnostics, files, admin, benchmarks, intel, reports, notifications, invitations

logger = logging.getLogger("vyre")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


async def _init_schema_safely() -> None:
    """
    Best-effort table creation + lightweight column migrations + default
    seed. Runs in a background task so /health responds fast on cold start.
    If the DB is unreachable we log and continue - the next request hitting
    a DB-backed route will surface the real error.

    Column migrations: Base.metadata.create_all only creates missing tables,
    it does not alter existing ones. For new columns added after the first
    deploy we run idempotent ADD COLUMN IF NOT EXISTS statements here. This
    is the pragmatic stand-in for Alembic until migrations are wired.
    """
    try:
        from app.models import user  # noqa: F401  register models on Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables ensured")
    except Exception as e:
        logger.warning("Schema init failed (will retry on first DB request): %s", e)
        return

    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.execute(text(
                "ALTER TABLE organisations ADD COLUMN IF NOT EXISTS is_demo BOOLEAN NOT NULL DEFAULT FALSE"
            ))
            await conn.execute(text(
                "ALTER TABLE diagnostics ADD COLUMN IF NOT EXISTS is_demo BOOLEAN NOT NULL DEFAULT FALSE"
            ))
            # Brand alignment: rename the original bootstrap org through
            # any of its previous names to "Outturn Operator". Idempotent
            # because the WHERE clause stops matching after the first run.
            await conn.execute(text(
                "UPDATE organisations SET name = 'Outturn Operator' "
                "WHERE name IN ('Vyre Operator', 'Vyre Operator')"
            ))
        logger.info("Column migrations applied")
    except Exception as e:
        logger.warning("Column migration failed (non-fatal): %s", e)

    try:
        from app.services.seed_defaults import seed_all
        async with AsyncSessionLocal() as db:
            result = await seed_all(db)
            if result.get("benchmarks_inserted"):
                logger.info("Default seed: %s", result)
    except Exception as e:
        logger.warning("Default seed failed (non-fatal): %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Outturn API starting in %s mode", settings.ENVIRONMENT)
    # Fire-and-forget so the health check passes immediately and Render
    # doesn't kill the boot waiting on Postgres.
    asyncio.create_task(_init_schema_safely())
    yield
    logger.info("Outturn API shutting down")


app = FastAPI(
    title="Outturn API",
    description="Payments Revenue Leakage Diagnostic Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

# slowapi: per-IP rate limiting on hot endpoints. Limiter is in-memory
# which is fine on single-instance free / Starter plans. Move to Redis
# storage when we go multi-instance.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(invitations.router, prefix="/api/v1/invitations", tags=["Invitations"])
app.include_router(diagnostics.router, prefix="/api/v1/diagnostics", tags=["Diagnostics"])
app.include_router(files.router, prefix="/api/v1/files", tags=["Files"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(benchmarks.router, prefix="/api/v1/benchmarks", tags=["Benchmarks"])
app.include_router(intel.router, prefix="/api/v1/intel", tags=["Intel"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])


@app.get("/health")
async def health():
    """Liveness probe - returns 200 as long as the process is alive."""
    return {"status": "ok", "service": "vyre-api"}


@app.get("/ready")
async def ready():
    """Readiness probe - returns 200 only when the DB is reachable."""
    from sqlalchemy import text
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "ready", "db": "ok"}
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"status": "not_ready", "db": str(e)})


@app.get("/")
async def root():
    return {"service": "vyre-api", "version": "1.0.0", "status": "ok"}
