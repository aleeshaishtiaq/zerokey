import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router

configured_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
allowed_origins = [
    origin.strip().rstrip("/")
    for origin in configured_origins.split(",")
    if origin.strip()
]
if not allowed_origins:
    allowed_origins = [
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

app = FastAPI(title="ZeroKey Telemetry API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(router, prefix="/api")
