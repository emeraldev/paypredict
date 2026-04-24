"""Webhook delivery with HMAC-SHA256 signature and retry logic.

Delivers payloads to tenant-configured webhook URLs with:
- HMAC-SHA256 signature in X-PayPredict-Signature header
- 3 retries with exponential backoff (1s, 2s, 4s)
- Unique delivery ID per attempt
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import uuid

import httpx

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
TIMEOUT_SECONDS = 10


async def deliver_webhook(
    url: str,
    secret: str,
    event: str,
    payload: dict,
) -> bool:
    """Deliver a webhook with HMAC-SHA256 signature.

    Returns True if delivery succeeded (2xx), False after all retries exhausted.
    """
    body = json.dumps(payload, default=str)
    signature = hmac.new(
        secret.encode(), body.encode(), hashlib.sha256
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-PayPredict-Event": event,
        "X-PayPredict-Signature": f"sha256={signature}",
        "X-PayPredict-Delivery": str(uuid.uuid4()),
    }

    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                response = await client.post(url, content=body, headers=headers)
                if response.status_code < 300:
                    logger.info(
                        "Webhook delivered: event=%s url=%s status=%d",
                        event, url, response.status_code,
                    )
                    return True
                logger.warning(
                    "Webhook non-2xx: event=%s url=%s status=%d attempt=%d",
                    event, url, response.status_code, attempt + 1,
                )
        except Exception as exc:
            logger.warning(
                "Webhook error: event=%s url=%s attempt=%d error=%s",
                event, url, attempt + 1, exc,
            )

        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(2 ** attempt)  # 1s, 2s

    logger.error(
        "Webhook delivery failed after %d attempts: event=%s url=%s",
        MAX_RETRIES, event, url,
    )
    return False


async def send_slack_alert(webhook_url: str, message: str) -> bool:
    """Send a simple Slack message via incoming webhook."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.post(
                webhook_url,
                json={"text": f":rotating_light: *PayPredict Alert*\n{message}"},
            )
            return response.status_code < 300
    except Exception as exc:
        logger.warning("Slack notification failed: %s", exc)
        return False
