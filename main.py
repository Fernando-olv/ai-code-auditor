"""ASGI entrypoint for uvicorn (`uvicorn main:app`)."""

from app.factory import create_app

app = create_app()
