"""FastAPI application factory."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    return FastAPI(title="AI Dev Auditor", version="0.1.0")
