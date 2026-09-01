from dataclasses import dataclass
from html import unescape
import ipaddress
import os
from pathlib import Path
import re
import socket
from typing import Callable, Literal
from urllib.parse import quote, urljoin, urlparse

import cv2
import httpx

from app.models import AssetRef

_EXTENSION_KINDS = {
    ".gif": "image",
    ".jpeg": "image",
    ".jpg": "image",
    ".png": "image",
    ".webp": "image",
    ".mov": "video",
    ".mp4": "video",
    ".webm": "video",
}

_STOP_WORDS = {
    "a",
    "an",
    "and",
    "is",
    "it",
    "much",
    "new",
    "of",
    "runs",
    "the",
    "this",
}

_SAFE_PROVIDER_HOSTS = {
    "wikimedia-commons": {"upload.wikimedia.org"},
    "pexels": {"images.pexels.com", "videos.pexels.com"},
    "pixabay": {"cdn.pixabay.com"},
}

_FREE_LICENSE_MARKERS = (
    "cc by",
    "cc0",
    "creative commons",
    "public domain",
    "pdm",
)


@dataclass(frozen=True)
class RemoteAssetCandidate:
    provider: str
    remote_id: str
    kind: Literal["image", "video"]
    download_url: str
    source_url: str
    title: str
    creator: str | None
    license: str
    license_url: str
    width: int | None
    height: int | None
    file_size: int | None
    keywords: list[str]


@dataclass(frozen=True)
class RemoteAssetRequest:
    query: str
    keywords: list[str]
    start_ms: int
    end_ms: int


def discover_local_assets(
    library_root: Path,
    *,
    text: str,
    start_ms: int,
    end_ms: int,
    limit: int = 3,
) -> list[AssetRef]:
    if not library_root.is_dir() or end_ms <= start_ms:
        return []
    query_tokens = _tokens(text)
    candidates: list[tuple[int, Path, list[str]]] = []
    for path in library_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in _EXTENSION_KINDS:
            continue
        asset_tokens = _tokens(path.stem)
        overlap = sorted(query_tokens.intersection(asset_tokens))
        if overlap:
            candidates.append((len(overlap), path, overlap))
    candidates.sort(key=lambda item: (-item[0], item[1].name.lower()))

    assets: list[AssetRef] = []
    for index, (_score, path, keywords) in enumerate(candidates[:limit], start=1):
        license_path = path.with_suffix(".license.txt")
        license_text = (
            license_path.read_text(encoding="utf-8").strip()
            if license_path.is_file()
            else None
        )
        assets.append(
            AssetRef(
                id=f"local-asset-{index}",
                kind=_EXTENSION_KINDS[path.suffix.lower()],
                path=str(path.resolve()),
                keywords=keywords,
                provenance="local-library",
                license=license_text,
                start_ms=start_ms,
                end_ms=end_ms,
            )
        )
    return assets


def search_wikimedia_commons(
    client: httpx.Client,
    *,
    query: str,
    limit: int = 6,
) -> list[RemoteAssetCandidate]:
    response = client.get(
        "https://commons.wikimedia.org/w/api.php",
        params={
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,
            "gsrlimit": max(1, min(limit * 3, 30)),
            "prop": "imageinfo",
            "iiprop": "url|mime|size|extmetadata",
            "iiurlwidth": 1080,
            "format": "json",
            "formatversion": 2,
        },
        headers={"User-Agent": _internet_user_agent()},
    )
    response.raise_for_status()
    pages = response.json().get("query", {}).get("pages", {})
    if isinstance(pages, list):
        iterable = pages
    elif isinstance(pages, dict):
        iterable = pages.values()
    else:
        return []

    candidates: list[RemoteAssetCandidate] = []
    for page in iterable:
        imageinfo = page.get("imageinfo") or []
        if not imageinfo:
            continue
        info = imageinfo[0]
        metadata = info.get("extmetadata") or {}
        license_name = _metadata_value(metadata, "LicenseShortName")
        license_url = _metadata_value(metadata, "LicenseUrl")
        if (
            not license_name
            or not license_url
            or not _is_reusable_license(license_name)
        ):
            continue
        mime = str(info.get("mime") or "").lower()
        if mime.startswith("image/"):
            kind: Literal["image", "video"] = "image"
            download_url = info.get("thumburl") or info.get("url")
        elif mime in {"video/webm", "video/mp4", "video/ogg"}:
            kind = "video"
            download_url = info.get("url")
        else:
            continue
        if not download_url:
            continue
        title = str(page.get("title") or "").removeprefix("File:")
        description = _clean_metadata_text(
            _metadata_value(metadata, "ImageDescription")
        )
        creator = _clean_metadata_text(
            _metadata_value(metadata, "Artist")
        ) or None
        page_title = str(page.get("title") or title).replace(" ", "_")
        candidates.append(
            RemoteAssetCandidate(
                provider="wikimedia-commons",
                remote_id=str(page.get("pageid") or page_title),
                kind=kind,
                download_url=str(download_url),
                source_url=(
                    "https://commons.wikimedia.org/wiki/"
                    + quote(page_title, safe=":_()-")
                ),
                title=title or description or query,
                creator=creator,
                license=license_name,
                license_url=license_url,
                width=_optional_int(info.get("width")),
                height=_optional_int(info.get("height")),
                file_size=_optional_int(info.get("size")),
                keywords=sorted(
                    _tokens(f"{title} {description} {query}")
                ),
            )
        )
        if len(candidates) >= limit:
            break
    return candidates


def search_pexels(
    client: httpx.Client,
    *,
    query: str,
    api_key: str,
    limit: int = 6,
) -> list[RemoteAssetCandidate]:
    if not api_key:
        return []
    headers = {"Authorization": api_key}
    per_type = max(1, min(limit, 20))
    photos_response = client.get(
        "https://api.pexels.com/v1/search",
        params={"query": query, "per_page": per_type, "orientation": "portrait"},
        headers=headers,
    )
    photos_response.raise_for_status()
    videos_response = client.get(
        "https://api.pexels.com/videos/search",
        params={"query": query, "per_page": per_type, "orientation": "portrait"},
        headers=headers,
    )
    videos_response.raise_for_status()

    photo_candidates: list[RemoteAssetCandidate] = []
    for photo in photos_response.json().get("photos", []):
        sources = photo.get("src") or {}
        download_url = (
            sources.get("portrait")
            or sources.get("large2x")
            or sources.get("large")
            or sources.get("original")
        )
        if not download_url:
            continue
        title = str(photo.get("alt") or query)
        photo_candidates.append(
            RemoteAssetCandidate(
                provider="pexels",
                remote_id=str(photo.get("id")),
                kind="image",
                download_url=str(download_url),
                source_url=str(photo.get("url")),
                title=title,
                creator=photo.get("photographer"),
                license="Pexels License",
                license_url="https://www.pexels.com/license/",
                width=_optional_int(photo.get("width")),
                height=_optional_int(photo.get("height")),
                file_size=None,
                keywords=sorted(_tokens(f"{title} {query}")),
            )
        )
    video_candidates: list[RemoteAssetCandidate] = []
    for video in videos_response.json().get("videos", []):
        selected = _select_video_file(video.get("video_files") or [])
        if selected is None:
            continue
        creator = (video.get("user") or {}).get("name")
        video_candidates.append(
            RemoteAssetCandidate(
                provider="pexels",
                remote_id=str(video.get("id")),
                kind="video",
                download_url=str(selected.get("link")),
                source_url=str(video.get("url")),
                title=query,
                creator=creator,
                license="Pexels License",
                license_url="https://www.pexels.com/license/",
                width=_optional_int(selected.get("width")),
                height=_optional_int(selected.get("height")),
                file_size=_optional_int(selected.get("size")),
                keywords=sorted(_tokens(query)),
            )
        )
    candidates: list[RemoteAssetCandidate] = []
    while len(candidates) < limit and (
        video_candidates or photo_candidates
    ):
        if video_candidates:
            candidates.append(video_candidates.pop(0))
        if len(candidates) < limit and photo_candidates:
            candidates.append(photo_candidates.pop(0))
    return candidates


def search_pixabay(
    client: httpx.Client,
    *,
    query: str,
    api_key: str,
    limit: int = 6,
) -> list[RemoteAssetCandidate]:
    if not api_key:
        return []
    per_type = max(3, min(limit, 20))
    common = {
        "key": api_key,
        "q": query,
        "safesearch": "true",
        "per_page": per_type,
    }
    images_response = client.get(
        "https://pixabay.com/api/",
        params={**common, "image_type": "photo", "orientation": "vertical"},
    )
    images_response.raise_for_status()
    videos_response = client.get(
        "https://pixabay.com/api/videos/",
        params=common,
    )
    videos_response.raise_for_status()

    candidates: list[RemoteAssetCandidate] = []
    for image in images_response.json().get("hits", []):
        download_url = image.get("largeImageURL") or image.get("webformatURL")
        if not download_url:
            continue
        title = str(image.get("tags") or query)
        candidates.append(
            RemoteAssetCandidate(
                provider="pixabay",
                remote_id=str(image.get("id")),
                kind="image",
                download_url=str(download_url),
                source_url=str(image.get("pageURL")),
                title=title,
                creator=image.get("user"),
                license="Pixabay Content License",
                license_url=(
                    "https://pixabay.com/service/license-summary/"
                ),
                width=_optional_int(image.get("imageWidth")),
                height=_optional_int(image.get("imageHeight")),
                file_size=None,
                keywords=sorted(_tokens(f"{title} {query}")),
            )
        )
    for video in videos_response.json().get("hits", []):
        selected = _select_pixabay_video(video.get("videos") or {})
        if selected is None:
            continue
        title = str(video.get("tags") or query)
        candidates.append(
            RemoteAssetCandidate(
                provider="pixabay",
                remote_id=str(video.get("id")),
                kind="video",
                download_url=str(selected.get("url")),
                source_url=str(video.get("pageURL")),
                title=title,
                creator=video.get("user"),
                license="Pixabay Content License",
                license_url=(
                    "https://pixabay.com/service/license-summary/"
                ),
                width=_optional_int(selected.get("width")),
                height=_optional_int(selected.get("height")),
                file_size=_optional_int(selected.get("size")),
                keywords=sorted(_tokens(f"{title} {query}")),
            )
        )
    return candidates[:limit]


def discover_internet_assets(
    requests: list[RemoteAssetRequest],
    destination_dir: Path,
) -> list[AssetRef]:
    if not requests:
        return []
    mode = os.getenv("VIDEO_EDITOR_INTERNET_ASSETS", "auto").lower()
    if mode == "off":
        return []
    providers = [
        item.strip().lower()
        for item in os.getenv(
            "VIDEO_EDITOR_ASSET_PROVIDERS",
            "pexels,pixabay,wikimedia",
        ).split(",")
        if item.strip()
    ]
    timeout = httpx.Timeout(25, connect=10)
    downloaded: list[AssetRef] = []
    used_ids: set[tuple[str, str]] = set()
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        for request in requests:
            candidates: list[RemoteAssetCandidate] = []
            for provider in providers:
                try:
                    if provider == "pexels":
                        candidates.extend(
                            search_pexels(
                                client,
                                query=request.query,
                                api_key=os.getenv("PEXELS_API_KEY", ""),
                                limit=4,
                            )
                        )
                    elif provider == "pixabay":
                        candidates.extend(
                            search_pixabay(
                                client,
                                query=request.query,
                                api_key=os.getenv("PIXABAY_API_KEY", ""),
                                limit=4,
                            )
                        )
                    elif provider in {"wikimedia", "wikimedia-commons"}:
                        candidates.extend(
                            search_wikimedia_commons(
                                client,
                                query=request.query,
                                limit=6,
                            )
                        )
                except (httpx.HTTPError, ValueError, KeyError, TypeError):
                    continue
            ranked = sorted(
                candidates,
                key=lambda candidate: _remote_candidate_score(
                    candidate,
                    request,
                ),
                reverse=True,
            )
            for candidate in ranked:
                key = (candidate.provider, candidate.remote_id)
                if key in used_ids:
                    continue
                try:
                    asset = download_remote_asset(
                        client,
                        candidate,
                        destination_dir=destination_dir,
                    )
                except (httpx.HTTPError, OSError, ValueError):
                    continue
                used_ids.add(key)
                downloaded.append(
                    asset.model_copy(
                        update={
                            "id": f"internet-asset-{len(downloaded) + 1}",
                            "keywords": sorted(
                                {
                                    *candidate.keywords,
                                    *request.keywords,
                                }
                            ),
                            "search_query": request.query,
                            "start_ms": request.start_ms,
                            "end_ms": request.end_ms,
                        }
                    )
                )
                break
    if mode == "required" and not downloaded:
        raise RuntimeError("No licensed internet assets could be downloaded")
    return downloaded


def download_remote_asset(
    client: httpx.Client,
    candidate: RemoteAssetCandidate,
    *,
    destination_dir: Path,
    max_bytes: int = 80 * 1024 * 1024,
    host_resolver: Callable[[str], list[str]] | None = None,
) -> AssetRef:
    if candidate.file_size is not None and candidate.file_size > max_bytes:
        raise ValueError("Remote asset exceeds size limit")
    resolver = host_resolver or _resolve_host
    destination_dir.mkdir(parents=True, exist_ok=True)
    current_url = candidate.download_url
    safe_provider = re.sub(r"[^a-z0-9-]", "-", candidate.provider.lower())
    safe_remote_id = re.sub(
        r"[^a-zA-Z0-9_-]",
        "-",
        candidate.remote_id,
    )
    destination: Path | None = None
    for _redirect in range(4):
        _validate_remote_url(
            current_url,
            provider=candidate.provider,
            host_resolver=resolver,
        )
        with client.stream(
            "GET",
            current_url,
            headers={"User-Agent": _internet_user_agent()},
            follow_redirects=False,
        ) as response:
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location")
                if not location:
                    raise ValueError(
                        "Remote asset redirect is missing a location"
                    )
                current_url = urljoin(current_url, location)
                continue
            response.raise_for_status()

            content_length = _optional_int(
                response.headers.get("content-length")
            )
            if content_length is not None and content_length > max_bytes:
                raise ValueError("Remote asset exceeds size limit")
            extension = _remote_extension(
                candidate.kind,
                response.headers.get("content-type"),
                current_url,
            )
            destination = (
                destination_dir
                / f"{safe_provider}-{safe_remote_id}{extension}"
            )
            partial = destination.with_suffix(destination.suffix + ".part")
            total = 0
            try:
                with partial.open("wb") as output:
                    for chunk in response.iter_bytes():
                        if not chunk:
                            continue
                        total += len(chunk)
                        if total > max_bytes:
                            raise ValueError(
                                "Remote asset exceeds size limit"
                            )
                        output.write(chunk)
                if total == 0:
                    raise ValueError("Remote asset is empty")
                partial.replace(destination)
            except Exception:
                partial.unlink(missing_ok=True)
                raise
        break
    else:
        raise ValueError("Remote asset has too many redirects")
    assert destination is not None
    try:
        _validate_downloaded_media(destination, candidate.kind)
    except Exception:
        destination.unlink(missing_ok=True)
        raise

    return AssetRef(
        id=f"internet-{safe_provider}-{safe_remote_id}",
        kind=candidate.kind,
        path=str(destination.resolve()),
        keywords=candidate.keywords,
        provenance=f"internet:{candidate.provider}",
        license=candidate.license,
        provider=candidate.provider,
        remote_id=candidate.remote_id,
        creator=candidate.creator,
        source_url=candidate.source_url,
        license_url=candidate.license_url,
    )


def _validate_remote_url(
    url: str,
    *,
    provider: str,
    host_resolver: Callable[[str], list[str]],
) -> None:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in {None, 443}
    ):
        raise ValueError("Remote asset URL is not safe HTTPS")
    allowed_hosts = _SAFE_PROVIDER_HOSTS.get(provider)
    if not allowed_hosts or parsed.hostname.lower() not in allowed_hosts:
        raise ValueError("Remote asset host is not approved")
    addresses = host_resolver(parsed.hostname)
    if not addresses:
        raise ValueError("Remote asset host could not be resolved")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError("Remote asset host resolves to a private address")


def _resolve_host(host: str) -> list[str]:
    return sorted(
        {
            item[4][0]
            for item in socket.getaddrinfo(
                host,
                443,
                type=socket.SOCK_STREAM,
            )
        }
    )


def _validate_downloaded_media(
    path: Path,
    kind: Literal["image", "video"],
) -> None:
    if kind == "image":
        image = cv2.imread(str(path))
        if image is None or image.shape[0] < 32 or image.shape[1] < 32:
            raise ValueError("Downloaded image is not decodable")
        return
    capture = cv2.VideoCapture(str(path))
    try:
        if (
            not capture.isOpened()
            or capture.get(cv2.CAP_PROP_FRAME_COUNT) < 1
            or capture.get(cv2.CAP_PROP_FRAME_WIDTH) < 64
            or capture.get(cv2.CAP_PROP_FRAME_HEIGHT) < 64
        ):
            raise ValueError("Downloaded video is not decodable")
    finally:
        capture.release()


def _remote_candidate_score(
    candidate: RemoteAssetCandidate,
    request: RemoteAssetRequest,
) -> float:
    overlap = len(set(candidate.keywords).intersection(request.keywords))
    portrait_bonus = 0.0
    if candidate.width and candidate.height:
        ratio = candidate.width / candidate.height
        portrait_bonus = max(0.0, 1.0 - abs(ratio - 9 / 16))
    video_bonus = 0.35 if candidate.kind == "video" else 0.0
    return overlap * 3 + portrait_bonus + video_bonus


def _select_video_file(files: list[dict]) -> dict | None:
    compatible = [
        item
        for item in files
        if item.get("file_type") == "video/mp4" and item.get("link")
    ]
    if not compatible:
        return None
    return min(
        compatible,
        key=lambda item: (
            abs(
                (_optional_int(item.get("width")) or 1)
                / (_optional_int(item.get("height")) or 1)
                - 9 / 16
            ),
            -(_optional_int(item.get("height")) or 0),
        ),
    )


def _select_pixabay_video(videos: dict) -> dict | None:
    for key in ("medium", "large", "small", "tiny"):
        candidate = videos.get(key)
        if candidate and candidate.get("url"):
            return candidate
    return None


def _remote_extension(
    kind: Literal["image", "video"],
    content_type: str | None,
    url: str,
) -> str:
    normalized_type = (content_type or "").split(";")[0].strip().lower()
    by_type = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "video/ogg": ".ogv",
    }
    extension = by_type.get(normalized_type)
    if extension:
        return extension
    url_extension = Path(urlparse(url).path).suffix.lower()
    allowed = (
        {".jpg", ".jpeg", ".png", ".webp"}
        if kind == "image"
        else {".mp4", ".webm", ".ogv"}
    )
    if url_extension in allowed:
        return ".jpg" if url_extension == ".jpeg" else url_extension
    raise ValueError("Remote asset content type is unsupported")


def _metadata_value(metadata: dict, key: str) -> str:
    value = metadata.get(key)
    if isinstance(value, dict):
        value = value.get("value")
    return str(value or "").strip()


def _clean_metadata_text(value: str) -> str:
    return " ".join(
        unescape(re.sub(r"<[^>]+>", " ", value)).split()
    )


def _is_reusable_license(value: str) -> bool:
    normalized = value.lower()
    return any(marker in normalized for marker in _FREE_LICENSE_MARKERS)


def _internet_user_agent() -> str:
    return os.getenv(
        "VIDEO_EDITOR_USER_AGENT",
        "Cutline/1.0 (local licensed-media editor)",
    )


def _optional_int(value) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 1 and token not in _STOP_WORDS
    }
