from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.database import init_db
from backend.app.routers import health, repositories, issues, retrieval, mentor, contributions, verification, review, learning, benchmark

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

# Include Routers
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
