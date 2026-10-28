"""
EV Infrastructure & Route Optimization — FastAPI Application
─────────────────────────────────────────────────────────────
Main entry point. Serves the API and the frontend dashboard.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .services.data_loader import store
from .routers import stations, analytics, routes


# ── Lifespan: load data once on startup ────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    store.load()
    yield


app = FastAPI(
    title="EV Infrastructure & Route Optimization API",
    description="Data-driven EV charging station analytics, clustering, and route optimization.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────
app.include_router(stations.router)
app.include_router(analytics.router)
app.include_router(routes.router)

# ── Serve Frontend ─────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def serve_dashboard():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/health")
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "stations_loaded": len(store.df) if store.df is not None else 0,
    }
