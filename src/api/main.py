import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router

configured_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
configured_allowed_origins = [
    origin.strip().rstrip("/")
    for origin in configured_origins.split(",")
    if origin.strip()
]
frontend_origin = os.getenv(
    "VERCEL_FRONTEND_ORIGIN", "https://YOUR-FRONTEND.vercel.app"
).strip().rstrip("/")
dashboard_origin = os.getenv(
    "VERCEL_DASHBOARD_ORIGIN", "https://YOUR-DASHBOARD.vercel.app"
).strip().rstrip("/")
allowed_origins = list(
    dict.fromkeys(
        [
            "http://localhost:5500",
            "http://127.0.0.1:5500",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            frontend_origin,
            dashboard_origin,
            *configured_allowed_origins,
        ]
    )
)

app = FastAPI(title="ZeroKey Telemetry API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(router, prefix="/api")
