import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from webapp.backend.database import init_db
from webapp.backend.routes_assets import router as assets_router
from webapp.backend.routes_config import router as config_router
from webapp.backend.routes_portfolio import router as portfolio_router
from webapp.backend.routes_analysis import router as analysis_router
from src.utils.analysts import ANALYST_CONFIG

app = FastAPI(title="AI Hedge Fund")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assets_router)
app.include_router(config_router)
app.include_router(portfolio_router)
app.include_router(analysis_router)


@app.get("/api/analysts")
def get_analysts():
    return [
        {"key": key, "display_name": config["display_name"], "description": config["description"], "order": config["order"]}
        for key, config in sorted(ANALYST_CONFIG.items(), key=lambda x: x[1]["order"])
    ]


# Serve frontend static files
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="static")

    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        # Serve the file if it exists, otherwise serve index.html for SPA routing
        file_path = os.path.join(FRONTEND_DIR, path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.on_event("startup")
def startup():
    init_db()
