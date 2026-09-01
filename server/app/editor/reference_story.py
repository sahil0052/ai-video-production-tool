from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any
import urllib.request

import cv2
from imageio_ffmpeg import get_ffmpeg_exe
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from app.editor.analysis import probe_video, validate_source
from app.editor.transcript import repair_nonpositive_word_durations
from app.models import (
    AssetRef,
    AudioPlan,
    EvidenceItem,
    GainAutomation,
    OutputSpec,
    SfxCue,
    SpeechProtectionWindow,
    TranscriptSegment,
)
from app.production_models import (
    BlueprintLayerSpec,
    EditPlanV2,
    LayerBounds,
    OpacityKeyframe,
    ProductionBlueprint,
    ProductionJobRecord,
    ProductionStateEvent,
    TransformKeyframe,
)


STORY_DURATION_MS = 50_833
_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_STORY_LICENSED_ROOT = (
    _WORKSPACE_ROOT / "storage" / "assets" / "licensed" / "mixkit" / "0809"
)
_GLOBAL_MIXKIT_ROOT = (
    _WORKSPACE_ROOT / "storage" / "assets" / "licensed" / "mixkit"
)
_SEC_ORDER_URL = (
    "https://www.sec.gov/files/litigation/admin/2013/34-70694.pdf"
)
_DEFAULT_STYLE_REFERENCE = Path(
    r"D:\Downloads\Trading_Reel 02(06-08-26).mp4"
)
_DEFAULT_BRAND_LOGO = Path(
    r"D:\Downloads\JEPG Profit Bricks Logo-01.jpg (1).jpeg"
)


def build_0809_story_schedule() -> list[dict[str, Any]]:
    specs = [
        (0, 2_200, "presenter", "source-presenter", "hook"),
        (
            2_200,
            4_500,
            "licensed-context",
            "licensed-mixkit-trader",
            "market-open",
        ),
        (4_500, 6_800, "presenter", "source-presenter", "order-scale"),
        (
            6_800,
            9_500,
            "licensed-context",
            "licensed-mixkit-forex-screen",
            "loss",
        ),
        (9_500, 11_000, "presenter", "source-presenter", "question-reset"),
        (
            11_000,
            14_800,
            "licensed-context",
            "licensed-mixkit-code",
            "software-update",
        ),
        (
            14_800,
            16_700,
            "direct-evidence",
            "evidence-sec-overview",
            "company",
        ),
        (
            16_700,
            19_000,
            "licensed-context",
            "licensed-mixkit-server",
            "server-deployment",
        ),
        (
            19_000,
            20_300,
            "deterministic-graphic",
            "graphic-eight-servers",
            "missed-server",
        ),
        (
            20_300,
            22_000,
            "direct-evidence",
            "evidence-sec-email",
            "error-emails-evidence",
        ),
        (22_000, 23_800, "presenter", "source-presenter", "error-emails"),
        (23_800, 25_600, "presenter", "source-presenter", "forex-lesson"),
        (
            25_600,
            27_500,
            "licensed-context",
            "licensed-mixkit-forex-screen",
            "forex-context",
        ),
        (
            27_500,
            30_100,
            "direct-evidence",
            "evidence-sec-deployment",
            "repeated-error",
        ),
        (30_100, 32_100, "presenter", "source-presenter", "verification"),
        (
            32_100,
            33_600,
            "direct-evidence",
            "evidence-sec-controls",
            "missing-controls",
        ),
        (33_600, 34_900, "presenter", "source-presenter", "emergency-stop"),
        (34_900, 38_300, "presenter", "source-presenter", "brand-controls"),
        (38_300, 40_200, "presenter", "source-presenter", "risk-reset"),
        (40_200, 42_500, "presenter", "source-presenter", "containment"),
        (42_500, 45_500, "presenter", "source-presenter", "cta-start"),
        (45_500, STORY_DURATION_MS, "presenter", "source-presenter", "cta-end"),
    ]
    return [
        {
            "id": f"story-shot-{index:02d}",
            "start_ms": start_ms,
            "end_ms": end_ms,
            "source_role": source_role,
            "asset_id": asset_id,
            "editorial_role": editorial_role,
            "reference_role": "primary-10",
        }
        for index, (
            start_ms,
            end_ms,
            source_role,
            asset_id,
            editorial_role,
        ) in enumerate(specs, start=1)
    ]


def build_0809_story_layers() -> list[BlueprintLayerSpec]:
    schedule = build_0809_story_schedule()
    layers = [
        _story_base_layer(shot, index=index)
        for index, shot in enumerate(schedule)
    ]
    layers.extend(
        [
            _story_overlay(
                layer_id="overlay-hook-white",
                shot_id="story-shot-01",
                asset_id="overlay-hook-white",
                start_ms=900,
                end_ms=2_200,
                start_y=18,
                start_scale=0.95,
            ),
            _story_overlay(
                layer_id="overlay-hook-accent",
                shot_id="story-shot-01",
                asset_id="overlay-hook-accent",
                start_ms=800,
                end_ms=2_200,
                start_y=28,
                start_scale=0.91,
            ),
            _story_overlay(
                layer_id="overlay-order-scale",
                shot_id="story-shot-03",
                asset_id="overlay-order-scale",
                start_ms=4_500,
                end_ms=6_800,
                start_y=24,
                start_scale=0.93,
            ),
            _story_overlay(
                layer_id="overlay-loss-white",
                shot_id="story-shot-04",
                asset_id="overlay-loss-white",
                start_ms=6_900,
                end_ms=9_500,
                start_y=16,
                start_scale=0.95,
            ),
            _story_overlay(
                layer_id="overlay-loss-accent",
                shot_id="story-shot-04",
                asset_id="overlay-loss-accent",
                start_ms=8_150,
                end_ms=9_500,
                start_y=34,
                start_scale=0.9,
            ),
            _story_overlay(
                layer_id="overlay-question",
                shot_id="story-shot-06",
                asset_id="overlay-question",
                start_ms=11_000,
                end_ms=14_800,
                start_y=12,
                start_scale=0.97,
            ),
            _story_overlay(
                layer_id="overlay-knight-capital",
                shot_id="story-shot-07",
                asset_id="overlay-knight-capital",
                start_ms=15_300,
                end_ms=16_700,
                start_y=22,
                start_scale=0.94,
            ),
            _story_overlay(
                layer_id="overlay-illustrative-trader",
                shot_id="story-shot-02",
                asset_id="overlay-illustrative",
                start_ms=2_200,
                end_ms=4_500,
                start_y=0,
                start_scale=1,
                entrance_ms=1,
                z_index=80,
            ),
            _story_overlay(
                layer_id="overlay-illustrative-chart-a",
                shot_id="story-shot-04",
                asset_id="overlay-illustrative",
                start_ms=6_800,
                end_ms=9_500,
                start_y=0,
                start_scale=1,
                entrance_ms=1,
                z_index=80,
            ),
            _story_overlay(
                layer_id="overlay-illustrative-code",
                shot_id="story-shot-06",
                asset_id="overlay-illustrative",
                start_ms=11_000,
                end_ms=14_800,
                start_y=0,
                start_scale=1,
                entrance_ms=1,
                z_index=80,
            ),
            _story_overlay(
                layer_id="overlay-illustrative-server",
                shot_id="story-shot-08",
                asset_id="overlay-illustrative",
                start_ms=16_700,
                end_ms=19_000,
                start_y=0,
                start_scale=1,
                entrance_ms=1,
                z_index=80,
            ),
            _story_overlay(
                layer_id="overlay-alerts",
                shot_id="story-shot-11",
                asset_id="overlay-alerts",
                start_ms=22_000,
                end_ms=23_800,
                start_y=18,
                start_scale=0.96,
            ),
            _story_overlay(
                layer_id="overlay-forex-lesson",
                shot_id="story-shot-12",
                asset_id="overlay-forex-lesson",
                start_ms=23_900,
                end_ms=25_600,
                start_y=16,
                start_scale=0.95,
            ),
            _story_overlay(
                layer_id="overlay-illustrative-chart-b",
                shot_id="story-shot-13",
                asset_id="overlay-illustrative",
                start_ms=25_600,
                end_ms=27_500,
                start_y=0,
                start_scale=1,
                entrance_ms=1,
                z_index=80,
            ),
            _story_overlay(
                layer_id="overlay-verify",
                shot_id="story-shot-15",
                asset_id="overlay-verify",
                start_ms=30_100,
                end_ms=32_100,
                start_y=18,
                start_scale=0.95,
            ),
            _story_overlay(
                layer_id="overlay-stop",
                shot_id="story-shot-17",
                asset_id="overlay-stop",
                start_ms=33_600,
                end_ms=34_900,
                start_y=22,
                start_scale=0.93,
            ),
            _story_overlay(
                layer_id="overlay-brand-controls",
                shot_id="story-shot-18",
                asset_id="overlay-brand-controls",
                start_ms=34_900,
                end_ms=38_300,
                start_y=26,
                start_scale=0.94,
            ),
            _story_overlay(
                layer_id="overlay-containment",
                shot_id="story-shot-20",
                asset_id="overlay-containment",
                start_ms=40_200,
                end_ms=42_500,
                start_y=18,
                start_scale=0.96,
            ),
            _story_overlay(
                layer_id="overlay-cta",
                shot_id="story-shot-22",
                asset_id="overlay-cta",
                start_ms=45_500,
                end_ms=50_833,
                start_y=18,
                start_scale=0.96,
            ),
        ]
    )
    layers.extend(
        _story_overlay(
            layer_id=f"vignette-{shot['editorial_role']}",
            shot_id=str(shot["id"]),
            asset_id="overlay-presenter-vignette",
            start_ms=int(shot["start_ms"]),
            end_ms=int(shot["end_ms"]),
            start_y=0,
            start_scale=1,
            entrance_ms=1,
            z_index=50,
        )
        for shot in schedule
        if shot["source_role"] == "presenter"
    )
    return layers


def _story_base_layer(
    shot: dict[str, Any],
    *,
    index: int,
) -> BlueprintLayerSpec:
    start_ms = int(shot["start_ms"])
    end_ms = int(shot["end_ms"])
    duration_ms = end_ms - start_ms
    asset_id = str(shot["asset_id"])
    kind = (
        "video"
        if shot["source_role"] in {"presenter", "licensed-context"}
        else "image"
    )
    source_start_ms: int | None = None
    source_end_ms: int | None = None
    playback_rate = 1.0
    if kind == "video":
        if asset_id == "source-presenter":
            source_start_ms = start_ms
            source_end_ms = end_ms
        elif asset_id == "licensed-mixkit-trader":
            source_start_ms, source_end_ms = 1_000, 3_300
        elif asset_id == "licensed-mixkit-forex-screen":
            if index < 10:
                source_start_ms, source_end_ms = 2_000, 4_700
            else:
                source_start_ms, source_end_ms = 10_000, 11_900
        elif asset_id == "licensed-mixkit-code":
            source_start_ms, source_end_ms = 1_000, 4_800
        elif asset_id == "licensed-mixkit-server":
            source_start_ms, source_end_ms = 2_000, 4_300
        if source_start_ms is None or source_end_ms is None:
            raise ValueError(f"Missing source trim for {asset_id}")
        source_duration = source_end_ms - source_start_ms
        playback_rate = source_duration / duration_ms
    color_filter = None
    if shot["source_role"] == "presenter":
        color_filter = "brightness(1.03) contrast(1.02) saturate(1.02)"
        if shot["editorial_role"] == "question-reset":
            color_filter = "grayscale(1) brightness(0.9) contrast(1.12)"
    elif shot["source_role"] == "licensed-context":
        color_filter = "brightness(0.94) contrast(1.1) saturate(0.88)"
    return BlueprintLayerSpec(
        id=f"base-{shot['editorial_role']}",
        shot_id=str(shot["id"]),
        start_ms=start_ms,
        end_ms=end_ms,
        source_role=str(shot["source_role"]),
        kind=kind,
        asset_id=asset_id,
        source_start_ms=source_start_ms,
        source_end_ms=source_end_ms,
        bounds=LayerBounds(),
        fit="fill" if kind == "image" else "cover",
        transform_keyframes=[
            TransformKeyframe(at_ms=0, scale=1),
            TransformKeyframe(
                at_ms=duration_ms,
                scale=1.045 if kind == "image" else 1.035,
            ),
        ],
        opacity_keyframes=[OpacityKeyframe(at_ms=0, value=1)],
        z_index=10,
        muted=True,
        playback_rate=playback_rate,
        color_filter=color_filter,
        reference_role="primary-10",
    )


def _story_overlay(
    *,
    layer_id: str,
    shot_id: str,
    asset_id: str,
    start_ms: int,
    end_ms: int,
    start_y: float,
    start_scale: float,
    entrance_ms: int = 150,
    z_index: int = 100,
) -> BlueprintLayerSpec:
    duration_ms = end_ms - start_ms
    entrance_ms = min(entrance_ms, duration_ms)
    return BlueprintLayerSpec(
        id=layer_id,
        shot_id=shot_id,
        start_ms=start_ms,
        end_ms=end_ms,
        source_role="deterministic-graphic",
        kind="image",
        asset_id=asset_id,
        bounds=LayerBounds(),
        fit="fill",
        transform_keyframes=[
            TransformKeyframe(
                at_ms=0,
                y=start_y,
                scale=start_scale,
            ),
            TransformKeyframe(
                at_ms=entrance_ms,
                y=0,
                scale=1,
            ),
            TransformKeyframe(
                at_ms=duration_ms,
                y=0,
                scale=1,
            ),
        ],
        opacity_keyframes=[
            OpacityKeyframe(at_ms=0, value=0 if entrance_ms > 1 else 1),
            OpacityKeyframe(
                at_ms=min(100, duration_ms),
                value=1,
            ),
        ],
        z_index=z_index,
        muted=True,
        reference_role="primary-10",
    )


def build_0809_evidence_items(
    *,
    accessed_at: datetime,
) -> list[EvidenceItem]:
    source_url = (
        "https://www.sec.gov/files/litigation/admin/2013/34-70694.pdf"
    )
    source_title = (
        "SEC Exchange Act Release No. 70694 - Knight Capital Americas LLC"
    )
    specs = [
        (
            "sec-four-million",
            "Knight's SMARS generated over 4 million executions in approximately 45 minutes.",
            "assets/evidence/sec-overview.png",
            "over 4 million executions in 154 stocks ... over a 45-minute period",
        ),
        (
            "sec-loss-460m",
            "Knight Capital lost over $460 million from the unwanted positions.",
            "assets/evidence/sec-overview.png",
            "Knight lost over $460 million from these unwanted positions",
        ),
        (
            "sec-one-of-eight",
            "A technician failed to copy the new code to one of eight SMARS servers, leaving old Power Peg code active.",
            "assets/evidence/sec-deployment.png",
            "did not copy the new code to one of the eight SMARS computer servers",
        ),
        (
            "sec-97-emails",
            "Knight's system sent 97 automated Power Peg disabled e-mails before market open.",
            "assets/evidence/sec-email.png",
            "Knight's system sent 97 of these e-mail messages",
        ),
        (
            "sec-missing-controls",
            "Knight lacked adequate controls to halt SMARS and lacked written code deployment procedures.",
            "assets/evidence/sec-controls.png",
            "did not have procedures in place to halt SMARS's operations",
        ),
    ]
    return [
        EvidenceItem(
            id=identifier,
            claim=claim,
            source_title=source_title,
            source_url=source_url,
            source_type="official",
            capture_path=capture_path,
            accessed_at=accessed_at,
            status="verified",
            visible_excerpt=visible_excerpt,
            license="Official U.S. SEC public record; editorial evidence use",
            notes="Visible source pixels are preserved in the rendered excerpt.",
        )
        for identifier, claim, capture_path, visible_excerpt in specs
    ]


def build_reference_story_blueprint(
    *,
    source: Path,
    output_dir: Path,
    style_reference: Path | None = None,
    brand_logo: Path | None = None,
) -> dict[str, str]:
    from app.editor.production_v4 import ProductionStore
    from app.editor.remotion import prepare_renderer_source_proxy

    source = source.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    style_reference = (
        style_reference.expanduser().resolve()
        if style_reference is not None
        else _DEFAULT_STYLE_REFERENCE
    )
    brand_logo = (
        brand_logo.expanduser().resolve()
        if brand_logo is not None
        else _DEFAULT_BRAND_LOGO
    )
    if not source.is_file():
        raise FileNotFoundError(source)
    metadata = probe_video(source)
    validate_source(metadata)
    if abs(metadata.duration_seconds * 1000 - STORY_DURATION_MS) > 100:
        raise ValueError(
            "The 0809 reference-style blueprint expects a 50.833-second "
            "source."
        )
    output_dir.mkdir(parents=True, exist_ok=True)

    presenter_path = (
        output_dir / "assets" / "presenter" / "source-presenter.mp4"
    )
    prepare_renderer_source_proxy(
        executable=Path(get_ffmpeg_exe()),
        source=source,
        output=presenter_path,
        fps=30,
    )
    segments = _load_or_transcribe_story(source, output_dir)
    evidence_paths = _prepare_sec_evidence(output_dir)
    brand_path = _prepare_brand_logo(
        source=brand_logo,
        output=output_dir / "assets" / "brand" / "profit-bricks-logo.png",
    )
    licensed_assets = _prepare_story_licensed_assets(output_dir)
    graphic_paths = _build_story_graphics(
        output_dir=output_dir,
        brand_logo=brand_path,
    )
    audio_paths = _prepare_story_audio(
        source=source,
        output_dir=output_dir,
    )

    assets = [
        AssetRef(
            id="source-presenter",
            kind="video",
            path=_relative(output_dir, presenter_path),
            keywords=["presenter", "talking head", "source narration"],
            provenance="user-provided",
            license="User-provided source footage",
        ),
        AssetRef(
            id="brand-profit-bricks-logo",
            kind="image",
            path=_relative(output_dir, brand_path),
            keywords=["Profit Bricks", "brand logo"],
            provenance="user-provided-brand-asset",
            license="User-provided",
        ),
    ]
    assets.extend(licensed_assets)
    for asset_id, path in evidence_paths.items():
        assets.append(
            AssetRef(
                id=asset_id,
                kind="image",
                path=_relative(output_dir, path),
                keywords=["SEC", "Knight Capital", "official evidence"],
                provenance="official-source-capture-derived-crop",
                license="Official U.S. SEC public record",
                provider="U.S. Securities and Exchange Commission",
                remote_id="34-70694",
                source_url=_SEC_ORDER_URL,
                license_url="https://www.sec.gov/about/rights-and-permissions",
                search_query="SEC Knight Capital Release 70694",
            )
        )
    for asset_id, path in graphic_paths.items():
        assets.append(
            AssetRef(
                id=asset_id,
                kind="image",
                path=_relative(output_dir, path),
                keywords=["reference-style", "deterministic graphic"],
                provenance="deterministic-production-graphic",
            )
        )
    for asset_id, path in audio_paths.items():
        assets.append(
            AssetRef(
                id=asset_id,
                kind="audio",
                path=_relative(output_dir, path),
                keywords=["production audio", asset_id],
                provenance=(
                    "source-dialogue-master"
                    if asset_id.startswith("dialogue-")
                    else "local-production-audio"
                ),
            )
        )

    sfx_specs = [
        _sfx(
            "section-orders",
            "sfx-hook-impact",
            6_580,
            150,
            "impact",
            "transition into loss figure",
        ),
        _sfx(
            "loss-reveal",
            "sfx-tonal-drop",
            9_500,
            180,
            "impact",
            "loss figure resolves",
        ),
        _sfx(
            "evidence-open",
            "sfx-paper-scroll",
            14_750,
            180,
            "whoosh",
            "official evidence enters",
        ),
        _sfx(
            "server-failure",
            "sfx-ui-click",
            20_100,
            140,
            "click",
            "missed server beat",
        ),
        _sfx(
            "lesson-turn",
            "sfx-label-snap",
            23_700,
            120,
            "click",
            "switch from incident to lesson",
        ),
        _sfx(
            "verification-fail",
            "sfx-tonal-drop",
            30_200,
            160,
            "impact",
            "verification failure beat",
        ),
        _sfx(
            "controls-reveal",
            "sfx-product-click",
            38_450,
            160,
            "click",
            "product controls resolve",
        ),
        _sfx(
            "cta-open",
            "sfx-label-snap",
            43_250,
            120,
            "click",
            "call to action begins",
        ),
    ]
    audio = build_story_audio_plan(
        segments,
        duration_ms=STORY_DURATION_MS,
        sfx_specs=sfx_specs,
    )
    evidence = build_0809_evidence_items(accessed_at=datetime.now(UTC))
    layers = build_0809_story_layers()
    blueprint = ProductionBlueprint(
        source_filename=source.name,
        source_metadata=metadata,
        output=OutputSpec(width=1080, height=1920, fps=30),
        duration_ms=STORY_DURATION_MS,
        assets=assets,
        layers=layers,
        caption_pages=[],
        audio=audio,
        flow_shots=[],
        evidence=evidence,
    )

    artifacts = {
        "blueprint": "blueprint.json",
        "storyboard": "storyboard.json",
        "evidence": "evidence.json",
        "caption_plan": "caption-plan.json",
        "asset_manifest": "asset-manifest.json",
        "transcript": "transcript-aligned.json",
        "production_settings": "production-settings.json",
    }
    _write_json(
        output_dir / artifacts["blueprint"],
        blueprint.model_dump(mode="json"),
    )
    layer_ids_by_shot: dict[str, list[str]] = {}
    for layer in layers:
        layer_ids_by_shot.setdefault(layer.shot_id, []).append(layer.id)
    _write_json(
        output_dir / artifacts["storyboard"],
        [
            {
                **shot,
                "layer_ids": layer_ids_by_shot.get(str(shot["id"]), []),
                "evidence_ids": _evidence_ids_for_role(
                    str(shot["editorial_role"])
                ),
                "caption_family": "display-emphasis"
                if str(shot["editorial_role"])
                in {"hook", "loss", "order-scale", "cta-end"}
                else "documentary-clean",
            }
            for shot in build_0809_story_schedule()
        ],
    )
    _write_json(
        output_dir / artifacts["evidence"],
        [item.model_dump(mode="json") for item in evidence],
    )
    _write_json(
        output_dir / artifacts["caption_plan"],
        {
            "continuous_captions": False,
            "typography_layers": [
                layer.id
                for layer in layers
                if layer.source_role == "deterministic-graphic"
                and layer.id.startswith("overlay-")
            ],
        },
    )
    _write_json(
        output_dir / artifacts["asset_manifest"],
        {
            "assets": [
                {
                    **asset.model_dump(mode="json"),
                    "checksum_sha256": _sha256(
                        output_dir / asset.path
                    ),
                }
                for asset in assets
            ]
        },
    )
    _write_json(
        output_dir / artifacts["production_settings"],
        {
            "primary_reference": 10,
            "secondary_reference": 4,
            "supplied_style_reference": (
                str(style_reference)
                if style_reference.is_file()
                else None
            ),
            "quality_target": "reference-style-max",
            "asset_policy": "official-and-free-licensed",
            "voice_policy": "preserve-verbatim",
            "flow_policy": "unused-real-and-evidence-assets-sufficient",
        },
    )
    _write_json(
        output_dir / "style-reference-audit.json",
        {
            "path": str(style_reference),
            "available": style_reference.is_file(),
            "role": "visual grammar only; never rendered as an output asset",
        },
    )

    store = ProductionStore(output_dir)
    now = datetime.now(UTC)
    record = ProductionJobRecord(
        id="production-0809-reference-style-v1",
        source_path=str(source),
        output_dir=str(output_dir),
        state="blueprint-ready",
        primary_reference=10,
        secondary_reference=4,
        flow_operation_budget=0,
        artifacts=artifacts,
        state_history=[
            ProductionStateEvent(
                state="analyzing",
                at=now,
                detail="0809 narration, evidence, and source structure analyzed.",
            ),
            ProductionStateEvent(
                state="blueprint-ready",
                at=now,
                detail=(
                    "Story-specific reference-style blueprint persisted "
                    "without Flow or reused reference footage."
                ),
            ),
        ],
        created_at=now,
        updated_at=now,
    )
    if store.record_path.is_file():
        store.save(record)
    else:
        store.create(record)
    return artifacts


def _load_or_transcribe_story(
    source: Path,
    output_dir: Path,
) -> list[TranscriptSegment]:
    audit_dir = output_dir / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    raw_path = audit_dir / "raw-transcript.json"
    if raw_path.is_file():
        segments = [
            TranscriptSegment.model_validate(item)
            for item in json.loads(raw_path.read_text(encoding="utf-8"))
        ]
    else:
        from app.editor.pipeline import transcribe_video

        segments = transcribe_video(source)
        _write_json(
            raw_path,
            [segment.model_dump(mode="json") for segment in segments],
        )
    repaired = repair_nonpositive_word_durations(segments)
    _write_json(
        output_dir / "transcript-aligned.json",
        [segment.model_dump(mode="json") for segment in repaired],
    )
    return repaired


def _prepare_sec_evidence(output_dir: Path) -> dict[str, Path]:
    import fitz

    evidence_dir = output_dir / "assets" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = evidence_dir / "sec-knight-capital-34-70694.pdf"
    if not pdf_path.is_file():
        request = urllib.request.Request(
            _SEC_ORDER_URL,
            headers={
                "User-Agent": (
                    "Codex reference-style video editor "
                    "production@example.com"
                )
            },
        )
        pdf_path.write_bytes(
            urllib.request.urlopen(request, timeout=60).read()
        )
    document = fitz.open(pdf_path)
    try:
        page_images: dict[int, Image.Image] = {}
        for page_number in (2, 6, 7):
            page = document.load_page(page_number - 1)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2.2, 2.2), alpha=False)
            page_images[page_number] = Image.frombytes(
                "RGB",
                (pixmap.width, pixmap.height),
                pixmap.samples,
            )
    finally:
        document.close()
    specs = {
        "evidence-sec-overview": (
            page_images[2],
            (0.08, 0.07, 0.93, 0.45),
            "WHAT HAPPENED",
            "SEC ORDER 34-70694 • PAGE 2",
            "#D7FF64",
        ),
        "evidence-sec-deployment": (
            page_images[6],
            (0.08, 0.05, 0.93, 0.61),
            "ONE OF EIGHT SERVERS MISSED",
            "SEC ORDER 34-70694 • PAGE 6",
            "#D7FF64",
        ),
        "evidence-sec-email": (
            page_images[6],
            (0.08, 0.61, 0.93, 0.94),
            "97 AUTOMATED E-MAILS",
            "SEC ORDER 34-70694 • PAGE 6",
            "#FF625F",
        ),
        "evidence-sec-controls": (
            page_images[7],
            (0.08, 0.04, 0.93, 0.73),
            "CONTROLS DID NOT HALT SMARS",
            "SEC ORDER 34-70694 • PAGE 7",
            "#FF625F",
        ),
    }
    outputs: dict[str, Path] = {}
    for asset_id, (
        page_image,
        crop,
        title,
        source_label,
        accent,
    ) in specs.items():
        path = evidence_dir / f"{asset_id.removeprefix('evidence-')}.png"
        _make_evidence_card(
            page=page_image,
            crop=crop,
            title=title,
            source_label=source_label,
            accent=accent,
            output=path,
        )
        outputs[asset_id] = path
    return outputs


def _make_evidence_card(
    *,
    page: Image.Image,
    crop: tuple[float, float, float, float],
    title: str,
    source_label: str,
    accent: str,
    output: Path,
) -> None:
    width, height = page.size
    excerpt = page.crop(
        (
            round(width * crop[0]),
            round(height * crop[1]),
            round(width * crop[2]),
            round(height * crop[3]),
        )
    )
    canvas = Image.new("RGB", (1080, 1920), "#EEECE7")
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        (48, 58, 1032, 1862),
        radius=34,
        fill="#F9F8F5",
        outline="#C9C5BC",
        width=3,
    )
    draw.rounded_rectangle((72, 88, 1008, 212), radius=22, fill="#11161C")
    draw.rectangle((72, 88, 86, 212), fill=accent)
    draw.text(
        (112, 126),
        title,
        font=_font(42, bold=True),
        fill="white",
        anchor="lm",
    )
    target_width = 900
    scale = target_width / excerpt.width
    target_height = min(1460, round(excerpt.height * scale))
    excerpt = excerpt.resize(
        (target_width, target_height),
        Image.Resampling.LANCZOS,
    )
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    y = 260 + (1480 - target_height) // 2
    shadow_draw.rounded_rectangle(
        (82, y + 10, 998, y + target_height + 26),
        radius=16,
        fill=(0, 0, 0, 45),
    )
    canvas = Image.alpha_composite(
        canvas.convert("RGBA"),
        shadow.filter(ImageFilter.GaussianBlur(14)),
    )
    canvas.alpha_composite(excerpt.convert("RGBA"), (90, y))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        (90, 1768, 990, 1822),
        radius=16,
        fill="#11161C",
    )
    draw.text(
        (540, 1795),
        source_label,
        font=_font(22, bold=True),
        fill="#FFFFFF",
        anchor="mm",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output, quality=96)


def _prepare_brand_logo(*, source: Path, output: Path) -> Path:
    if not source.is_file():
        extracted = (
            output.parents[2]
            / "tmp"
            / "profit-bricks-deck"
            / "unzipped"
            / "ppt"
            / "media"
            / "image.png"
        )
        if extracted.is_file():
            source = extracted
        else:
            raise FileNotFoundError(source)
    image = Image.open(source).convert("RGBA")
    pixels = np.array(image)
    if source.suffix.casefold() not in {".png", ".webp"}:
        minimum = pixels[:, :, :3].min(axis=2)
        alpha = np.clip((255 - minimum) * 5, 0, 255).astype(np.uint8)
        pixels[:, :, 3] = alpha
        image = Image.fromarray(pixels, "RGBA")
    alpha = image.getchannel("A")
    bounding = alpha.getbbox()
    if bounding:
        image = image.crop(bounding)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return output


def _prepare_story_licensed_assets(
    output_dir: Path,
) -> list[AssetRef]:
    destination = output_dir / "assets" / "licensed" / "mixkit"
    destination.mkdir(parents=True, exist_ok=True)
    specs = [
        {
            "id": "licensed-mixkit-trader",
            "source": _STORY_LICENSED_ROOT / "trader-realtime-47214.mp4",
            "filename": "trader-realtime-47214.mp4",
            "remote_id": "47214",
            "source_url": (
                "https://mixkit.co/free-stock-video/"
                "man-analyzing-the-stock-market-in-real-time-47214/"
            ),
            "query": "trader stock market monitors",
        },
        {
            "id": "licensed-mixkit-forex-screen",
            "source": _STORY_LICENSED_ROOT / "forex-screen-47211.mp4",
            "filename": "forex-screen-47211.mp4",
            "remote_id": "47211",
            "source_url": (
                "https://mixkit.co/free-stock-video/"
                "forex-in-real-time-on-a-screen-47211/"
            ),
            "query": "forex chart screen",
        },
        {
            "id": "licensed-mixkit-server",
            "source": _STORY_LICENSED_ROOT / "server-lights-7863.mp4",
            "filename": "server-lights-7863.mp4",
            "remote_id": "7863",
            "source_url": (
                "https://mixkit.co/free-stock-video/"
                "server-lights-flickering-7863/"
            ),
            "query": "server racks data center",
        },
        {
            "id": "licensed-mixkit-code",
            "source": _GLOBAL_MIXKIT_ROOT / "code-screen-9757.mp4",
            "filename": "code-screen-9757.mp4",
            "remote_id": "9757",
            "source_url": (
                "https://mixkit.co/free-stock-video/"
                "computer-code-in-the-screen-9757/"
            ),
            "query": "computer code screen",
        },
    ]
    assets: list[AssetRef] = []
    for spec in specs:
        source = Path(spec["source"])
        if not source.is_file():
            raise FileNotFoundError(source)
        target = _copy_file(source, destination / str(spec["filename"]))
        assets.append(
            AssetRef(
                id=str(spec["id"]),
                kind="video",
                path=_relative(output_dir, target),
                keywords=["licensed context", str(spec["query"])],
                provenance="internet:licensed-stock-video",
                license="Mixkit Free License",
                provider="Mixkit",
                remote_id=str(spec["remote_id"]),
                creator="Mixkit contributor",
                source_url=str(spec["source_url"]),
                license_url="https://mixkit.co/license/",
                search_query=str(spec["query"]),
            )
        )
    license_source = _STORY_LICENSED_ROOT / "mixkit-license.html"
    if license_source.is_file():
        _copy_file(
            license_source,
            destination / "licenses" / "mixkit-license.html",
        )
    for html in _STORY_LICENSED_ROOT.glob("*-page.html"):
        _copy_file(html, destination / "licenses" / html.name)
    return assets


def _build_story_graphics(
    *,
    output_dir: Path,
    brand_logo: Path,
) -> dict[str, Path]:
    graphics_dir = output_dir / "assets" / "graphics"
    graphics_dir.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}

    def save(asset_id: str, image: Image.Image) -> None:
        path = graphics_dir / f"{asset_id}.png"
        image.save(path)
        outputs[asset_id] = path

    save("overlay-presenter-vignette", _presenter_vignette())
    save(
        "overlay-hook-white",
        _text_overlay("AUGUST 1, 2012", y=1285, size=54, color="#FFFFFF"),
    )
    save(
        "overlay-hook-accent",
        _text_overlay(
            "4 MILLION ORDERS",
            y=1385,
            size=88,
            color="#F4EA58",
            bold=True,
        ),
    )
    save(
        "overlay-order-scale",
        _two_line_overlay(
            "AUTOMATED SYSTEM",
            "4M EXECUTIONS",
            accent="#F4EA58",
        ),
    )
    save(
        "overlay-loss-white",
        _text_overlay("IN JUST 45 MINUTES", y=1260, size=52),
    )
    save(
        "overlay-loss-accent",
        _text_overlay(
            "$460 MILLION",
            y=1380,
            size=94,
            color="#FF625F",
            bold=True,
        ),
    )
    save(
        "overlay-question",
        _two_line_overlay(
            "ONE SOFTWARE UPDATE",
            "HOW?",
            accent="#F4EA58",
        ),
    )
    save(
        "overlay-knight-capital",
        _text_overlay(
            "KNIGHT CAPITAL",
            y=1655,
            size=62,
            color="#FFFFFF",
            bold=True,
        ),
    )
    save("overlay-illustrative", _illustrative_label())
    save("graphic-eight-servers", _eight_server_graphic())
    save("overlay-alerts", _alerts_overlay())
    save(
        "overlay-forex-lesson",
        _two_line_overlay(
            "NOT A FOREX INCIDENT",
            "A FOREX LESSON",
            accent="#B8B5F2",
        ),
    )
    save(
        "overlay-verify",
        _two_line_overlay(
            "UPDATE NOT VERIFIED",
            "1 SERVER MISSED",
            accent="#FF625F",
        ),
    )
    save(
        "overlay-stop",
        _two_line_overlay(
            "NO AUTOMATIC",
            "STOP",
            accent="#FF625F",
        ),
    )
    save(
        "overlay-brand-controls",
        _brand_controls_overlay(brand_logo),
    )
    save("overlay-containment", _containment_overlay())
    save("overlay-cta", _cta_overlay(brand_logo))
    return outputs


def _presenter_vignette() -> Image.Image:
    image = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    pixels = image.load()
    for y in range(1920):
        lower = max(0.0, min(1.0, (y - 1040) / 740))
        upper = max(0.0, min(1.0, (250 - y) / 250))
        alpha = round(150 * lower * lower + 34 * upper)
        for x in range(1080):
            pixels[x, y] = (6, 9, 12, min(190, alpha))
    return image


def _text_overlay(
    text: str,
    *,
    y: int,
    size: int,
    color: str = "#FFFFFF",
    bold: bool = False,
) -> Image.Image:
    image = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.text(
        (540, y),
        text,
        font=_font(size, bold=bold),
        fill=color,
        stroke_width=5,
        stroke_fill=(0, 0, 0, 185),
        anchor="mm",
    )
    return image


def _two_line_overlay(
    top: str,
    bottom: str,
    *,
    accent: str,
) -> Image.Image:
    image = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.text(
        (540, 1295),
        top,
        font=_font(49),
        fill="#FFFFFF",
        stroke_width=5,
        stroke_fill=(0, 0, 0, 185),
        anchor="mm",
    )
    draw.text(
        (540, 1400),
        bottom,
        font=_font(82, bold=True),
        fill=accent,
        stroke_width=6,
        stroke_fill=(0, 0, 0, 200),
        anchor="mm",
    )
    return image


def _illustrative_label() -> Image.Image:
    image = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (798, 74, 1020, 126),
        radius=18,
        fill=(8, 12, 16, 185),
        outline=(255, 255, 255, 70),
        width=1,
    )
    draw.text(
        (909, 100),
        "ILLUSTRATIVE",
        font=_font(20, bold=True),
        fill="#FFFFFF",
        anchor="mm",
    )
    return image


def _eight_server_graphic() -> Image.Image:
    image = Image.new("RGB", (1080, 1920), "#0B1016")
    draw = ImageDraw.Draw(image)
    draw.text(
        (72, 155),
        "CODE DEPLOYMENT",
        font=_font(30, bold=True),
        fill="#A8B7C4",
    )
    draw.text(
        (72, 235),
        "8 SERVERS",
        font=_font(76, bold=True),
        fill="#FFFFFF",
    )
    positions = []
    for row in range(4):
        for column in range(2):
            positions.append(
                (
                    100 + column * 475,
                    420 + row * 260,
                    505 + column * 475,
                    610 + row * 260,
                )
            )
    for index, box in enumerate(positions, start=1):
        missed = index == 8
        fill = "#32171A" if missed else "#17232C"
        outline = "#FF625F" if missed else "#6EA8A9"
        draw.rounded_rectangle(
            box,
            radius=24,
            fill=fill,
            outline=outline,
            width=5 if missed else 2,
        )
        x0, y0, x1, y1 = box
        for light in range(5):
            color = "#FF625F" if missed else "#8EE6C2"
            draw.ellipse(
                (
                    x0 + 36 + light * 36,
                    y0 + 42,
                    x0 + 48 + light * 36,
                    y0 + 54,
                ),
                fill=color,
            )
        draw.text(
            ((x0 + x1) // 2, y0 + 122),
            f"SERVER {index}",
            font=_font(27, bold=True),
            fill="#FFFFFF",
            anchor="mm",
        )
        draw.text(
            ((x0 + x1) // 2, y0 + 158),
            "MISSED" if missed else "UPDATED",
            font=_font(22, bold=True),
            fill=outline,
            anchor="mm",
        )
    draw.rounded_rectangle(
        (92, 1560, 988, 1740),
        radius=30,
        fill="#121A22",
        outline="#263744",
        width=2,
    )
    draw.text(
        (540, 1620),
        "7 UPDATED  •  1 MISSED",
        font=_font(42, bold=True),
        fill="#FFFFFF",
        anchor="mm",
    )
    draw.text(
        (540, 1688),
        "ILLUSTRATIVE • BASED ON SEC ORDER 34-70694",
        font=_font(19, bold=True),
        fill="#9CAAB6",
        anchor="mm",
    )
    return image


def _alerts_overlay() -> Image.Image:
    image = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    for index, y in enumerate((1160, 1285, 1410)):
        draw.rounded_rectangle(
            (110 + index * 18, y, 970 - index * 18, y + 96),
            radius=20,
            fill=(20, 25, 31, 226),
            outline=(255, 98, 95, 165),
            width=2,
        )
        draw.ellipse((140, y + 30, 174, y + 64), fill="#FF625F")
        draw.text(
            (205, y + 48),
            "POWER PEG DISABLED",
            font=_font(28, bold=True),
            fill="#FFFFFF",
            anchor="lm",
        )
    draw.text(
        (540, 1595),
        "97",
        font=_font(118, bold=True),
        fill="#FF625F",
        stroke_width=5,
        stroke_fill=(0, 0, 0, 180),
        anchor="mm",
    )
    draw.text(
        (540, 1695),
        "ERROR E-MAILS",
        font=_font(43, bold=True),
        fill="#FFFFFF",
        stroke_width=4,
        stroke_fill=(0, 0, 0, 180),
        anchor="mm",
    )
    return image


def _brand_controls_overlay(brand_logo: Path) -> Image.Image:
    image = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (58, 1080, 1022, 1815),
        radius=38,
        fill=(10, 15, 21, 225),
        outline=(184, 181, 242, 145),
        width=2,
    )
    logo = Image.open(brand_logo).convert("RGBA")
    logo.thumbnail((620, 130), Image.Resampling.LANCZOS)
    image.alpha_composite(logo, ((1080 - logo.width) // 2, 1125))
    draw.text(
        (540, 1325),
        "AUTOMATION SAFETY CONTROLS",
        font=_font(29, bold=True),
        fill="#A5C9CA",
        anchor="mm",
    )
    rows = [
        ("ORDER LIMITS", "#B8B5F2"),
        ("CONTROL AUTOMATION", "#A5C9CA"),
        ("EQUITY PROTECTION", "#FFFFFF"),
    ]
    for index, (label, color) in enumerate(rows):
        y = 1415 + index * 118
        draw.rounded_rectangle(
            (145, y, 935, y + 88),
            radius=20,
            fill=(27, 35, 43, 230),
        )
        draw.ellipse((178, y + 27, 212, y + 61), fill=color)
        draw.text(
            (250, y + 44),
            label,
            font=_font(30, bold=True),
            fill="#FFFFFF",
            anchor="lm",
        )
    return image


def _containment_overlay() -> Image.Image:
    image = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    center = (540, 1425)
    for radius, color, width in (
        (300, (184, 181, 242, 70), 8),
        (220, (165, 201, 202, 110), 8),
        (135, (255, 98, 95, 190), 10),
    ):
        draw.ellipse(
            (
                center[0] - radius,
                center[1] - radius,
                center[0] + radius,
                center[1] + radius,
            ),
            outline=color,
            width=width,
        )
    draw.ellipse((510, 1395, 570, 1455), fill="#FF625F")
    draw.text(
        (540, 1740),
        "LIMIT REPEATED DAMAGE",
        font=_font(44, bold=True),
        fill="#FFFFFF",
        stroke_width=4,
        stroke_fill=(0, 0, 0, 180),
        anchor="mm",
    )
    draw.text(
        (540, 1790),
        "ILLUSTRATIVE SAFETY MODEL",
        font=_font(19, bold=True),
        fill="#B8B5F2",
        anchor="mm",
    )
    return image


def _cta_overlay(brand_logo: Path) -> Image.Image:
    image = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (118, 1170, 962, 1795),
        radius=36,
        fill=(9, 14, 20, 220),
        outline=(184, 181, 242, 145),
        width=2,
    )
    logo = Image.open(brand_logo).convert("RGBA")
    logo.thumbnail((570, 115), Image.Resampling.LANCZOS)
    image.alpha_composite(logo, ((1080 - logo.width) // 2, 1215))
    draw.text(
        (540, 1430),
        "COMMENT FOR",
        font=_font(48),
        fill="#FFFFFF",
        anchor="mm",
    )
    draw.text(
        (540, 1535),
        "LIVE DEMO",
        font=_font(82, bold=True),
        fill="#B8B5F2",
        anchor="mm",
    )
    draw.rounded_rectangle(
        (260, 1630, 820, 1710),
        radius=28,
        fill="#FFFFFF",
    )
    draw.text(
        (540, 1670),
        "DETAILS IN DM",
        font=_font(28, bold=True),
        fill="#10151B",
        anchor="mm",
    )
    return image


def _prepare_story_audio(
    *,
    source: Path,
    output_dir: Path,
) -> dict[str, Path]:
    audio_dir = output_dir / "assets" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    executable = Path(get_ffmpeg_exe())
    original = audio_dir / "dialogue-original.wav"
    processed = audio_dir / "dialogue-processed.wav"
    _run_command(
        [
            str(executable),
            "-hide_banner",
            "-y",
            "-i",
            str(source),
            "-map",
            "0:a:0",
            "-vn",
            "-ac",
            "2",
            "-ar",
            "48000",
            "-c:a",
            "pcm_s24le",
            str(original),
        ]
    )
    _run_command(
        [
            str(executable),
            "-hide_banner",
            "-y",
            "-i",
            str(original),
            "-af",
            (
                "highpass=f=65,"
                "acompressor=threshold=-20dB:ratio=1.8:"
                "attack=20:release=180:makeup=1.15"
            ),
            "-ac",
            "2",
            "-ar",
            "48000",
            "-c:a",
            "pcm_s24le",
            str(processed),
        ]
    )
    v4_audio = (
        _WORKSPACE_ROOT
        / "storage"
        / "deliverables"
        / "0806-production-v4"
        / "assets"
        / "audio"
    )
    music_source = v4_audio / "reference-10-micro-score.wav"
    music = audio_dir / "reference-style-score.wav"
    _run_command(
        [
            str(executable),
            "-hide_banner",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(music_source),
            "-t",
            f"{STORY_DURATION_MS / 1000:.3f}",
            "-af",
            "afade=t=in:st=0:d=0.35,afade=t=out:st=50.15:d=0.65",
            "-ac",
            "2",
            "-ar",
            "48000",
            "-c:a",
            "pcm_s16le",
            str(music),
        ]
    )
    outputs = {
        "dialogue-original": original,
        "dialogue-processed": processed,
        "music-reference-score": music,
    }
    source_sfx = {
        "sfx-hook-impact": "hook-impact.wav",
        "sfx-paper-scroll": "paper-scroll.wav",
        "sfx-ui-click": "ui-click.wav",
        "sfx-tonal-drop": "tonal-drop.wav",
        "sfx-label-snap": "label-snap.wav",
        "sfx-product-click": "product-click.wav",
    }
    for asset_id, filename in source_sfx.items():
        path = _copy_file(v4_audio / filename, audio_dir / filename)
        outputs[asset_id] = path
    return outputs


def _sfx(
    identifier: str,
    asset_id: str,
    start_ms: int,
    duration_ms: int,
    kind: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "id": identifier,
        "asset_id": asset_id,
        "start_ms": start_ms,
        "duration_ms": duration_ms,
        "volume": 0.42,
        "gain_db": -16,
        "kind": kind,
        "reason": reason,
    }


def _evidence_ids_for_role(role: str) -> list[str]:
    return {
        "company": ["sec-four-million", "sec-loss-460m"],
        "missed-server": ["sec-one-of-eight"],
        "error-emails-evidence": ["sec-97-emails"],
        "repeated-error": ["sec-one-of-eight"],
        "missing-controls": ["sec-missing-controls"],
    }.get(role, [])


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path(r"C:\Windows\Fonts\arialbd.ttf")
        if bold
        else Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\segoeuib.ttf")
        if bold
        else Path(r"C:\Windows\Fonts\segoeui.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    raise FileNotFoundError("A reference-compatible system font is required")


def _copy_file(source: Path, destination: Path) -> Path:
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)
    return destination


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _run_command(command: list[str]) -> None:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=3600,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Media command failed")


def build_story_audio_plan(
    segments: list[TranscriptSegment],
    *,
    duration_ms: int,
    sfx_specs: list[dict[str, Any]],
) -> AudioPlan:
    protection = [
        SpeechProtectionWindow(
            start_ms=max(0, round(word.start * 1000) - 100),
            end_ms=min(duration_ms, round(word.start * 1000) + 120),
            word=word.text.strip(),
        )
        for segment in segments
        for word in segment.words
        if word.text.strip()
    ]
    automation = [
        GainAutomation(
            start_ms=max(0, round(segment.start * 1000) - 80),
            end_ms=min(duration_ms, round(segment.end * 1000) + 100),
            gain_db=-5.5,
            reason="duck music beneath narration",
        )
        for segment in segments
        if segment.end > segment.start
    ]
    cues: list[SfxCue] = []
    for spec in sfx_specs:
        cue = SfxCue.model_validate(spec)
        if any(
            cue.start_ms < window.end_ms
            and cue.start_ms + cue.duration_ms > window.start_ms
            for window in protection
        ):
            continue
        cues.append(cue)
    return AudioPlan(
        dialogue_asset_id="dialogue-processed",
        music_asset_id="music-reference-score",
        music_base_gain_db=-20,
        music_duck_db=5.5,
        music_gain_automation=automation,
        speech_protection_windows=protection,
        sfx_asset_ids=sorted({cue.asset_id for cue in cues}),
        sfx_cues=cues,
    )


def story_unverifiable_source_tokens(
    segments: list[TranscriptSegment],
    *,
    confidence_threshold: float = 0.45,
) -> list[str]:
    return [
        word.text.strip().strip(".,!?;:")
        for segment in segments
        for word in segment.words
        if word.text.strip()
        and (
            word.end <= word.start
            or (
                word.confidence is not None
                and word.confidence < confidence_threshold
            )
        )
    ]


def evaluate_reference_style_story(
    *,
    metadata: dict[str, Any],
    frame_audit: dict[str, Any],
    audio: dict[str, Any],
    loudness: dict[str, Any],
    narration: dict[str, Any],
) -> dict[str, Any]:
    checks = [
        _check(
            "duration",
            abs(float(metadata["duration_seconds"]) - 50.833) <= 0.075,
            metadata["duration_seconds"],
            "50.833 +/- 0.075 seconds",
        ),
        _check(
            "frame-count",
            int(metadata["frame_count"]) == 1_525,
            metadata["frame_count"],
            1_525,
        ),
        _check(
            "codec-geometry",
            int(metadata["width"]) == 1080
            and int(metadata["height"]) == 1920
            and abs(float(metadata["fps"]) - 30) <= 0.01,
            {
                "width": metadata["width"],
                "height": metadata["height"],
                "fps": metadata["fps"],
            },
            "1080x1920 at 30 fps",
        ),
        _check(
            "rendered-hard-cuts",
            17 <= int(frame_audit["rendered_cut_count"]) <= 24,
            frame_audit["rendered_cut_count"],
            "17-24",
        ),
        _check(
            "median-shot",
            1_800 <= float(frame_audit["median_shot_ms"]) <= 3_000,
            frame_audit["median_shot_ms"],
            "1800-3000 ms",
        ),
        _check(
            "motion",
            3.0 <= float(frame_audit["motion_score"]) <= 7.5,
            frame_audit["motion_score"],
            "3.0-7.5",
        ),
        _check(
            "darkness",
            float(frame_audit["dark_frame_ratio"]) <= 0.45,
            frame_audit["dark_frame_ratio"],
            "<= 0.45",
        ),
        _check(
            "luminance",
            60 <= float(frame_audit["mean_luminance"]) <= 105,
            frame_audit["mean_luminance"],
            "60-105",
        ),
        _check(
            "saturation",
            45 <= float(frame_audit["mean_saturation"]) <= 110,
            frame_audit["mean_saturation"],
            "45-110",
        ),
        _check(
            "audio-continuity",
            bool(audio["delay_passed"])
            and bool(audio["duration_passed"])
            and bool(audio["spectral_passed"]),
            audio,
            "zero damaging delay, duration loss, or speech-band discontinuity",
        ),
        _check(
            "loudness",
            -14.7 <= float(loudness["integrated_lufs"]) <= -13.7
            and float(loudness["true_peak_dbtp"]) <= -1,
            loudness,
            "-14.2 LUFS +/- 0.5; true peak <= -1 dBTP",
        ),
        _check(
            "narration-retention",
            float(narration["token_retention"]) >= 0.99
            and not narration["protected_tokens_missing"],
            narration,
            ">= 99% tokens; no protected words missing",
        ),
    ]
    return {
        "automated_pass": all(check["passed"] for check in checks),
        "human_approved": False,
        "checks": checks,
    }


def build_reference_story_master_command(
    *,
    executable: Path,
    rendered: Path,
    output: Path,
    measurement: dict[str, float],
    duration_seconds: float,
    leading_trim_ms: int,
) -> list[str]:
    trim_seconds = max(0, leading_trim_ms) / 1000
    filters: list[str] = []
    if trim_seconds > 0:
        filters.extend(
            [
                f"atrim=start={trim_seconds:.6f}",
                "asetpts=PTS-STARTPTS",
            ]
        )
    filters.append(
        (
            "loudnorm=I=-14.2:TP=-1.5:LRA=5"
            f":measured_I={measurement['input_i']}"
            f":measured_TP={measurement['input_tp']}"
            f":measured_LRA={measurement['input_lra']}"
            f":measured_thresh={measurement['input_thresh']}"
            f":offset={measurement['target_offset']}"
            ":linear=true:print_format=summary"
        )
    )
    if trim_seconds > 0:
        filters.append(f"apad=pad_dur={trim_seconds:.6f}")
    output_duration = duration_seconds + trim_seconds
    return [
        str(executable),
        "-hide_banner",
        "-y",
        "-i",
        str(rendered),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0",
        "-c:v",
        "copy",
        "-af",
        ",".join(filters),
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "48000",
        "-t",
        f"{output_duration:.3f}",
        "-movflags",
        "+faststart",
        str(output),
    ]


def master_reference_story_render(
    *,
    plan: EditPlanV2,
    rendered: Path,
    output: Path,
) -> dict[str, Any]:
    from app.editor.ffmpeg import measure_loudness_for_master
    from app.editor.production_assembly import _measure_audio_continuity

    pre_master_continuity = _measure_audio_continuity(
        plan=plan,
        edited=rendered,
    )
    estimated_delay_ms = int(
        pre_master_continuity.get("estimated_delay_ms", 0)
    )
    leading_trim_ms = estimated_delay_ms if estimated_delay_ms > 20 else 0
    if leading_trim_ms > 250:
        raise ValueError(
            "Refusing to hide an unexpected dialogue delay greater than "
            "250 ms."
        )
    measurement = measure_loudness_for_master(
        rendered,
        clean_completed_mix=False,
    )
    measurement_dict = {
        "input_i": measurement.input_i,
        "input_tp": measurement.input_tp,
        "input_lra": measurement.input_lra,
        "input_thresh": measurement.input_thresh,
        "target_offset": measurement.target_offset,
    }
    temporary = output.with_name(
        f"{output.stem}.remaster{output.suffix}"
    )
    command = build_reference_story_master_command(
        executable=Path(get_ffmpeg_exe()),
        rendered=rendered,
        output=temporary,
        measurement=measurement_dict,
        duration_seconds=plan.duration_ms / 1000,
        leading_trim_ms=leading_trim_ms,
    )
    _run_command(command)
    os.replace(temporary, output)
    manifest = {
        "pre_master_continuity": pre_master_continuity,
        "applied_leading_trim_ms": leading_trim_ms,
        "target_integrated_lufs": -14.2,
        "target_true_peak_dbtp": -1.5,
        "measurement": measurement_dict,
        "output_duration_seconds": round(
            plan.duration_ms / 1000 + leading_trim_ms / 1000,
            3,
        ),
    }
    _write_json(output.parent / "audio-master.json", manifest)
    return manifest


def assemble_reference_story(
    *,
    output_dir: Path,
) -> dict[str, Any]:
    from app.editor.production_assembly import (
        compile_production_plan,
        render_production_plan,
    )
    from app.editor.production_v4 import ProductionStore

    output_dir = output_dir.expanduser().resolve()
    store = ProductionStore(output_dir)
    record = store.load()
    if record.state not in {
        "blueprint-ready",
        "automated-review",
        "awaiting-final-approval",
    }:
        raise ValueError(
            f"Reference-story assembly is not allowed from {record.state}"
        )
    store.transition(
        "assembling",
        detail="0809 reference-style visual and audio layers are assembling.",
        updates={
            "automated_pass": False,
            "human_approved": False,
            "final_reviewer": None,
            "error": None,
        },
    )
    try:
        plan = compile_production_plan(output_dir)
        rendered = output_dir / "rendered-story.mp4"
        edited = output_dir / "edited.mp4"
        render_production_plan(
            output_dir=output_dir,
            plan=plan,
            output=rendered,
        )
        master_reference_story_render(
            plan=plan,
            rendered=rendered,
            output=edited,
        )
        store.transition(
            "automated-review",
            detail="0809 render complete; pixel, evidence, and audio gates run.",
        )
        report = run_reference_story_review(
            output_dir=output_dir,
            plan=plan,
            edited=edited,
        )
        _write_json(output_dir / "review-report.json", report)
    except Exception:
        current = store.load()
        if current.state in {"assembling", "automated-review"}:
            store.transition(
                "blueprint-ready",
                detail=(
                    "0809 assembly failed; the blueprint and provenance "
                    "were preserved for repair."
                ),
                updates={
                    "automated_pass": False,
                    "error": "Reference-story assembly failed.",
                },
            )
        raise

    artifacts = {
        **record.artifacts,
        "edit_plan": "edit-plan.json",
        "rendered_video": "rendered-story.mp4",
        "edited_video": "edited.mp4",
        "frame_audit": "frame-audit.json",
        "audio_continuity": "audio-continuity.json",
        "asr_retention": "asr-retention.json",
        "review_report": "review-report.json",
        "comparison_sheet": "review/style-comparison-sheet.jpg",
        "contact_sheet": "review/contact-sheet-story.jpg",
    }
    if report["automated_pass"]:
        record = store.transition(
            "awaiting-final-approval",
            detail=(
                "0809 automated gates passed; explicit human approval "
                "is still required."
            ),
            updates={
                "automated_pass": True,
                "human_approved": False,
                "artifacts": artifacts,
                "error": None,
            },
        )
    else:
        record = store.transition(
            "blueprint-ready",
            detail=(
                "0809 automated gates blocked release; revise and rerender."
            ),
            updates={
                "automated_pass": False,
                "human_approved": False,
                "artifacts": artifacts,
                "error": (
                    "Reference-story automated gates failed. Review "
                    "review-report.json."
                ),
            },
        )
    return {
        **record.model_dump(mode="json"),
        "edited_video": "edited.mp4",
        "review_report": "review-report.json",
    }


def remaster_reference_story(
    *,
    output_dir: Path,
) -> dict[str, Any]:
    from app.editor.production_v4 import ProductionStore

    output_dir = output_dir.expanduser().resolve()
    store = ProductionStore(output_dir)
    record = store.load()
    if record.state not in {
        "blueprint-ready",
        "automated-review",
        "awaiting-final-approval",
    }:
        raise ValueError(
            f"Reference-story remaster is not allowed from {record.state}"
        )
    plan = EditPlanV2.model_validate_json(
        (output_dir / "edit-plan.json").read_text(encoding="utf-8")
    )
    rendered = output_dir / "rendered-story.mp4"
    edited = output_dir / "edited.mp4"
    if not rendered.is_file():
        raise FileNotFoundError(rendered)
    store.transition(
        "assembling",
        detail="0809 existing visual master is receiving an audio-only remaster.",
        updates={
            "automated_pass": False,
            "human_approved": False,
            "final_reviewer": None,
            "error": None,
        },
    )
    try:
        master_reference_story_render(
            plan=plan,
            rendered=rendered,
            output=edited,
        )
        store.transition(
            "automated-review",
            detail="0809 audio-only remaster complete; all gates rerun.",
        )
        report = run_reference_story_review(
            output_dir=output_dir,
            plan=plan,
            edited=edited,
        )
        _write_json(output_dir / "review-report.json", report)
    except Exception:
        current = store.load()
        if current.state in {"assembling", "automated-review"}:
            store.transition(
                "blueprint-ready",
                detail=(
                    "0809 audio remaster failed; the existing visual "
                    "master was preserved for repair."
                ),
                updates={
                    "automated_pass": False,
                    "error": "Reference-story audio remaster failed.",
                },
            )
        raise
    artifacts = {
        **record.artifacts,
        "audio_master": "audio-master.json",
        "edit_plan": "edit-plan.json",
        "rendered_video": "rendered-story.mp4",
        "edited_video": "edited.mp4",
        "frame_audit": "frame-audit.json",
        "audio_continuity": "audio-continuity.json",
        "asr_retention": "asr-retention.json",
        "review_report": "review-report.json",
        "comparison_sheet": "review/style-comparison-sheet.jpg",
        "contact_sheet": "review/contact-sheet-story.jpg",
    }
    if report["automated_pass"]:
        record = store.transition(
            "awaiting-final-approval",
            detail=(
                "0809 automated gates passed after the audio-only "
                "remaster; explicit human approval is still required."
            ),
            updates={
                "automated_pass": True,
                "human_approved": False,
                "artifacts": artifacts,
                "error": None,
            },
        )
    else:
        record = store.transition(
            "blueprint-ready",
            detail=(
                "0809 remaster gates blocked release; revise and rerun."
            ),
            updates={
                "automated_pass": False,
                "human_approved": False,
                "artifacts": artifacts,
                "error": (
                    "Reference-story automated gates failed. Review "
                    "review-report.json."
                ),
            },
        )
    return {
        **record.model_dump(mode="json"),
        "edited_video": "edited.mp4",
        "review_report": "review-report.json",
    }


def run_reference_story_review(
    *,
    output_dir: Path,
    plan: EditPlanV2,
    edited: Path,
) -> dict[str, Any]:
    from app.editor.ffmpeg import (
        measure_loudness_for_master,
        verify_render,
    )
    from app.editor.production_assembly import (
        _measure_audio_continuity,
        calculate_layer_coverage,
    )
    from app.editor.production_audit import (
        compare_asr_tokens,
        measure_frame_audit,
    )
    from app.editor.pipeline import transcribe_video_fixed_language

    metadata = verify_render(
        edited,
        expected_width=1080,
        expected_height=1920,
        expected_fps=30,
        require_h264_aac=True,
        require_yuv420p=True,
    )
    frame_audit = measure_frame_audit(edited)
    coverage = calculate_layer_coverage(plan)
    loudness_measurement = measure_loudness_for_master(
        edited,
        clean_completed_mix=False,
    )
    audio = _measure_audio_continuity(plan=plan, edited=edited)
    dialogue = next(
        (
            asset
            for asset in plan.assets
            if asset.id == "dialogue-original"
        ),
        None,
    )
    if dialogue is None:
        raise ValueError("Untouched dialogue master is missing from the plan")
    source_segments = transcribe_video_fixed_language(
        Path(dialogue.path),
        language="en",
    )
    final_segments = transcribe_video_fixed_language(
        edited,
        language="en",
    )
    _write_json(
        output_dir / "transcript-source-audio-asr.json",
        [segment.model_dump(mode="json") for segment in source_segments],
    )
    _write_json(
        output_dir / "transcript-final-asr.json",
        [segment.model_dump(mode="json") for segment in final_segments],
    )
    token_report = compare_asr_tokens(
        source_text=" ".join(segment.text for segment in source_segments),
        final_text=" ".join(segment.text for segment in final_segments),
        protected_terms=[
            "1st August 2012",
            "40 lakh",
            "45 minutes",
            "460 million",
            "Knight Capital",
            "97",
            "Profit Bricks",
            "equity protection",
            "DM",
        ],
        protected_term_aliases={
            "40 lakh": ["40 lakhs"],
            "Knight Capital": ["Night Capital"],
        },
        unverifiable_source_tokens=story_unverifiable_source_tokens(
            source_segments
        ),
    )
    narration = {
        "token_retention": token_report["content_retention_ratio"],
        "content_token_retention": token_report[
            "content_retention_ratio"
        ],
        "raw_token_retention": token_report["raw_retention_ratio"],
        "protected_tokens_missing": token_report[
            "missing_protected_terms"
        ],
        **token_report,
    }
    metadata_dict = {
        "duration_seconds": metadata.duration_seconds,
        "frame_count": metadata.frame_count,
        "width": metadata.width,
        "height": metadata.height,
        "fps": metadata.fps,
    }
    loudness = {
        "integrated_lufs": loudness_measurement.input_i,
        "true_peak_dbtp": loudness_measurement.input_tp,
        "loudness_range": loudness_measurement.input_lra,
    }
    report = evaluate_reference_style_story(
        metadata=metadata_dict,
        frame_audit=frame_audit,
        audio=audio,
        loudness=loudness,
        narration=narration,
    )
    additional_checks = [
        _check(
            "real-direct-source-coverage",
            float(coverage["real_direct_source_ratio"]) >= 0.55,
            coverage["real_direct_source_ratio"],
            ">= 0.55",
        ),
        _check(
            "presenter-coverage",
            0.43 <= float(coverage["presenter_ratio"]) <= 0.72,
            coverage["presenter_ratio"],
            "0.43-0.72 visible pixels",
        ),
        _check(
            "flow-coverage",
            float(coverage["flow_ratio"]) == 0,
            coverage["flow_ratio"],
            0,
        ),
        _check(
            "evidence-count",
            (
                evidence_count := len(
                    json.loads(
                        (output_dir / "evidence.json").read_text(
                            encoding="utf-8"
                        )
                    )
                )
            )
            >= 5,
            evidence_count,
            ">= 5 verified evidence records",
        ),
        _check(
            "continuous-captions",
            not plan.caption_pages,
            len(plan.caption_pages),
            0,
        ),
    ]
    report["checks"].extend(additional_checks)
    report["automated_pass"] = all(
        check["passed"] for check in report["checks"]
    )
    report.update(
        {
            "human_approved": False,
            "frame_audit": frame_audit,
            "coverage": coverage,
            "audio_continuity": audio,
            "loudness": loudness,
            "narration": narration,
            "metadata": metadata_dict,
        }
    )
    _write_json(output_dir / "frame-audit.json", frame_audit)
    _write_json(output_dir / "audio-continuity.json", audio)
    _write_json(output_dir / "asr-retention.json", narration)
    _create_story_contact_sheet(
        video=edited,
        output=output_dir / "review" / "contact-sheet-story.jpg",
    )
    settings = json.loads(
        (output_dir / "production-settings.json").read_text(
            encoding="utf-8"
        )
    )
    reference_value = settings.get("supplied_style_reference")
    if reference_value and Path(reference_value).is_file():
        reference = Path(reference_value)
        _create_style_comparison_sheet(
            reference=reference,
            edited=edited,
            output=output_dir / "review" / "style-comparison-sheet.jpg",
        )
        report["style_reference_frame_audit"] = measure_frame_audit(
            reference
        )
    return report


def _create_story_contact_sheet(*, video: Path, output: Path) -> None:
    timestamps = [
        0.9,
        2.9,
        5.4,
        8.4,
        10.1,
        12.2,
        15.6,
        17.8,
        19.6,
        21.1,
        22.9,
        24.7,
        26.4,
        28.7,
        31.0,
        32.8,
        34.3,
        36.5,
        39.0,
        41.2,
        44.0,
        46.5,
        49.2,
    ]
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise RuntimeError(f"Unable to inspect {video}")
    cells: list[np.ndarray] = []
    try:
        for timestamp in timestamps:
            frame = _frame_at(capture, timestamp)
            cell = cv2.resize(frame, (270, 480))
            cv2.rectangle(cell, (0, 0), (270, 34), (0, 0, 0), -1)
            cv2.putText(
                cell,
                f"{timestamp:04.1f}s",
                (8, 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.62,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
            cells.append(cell)
    finally:
        capture.release()
    while len(cells) % 4:
        cells.append(np.zeros((480, 270, 3), dtype=np.uint8))
    rows = [
        np.hstack(cells[index : index + 4])
        for index in range(0, len(cells), 4)
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(
        str(output),
        np.vstack(rows),
        [cv2.IMWRITE_JPEG_QUALITY, 93],
    )


def _create_style_comparison_sheet(
    *,
    reference: Path,
    edited: Path,
    output: Path,
) -> None:
    pairs = [
        ("HOOK", 1.2, 1.2),
        ("MARKET", 4.0, 3.2),
        ("SCALE", 8.2, 5.4),
        ("LOSS", 16.8, 8.5),
        ("RESET", 20.6, 10.2),
        ("EVIDENCE", 13.3, 15.6),
        ("SERVER", 24.5, 17.8),
        ("ALERT", 13.3, 21.0),
        ("LESSON", 24.5, 26.4),
        ("CONTROLS", 28.8, 36.5),
        ("RISK", 28.8, 41.2),
        ("ENDING", 32.5, 49.2),
    ]
    reference_capture = cv2.VideoCapture(str(reference))
    edited_capture = cv2.VideoCapture(str(edited))
    if not reference_capture.isOpened() or not edited_capture.isOpened():
        reference_capture.release()
        edited_capture.release()
        raise RuntimeError("Unable to create style comparison sheet")
    pair_cells: list[np.ndarray] = []
    try:
        for label, reference_time, edited_time in pairs:
            reference_frame = cv2.resize(
                _frame_at(reference_capture, reference_time),
                (270, 480),
            )
            edited_frame = cv2.resize(
                _frame_at(edited_capture, edited_time),
                (270, 480),
            )
            for cell, suffix in (
                (reference_frame, "REF"),
                (edited_frame, "0809"),
            ):
                cv2.rectangle(cell, (0, 0), (270, 38), (0, 0, 0), -1)
                cv2.putText(
                    cell,
                    _comparison_sheet_label(label, suffix),
                    (8, 26),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )
            pair_cells.append(np.hstack([reference_frame, edited_frame]))
    finally:
        reference_capture.release()
        edited_capture.release()
    rows = [
        np.hstack(pair_cells[index : index + 2])
        for index in range(0, len(pair_cells), 2)
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(
        str(output),
        np.vstack(rows),
        [cv2.IMWRITE_JPEG_QUALITY, 93],
    )


def _comparison_sheet_label(label: str, suffix: str) -> str:
    return f"{label} | {suffix}"


def _frame_at(capture: cv2.VideoCapture, timestamp: float) -> np.ndarray:
    capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
    ok, frame = capture.read()
    if not ok:
        raise RuntimeError(f"Unable to read frame at {timestamp:.3f}s")
    return frame


def _check(
    name: str,
    passed: bool,
    measured: Any,
    target: Any,
) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "measured": measured,
        "target": target,
    }
