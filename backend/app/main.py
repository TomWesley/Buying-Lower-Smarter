from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.db.database import init_db
from app.routers import training, analysis, models, data


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database
    await init_db()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="Stock Analysis - Biggest Losers",
    description="Analyze S&P 500 biggest daily losers and their recovery patterns",
    version="2.0.0",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(training.router, prefix="/api/training", tags=["training"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(models.router, prefix="/api/models", tags=["models"])
app.include_router(data.router, prefix="/api/data", tags=["data"])


@app.get("/")
async def root():
    return {
        "message": "Stock Analysis API",
        "docs": "/docs",
        "endpoints": {
            "training": "/api/training",
            "analysis": "/api/analysis",
            "models": "/api/models",
            "data": "/api/data"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
