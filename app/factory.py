"""FastAPI application factory."""

from fastapi import FastAPI

from app.api.health import router as health_router


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    application = FastAPI(title="AI Dev Auditor", version="0.1.0")
    application.include_router(health_router)
    return application
