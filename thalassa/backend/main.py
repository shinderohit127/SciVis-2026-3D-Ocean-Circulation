"""THALASSA backend — FastAPI application entry point."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.derived import router as derived_router
from api.jobs import router as jobs_router
from api.metadata import router as metadata_router
from api.overview import router as overview_router
from api.roi import router as roi_router
from api.scene import router as scene_router

app = FastAPI(
    title="THALASSA API",
    description="Multiscale visual analytics backend for ECCO LLC4320 ocean circulation.",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metadata_router, prefix="/api")
app.include_router(roi_router,      prefix="/api")
app.include_router(derived_router,  prefix="/api")
app.include_router(overview_router, prefix="/api")
app.include_router(scene_router,    prefix="/api")
app.include_router(jobs_router,     prefix="/api")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "0.3.0"}
