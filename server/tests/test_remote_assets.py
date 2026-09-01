from pathlib import Path

import cv2
import httpx
import numpy as np
import pytest

from app.editor import assets


def make_client(payload: dict, *, content: bytes | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if content is not None:
            return httpx.Response(
                200,
                content=content,
                headers={"content-type": "image/jpeg"},
                request=request,
            )
        return httpx.Response(200, json=payload, request=request)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_wikimedia_search_returns_only_reusable_media_with_provenance() -> None:
    payload = {
        "query": {
            "pages": {
                "10": {
                    "pageid": 10,
                    "title": "File:Foreign exchange market.jpg",
                    "imageinfo": [
                        {
                            "url": "https://upload.wikimedia.org/example.jpg",
                            "thumburl": (
                                "https://upload.wikimedia.org/example-1080.jpg"
                            ),
                            "mime": "image/jpeg",
                            "width": 1600,
                            "height": 1067,
                            "extmetadata": {
                                "LicenseShortName": {"value": "CC BY-SA 4.0"},
                                "LicenseUrl": {
                                    "value": (
                                        "https://creativecommons.org/"
                                        "licenses/by-sa/4.0/"
                                    )
                                },
                                "Artist": {"value": "Example Photographer"},
                                "ImageDescription": {
                                    "value": "Foreign exchange trading screens"
                                },
                            },
                        }
                    ],
                },
                "11": {
                    "pageid": 11,
                    "title": "File:Unknown.jpg",
                    "imageinfo": [
                        {
                            "url": "https://upload.wikimedia.org/unknown.jpg",
                            "mime": "image/jpeg",
                            "width": 1000,
                            "height": 700,
                            "extmetadata": {},
                        }
                    ],
                },
            }
        }
    }

    candidates = assets.search_wikimedia_commons(
        make_client(payload),
        query="forex trading screens",
        limit=4,
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.provider == "wikimedia-commons"
    assert candidate.kind == "image"
    assert candidate.license == "CC BY-SA 4.0"
    assert candidate.creator == "Example Photographer"
    assert candidate.download_url.endswith("example-1080.jpg")
    assert candidate.source_url.startswith(
        "https://commons.wikimedia.org/wiki/"
    )


def test_pexels_search_parses_real_photo_and_video_results() -> None:
    photo_payload = {
        "photos": [
            {
                "id": 123,
                "url": "https://www.pexels.com/photo/123/",
                "photographer": "A. Creator",
                "photographer_url": "https://www.pexels.com/@creator",
                "width": 1200,
                "height": 1800,
                "alt": "Trading monitor",
                "src": {
                    "portrait": "https://images.pexels.com/photo.jpg"
                },
            }
        ]
    }
    video_payload = {
        "videos": [
            {
                "id": 456,
                "url": "https://www.pexels.com/video/456/",
                "user": {"name": "Video Creator"},
                "video_files": [
                    {
                        "id": 1,
                        "quality": "hd",
                        "file_type": "video/mp4",
                        "width": 1080,
                        "height": 1920,
                        "link": "https://videos.pexels.com/video.mp4",
                        "size": 10_000_000,
                    }
                ],
            }
        ]
    }
    responses = iter([photo_payload, video_payload])

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "test-key"
        return httpx.Response(200, json=next(responses), request=request)

    candidates = assets.search_pexels(
        httpx.Client(transport=httpx.MockTransport(handler)),
        query="trading monitor",
        api_key="test-key",
        limit=4,
    )

    assert {candidate.kind for candidate in candidates} == {"image", "video"}
    assert all(candidate.license == "Pexels License" for candidate in candidates)
    assert {candidate.remote_id for candidate in candidates} == {"123", "456"}


def test_pexels_search_keeps_video_results_when_photos_fill_the_limit() -> None:
    photo_payload = {
        "photos": [
            {
                "id": index,
                "url": f"https://www.pexels.com/photo/{index}/",
                "photographer": "Photo Creator",
                "width": 1200,
                "height": 1800,
                "alt": "Static result",
                "src": {
                    "portrait": f"https://images.pexels.com/{index}.jpg"
                },
            }
            for index in range(1, 5)
        ]
    }
    video_payload = {
        "videos": [
            {
                "id": 456,
                "url": "https://www.pexels.com/video/456/",
                "user": {"name": "Video Creator"},
                "video_files": [
                    {
                        "id": 1,
                        "quality": "hd",
                        "file_type": "video/mp4",
                        "width": 1080,
                        "height": 1920,
                        "link": "https://videos.pexels.com/video.mp4",
                        "size": 10_000_000,
                    }
                ],
            }
        ]
    }
    responses = iter([photo_payload, video_payload])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=next(responses), request=request)

    candidates = assets.search_pexels(
        httpx.Client(transport=httpx.MockTransport(handler)),
        query="moving subject",
        api_key="test-key",
        limit=4,
    )

    assert any(candidate.kind == "video" for candidate in candidates)


def test_pixabay_search_parses_real_photo_and_video_results() -> None:
    image_payload = {
        "hits": [
            {
                "id": 321,
                "pageURL": "https://pixabay.com/photos/trading-321/",
                "user": "Image Creator",
                "largeImageURL": "https://cdn.pixabay.com/image.jpg",
                "imageWidth": 1920,
                "imageHeight": 1280,
                "tags": "trading, monitor, finance",
            }
        ]
    }
    video_payload = {
        "hits": [
            {
                "id": 654,
                "pageURL": "https://pixabay.com/videos/trading-654/",
                "user": "Video Creator",
                "tags": "trading, chart",
                "videos": {
                    "medium": {
                        "url": "https://cdn.pixabay.com/video.mp4",
                        "width": 1080,
                        "height": 1920,
                        "size": 12_000_000,
                    }
                },
            }
        ]
    }
    responses = iter([image_payload, video_payload])

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["key"] == "test-key"
        return httpx.Response(200, json=next(responses), request=request)

    candidates = assets.search_pixabay(
        httpx.Client(transport=httpx.MockTransport(handler)),
        query="trading monitor",
        api_key="test-key",
        limit=4,
    )

    assert {candidate.kind for candidate in candidates} == {"image", "video"}
    assert all(
        candidate.license == "Pixabay Content License"
        for candidate in candidates
    )


def test_download_remote_asset_rejects_private_or_insecure_urls(
    tmp_path: Path,
) -> None:
    candidate = assets.RemoteAssetCandidate(
        provider="wikimedia-commons",
        remote_id="1",
        kind="image",
        download_url="http://127.0.0.1/private.jpg",
        source_url="https://commons.wikimedia.org/wiki/File:Private.jpg",
        title="Private",
        creator="Unknown",
        license="CC BY 4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        width=1000,
        height=1000,
        file_size=None,
        keywords=["private"],
    )

    with pytest.raises(ValueError, match="safe HTTPS"):
        assets.download_remote_asset(
            make_client({}, content=b"not-used"),
            candidate,
            destination_dir=tmp_path,
        )


def test_download_remote_asset_validates_image_and_records_metadata(
    tmp_path: Path,
) -> None:
    ok, encoded = cv2.imencode(
        ".jpg",
        np.full((80, 120, 3), 180, dtype=np.uint8),
    )
    assert ok
    candidate = assets.RemoteAssetCandidate(
        provider="wikimedia-commons",
        remote_id="10",
        kind="image",
        download_url="https://upload.wikimedia.org/example.jpg",
        source_url=(
            "https://commons.wikimedia.org/wiki/"
            "File:Foreign_exchange_market.jpg"
        ),
        title="Foreign exchange market",
        creator="Example Photographer",
        license="CC BY-SA 4.0",
        license_url="https://creativecommons.org/licenses/by-sa/4.0/",
        width=120,
        height=80,
        file_size=len(encoded),
        keywords=["foreign", "exchange", "market"],
    )

    downloaded = assets.download_remote_asset(
        make_client({}, content=encoded.tobytes()),
        candidate,
        destination_dir=tmp_path,
        host_resolver=lambda _host: ["93.184.216.34"],
    )

    assert Path(downloaded.path).is_file()
    assert downloaded.provenance == "internet:wikimedia-commons"
    assert downloaded.provider == "wikimedia-commons"
    assert downloaded.remote_id == "10"
    assert downloaded.creator == "Example Photographer"
    assert downloaded.source_url == candidate.source_url
    assert downloaded.license_url == candidate.license_url


def test_download_remote_asset_enforces_maximum_size(tmp_path: Path) -> None:
    candidate = assets.RemoteAssetCandidate(
        provider="pexels",
        remote_id="20",
        kind="video",
        download_url="https://videos.pexels.com/large.mp4",
        source_url="https://www.pexels.com/video/20/",
        title="Large video",
        creator="Creator",
        license="Pexels License",
        license_url="https://www.pexels.com/license/",
        width=1080,
        height=1920,
        file_size=200_000_000,
        keywords=["large"],
    )

    with pytest.raises(ValueError, match="size limit"):
        assets.download_remote_asset(
            make_client({}, content=b"x"),
            candidate,
            destination_dir=tmp_path,
            max_bytes=50_000_000,
            host_resolver=lambda _host: ["93.184.216.34"],
        )


def test_download_remote_asset_stops_streaming_at_size_limit(
    tmp_path: Path,
) -> None:
    class GuardedStream(httpx.SyncByteStream):
        def __iter__(self):
            yield b"a" * 700
            yield b"b" * 700
            raise AssertionError("download read beyond the configured limit")

    candidate = assets.RemoteAssetCandidate(
        provider="wikimedia-commons",
        remote_id="stream-limit",
        kind="image",
        download_url="https://upload.wikimedia.org/stream.jpg",
        source_url="https://commons.wikimedia.org/wiki/File:Stream.jpg",
        title="Stream",
        creator="Creator",
        license="CC BY 4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        width=120,
        height=80,
        file_size=None,
        keywords=["stream"],
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "image/jpeg"},
            stream=GuardedStream(),
            request=request,
        )

    with pytest.raises(ValueError, match="size limit"):
        assets.download_remote_asset(
            httpx.Client(transport=httpx.MockTransport(handler)),
            candidate,
            destination_dir=tmp_path,
            max_bytes=1000,
            host_resolver=lambda _host: ["93.184.216.34"],
        )

    assert not list(tmp_path.iterdir())
