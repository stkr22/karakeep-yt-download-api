# karakeep-yt-download-api

A small sidecar for [Karakeep](https://karakeep.app) that archives bookmarked YouTube videos into a
[Jellyfin](https://jellyfin.org) library. Karakeep's own video download stores files in an opaque asset store;
this service writes regular, properly named files to a folder you mount, so Jellyfin can treat it as a real library.

```
Karakeep ──webhook (created, bearer token)──▶ karakeep-yt-download-api ──yt-dlp──▶ library folder (NFS)
                                                         │
                                                         └──API key──▶ Jellyfin: refresh that library only
```

## How it works

1. Karakeep sends `POST /webhook` with `Authorization: Bearer <token>` for each new bookmark.
2. The token is verified in constant time (`401` otherwise). Events other than `created`, and URLs that are not a
   single YouTube video (`youtube.com/watch`, `/shorts/`, `/live/`, `/embed/`, `youtu.be/<id>`), are ignored.
3. Accepted URLs are answered with `202` immediately and downloaded one at a time by a background worker, so
   Karakeep's webhook timeout is not an issue. A full queue returns `503` and Karakeep retries.
4. yt-dlp writes `<Channel>/<Title> [<VIDEOID>].<ext>` (or flat without the channel folder, see `KYT_CHANNEL_FOLDERS`) plus a `.info.json` and a `.jpg` thumbnail next to it, which
   the Jellyfin YouTube metadata plugin can read. A yt-dlp download archive prevents downloading a video twice.
5. After a new download the service calls `POST /Items/{libraryId}/Refresh` on Jellyfin, so only the YouTube library
   is scanned. Deleting and managing videos stays in Jellyfin.

Other endpoints: `GET /healthz`.

## Configuration

All settings are environment variables with the `KYT_` prefix.

| Variable | Default | Description |
|---|---|---|
| `KYT_WEBHOOK_TOKEN` | required | Bearer token configured in the Karakeep webhook |
| `KYT_LIBRARY_PATH` | required | Directory of the Jellyfin YouTube library |
| `KYT_JELLYFIN_URL` | required | Jellyfin base URL, e.g. `https://jellyfin.example.lan` |
| `KYT_JELLYFIN_API_KEY` | required | Jellyfin API key (Dashboard → API Keys) |
| `KYT_JELLYFIN_LIBRARY_ID` | required | Item ID of the library to refresh (`GET /Library/VirtualFolders`, field `ItemId`) |
| `KYT_YTDLP_FORMAT` | `bestvideo*+bestaudio/best` | yt-dlp format selector |
| `KYT_YTDLP_MERGE_FORMAT` | `mkv` | Container for merged streams |
| `KYT_CHANNEL_FOLDERS` | `true` | `true`: `<Channel>/<Title> [<id>].<ext>`; `false`: flat `<Title> [<id>].<ext>` |
| `KYT_YTDLP_COOKIES_FILE` | unset | Netscape `cookies.txt` for age-gated or members-only videos |
| `KYT_YTDLP_ARCHIVE_FILE` | `<library>/.yt-dlp-archive.txt` | yt-dlp download archive |
| `KYT_QUEUE_SIZE` | `100` | Maximum number of pending downloads |

## Karakeep setup

Settings → Webhooks → add `http://<service>:8000/webhook`, event **created**, and the same bearer token as
`KYT_WEBHOOK_TOKEN`. If Karakeep and this service run in a cluster with network policies, allow Karakeep → this
service on port 8000. Karakeep may also need the host listed in `CRAWLER_ALLOWED_INTERNAL_HOSTNAMES` when it
resolves to a private address.

## Run locally

```bash
uv sync
KYT_WEBHOOK_TOKEN=secret KYT_LIBRARY_PATH=./library \
KYT_JELLYFIN_URL=https://jellyfin.example.lan KYT_JELLYFIN_API_KEY=... KYT_JELLYFIN_LIBRARY_ID=... \
  uv run uvicorn karakeep_yt_download_api.main:app --port 8000
```

ffmpeg must be installed locally (the container image includes it). Deno and the yt-dlp challenge solver, which
YouTube extraction needs, are installed as Python dependencies.

## Deploy

The container image is published to `ghcr.io/stkr22/karakeep-yt-download-api` and the Helm chart
(a wrapper around the [bjw-s app-template](https://github.com/bjw-s-labs/helm-charts)) to
`oci://ghcr.io/stkr22/charts/karakeep-yt-download-api`, both on every GitHub release.

Create a secret with the webhook token and API key, then set the NFS mount and library ID:

```bash
kubectl create secret generic karakeep-yt-download-api \
  --from-literal=webhook-token=... --from-literal=jellyfin-api-key=...
```

```yaml
# values.yaml
app-template:
  controllers:
    main:
      containers:
        main:
          env:
            KYT_JELLYFIN_URL: https://jellyfin.example.lan
            KYT_JELLYFIN_LIBRARY_ID: <library item id>
  persistence:
    library:
      server: nfs.example.lan
      path: /export/media/youtube
```

The container runs as UID/GID 1001 with a read-only root filesystem, so that user needs write access to the NFS path.
Jellyfin should mount the same folder as its YouTube library.

## Development

```bash
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run ty check
```

Commits follow [Conventional Commits](https://www.conventionalcommits.org); releases are cut by release-please,
which needs the repository secrets `APP_ID` and `APP_PRIVATE_KEY` (a GitHub App that may open PRs).

## License

GPL-3.0-only, see [LICENSE](LICENSE).
