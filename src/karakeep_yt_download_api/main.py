"""FastAPI app: receives Karakeep webhooks and archives YouTube videos."""

import asyncio
import contextlib
import hmac
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from karakeep_yt_download_api import downloader, jellyfin
from karakeep_yt_download_api.config import Settings, get_settings
from karakeep_yt_download_api.models import KarakeepWebhook
from karakeep_yt_download_api.youtube import is_youtube_video_url

logger = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)


async def verify_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Reject requests without the configured bearer token (constant-time compare)."""
    expected = settings.webhook_token.get_secret_value().encode()
    given = credentials.credentials.encode() if credentials else b""
    if not hmac.compare_digest(given, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token", headers={"WWW-Authenticate": "Bearer"})


async def _process(url: str, settings: Settings, client: httpx.AsyncClient) -> None:
    try:
        new = await asyncio.to_thread(downloader.download, url, settings)
    except Exception:
        logger.exception("Download failed for %s", url)
        return
    if not new:
        logger.info("Already archived, skipping scan: %s", url)
        return
    logger.info("Downloaded %s", url)
    try:
        await jellyfin.refresh_library(client, settings)
    except httpx.HTTPError:
        logger.exception("Jellyfin refresh failed after downloading %s", url)


async def _worker(queue: asyncio.Queue[str], settings: Settings, client: httpx.AsyncClient) -> None:
    while True:
        url = await queue.get()
        try:
            await _process(url, settings, client)
        finally:
            queue.task_done()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Start the single download worker and shared HTTP client."""
    settings = get_settings()
    app.state.queue = asyncio.Queue(maxsize=settings.queue_size)
    async with httpx.AsyncClient() as client:
        task = asyncio.create_task(_worker(app.state.queue, settings, client))
        yield
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="karakeep-yt-download-api", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness/readiness probe."""
    return {"status": "ok"}


@app.post("/webhook", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(verify_token)])
async def webhook(payload: KarakeepWebhook, request: Request) -> dict[str, str]:
    """Queue a download for created YouTube bookmarks; ignore everything else."""
    if payload.operation != "created" or not payload.url or not is_youtube_video_url(payload.url):
        return {"status": "ignored"}
    queue: asyncio.Queue[str] = request.app.state.queue
    try:
        queue.put_nowait(payload.url)
    except asyncio.QueueFull:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Queue full") from None
    return {"status": "queued"}
