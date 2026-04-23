"""GitHub webhook endpoints."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.services.webhook_service import parse_pull_request_event, verify_github_signature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/github")
async def github_webhook(request: Request) -> dict[str, object]:
    settings = get_settings()
    if not settings.github_webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    body = await request.body()
    signature_256 = request.headers.get("X-Hub-Signature-256", "")

    if not verify_github_signature(body, signature_256, settings.github_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = request.headers.get("X-GitHub-Event", "")
    delivery = request.headers.get("X-GitHub-Delivery", "")

    if event == "ping":
        logger.info("github_webhook_ping", extra={"delivery": delivery, "event": event})
        return JSONResponse(status_code=200, content={"status": "ok"})

    if event != "pull_request":
        logger.info(
            "github_webhook_ignored",
            extra={"delivery": delivery, "event": event},
        )
        return JSONResponse(status_code=202, content={"ignored": True})

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    pr_event = parse_pull_request_event(payload)
    logger.info(
        "github_webhook_pull_request",
        extra={
            "delivery": delivery,
            "event": event,
            "repo": pr_event.repository_full_name,
            "action": pr_event.action,
            "pr_number": pr_event.pr_number,
            "head_sha": pr_event.head_sha,
        },
    )

    return JSONResponse(status_code=202, content={"accepted": True})
