from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any
from urllib.request import Request, urlopen

from imageio_ffmpeg import get_ffmpeg_exe


SERVER_DIR = Path(__file__).resolve().parent
WORKSPACE = SERVER_DIR.parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from app.editor.human_reference_0810 import (  # noqa: E402
    _map_source_time_ms,
    _prepare_dialogue_media,
)
from app.production_models import DialogueEditSegment  # noqa: E402
from story_0813_live_common import (  # noqa: E402
    build_caption_pages as _build_caption_pages,
)


SOURCE = Path(r"D:\Downloads\0813 (1).mp4")
SEED_OUTPUT = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0813-production-v3-live-footage"
)
OUTPUT = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0813-production-v7-semantic-visuals"
)
DURATION_MS = 46_000
FFMPEG = Path(get_ffmpeg_exe())
ANALYSIS_DIR = OUTPUT / "analysis"
TRANSCRIPT_PATH = (
    SEED_OUTPUT / "analysis" / "transcript-deepgram.json"
)
PRIMARY_REFERENCE = next(
    (
        WORKSPACE
        / "storage"
        / "deliverables"
        / "0810-production-v2-human-reference"
    ).glob("edited.mp4")
)


BOUNDARIES = [
    0,
    2_300,
    5_063,
    9_400,
    11_137,
    12_700,
    18_500,
    20_503,
    24_346,
    26_573,
    28_900,
    32_444,
    35_952,
    38_897,
    41_843,
    44_688,
    46_000,
]


def _shot(
    asset_id: str,
    source_start_ms: int,
    editorial_role: str,
    *,
    visual_job: str,
    zoom: float = 1.06,
    crop_y: float = 0.5,
    secondary_asset_id: str | None = None,
    secondary_source_start_ms: int | None = None,
) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "kind": "video",
        "source_start_ms": source_start_ms,
        "editorial_role": editorial_role,
        "visual_job": visual_job,
        "zoom": zoom,
        "crop_y": crop_y,
        "secondary_asset_id": secondary_asset_id,
        "secondary_source_start_ms": secondary_source_start_ms,
    }


SHOT_SPECS = [
    _shot(
        "pexels-27093700",
        800,
        "tea-price-hook",
        visual_job="presenter-supported",
        zoom=1.08,
        secondary_asset_id="presenter-edl",
        secondary_source_start_ms=0,
    ),
    _shot(
        "pexels-4820115",
        2_200,
        "producer-price-action",
        visual_job="literal-action",
        zoom=1.10,
    ),
    _shot(
        "presenter-edl",
        5_063,
        "ppi-definition",
        visual_job="presenter-explanation",
        zoom=1.06,
    ),
    _shot(
        "pexels-37101039",
        1_200,
        "customer-checkout",
        visual_job="literal-action",
        zoom=1.08,
    ),
    _shot(
        "pexels-38362060",
        1_000,
        "factory-action",
        visual_job="literal-action",
        zoom=1.10,
    ),
    _shot(
        "presenter-edl",
        12_700,
        "factory-and-release-explanation",
        visual_job="presenter-explanation",
        zoom=1.06,
    ),
    _shot(
        "bls-ppi-july-2026",
        0,
        "official-ppi-evidence",
        visual_job="direct-evidence",
        zoom=1.00,
    ),
    _shot(
        "presenter-edl",
        20_503,
        "zero-not-uniform",
        visual_job="presenter-explanation",
        zoom=1.09,
    ),
    _shot(
        "pexels-6169086",
        1_300,
        "goods-price-move",
        visual_job="literal-action",
        zoom=1.09,
    ),
    _shot(
        "pexels-9046227",
        1_200,
        "services-price-move",
        visual_job="presenter-supported",
        zoom=1.10,
        secondary_asset_id="presenter-edl",
        secondary_source_start_ms=26_573,
    ),
    _shot(
        "presenter-edl",
        28_900,
        "opposite-directions",
        visual_job="presenter-explanation",
        zoom=1.08,
    ),
    _shot(
        "pexels-34433115",
        6_800,
        "market-reaction",
        visual_job="literal-action",
        zoom=1.12,
    ),
    _shot(
        "presenter-edl",
        35_952,
        "risk-controls",
        visual_job="presenter-explanation",
        zoom=1.06,
    ),
    _shot(
        "presenter-edl",
        38_897,
        "robot-market-lesson",
        visual_job="presenter-explanation",
        zoom=1.10,
    ),
    _shot(
        "presenter-edl",
        41_843,
        "market-reads-why",
        visual_job="presenter-explanation",
        zoom=1.13,
    ),
    _shot(
        "presenter-edl",
        44_688,
        "clean-cta",
        visual_job="presenter-explanation",
        zoom=1.06,
    ),
]


EDL_ROWS = [
    (0, 672, 0, 672),
    (1_108, 5_499, 672, 5_063),
    (5_831, 9_495, 5_063, 8_727),
    (9_576, 11_222, 8_727, 10_373),
    (11_359, 12_123, 10_373, 11_137),
    (12_974, 15_632, 11_137, 13_795),
    (15_842, 16_520, 13_795, 14_473),
    (16_559, 19_852, 14_473, 17_766),
    (20_147, 22_884, 17_766, 20_503),
    (23_047, 26_890, 20_503, 24_346),
    (27_325, 29_552, 24_346, 26_573),
    (29_772, 33_218, 26_573, 30_019),
    (33_224, 35_511, 30_019, 32_306),
    (35_712, 39_358, 32_306, 35_952),
    (39_596, 41_650, 35_952, 38_006),
    (41_691, 42_582, 38_006, 38_897),
    (42_710, 43_848, 38_897, 40_035),
    (44_001, 45_809, 40_035, 41_843),
    (46_174, 49_019, 41_843, 44_688),
    (49_161, 50_023, 44_688, 45_550),
    (50_133, 50_516, 45_550, 45_933),
    (50_566, 50_633, 45_933, 46_000),
]


def dialogue_edl() -> list[DialogueEditSegment]:
    return [
        DialogueEditSegment(
            id=f"dialogue-{index:03d}",
            source_start_ms=source_start,
            source_end_ms=source_end,
            output_start_ms=output_start,
            output_end_ms=output_end,
            playback_rate=1,
            preserve_pitch=True,
        )
        for index, (
            source_start,
            source_end,
            output_start,
            output_end,
        ) in enumerate(EDL_ROWS, start=1)
    ]


CAPTION_GROUPS = [
    (0, 0, "SOCHIYE"),
    (1, 4, "CHAI MEHENGI HONE SE"),
    (5, 7, "PEHLE DOODH, CHEENI"),
    (8, 12, "AUR PAPER CUP WALE"),
    (13, 16, "APNE RATES BADHATE HAIN"),
    (17, 19, "PRODUCER LEVEL PAR"),
    (20, 24, "PRICE CHANGE = PPI"),
    (25, 26, "PPI KEHTE HAIN"),
    (27, 28, "SIMPLE DIFFERENCE"),
    (29, 32, "CUSTOMER FINAL PRICE"),
    (33, 34, "CUSTOMER PAYS"),
    (35, 37, "THAT IS CPI"),
    (38, 40, "FACTORY YA PRODUCER"),
    (41, 43, "JIS RATE PAR"),
    (44, 46, "MAAL BECHTA HAI"),
    (47, 49, "WOH PPI HAI"),
    (50, 52, "13 AUGUST"),
    (53, 55, "2026 KO"),
    (56, 58, "AMERICA KA JULY"),
    (59, 60, "PPI RELEASE"),
    (61, 62, "FORECAST +0.2%"),
    (63, 65, "PERCENT INCREASE EXPECTED"),
    (66, 68, "KAR RAHA THA"),
    (69, 71, "BUT ACTUAL RESULT"),
    (72, 73, "WAS 0%"),
    (74, 77, "ZERO DOESN'T MEAN"),
    (78, 80, "ALL PRICES SAME"),
    (81, 82, "NAHI THE"),
    (83, 84, "GOODS PRICES"),
    (85, 86, "0.7 PERCENT"),
    (87, 88, "FELL, WHILE"),
    (89, 90, "SERVICES 0.2"),
    (91, 92, "PERCENT BADHI"),
    (93, 96, "TOTAL RESULT 0"),
    (97, 99, "BUT INSIDE PRICES"),
    (100, 101, "OPPOSITE DIRECTIONS"),
    (102, 103, "MEIN CHALE"),
    (104, 107, "INFLATION EXPECTED SE KAM"),
    (108, 111, "HONE KE BAAD BHI"),
    (112, 113, "DOLLAR COMPLETELY"),
    (114, 116, "CRASH NAHI HUA"),
    (117, 118, "SPREAD LIMIT"),
    (119, 120, "AUR CONFIRMATION"),
    (121, 122, "ZAROORI HAI"),
    (123, 125, "LESSON SIMPLE HAI"),
    (126, 129, "ROBOT ZERO DEKHTA HAI"),
    (130, 132, "LEKIN MARKET USKA"),
    (133, 135, "REASON DEKHTA HAI"),
    (136, 140, "FOREX MARKET SE"),
    (141, 145, "INFORMATIVE VIDEOS KE LIYE"),
    (146, 148, "ABHI FOLLOW KIJIYE"),
    (149, 150, "THANK YOU"),
]


def _map_time(source_ms: int, edl: list[DialogueEditSegment], *, end: bool) -> int:
    return _map_source_time_ms(source_ms, edl, end_boundary=end)


def build_caption_pages(
    transcript: dict[str, Any],
    edl: list[DialogueEditSegment],
) -> list[dict[str, Any]]:
    return _build_caption_pages(
        transcript=transcript,
        edl=edl,
        groups=CAPTION_GROUPS,
        duration_ms=DURATION_MS,
    )


def fact_overlay_specs() -> list[dict[str, Any]]:
    return [
        {
            "id": "hook-title",
            "text": "BEFORE TEA GETS EXPENSIVE...",
            "start_ms": 120,
            "end_ms": 1_180,
            "width": 870,
            "height": 190,
            "x": 105,
            "y": 735,
            "style": "serif-hook",
            "evidence_id": None,
            "transparent": True,
        },
        {
            "id": "ppi-definition",
            "text": "PPI = PRODUCER PRICE",
            "start_ms": 6_000,
            "end_ms": 8_100,
            "width": 720,
            "height": 118,
            "x": 180,
            "y": 220,
            "style": "technical",
            "evidence_id": None,
            "transparent": True,
        },
        {
            "id": "cpi-definition",
            "text": "CPI = CUSTOMER PRICE",
            "start_ms": 8_900,
            "end_ms": 11_100,
            "width": 720,
            "height": 118,
            "x": 180,
            "y": 220,
            "style": "technical",
            "evidence_id": None,
            "transparent": True,
        },
        {
            "id": "release-date",
            "text": "13 AUG 2026 · JULY PPI",
            "start_ms": 15_700,
            "end_ms": 17_760,
            "width": 760,
            "height": 118,
            "x": 160,
            "y": 220,
            "style": "source",
            "evidence_id": "bls-july-2026-ppi",
            "transparent": True,
        },
        {
            "id": "forecast",
            "text": "FORECAST +0.2%",
            "start_ms": 18_000,
            "end_ms": 20_500,
            "width": 650,
            "height": 150,
            "x": 215,
            "y": 285,
            "style": "forecast",
            "evidence_id": "forecast-july-2026-ppi",
            "transparent": True,
        },
        {
            "id": "actual",
            "text": "ACTUAL 0.0%",
            "start_ms": 20_500,
            "end_ms": 22_700,
            "width": 650,
            "height": 150,
            "x": 215,
            "y": 285,
            "style": "actual",
            "evidence_id": "bls-july-2026-ppi",
            "transparent": True,
        },
        {
            "id": "goods",
            "text": "GOODS -0.7%",
            "start_ms": 24_300,
            "end_ms": 26_650,
            "width": 610,
            "height": 150,
            "x": 235,
            "y": 260,
            "style": "negative",
            "evidence_id": "bls-july-2026-ppi",
            "transparent": True,
        },
        {
            "id": "services",
            "text": "SERVICES +0.2%",
            "start_ms": 26_650,
            "end_ms": 28_900,
            "width": 650,
            "height": 150,
            "x": 215,
            "y": 260,
            "style": "positive",
            "evidence_id": "bls-july-2026-ppi",
            "transparent": True,
        },
        {
            "id": "opposite",
            "text": "SAME TOTAL · OPPOSITE MOVES",
            "start_ms": 28_900,
            "end_ms": 32_350,
            "width": 850,
            "height": 118,
            "x": 115,
            "y": 225,
            "style": "technical",
            "evidence_id": "bls-july-2026-ppi",
            "transparent": True,
        },
        {
            "id": "dollar",
            "text": "DOLLAR: MODEST REACTION",
            "start_ms": 32_350,
            "end_ms": 35_950,
            "width": 760,
            "height": 118,
            "x": 160,
            "y": 220,
            "style": "source",
            "evidence_id": "dollar-reaction-july-2026-ppi",
            "transparent": True,
        },
        {
            "id": "spread",
            "text": "SPREAD LIMIT",
            "start_ms": 35_950,
            "end_ms": 37_050,
            "width": 540,
            "height": 118,
            "x": 270,
            "y": 260,
            "style": "technical",
            "evidence_id": None,
            "transparent": True,
        },
        {
            "id": "confirmation",
            "text": "CONFIRMATION",
            "start_ms": 37_050,
            "end_ms": 38_900,
            "width": 540,
            "height": 118,
            "x": 270,
            "y": 260,
            "style": "technical",
            "evidence_id": None,
            "transparent": True,
        },
        {
            "id": "robot-market",
            "text": "ROBOT READS 0 · MARKET READS WHY",
            "start_ms": 38_900,
            "end_ms": 43_600,
            "width": 880,
            "height": 118,
            "x": 100,
            "y": 220,
            "style": "technical",
            "evidence_id": None,
            "transparent": True,
        },
    ]


def evidence_items() -> list[dict[str, Any]]:
    accessed = datetime.now(UTC).isoformat()
    return [
        {
            "id": "bls-july-2026-ppi",
            "claim": (
                "U.S. final-demand producer prices were unchanged in July "
                "2026; goods fell 0.7% and services rose 0.2%."
            ),
            "title": "Producer Price Index News Release - July 2026",
            "url": "https://www.bls.gov/news.release/ppi.nr0.htm",
            "source_type": "official",
            "capture_path": (
                "source-captures/bls-ppi-july-2026-excerpt.png"
            ),
            "accessed_at": accessed,
            "status": "verified",
            "published_at": "2026-08-13T08:30:00-04:00",
            "visible_excerpt": (
                "Final demand unchanged; goods -0.7%; services +0.2%."
            ),
            "license": "Official U.S. government source",
            "notes": "Used only to validate compact numeric overlays.",
        },
        {
            "id": "forecast-july-2026-ppi",
            "claim": "Economists expected July 2026 headline PPI to rise 0.2%.",
            "title": "Wholesale prices unexpectedly unchanged in July",
            "url": (
                "https://www.cnbc.com/2026/08/13/"
                "wholesale-prices-were-flat-in-july-below-expectations-"
                "for-0point2percent-increase.html"
            ),
            "source_type": "editorial",
            "capture_path": "source-captures/cnbc-ppi-july-2026.html",
            "accessed_at": accessed,
            "status": "verified",
            "published_at": "2026-08-13T08:30:00-04:00",
            "visible_excerpt": "Dow Jones estimate: +0.2% month over month.",
            "license": "Editorial verification; no source pixels shown",
            "notes": "Only the verified forecast value appears onscreen.",
        },
        {
            "id": "dollar-reaction-july-2026-ppi",
            "claim": (
                "The dollar reaction after the release was modest rather "
                "than a complete crash."
            ),
            "title": "Dollar holds steady as PPI data affirms rate-cut bets",
            "url": (
                "https://www.reuters.com/markets/currencies/"
                "dollar-holds-steady-ppi-data-affirms-rate-cut-bets-"
                "2026-08-13/"
            ),
            "source_type": "editorial",
            "capture_path": None,
            "accessed_at": accessed,
            "status": "verified",
            "published_at": "2026-08-13T00:00:00Z",
            "visible_excerpt": (
                "Dollar held broadly steady with only modest moves after PPI."
            ),
            "license": "Editorial verification; no source pixels shown",
            "notes": "Rendered wording is qualitative, not a price claim.",
        },
    ]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _run(command: list[str], *, timeout: int = 3_600) -> None:
    completed = subprocess.run(
        command,
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        shell=False,
    )
    if completed.returncode:
        raise RuntimeError(
            "\n".join(
                part
                for part in (
                    completed.stdout[-4_000:],
                    completed.stderr[-8_000:],
                )
                if part
            )
        )


def _copy(source: Path, destination: Path) -> Path:
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)
    return destination


def _capture_url(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/139 Safari/537.36"
            )
        },
    )
    try:
        with urlopen(request, timeout=45) as response:
            destination.write_bytes(response.read())
    except Exception as exc:  # pragma: no cover - network best effort
        destination.with_suffix(".capture-error.txt").write_text(
            f"{url}\n{type(exc).__name__}: {exc}\n",
            encoding="utf-8",
        )


def _candidate_records() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for relative in (
        "asset-candidates/live-search/candidates.json",
        "asset-candidates/ppi-search/candidates.json",
    ):
        path = SEED_OUTPUT / relative
        for item in json.loads(path.read_text(encoding="utf-8")):
            records[str(item["id"])] = item
    return records


def _prepare_assets() -> tuple[list[dict[str, Any]], dict[str, Path]]:
    records = _candidate_records()
    selected_ids = sorted(
        {
            spec["asset_id"].removeprefix("pexels-")
            for spec in SHOT_SPECS
            if spec["asset_id"].startswith("pexels-")
        }
        | {
            str(spec["secondary_asset_id"]).removeprefix("pexels-")
            for spec in SHOT_SPECS
            if str(spec.get("secondary_asset_id", "")).startswith("pexels-")
        }
    )
    asset_paths: dict[str, Path] = {}
    manifest: list[dict[str, Any]] = []
    licensed_dir = OUTPUT / "assets" / "licensed"
    for remote_id in selected_ids:
        record = records[remote_id]
        source = WORKSPACE / str(record["local_path"])
        destination = licensed_dir / f"pexels-{remote_id}.mp4"
        _copy(source, destination)
        asset_id = f"pexels-{remote_id}"
        asset_paths[asset_id] = destination
        manifest.append(
            {
                **record,
                "asset_id": asset_id,
                "local_path": destination.relative_to(OUTPUT).as_posix(),
                "checksum_sha256": _sha256(destination),
            }
        )

    bls_source = (
        WORKSPACE
        / "storage"
        / "assets"
        / "0813-stories"
        / "bls-ppi-july-2026-evidence.mp4"
    )
    bls_destination = _copy(
        bls_source,
        OUTPUT / "assets" / "evidence" / bls_source.name,
    )
    bls_capture_source = (
        WORKSPACE
        / "storage"
        / "assets"
        / "0813-stories"
        / "bls-ppi-july-2026-excerpt.png"
    )
    bls_capture = _copy(
        bls_capture_source,
        OUTPUT / "source-captures" / bls_capture_source.name,
    )
    asset_paths["bls-ppi-july-2026"] = bls_destination
    manifest.append(
        {
            "asset_id": "bls-ppi-july-2026",
            "local_path": bls_destination.relative_to(OUTPUT).as_posix(),
            "source_kind": "direct-evidence",
            "provider": "U.S. Bureau of Labor Statistics",
            "source_url": "https://www.bls.gov/news.release/ppi.nr0.htm",
            "capture_path": bls_capture.relative_to(OUTPUT).as_posix(),
            "captured_at": datetime.now(UTC).isoformat(),
            "license": "Official U.S. government source",
            "checksum_sha256": _sha256(bls_destination),
            "capture_checksum_sha256": _sha256(bls_capture),
        }
    )

    presenter = OUTPUT / "assets" / "presenter" / "presenter-edl.mp4"
    dialogue_original = OUTPUT / "assets" / "audio" / "dialogue-original.wav"
    dialogue_processed = OUTPUT / "assets" / "audio" / "dialogue-processed.wav"
    _prepare_dialogue_media(
        source=SOURCE,
        edl=dialogue_edl(),
        presenter_output=presenter,
        original_audio_output=dialogue_original,
        processed_audio_output=dialogue_processed,
    )
    asset_paths["presenter-edl"] = presenter

    music_source = (
        WORKSPACE
        / "storage"
        / "assets"
        / "audio"
        / "technical-reference"
        / "candidates"
        / "feedback-dreams-588.mp3"
    )
    music = OUTPUT / "assets" / "audio" / "music-documentary.wav"
    music.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            str(FFMPEG),
            "-hide_banner",
            "-y",
            "-ss",
            "50",
            "-i",
            str(music_source),
            "-af",
            (
                "highpass=f=42,lowpass=f=6900,"
                "equalizer=f=2800:t=q:w=0.9:g=-2.5,"
                "afade=t=in:st=0:d=0.35,"
                "afade=t=out:st=45.45:d=0.55,"
                "atrim=duration=46,aresample=48000"
            ),
            "-c:a",
            "pcm_s24le",
            str(music),
        ]
    )

    sfx_source = (
        WORKSPACE / "storage" / "assets" / "audio" / "social-kinetic"
    )
    sfx: dict[str, Path] = {}
    for name in ("click", "impact", "riser", "snap", "whoosh"):
        path = _copy(
            sfx_source / f"sfx-{name}.mp3",
            OUTPUT / "assets" / "audio" / f"sfx-{name}.mp3",
        )
        sfx[f"sfx-{name}"] = path

    logo = _copy(
        WORKSPACE
        / "storage"
        / "assets"
        / "brand"
        / "profit-bricks-forex-automation.png",
        OUTPUT / "assets" / "brand" / "profit-bricks-logo.png",
    )

    manifest.extend(
        [
            {
                "asset_id": "presenter-edl",
                "local_path": presenter.relative_to(OUTPUT).as_posix(),
                "provenance": "user-provided-source",
                "checksum_sha256": _sha256(presenter),
            },
            {
                "asset_id": "music-documentary",
                "local_path": music.relative_to(OUTPUT).as_posix(),
                "provider": "Mixkit",
                "remote_id": "588",
                "source_url": "https://mixkit.co/free-stock-music/",
                "license": "Mixkit Free License",
                "license_url": "https://mixkit.co/license/",
                "checksum_sha256": _sha256(music),
            },
        ]
    )
    _write_json(OUTPUT / "asset-manifest.json", manifest)
    return manifest, {
        **asset_paths,
        "dialogue-original": dialogue_original,
        "dialogue-processed": dialogue_processed,
        "music-documentary": music,
        "brand-logo": logo,
        **sfx,
    }


def _safe_cue_start(
    desired_ms: int,
    duration_ms: int,
    windows: list[dict[str, Any]],
) -> int:
    offsets = [0]
    for delta in range(20, 601, 20):
        offsets.extend((-delta, delta))
    for offset in offsets:
        candidate = max(0, min(DURATION_MS - duration_ms, desired_ms + offset))
        if all(
            not (
                candidate < window["end_ms"]
                and candidate + duration_ms > window["start_ms"]
            )
            for window in windows
        ):
            return candidate
    raise ValueError(f"No speech-safe SFX position near {desired_ms}")


def build_audio_plan(
    transcript: dict[str, Any],
    edl: list[DialogueEditSegment],
) -> dict[str, Any]:
    windows = []
    for word in transcript["words"]:
        start_ms = _map_time(
            round(float(word["start"]) * 1000),
            edl,
            end=False,
        )
        windows.append(
            {
                "start_ms": max(0, start_ms - 100),
                "end_ms": min(DURATION_MS, start_ms + 120),
                "word": word["word"],
            }
        )
    desired = [
        ("hook-settle", "sfx-impact", 700, 90, -21.0),
        ("ppi-reveal", "sfx-snap", 5_960, 70, -22.0),
        ("cpi-reveal", "sfx-click", 8_850, 70, -23.0),
        ("forecast-reveal", "sfx-whoosh", 17_900, 110, -23.0),
        ("actual-reveal", "sfx-impact", 20_450, 90, -22.0),
        ("goods-services", "sfx-snap", 24_250, 70, -23.0),
        ("opposite-turn", "sfx-whoosh", 28_760, 100, -24.0),
        ("risk-controls", "sfx-click", 35_900, 70, -23.0),
        ("cta-lift", "sfx-riser", 41_560, 100, -25.0),
    ]
    cues = [
        {
            "id": cue_id,
            "asset_id": asset_id,
            "start_ms": _safe_cue_start(start, duration, windows),
            "source_start_ms": 0,
            "duration_ms": duration,
            "gain_db": gain,
            "volume": 0.35,
        }
        for cue_id, asset_id, start, duration, gain in desired
    ]
    return {
        "integrated_lufs": -14.2,
        "true_peak_dbtp": -1.0,
        "target_lra_lu": 3.0,
        "dialogue_asset_id": "dialogue-original",
        "music_asset_id": "music-documentary",
        "music_base_gain_db": -27.0,
        "music_duck_db": 6.0,
        "speech_protection_windows": windows,
        "sfx_cues": cues,
    }


def _storyboard() -> list[dict[str, Any]]:
    return [
        {
            "id": f"shot-{index:02d}",
            "start_ms": start,
            "end_ms": end,
            "source_kind": (
                "presenter"
                if shot["asset_id"] == "presenter-edl"
                else (
                    "direct-evidence"
                    if shot["asset_id"] == "bls-ppi-july-2026"
                    else "licensed-context"
                )
            ),
            "reference_role": "primary-human",
            **shot,
        }
        for index, (start, end, shot) in enumerate(
            zip(BOUNDARIES[:-1], BOUNDARIES[1:], SHOT_SPECS, strict=True),
            start=1,
        )
    ]


def main() -> int:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    if not TRANSCRIPT_PATH.is_file():
        raise FileNotFoundError(TRANSCRIPT_PATH)
    OUTPUT.mkdir(parents=True, exist_ok=True)

    transcript = json.loads(TRANSCRIPT_PATH.read_text(encoding="utf-8"))
    edl = dialogue_edl()
    captions = build_caption_pages(transcript, edl)
    evidence = evidence_items()
    audio = build_audio_plan(transcript, edl)
    _, asset_paths = _prepare_assets()

    capture_dir = OUTPUT / "source-captures"
    _capture_url(
        (
            "https://www.cnbc.com/2026/08/13/"
            "wholesale-prices-were-flat-in-july-below-expectations-"
            "for-0point2percent-increase.html"
        ),
        capture_dir / "cnbc-ppi-july-2026.html",
    )

    _write_json(
        OUTPUT / "dialogue-edl.json",
        [segment.model_dump(mode="json") for segment in edl],
    )
    _write_json(OUTPUT / "evidence.json", evidence)
    _write_json(OUTPUT / "storyboard.json", _storyboard())
    _write_json(OUTPUT / "caption-plan.json", captions)
    _write_json(OUTPUT / "fact-overlay-plan.json", fact_overlay_specs())
    _write_json(OUTPUT / "sound-cue-sheet.json", audio)
    _write_json(
        OUTPUT / "edit-plan.json",
        {
            "version": "0813-ppi-live-v1",
            "source": str(SOURCE),
            "output": str(OUTPUT / "edited.mp4"),
            "duration_ms": DURATION_MS,
            "width": 1_080,
            "height": 1_920,
            "fps": 30,
            "primary_reference": str(PRIMARY_REFERENCE),
            "voice_policy": "pause-compressed-verbatim",
            "visual_policy": "live-footage-only",
            "flow_coverage": 0,
            "storyboard": _storyboard(),
            "caption_pages": captions,
            "fact_overlays": fact_overlay_specs(),
            "audio": audio,
            "assets": {
                key: path.relative_to(OUTPUT).as_posix()
                for key, path in asset_paths.items()
            },
        },
    )
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "duration_ms": DURATION_MS,
                "shots": len(SHOT_SPECS),
                "captions": len(captions),
                "assets": len(asset_paths),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
