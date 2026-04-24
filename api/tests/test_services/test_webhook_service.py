"""Tests for webhook delivery service."""
import hashlib
import hmac
import json

import pytest
from unittest.mock import AsyncMock, patch

from app.services.webhook_service import deliver_webhook, send_slack_alert


@pytest.mark.asyncio
async def test_deliver_webhook_success():
    """Successful delivery returns True."""
    mock_response = AsyncMock()
    mock_response.status_code = 200

    with patch("app.services.webhook_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await deliver_webhook(
            url="https://example.com/hook",
            secret="test-secret",
            event="bulk_scoring_complete",
            payload={"job_id": "123", "total": 50},
        )

    assert result is True
    mock_client.post.assert_called_once()

    # Verify HMAC signature was sent
    call_kwargs = mock_client.post.call_args
    headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})
    assert "X-PayPredict-Signature" in headers
    assert "X-PayPredict-Event" in headers
    assert headers["X-PayPredict-Event"] == "bulk_scoring_complete"

    # Verify signature is correct
    body = call_kwargs.kwargs.get("content") or call_kwargs[1].get("content", "")
    expected_sig = hmac.new(
        b"test-secret", body.encode(), hashlib.sha256
    ).hexdigest()
    assert headers["X-PayPredict-Signature"] == f"sha256={expected_sig}"


@pytest.mark.asyncio
async def test_deliver_webhook_retries_on_failure():
    """Retries up to 3 times on failure."""
    mock_response = AsyncMock()
    mock_response.status_code = 500

    with patch("app.services.webhook_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with patch("app.services.webhook_service.asyncio.sleep", new_callable=AsyncMock):
            result = await deliver_webhook(
                url="https://example.com/hook",
                secret="s",
                event="test",
                payload={},
            )

    assert result is False
    assert mock_client.post.call_count == 3


@pytest.mark.asyncio
async def test_deliver_webhook_retries_on_exception():
    """Retries on network exceptions."""
    with patch("app.services.webhook_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with patch("app.services.webhook_service.asyncio.sleep", new_callable=AsyncMock):
            result = await deliver_webhook(
                url="https://example.com/hook",
                secret="s",
                event="test",
                payload={},
            )

    assert result is False
    assert mock_client.post.call_count == 3


@pytest.mark.asyncio
async def test_send_slack_alert_success():
    """Slack notification returns True on success."""
    mock_response = AsyncMock()
    mock_response.status_code = 200

    with patch("app.services.webhook_service.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await send_slack_alert(
            "https://hooks.slack.com/services/xxx",
            "10 of 50 collections scored as high risk",
        )

    assert result is True
