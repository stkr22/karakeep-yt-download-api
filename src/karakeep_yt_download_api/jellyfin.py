"""Minimal Jellyfin API client."""

import logging

import httpx

from karakeep_yt_download_api.config import Settings

logger = logging.getLogger(__name__)


async def refresh_library(client: httpx.AsyncClient, settings: Settings) -> None:
    """Trigger a scan of only the configured YouTube library."""
    token = settings.jellyfin_api_key.get_secret_value()
    response = await client.post(
        f"{settings.jellyfin_url.rstrip('/')}/Items/{settings.jellyfin_library_id}/Refresh",
        params={
            "Recursive": "true",
            "MetadataRefreshMode": "Default",
            "ImageRefreshMode": "Default",
            "ReplaceAllMetadata": "false",
            "ReplaceAllImages": "false",
        },
        headers={"Authorization": f'MediaBrowser Token="{token}"'},
        timeout=settings.jellyfin_timeout_sec,
    )
    response.raise_for_status()
    logger.info("Jellyfin library refresh triggered")
