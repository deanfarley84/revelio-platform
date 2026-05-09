from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, Base
from app.api.routes import auth, diagnostics, files, admin, benchmarks, intel, reports, notifications


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"Revelio API starting — environment: {settings.ENVIRONMENT}")

    # Auto-create tables on first boot (early-stage; replace with Alembic migrations in production)
    if settings.ENVIRONMENT in ("production", "development"):
        try:
            # Import models so they register against Base.metadata
            from app.models import user  # noqa: F401
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("Database tables ensured")
        except Exception as e:
            print(f"Warning: table creation failed: {e}")

    yield
    # Shutdown
    print("Revelio API shutting down")


app = FastAPI(
    title="Revelio API",
    description="Payments Revenue Leakage Diagnostic Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(diagnostics.router, prefix="/api/v1/diagnostics", tags=["Diagnostics"])
app.include_router(files.router, prefix="/api/v1/files", tags=["Files"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(benchmarks.router, prefix="/api/v1/benchmarks", tags=["Benchmarks"])
app.include_router(intel.router, prefix="/api/v1/intel", tags=["Intel"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "revelio-api"}
