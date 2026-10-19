import sys
import os
from contextlib import asynccontextmanager

# Ensure workspace root and backend root are in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
workspace_dir = os.path.dirname(backend_dir)
for p in (workspace_dir, backend_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.database import init_db
from backend.app.routers import (
    health,
    repositories,
    issues,
    retrieval,
    mentor,
    contributions,
    verification,
    review,
    learning,
    benchmark,
    compliance
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database and FTS5 tables
    init_db()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Local-First AI Open-Source Contribution Mentor with Evidence Grounding, Setup Failure Doctor & Flight Recorder",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core Routers
app.include_router(health.router)
app.include_router(repositories.router)
app.include_router(issues.router)
app.include_router(retrieval.router)
app.include_router(mentor.router)
app.include_router(contributions.router)
app.include_router(verification.router)
app.include_router(review.router)
app.include_router(learning.router)
app.include_router(benchmark.router)
app.include_router(compliance.router)

# Mount Trust & Dataset extensions if available
try:
    from app.api.routes.trust import router as trust_router
    app.include_router(trust_router)
except Exception:
    pass

try:
    from app.api.routes.dataset import router as dataset_router, benchmark_router as ds_benchmark_router
    app.include_router(dataset_router)
    app.include_router(ds_benchmark_router)
except Exception:
    pass

@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "mission": "Turning unfamiliar repositories into verified open-source contributions",
        "docs": "/docs",
        "health": "/api/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
