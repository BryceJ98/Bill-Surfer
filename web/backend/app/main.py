"""
main.py — Bill-Surfer FastAPI application entry point
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.routers import keys, docket, search, reports, export, chat, settings, explain, track, import_csv, memory, federal_register

load_dotenv()

app = FastAPI(
    title="Bill-Surfer API",
    description="Legislative research platform for political science researchers",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(keys.router,    prefix="/keys",    tags=["API Keys"])
app.include_router(docket.router,  prefix="/docket",  tags=["Docket"])
app.include_router(search.router,  prefix="/search",  tags=["Search"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])
app.include_router(export.router,  prefix="/export",  tags=["Export"])
app.include_router(chat.router,     prefix="/chat",     tags=["Chat"])
app.include_router(settings.router, prefix="/settings", tags=["Settings"])
app.include_router(explain.router,  prefix="/explain",  tags=["Explain"])
app.include_router(track.router,      prefix="/track",      tags=["Track"])
app.include_router(import_csv.router, prefix="/import",     tags=["Import"])
app.include_router(memory.router,           prefix="/memory",           tags=["Memory"])
app.include_router(federal_register.router, prefix="/federal-register", tags=["Federal Register"])


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
