from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any

from PIL import Image, ImageDraw, ImageFont
from imageio_ffmpeg import get_ffmpeg_exe

from app.editor.analysis import probe_video
from app.editor.production_v4 import (
    _ensure_flow_instructions,
    build_0806_flow_shots,
    build_0806_shot_schedule,
)
from app.editor.remotion import prepare_renderer_source_proxy
from app.models import (
    AssetRef,
    AudioPlan,
    CaptionPage,
    CaptureManifest,
    EditPlanV1,
    EvidenceItem,
    OutputSpec,
    SfxCue,
)
from app.production_models import (
    BlueprintLayerSpec,
    FlowShotSpec,
    LayerBounds,
    OpacityKeyframe,
    ProductionBlueprint,
    TransformKeyframe,
)


_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_0806_SEED = (
    _WORKSPACE_ROOT
    / "storage"
    / "deliverables"
    / "0806-production-v3"
)
_LICENSED_CONTEXT_ROOT = (
    _WORKSPACE_ROOT / "storage" / "assets" / "licensed" / "mixkit"
)
_LICENSED_CONTEXT_SPECS = [
    {
        "id": "licensed-mixkit-microchip",
        "filename": "microchip-1140.mp4",
        "remote_id": "1140",
        "source_url": (
            "https://mixkit.co/free-stock-video/"
            "microchip-technology-close-up-1140/"
        ),
        "keywords": ["microchip", "processor", "macro", "technology"],
    },
    {
        "id": "licensed-mixkit-code-screen",
        "filename": "code-screen-9757.mp4",
        "remote_id": "9757",
        "source_url": (
            "https://mixkit.co/free-stock-video/"
            "computer-code-in-the-screen-9757/"
        ),
        "keywords": ["code", "screen", "programming", "software"],
    },
    {
        "id": "licensed-mixkit-screen-glasses",
        "filename": "screen-glasses-221.mp4",
        "remote_id": "221",
        "source_url": (
            "https://mixkit.co/free-stock-video/"
            "reflection-of-a-screen-in-glasses-221/"
        ),
        "keywords": ["screen reflection", "developer", "software"],
    },
    {
        "id": "licensed-mixkit-typing",
        "filename": "typing-242.mp4",
        "remote_id": "242",
        "source_url": (
            "https://mixkit.co/free-stock-video/"
            "typing-on-a-laptop-242/"
        ),
        "keywords": ["typing", "laptop", "hands", "software"],
    },
]
_MIXKIT_LICENSE_URL = "https://mixkit.co/license/"

_PRODUCT_CAPTURE_IDS = [
    "capture-metaeditor-code-macro",
    "capture-metaeditor-open",
    "capture-metaeditor-risk-code",
    "capture-metaeditor-rule-highlight",
    "capture-mt5-attach-ea",
    "capture-mt5-hook-action",
    "capture-mt5-navigator-ea",
    "capture-mt5-risk-alternate",
    "capture-mt5-risk-inputs",
    "capture-mt5-strategy-tester",
]
_EVIDENCE_ASSET_IDS = [
    "v3-evidence-automated-trading",
    "v3-evidence-ea-definition",
    "v3-evidence-history",
    "v3-evidence-result",
]
_AUDIO_ASSET_IDS = [
    "dialogue-original",
    "dialogue-processed",
    "generated-music",
    "generated-hook-impact",
    "generated-ui-click",
    "generated-code-tick",
    "generated-label-snap",
    "generated-paper-scroll",
    "generated-number-impact",
    "generated-tonal-drop",
    "generated-reversal-drop",
    "generated-product-click",
]


def build_production_blueprint(
    *,
    source: Path,
    output_dir: Path,
    primary_reference: int,
    secondary_reference: int,
    seed_dir: Path | None = None,
    refresh_evidence: bool = True,
    prepare_media: bool = True,
) -> dict[str, str]:
    source = source.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_seed = (
        seed_dir.expanduser().resolve()
        if seed_dir is not None
        else _DEFAULT_0806_SEED
    )
    if source.stem.casefold() == "0806" and (
        resolved_seed / "edit-plan.json"
    ).is_file():
        return _build_0806_blueprint(
            source=source,
            output_dir=output_dir,
            primary_reference=primary_reference,
            secondary_reference=secondary_reference,
            seed_dir=resolved_seed,
            refresh_evidence=refresh_evidence,
            prepare_media=prepare_media,
        )
    return _build_generic_blueprint(
        source=source,
        output_dir=output_dir,
        prepare_media=prepare_media,
    )


def _build_0806_blueprint(
    *,
    source: Path,
    output_dir: Path,
    primary_reference: int,
    secondary_reference: int,
    seed_dir: Path,
    refresh_evidence: bool,
    prepare_media: bool,
) -> dict[str, str]:
    seed_plan = EditPlanV1.model_validate_json(
        (seed_dir / "edit-plan.json").read_text(encoding="utf-8")
    )
    seed_evidence = [
        EvidenceItem.model_validate(item)
        for item in json.loads(
            (seed_dir / "evidence.json").read_text(encoding="utf-8")
        )
    ]
    capture_manifest = CaptureManifest.model_validate_json(
        (seed_dir / "capture-manifest.json").read_text(encoding="utf-8")
    )
    seed_assets = {asset.id: asset for asset in seed_plan.assets}

    assets: list[AssetRef] = []
    copied_paths: dict[str, Path] = {}
    presenter_path = (
        output_dir / "assets" / "presenter" / "source-presenter.mp4"
    )
    if prepare_media:
        prepare_renderer_source_proxy(
            executable=Path(get_ffmpeg_exe()),
            source=source,
            output=presenter_path,
            fps=30,
        )
    else:
        presenter_path = _copy_file(source, presenter_path)
    assets.append(
        AssetRef(
            id="source-presenter",
            kind="video",
            path=_relative(output_dir, presenter_path),
            keywords=["presenter", "talking head", "source narration"],
            provenance="user-provided",
        )
    )
    copied_paths["source-presenter"] = presenter_path

    for asset_id in _PRODUCT_CAPTURE_IDS:
        source_asset = seed_assets[asset_id]
        original = Path(source_asset.path)
        destination = _copy_file(
            original,
            (
                output_dir
                / "assets"
                / "product"
                / original.name
            ),
        )
        copied_paths[asset_id] = destination
        assets.append(
            source_asset.model_copy(
                update={
                    "path": _relative(output_dir, destination),
                    "provenance": "local-safe-demo-capture",
                }
            )
        )

    licensed_destination = output_dir / "assets" / "licensed" / "mixkit"
    licensed_license_destination = licensed_destination / "licenses"
    for spec in _LICENSED_CONTEXT_SPECS:
        original = _LICENSED_CONTEXT_ROOT / str(spec["filename"])
        destination = _copy_file(
            original,
            licensed_destination / str(spec["filename"]),
        )
        copied_paths[str(spec["id"])] = destination
        assets.append(
            AssetRef(
                id=str(spec["id"]),
                kind="video",
                path=_relative(output_dir, destination),
                keywords=list(spec["keywords"]),
                provenance="internet:licensed-stock-video",
                license="Mixkit Free License",
                provider="Mixkit",
                remote_id=str(spec["remote_id"]),
                creator="Mixkit contributor",
                source_url=str(spec["source_url"]),
                license_url=_MIXKIT_LICENSE_URL,
                search_query="technology programming laptop microchip",
            )
        )
        source_page = (
            _LICENSED_CONTEXT_ROOT
            / "licenses"
            / f"{Path(str(spec['filename'])).stem}.html"
        )
        if source_page.is_file():
            _copy_file(
                source_page,
                licensed_license_destination / source_page.name,
            )
    license_page = (
        _LICENSED_CONTEXT_ROOT / "licenses" / "mixkit-license.html"
    )
    if license_page.is_file():
        _copy_file(
            license_page,
            licensed_license_destination / license_page.name,
        )

    for asset_id in _EVIDENCE_ASSET_IDS:
        source_asset = seed_assets[asset_id]
        original = Path(source_asset.path)
        destination = output_dir / "assets" / "evidence" / original.name
        if asset_id == "v3-evidence-result" and refresh_evidence:
            refreshed = (
                output_dir
                / "assets"
                / "evidence"
                / "mql5-atc-2008-risk-readable.png"
            )
            try:
                _capture_mql5_risk_excerpt(refreshed)
                destination = refreshed
            except Exception:
                destination = _copy_file(original, destination)
        else:
            destination = _copy_file(original, destination)
        copied_paths[asset_id] = destination
        assets.append(
            source_asset.model_copy(
                update={
                    "path": _relative(output_dir, destination),
                    "provenance": "official-source-capture",
                }
            )
        )

    evidence_asset_by_id = {
        "metaquotes-automated-trading": (
            "v3-evidence-automated-trading"
        ),
        "metaquotes-expert-advisor": "v3-evidence-ea-definition",
        "metaquotes-atc-history": "v3-evidence-history",
        "mql5-atc-2008-risk": "v3-evidence-result",
    }
    evidence = [
        item.model_copy(
            update={
                "capture_path": _relative(
                    output_dir,
                    copied_paths[evidence_asset_by_id[item.id]],
                )
            }
        )
        for item in seed_evidence
    ]

    evidence_derivatives = _build_evidence_derivatives(
        output_dir=output_dir,
        history_source=copied_paths["v3-evidence-history"],
        risk_source=copied_paths["v3-evidence-result"],
    )
    for asset_id, path, keywords in evidence_derivatives:
        copied_paths[asset_id] = path
        assets.append(
            AssetRef(
                id=asset_id,
                kind="image",
                path=_relative(output_dir, path),
                keywords=keywords,
                provenance="official-source-capture-derived-crop",
            )
        )

    for asset_id in _AUDIO_ASSET_IDS:
        source_asset = seed_assets[asset_id]
        original = Path(source_asset.path)
        destination = _copy_file(
            original,
            output_dir / "assets" / "audio" / original.name,
        )
        copied_paths[asset_id] = destination
        assets.append(
            source_asset.model_copy(
                update={
                    "path": _relative(output_dir, destination),
                    "provenance": (
                        "source-dialogue-master"
                        if asset_id.startswith("dialogue-")
                        else "local-production-audio"
                    ),
                }
            )
        )

    graphics = _build_deterministic_graphics(output_dir)
    for asset_id, path, keywords in graphics:
        copied_paths[asset_id] = path
        assets.append(
            AssetRef(
                id=asset_id,
                kind="image",
                path=_relative(output_dir, path),
                keywords=keywords,
                provenance="deterministic-production-graphic",
            )
        )
    _build_flow_plates(output_dir)

    captions = _adapt_0806_captions(seed_plan.caption_pages)
    audio = _build_0806_audio(seed_plan.audio)
    flow_shots = _preserve_flow_generation_state(
        build_0806_flow_shots(output_dir),
        output_dir / "flow-shot-plan.json",
    )
    shots = build_0806_shot_schedule()
    layers = _build_0806_layers(shots=shots, flow_shots=flow_shots)

    blueprint = ProductionBlueprint(
        source_filename=source.name,
        source_metadata=seed_plan.source_metadata,
        output=OutputSpec(width=1080, height=1920, fps=30),
        duration_ms=41400,
        assets=assets,
        layers=layers,
        caption_pages=captions,
        audio=audio,
        flow_shots=flow_shots,
        evidence=evidence,
    )
    blueprint_path = output_dir / "blueprint.json"
    _write_json(
        blueprint_path,
        blueprint.model_dump(mode="json"),
    )
    _write_json(
        output_dir / "flow-shot-plan.json",
        [shot.model_dump(mode="json") for shot in flow_shots],
    )
    _ensure_flow_instructions(output_dir)
    _write_json(
        output_dir / "caption-plan.json",
        {
            "primary_reference": primary_reference,
            "secondary_reference": secondary_reference,
            "pages": [
                page.model_dump(mode="json") for page in captions
            ],
        },
    )
    _write_json(
        output_dir / "evidence.json",
        [item.model_dump(mode="json") for item in evidence],
    )
    layer_ids_by_shot: dict[str, list[str]] = defaultdict(list)
    for layer in layers:
        layer_ids_by_shot[layer.shot_id].append(layer.id)
    storyboard = [
        {
            **shot,
            "layer_ids": layer_ids_by_shot[shot["id"]],
            "caption_family": _caption_family_at(
                captions,
                int(shot["start_ms"]),
            ),
        }
        for shot in shots
    ]
    _write_json(output_dir / "storyboard.json", storyboard)
    _write_capture_manifest(
        output_dir=output_dir,
        capture_manifest=capture_manifest,
    )
    _write_asset_manifest(output_dir=output_dir, assets=assets)
    _write_json(
        output_dir / "production-settings.json",
        {
            "primary_reference": primary_reference,
            "secondary_reference": secondary_reference,
            "quality_target": "reference-max",
            "asset_policy": "free-licensed",
            "voice_policy": "preserve-verbatim",
            "flow_policy": {
                "default_budget": 3,
                "hard_maximum": 5,
                "attempts_per_shot": 2,
                "model": "veo-lite",
                "aspect": "9:16",
                "count": 1,
                "explicit_duration": False,
            },
        },
    )
    transcript_source = seed_dir / "transcript-aligned.json"
    if transcript_source.is_file():
        _copy_file(
            transcript_source,
            output_dir / "transcript-aligned.json",
        )
    _copy_reference_review_targets(
        seed_dir=seed_dir,
        output_dir=output_dir,
    )
    return {
        "blueprint": "blueprint.json",
        "storyboard": "storyboard.json",
        "evidence": "evidence.json",
        "caption_plan": "caption-plan.json",
        "flow_shot_plan": "flow-shot-plan.json",
        "flow_instructions": "flow-instructions.json",
        "capture_manifest": "capture-manifest.json",
        "asset_manifest": "asset-manifest.json",
        "production_settings": "production-settings.json",
        "transcript": "transcript-aligned.json",
        "reference_targets": "review/reference-targets",
    }


def _preserve_flow_generation_state(
    planned_shots: list[FlowShotSpec],
    existing_plan_path: Path,
) -> list[FlowShotSpec]:
    if not existing_plan_path.is_file():
        return planned_shots
    existing_by_id = {
        shot.id: shot
        for shot in (
            FlowShotSpec.model_validate(item)
            for item in json.loads(
                existing_plan_path.read_text(encoding="utf-8")
            )
        )
    }
    return [
        shot.model_copy(
            update={
                "attempts": existing.attempts,
                "status": existing.status,
            }
        )
        if (existing := existing_by_id.get(shot.id)) is not None
        else shot
        for shot in planned_shots
    ]


def _build_generic_blueprint(
    *,
    source: Path,
    output_dir: Path,
    prepare_media: bool,
) -> dict[str, str]:
    metadata = probe_video(source)
    presenter = (
        output_dir / "assets" / "presenter" / "source-presenter.mp4"
    )
    if prepare_media:
        prepare_renderer_source_proxy(
            executable=Path(get_ffmpeg_exe()),
            source=source,
            output=presenter,
            fps=30,
        )
    else:
        presenter = _copy_file(source, presenter)
    asset = AssetRef(
        id="source-presenter",
        kind="video",
        path=_relative(output_dir, presenter),
        keywords=["presenter", "source"],
        provenance="user-provided",
    )
    duration_ms = round(metadata.duration_seconds * 1000)
    blueprint = ProductionBlueprint(
        source_filename=source.name,
        source_metadata=metadata,
        duration_ms=duration_ms,
        assets=[asset],
        layers=[
            BlueprintLayerSpec(
                id="layer-presenter",
                shot_id="shot-01",
                start_ms=0,
                end_ms=duration_ms,
                source_role="presenter",
                asset_id=asset.id,
                source_start_ms=0,
                source_end_ms=duration_ms,
                muted=True,
            )
        ],
    )
    _write_json(
        output_dir / "blueprint.json",
        blueprint.model_dump(mode="json"),
    )
    _write_json(output_dir / "storyboard.json", [])
    _write_json(output_dir / "evidence.json", [])
    _write_json(output_dir / "caption-plan.json", {"pages": []})
    _write_json(output_dir / "flow-shot-plan.json", [])
    _write_asset_manifest(output_dir=output_dir, assets=[asset])
    return {
        "blueprint": "blueprint.json",
        "storyboard": "storyboard.json",
        "evidence": "evidence.json",
        "caption_plan": "caption-plan.json",
        "flow_shot_plan": "flow-shot-plan.json",
        "asset_manifest": "asset-manifest.json",
    }


def _build_0806_layers(
    *,
    shots: list[dict[str, Any]],
    flow_shots,
) -> list[BlueprintLayerSpec]:
    by_role = {str(shot["editorial_role"]): shot for shot in shots}
    product_bounds = LayerBounds(x=0, y=70, width=1080, height=1580)
    product_card_bounds = LayerBounds(
        x=20,
        y=120,
        width=1040,
        height=1250,
    )
    evidence_bounds = LayerBounds(x=38, y=70, width=1004, height=1540)
    flow_bounds = LayerBounds(x=0, y=60, width=1080, height=1580)
    layers: list[BlueprintLayerSpec] = []

    def add_video(
        editorial_role: str,
        asset_id: str,
        *,
        source_start_ms: int,
        source_end_ms: int,
        bounds: LayerBounds = product_bounds,
        source_role: str = "real-product",
        crop_x: float = 0,
        crop_width: float = 1,
        z_index: int = 10,
        border_radius: int = 24,
        scale_end: float = 1.08,
        x_end: float = 0,
        y_end: float = 0,
        fit: str = "cover",
        timeline_start_ms: int | None = None,
        timeline_end_ms: int | None = None,
        layer_id: str | None = None,
        color_filter: str | None = None,
        entrance_scale: float | None = None,
    ) -> None:
        shot = by_role[editorial_role]
        start_ms = (
            timeline_start_ms
            if timeline_start_ms is not None
            else int(shot["start_ms"])
        )
        end_ms = (
            timeline_end_ms
            if timeline_end_ms is not None
            else int(shot["end_ms"])
        )
        duration = end_ms - start_ms
        transform_keyframes = [TransformKeyframe(at_ms=0, scale=1)]
        if entrance_scale is not None:
            transform_keyframes.append(
                TransformKeyframe(
                    at_ms=min(120, max(1, duration - 1)),
                    scale=entrance_scale,
                )
            )
        transform_keyframes.append(
            TransformKeyframe(
                at_ms=duration,
                x=x_end,
                y=y_end,
                scale=scale_end,
            )
        )
        layers.append(
            BlueprintLayerSpec(
                id=f"layer-{layer_id or editorial_role}",
                shot_id=str(shot["id"]),
                start_ms=start_ms,
                end_ms=end_ms,
                source_role=source_role,
                kind="video",
                asset_id=asset_id,
                source_start_ms=source_start_ms,
                source_end_ms=source_end_ms,
                bounds=bounds,
                crop={
                    "x": crop_x,
                    "y": 0,
                    "width": crop_width,
                    "height": 1,
                },
                fit=fit,
                transform_keyframes=transform_keyframes,
                z_index=z_index,
                muted=True,
                border_radius=border_radius,
                color_filter=color_filter
                or (
                    "brightness(1.18) contrast(1.04) saturate(1.22)"
                    if source_role == "real-product"
                    else (
                        "brightness(1.08) contrast(1.04) saturate(1.08)"
                        if source_role == "licensed-context"
                        else (
                            "brightness(1.1) contrast(1.01) saturate(1.05)"
                            if source_role == "presenter"
                            else (
                                "brightness(1.06) contrast(1.01) "
                                "saturate(1.05)"
                            )
                        )
                    )
                ),
                reference_role=str(shot["reference_role"]),
            )
        )

    def add_product_card(
        editorial_role: str,
        asset_id: str,
        *,
        source_start_ms: int,
        source_end_ms: int,
        crop_x: float,
        crop_width: float,
        x_end: float,
        source_role: str = "real-product",
    ) -> None:
        add_image(
            editorial_role,
            "graphic-product-canvas",
            source_role="deterministic-graphic",
            bounds=LayerBounds(x=0, y=0, width=1080, height=1920),
            z_index=5,
            border_radius=0,
            scale_end=1,
            fit="fill",
            layer_id=f"{editorial_role}-backdrop",
        )
        add_video(
            editorial_role,
            asset_id,
            source_start_ms=source_start_ms,
            source_end_ms=source_end_ms,
            bounds=product_card_bounds,
            source_role=source_role,
            crop_x=crop_x,
            crop_width=crop_width,
            z_index=10,
            border_radius=30,
            scale_end=1.15,
            x_end=x_end,
            fit="cover",
            entrance_scale=1.055,
        )
        shot = by_role[editorial_role]
        start_ms = int(shot["start_ms"])
        end_ms = int(shot["end_ms"])
        duration = end_ms - start_ms
        enter_start = round(duration * 0.4)
        enter_end = min(duration - 2, enter_start + 120)
        exit_start = max(enter_end + 1, round(duration * 0.72))
        exit_end = min(duration - 1, exit_start + 120)
        detail_crop_width = crop_width * 0.72
        detail_crop_x = crop_x + (crop_width - detail_crop_width) / 2
        layers.append(
            BlueprintLayerSpec(
                id=f"layer-{editorial_role}-detail",
                shot_id=str(shot["id"]),
                start_ms=start_ms,
                end_ms=end_ms,
                source_role=source_role,
                kind="video",
                asset_id=asset_id,
                source_start_ms=source_start_ms,
                source_end_ms=source_end_ms,
                bounds=product_card_bounds,
                crop={
                    "x": detail_crop_x,
                    "y": 0,
                    "width": detail_crop_width,
                    "height": 1,
                },
                fit="cover",
                transform_keyframes=[
                    TransformKeyframe(at_ms=0, scale=1.06),
                    TransformKeyframe(
                        at_ms=duration,
                        x=-x_end * 0.45,
                        scale=1.18,
                    ),
                ],
                opacity_keyframes=[
                    OpacityKeyframe(at_ms=0, value=0),
                    OpacityKeyframe(at_ms=enter_start, value=0),
                    OpacityKeyframe(at_ms=enter_end, value=0.94),
                    OpacityKeyframe(at_ms=exit_start, value=0.94),
                    OpacityKeyframe(at_ms=exit_end, value=0),
                    OpacityKeyframe(at_ms=duration, value=0),
                ],
                z_index=12,
                muted=True,
                border_radius=30,
                color_filter=(
                    "brightness(1.18) contrast(1.04) saturate(1.22)"
                    if source_role == "real-product"
                    else "brightness(1.08) contrast(1.04) saturate(1.08)"
                ),
                reference_role=str(shot["reference_role"]),
            )
        )

    def add_image(
        editorial_role: str,
        asset_id: str,
        *,
        source_role: str,
        bounds: LayerBounds,
        z_index: int = 10,
        border_radius: int = 18,
        fit: str = "contain",
        scale_end: float = 1.06,
        x_end: float = 0,
        y_end: float = 0,
        timeline_start_ms: int | None = None,
        timeline_end_ms: int | None = None,
        layer_id: str | None = None,
        entrance_scale: float | None = None,
    ) -> None:
        shot = by_role[editorial_role]
        start_ms = (
            timeline_start_ms
            if timeline_start_ms is not None
            else int(shot["start_ms"])
        )
        end_ms = (
            timeline_end_ms
            if timeline_end_ms is not None
            else int(shot["end_ms"])
        )
        duration = end_ms - start_ms
        transform_keyframes = [TransformKeyframe(at_ms=0, scale=1)]
        if entrance_scale is not None:
            transform_keyframes.append(
                TransformKeyframe(
                    at_ms=min(120, max(1, duration - 1)),
                    scale=entrance_scale,
                )
            )
        transform_keyframes.append(
            TransformKeyframe(
                at_ms=duration,
                x=x_end,
                y=y_end,
                scale=scale_end,
            )
        )
        layers.append(
            BlueprintLayerSpec(
                id=f"layer-{layer_id or f'{editorial_role}-{asset_id}'}",
                shot_id=str(shot["id"]),
                start_ms=start_ms,
                end_ms=end_ms,
                source_role=source_role,
                kind="image",
                asset_id=asset_id,
                bounds=bounds,
                fit=fit,
                transform_keyframes=transform_keyframes,
                z_index=z_index,
                muted=True,
                border_radius=border_radius,
                color_filter=(
                    "brightness(1.04) contrast(1.02) saturate(1.08)"
                    if source_role == "direct-evidence"
                    else None
                ),
                reference_role=str(shot["reference_role"]),
            )
        )

    add_video(
        "hook-action",
        "licensed-mixkit-microchip",
        source_start_ms=3000,
        source_end_ms=3650,
        bounds=LayerBounds(x=0, y=0, width=1080, height=1720),
        source_role="licensed-context",
        border_radius=0,
        scale_end=1.04,
        x_end=-12,
        timeline_start_ms=0,
        timeline_end_ms=650,
        layer_id="hook-context",
    )
    add_video(
        "hook-split",
        "capture-mt5-hook-action",
        source_start_ms=650,
        source_end_ms=2340,
        bounds=LayerBounds(x=0, y=0, width=1080, height=960),
        border_radius=0,
        scale_end=1.08,
        x_end=-10,
    )
    hook_shot = by_role["hook-split"]
    layers.append(
        BlueprintLayerSpec(
            id="layer-hook-presenter",
            shot_id=str(hook_shot["id"]),
            start_ms=int(hook_shot["start_ms"]),
            end_ms=int(hook_shot["end_ms"]),
            source_role="presenter",
            kind="video",
            asset_id="source-presenter",
            source_start_ms=int(hook_shot["start_ms"]),
            source_end_ms=int(hook_shot["end_ms"]),
            bounds=LayerBounds(x=0, y=960, width=1080, height=960),
            fit="cover",
            z_index=20,
            muted=True,
            border_radius=0,
            color_filter="brightness(1.08) contrast(1) saturate(1)",
        )
    )
    add_image(
        "hook-action",
        "graphic-hook-headline",
        source_role="deterministic-graphic",
        bounds=LayerBounds(),
        z_index=28,
        border_radius=0,
        fit="fill",
        scale_end=1,
        timeline_start_ms=0,
        timeline_end_ms=2340,
        layer_id="hook-headline",
    )
    add_product_card(
        "metaeditor-open",
        "capture-metaeditor-open",
        source_start_ms=0,
        source_end_ms=1460,
        crop_x=0.18,
        crop_width=0.64,
        x_end=-18,
    )
    add_product_card(
        "code-macro",
        "licensed-mixkit-code-screen",
        source_start_ms=4000,
        source_end_ms=5450,
        source_role="licensed-context",
        crop_x=0,
        crop_width=1,
        x_end=14,
    )
    add_video(
        "rule-highlight",
        "capture-metaeditor-rule-highlight",
        source_start_ms=0,
        source_end_ms=1570,
        crop_x=0.08,
        crop_width=0.84,
        x_end=22,
        scale_end=1.1,
    )
    add_image(
        "rule-highlight",
        "graphic-code-focus",
        source_role="deterministic-graphic",
        bounds=LayerBounds(),
        z_index=22,
        border_radius=0,
        fit="fill",
    )
    add_video(
        "navigator-open",
        "licensed-mixkit-screen-glasses",
        source_start_ms=5000,
        source_end_ms=6100,
        bounds=LayerBounds(x=0, y=0, width=1080, height=1720),
        source_role="licensed-context",
        border_radius=0,
        scale_end=1.05,
        x_end=-12,
    )
    add_product_card(
        "ea-identification",
        "capture-mt5-navigator-ea",
        source_start_ms=1100,
        source_end_ms=2740,
        crop_x=0,
        crop_width=0.48,
        x_end=-34,
    )
    add_video(
        "presenter-reset",
        "source-presenter",
        source_start_ms=9560,
        source_end_ms=10700,
        bounds=LayerBounds(),
        source_role="presenter",
        border_radius=0,
        scale_end=1.02,
    )
    add_product_card(
        "risk-code-detail",
        "capture-metaeditor-risk-code",
        source_start_ms=0,
        source_end_ms=1350,
        crop_x=0.08,
        crop_width=0.84,
        x_end=-20,
    )
    add_video(
        "wrong-rule-branch",
        "capture-metaeditor-risk-code",
        source_start_ms=1350,
        source_end_ms=3460,
        crop_x=0.08,
        crop_width=0.84,
        scale_end=1.12,
        x_end=24,
    )
    add_image(
        "evidence-overview",
        "evidence-history-overview",
        source_role="direct-evidence",
        bounds=evidence_bounds,
        fit="cover",
        scale_end=1.07,
        y_end=-18,
        entrance_scale=1.045,
    )
    add_image(
        "evidence-championship",
        "evidence-history-excerpt",
        source_role="direct-evidence",
        bounds=evidence_bounds,
        fit="cover",
        scale_end=1.07,
        y_end=-18,
        entrance_scale=1.045,
    )
    add_image(
        "evidence-risk-excerpt",
        "evidence-risk-excerpt",
        source_role="direct-evidence",
        bounds=evidence_bounds,
        fit="cover",
        scale_end=1.07,
        y_end=-18,
        entrance_scale=1.045,
    )
    add_image(
        "evidence-number",
        "evidence-risk-number",
        source_role="direct-evidence",
        bounds=evidence_bounds,
        fit="cover",
        scale_end=1.08,
        y_end=-22,
        entrance_scale=1.045,
    )
    add_video(
        "risk-input",
        "capture-mt5-risk-inputs",
        source_start_ms=0,
        source_end_ms=2000,
        crop_x=0.18,
        crop_width=0.64,
        scale_end=1.12,
        x_end=-24,
    )
    add_product_card(
        "risk-input-detail",
        "capture-mt5-risk-inputs",
        source_start_ms=2000,
        source_end_ms=3510,
        crop_x=0.18,
        crop_width=0.64,
        x_end=20,
    )
    add_video(
        "risk-alternate",
        "capture-mt5-risk-alternate",
        source_start_ms=0,
        source_end_ms=1430,
        crop_x=0.18,
        crop_width=0.64,
        scale_end=1.12,
        x_end=22,
    )
    add_video(
        "risk-reversal",
        "capture-mt5-risk-alternate",
        source_start_ms=1430,
        source_end_ms=3130,
        crop_x=0.18,
        crop_width=0.64,
        scale_end=1.1,
        x_end=-20,
    )
    add_image(
        "risk-reversal",
        "graphic-risk-path",
        source_role="deterministic-graphic",
        bounds=LayerBounds(),
        z_index=30,
        border_radius=0,
        fit="fill",
    )
    add_video(
        "lesson-code",
        "licensed-mixkit-typing",
        source_start_ms=1000,
        source_end_ms=3120,
        bounds=LayerBounds(x=0, y=0, width=1080, height=1720),
        source_role="licensed-context",
        border_radius=0,
        scale_end=1.06,
        x_end=12,
    )
    add_product_card(
        "lesson-parameters",
        "capture-mt5-risk-inputs",
        source_start_ms=0,
        source_end_ms=2300,
        crop_x=0.18,
        crop_width=0.64,
        x_end=-20,
    )
    add_video(
        "presenter-reset-2",
        "source-presenter",
        source_start_ms=32200,
        source_end_ms=33180,
        bounds=LayerBounds(),
        source_role="presenter",
        border_radius=0,
        scale_end=1.02,
    )
    add_product_card(
        "attach-ea",
        "capture-mt5-attach-ea",
        source_start_ms=0,
        source_end_ms=2020,
        crop_x=0.16,
        crop_width=0.68,
        x_end=22,
    )
    add_product_card(
        "strategy-tester",
        "capture-mt5-strategy-tester",
        source_start_ms=0,
        source_end_ms=1960,
        crop_x=0.12,
        crop_width=0.76,
        x_end=-16,
    )
    add_video(
        "presenter-cta",
        "source-presenter",
        source_start_ms=37160,
        source_end_ms=41400,
        bounds=LayerBounds(),
        source_role="presenter",
        border_radius=0,
        scale_end=1.025,
    )

    shot_for_time = lambda timestamp: next(
        shot
        for shot in shots
        if int(shot["start_ms"]) <= timestamp < int(shot["end_ms"])
    )
    for flow_shot in flow_shots:
        owner = shot_for_time(flow_shot.start_ms)
        duration = flow_shot.end_ms - flow_shot.start_ms
        flow_x_end = {
            "flow-wrong-rule-branch": 32,
            "flow-physical-risk": -28,
            "flow-reversal-texture": 34,
        }[flow_shot.id]
        layers.append(
            BlueprintLayerSpec(
                id=f"layer-{flow_shot.id}",
                shot_id=str(owner["id"]),
                start_ms=flow_shot.start_ms,
                end_ms=flow_shot.end_ms,
                source_role="flow-illustrative",
                kind="video",
                flow_shot_id=flow_shot.id,
                bounds=flow_bounds,
                fit="cover",
                transform_keyframes=[
                    TransformKeyframe(at_ms=0, scale=1),
                    TransformKeyframe(at_ms=120, scale=1.05),
                    TransformKeyframe(
                        at_ms=duration,
                        x=flow_x_end,
                        scale=1.14,
                    ),
                ],
                opacity_keyframes=[
                    OpacityKeyframe(at_ms=0, value=1),
                    OpacityKeyframe(at_ms=duration, value=1),
                ],
                blend_mode="normal",
                z_index=24,
                muted=True,
                illustrative_label=True,
                border_radius=28,
                color_filter=(
                    "brightness(1.08) contrast(1.04) saturate(1.15)"
                ),
                reference_role=(
                    "secondary-4"
                    if "risk" in flow_shot.editorial_role
                    else "primary-10"
                ),
            )
        )
    return layers


def _adapt_0806_captions(
    pages: list[CaptionPage],
) -> list[CaptionPage]:
    adapted: list[CaptionPage] = []
    for page in pages:
        if page.start_ms < 2340 or page.start_ms >= 37160:
            family = "compact-pill"
            anchor = "center-76"
            transition = "fade-up"
        elif 14160 <= page.start_ms < 21140:
            family = "documentary-clean"
            anchor = "center-71"
            transition = "hard-cut"
        else:
            family = "technical-mono"
            anchor = "center-74"
            transition = "hard-cut"
        adapted.append(
            page.model_copy(
                update={
                    "family": family,
                    "anchor": anchor,
                    "transition": transition,
                    "max_width": min(page.max_width, 900),
                }
            )
        )
    return adapted


def _build_0806_audio(seed_audio: AudioPlan) -> AudioPlan:
    cue_specs = [
        (
            "v4-hook-impact",
            "generated-hook-impact",
            2380,
            260,
            "impact",
            "Hook release after the opening phrase.",
        ),
        (
            "v4-editor-click",
            "generated-ui-click",
            3380,
            70,
            "click",
            "MetaEditor open action.",
        ),
        (
            "v4-code-tick",
            "generated-code-tick",
            5290,
            45,
            "click",
            "Rule-line highlight.",
        ),
        (
            "v4-label-snap",
            "generated-label-snap",
            7440,
            100,
            "notification",
            "Expert Advisor identification.",
        ),
        (
            "v4-paper",
            "generated-paper-scroll",
            17540,
            360,
            "whoosh",
            "Evidence transition during a narration pause.",
        ),
        (
            "v4-number",
            "generated-number-impact",
            21160,
            180,
            "impact",
            "Verified-number sequence release.",
        ),
        (
            "v4-risk-turn",
            "generated-tonal-drop",
            23160,
            420,
            "impact",
            "Risk turn after the sentence completes.",
        ),
        (
            "v4-reversal",
            "generated-reversal-drop",
            27940,
            520,
            "whoosh",
            "Reversal tail after the lesson onset.",
        ),
        (
            "v4-product",
            "generated-product-click",
            32900,
            80,
            "click",
            "Product demonstration setup before speech resumes.",
        ),
    ]
    cues = [
        SfxCue(
            id=cue_id,
            asset_id=asset_id,
            start_ms=start_ms,
            duration_ms=duration_ms,
            volume=0.16,
            gain_db=-18,
            kind=kind,
            reason=reason,
        )
        for (
            cue_id,
            asset_id,
            start_ms,
            duration_ms,
            kind,
            reason,
        ) in cue_specs
    ]
    protected = seed_audio.speech_protection_windows
    safe_cues = [
        cue
        for cue in cues
        if not any(
            cue.start_ms < window.end_ms
            and cue.start_ms + cue.duration_ms > window.start_ms
            for window in protected
        )
    ]
    return seed_audio.model_copy(
        update={
            "dialogue_asset_id": "dialogue-processed",
            "dialogue_offset_ms": -70,
            "music_asset_id": "generated-music",
            "music_base_gain_db": -20,
            "music_duck_db": 6,
            "sfx_asset_ids": sorted(
                {cue.asset_id for cue in safe_cues}
            ),
            "sfx_cues": safe_cues,
        }
    )


def _build_evidence_derivatives(
    *,
    output_dir: Path,
    history_source: Path,
    risk_source: Path,
) -> list[tuple[str, Path, list[str]]]:
    evidence_dir = output_dir / "assets" / "evidence"
    history_overview = evidence_dir / "history-overview-card.png"
    history_excerpt = evidence_dir / "history-championship-excerpt.png"
    risk_excerpt = evidence_dir / "risk-110000-excerpt.png"
    risk_number = evidence_dir / "risk-110000-number.png"
    with Image.open(history_source) as opened_history:
        history = opened_history.convert("RGB")
    history_crop = history.crop(
        (
            round(0.06 * history.width),
            round(0.48 * history.height),
            round(0.94 * history.width),
            round(0.68 * history.height),
        )
    )
    with Image.open(risk_source) as opened_risk:
        risk = opened_risk.convert("RGB")
    if risk.width / max(1, risk.height) > 2:
        readable_risk = risk
    else:
        readable_risk = risk.crop(
            (
                round(0.14 * risk.width),
                round(0.14 * risk.height),
                round(0.96 * risk.width),
                round(0.30 * risk.height),
            )
        )

    _build_editorial_evidence_card(
        source_pixels=history,
        destination=history_overview,
        kicker="OFFICIAL METAQUOTES SOURCE",
        title="AUTOMATED TRADING",
        source_line="metatrader5.com/en/automated-trading",
        background="#10292A",
        accent="#6FE5D4",
    )
    _build_editorial_evidence_card(
        source_pixels=history_crop,
        destination=history_excerpt,
        kicker="OFFICIAL HISTORY",
        title="AUTOMATED TRADING\nCHAMPIONSHIP",
        source_line="MetaQuotes • 2006–2012 overview",
        background="#F1EBDD",
        accent="#2D9E8E",
        dark_text=True,
        callout_label="OFFICIAL CHAMPIONSHIP YEARS",
        callout="2006 — 2012",
        callout_size=92,
    )
    _build_editorial_evidence_card(
        source_pixels=readable_risk,
        destination=risk_excerpt,
        kicker="PRIMARY EVIDENCE",
        title="THE 2008 RESULT",
        source_line="mql5.com/en/articles/525",
        background="#172238",
        accent="#80D9FF",
        callout_label="VERBATIM SOURCE EXCERPT",
        callout="TOO AGGRESSIVE\nMONEY MANAGEMENT",
        callout_size=66,
    )
    _build_risk_number_card(
        risk_source,
        risk_number,
    )
    return [
        (
            "evidence-history-overview",
            history_overview,
            ["MetaQuotes", "Automated Trading", "official overview"],
        ),
        (
            "evidence-history-excerpt",
            history_excerpt,
            ["Automated Trading Championship", "2006-2012"],
        ),
        (
            "evidence-risk-excerpt",
            risk_excerpt,
            ["ATC 2008", "money management", "110,000"],
        ),
        (
            "evidence-risk-number",
            risk_number,
            ["110,000", "14,749", "money management"],
        ),
    ]


def _build_risk_number_card(source: Path, destination: Path) -> None:
    with Image.open(source) as opened:
        source_pixels = opened.convert("RGB")
    if source_pixels.width / max(1, source_pixels.height) <= 2:
        source_pixels = source_pixels.crop(
            (
                round(0.14 * source_pixels.width),
                round(0.14 * source_pixels.height),
                round(0.96 * source_pixels.width),
                round(0.30 * source_pixels.height),
            )
        )
    _build_editorial_evidence_card(
        source_pixels=source_pixels,
        destination=destination,
        kicker="VERIFIED PRIMARY SOURCE",
        title="$110,000",
        subtitle="earned before aggressive risk reversed the result",
        source_line="MQL5 • Automated Trading Championship 2008",
        background="#E8B44F",
        accent="#14202B",
        dark_text=True,
        number_layout=True,
    )


def _build_editorial_evidence_card(
    *,
    source_pixels: Image.Image,
    destination: Path,
    kicker: str,
    title: str,
    source_line: str,
    background: str,
    accent: str,
    subtitle: str | None = None,
    dark_text: bool = False,
    number_layout: bool = False,
    callout_label: str | None = None,
    callout: str | None = None,
    callout_size: int = 78,
) -> None:
    card = Image.new("RGB", (1080, 1600), background)
    draw = ImageDraw.Draw(card, "RGBA")
    foreground = "#122025" if dark_text else "#F7F5EE"
    muted = "#4D5B5C" if dark_text else "#B5C6C4"
    kicker_font = _font(
        [
            Path(r"C:\Windows\Fonts\seguisb.ttf"),
            Path(r"C:\Windows\Fonts\arialbd.ttf"),
        ],
        27,
    )
    title_font = _font(
        [
            Path(r"C:\Windows\Fonts\georgiab.ttf"),
            Path(r"C:\Windows\Fonts\timesbd.ttf"),
        ],
        118 if number_layout else 54,
    )
    subtitle_font = _font(
        [
            Path(r"C:\Windows\Fonts\segoeui.ttf"),
            Path(r"C:\Windows\Fonts\arial.ttf"),
        ],
        31,
    )
    source_font = _font(
        [
            Path(r"C:\Windows\Fonts\seguisb.ttf"),
            Path(r"C:\Windows\Fonts\arialbd.ttf"),
        ],
        25,
    )
    callout_label_font = _font(
        [
            Path(r"C:\Windows\Fonts\seguisb.ttf"),
            Path(r"C:\Windows\Fonts\arialbd.ttf"),
        ],
        23,
    )
    callout_font = _font(
        [
            Path(r"C:\Windows\Fonts\georgiab.ttf"),
            Path(r"C:\Windows\Fonts\timesbd.ttf"),
        ],
        callout_size,
    )

    draw.rectangle((0, 0, 1080, 18), fill=accent)
    draw.text(
        (64, 74),
        kicker,
        font=kicker_font,
        fill=accent,
    )
    title_y = 134
    draw.multiline_text(
        (64, title_y),
        title,
        font=title_font,
        fill=foreground,
        spacing=6,
    )
    title_box = draw.multiline_textbbox(
        (64, title_y),
        title,
        font=title_font,
        spacing=6,
    )
    current_y = title_box[3] + 26
    if subtitle:
        draw.multiline_text(
            (68, current_y),
            subtitle,
            font=subtitle_font,
            fill=foreground,
            spacing=5,
        )
        subtitle_box = draw.multiline_textbbox(
            (68, current_y),
            subtitle,
            font=subtitle_font,
            spacing=5,
        )
        current_y = subtitle_box[3] + 34
    content_top = max(current_y, 390 if number_layout else 300)
    maximum_width = 916
    maximum_height = max(240, 1400 - content_top - 80)
    pixels = source_pixels.copy()
    pixels.thumbnail(
        (maximum_width, maximum_height),
        Image.Resampling.LANCZOS,
    )
    content_height = min(
        max(pixels.height + 112, 440),
        1400 - content_top,
    )
    content_bottom = content_top + content_height
    draw.rounded_rectangle(
        (42, content_top + 16, 1038, content_bottom + 18),
        radius=28,
        fill=(0, 0, 0, 35),
    )
    draw.rounded_rectangle(
        (42, content_top, 1038, content_bottom),
        radius=28,
        fill=(250, 249, 245, 255),
        outline=(255, 255, 255, 70),
        width=2,
    )

    paste_x = (card.width - pixels.width) // 2
    paste_y = content_top + (content_bottom - content_top - pixels.height) // 2
    card.paste(pixels, (paste_x, paste_y))
    draw.rounded_rectangle(
        (
            paste_x - 6,
            paste_y - 6,
            paste_x + pixels.width + 6,
            paste_y + pixels.height + 6,
        ),
        radius=14,
        outline=(27, 46, 47, 80),
        width=2,
    )
    if callout:
        callout_y = max(content_bottom + 82, 830)
        if callout_label:
            draw.text(
                (64, callout_y),
                callout_label,
                font=callout_label_font,
                fill=accent,
            )
            callout_y += 48
        draw.multiline_text(
            (64, callout_y),
            callout,
            font=callout_font,
            fill=foreground,
            spacing=4,
        )
        callout_box = draw.multiline_textbbox(
            (64, callout_y),
            callout,
            font=callout_font,
            spacing=4,
        )
        rule_y = min(1430, callout_box[3] + 34)
        draw.rounded_rectangle(
            (64, rule_y, 1016, rule_y + 6),
            radius=3,
            fill=accent,
        )
    draw.text(
        (64, 1510),
        source_line,
        font=source_font,
        fill=muted,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    card.save(destination, optimize=True)


def _crop_normalized(
    source: Path,
    destination: Path,
    box: tuple[float, float, float, float],
    *,
    border: int,
    highlight: tuple[float, float, float, float] | None = None,
) -> None:
    image = Image.open(source).convert("RGB")
    width, height = image.size
    crop = image.crop(
        (
            round(box[0] * width),
            round(box[1] * height),
            round(box[2] * width),
            round(box[3] * height),
        )
    )
    canvas = Image.new(
        "RGB",
        (crop.width + border * 2, crop.height + border * 2),
        "#F7F7F5",
    )
    canvas.paste(crop, (border, border))
    if highlight is not None:
        draw = ImageDraw.Draw(canvas, "RGBA")
        draw.rounded_rectangle(
            (
                border + round(highlight[0] * crop.width),
                border + round(highlight[1] * crop.height),
                border + round(highlight[2] * crop.width),
                border + round(highlight[3] * crop.height),
            ),
            radius=10,
            fill=(255, 219, 92, 72),
            outline=(235, 172, 32, 180),
            width=3,
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, optimize=True)


def _capture_mql5_risk_excerpt(destination: Path) -> None:
    import httpx
    from playwright.sync_api import sync_playwright
    from tempfile import TemporaryDirectory

    source_url = "https://www.mql5.com/en/articles/525"
    response = httpx.get(
        source_url,
        headers={"User-Agent": "Mozilla/5.0"},
        follow_redirects=True,
        timeout=60,
    )
    response.raise_for_status()
    if "I managed to earn 110,000" not in response.text:
        raise RuntimeError("The primary evidence excerpt is unavailable")
    html = response.text.replace(
        "<head>",
        '<head><base href="https://www.mql5.com/">',
        1,
    )
    chrome_candidates = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(
            r"C:\Program Files (x86)\Microsoft\Edge\Application"
            r"\msedge.exe"
        ),
    ]
    executable = next(
        (candidate for candidate in chrome_candidates if candidate.is_file()),
        None,
    )
    if executable is None:
        raise RuntimeError("Chrome or Edge is required for evidence capture")

    with TemporaryDirectory(prefix="cutline-evidence-") as temporary:
        root = Path(temporary)
        intro_path = root / "intro.png"
        question_path = root / "question.png"
        answer_path = root / "answer.png"
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                executable_path=str(executable),
            )
            page = browser.new_page(
                viewport={"width": 650, "height": 1000},
                device_scale_factor=2,
            )
            page.set_content(
                html,
                wait_until="networkidle",
                timeout=120_000,
            )
            question = page.get_by_text(
                "Almost two years have passed since the ATC 2008",
                exact=False,
            ).first
            answer = page.get_by_text(
                "I managed to earn 110,000",
                exact=False,
            ).first
            intro = page.get_by_text(
                "earning $110,000 in a certain moment",
                exact=False,
            ).first
            intro.screenshot(path=str(intro_path))
            question.screenshot(path=str(question_path))
            answer.screenshot(path=str(answer_path))
            range_rect = answer.evaluate(
                """element => {
                  const startText = 'I managed to earn 110,000';
                  const endText = 'money management.';
                  const walker = document.createTreeWalker(
                    element,
                    NodeFilter.SHOW_TEXT
                  );
                  const nodes = [];
                  let node;
                  while ((node = walker.nextNode())) nodes.push(node);
                  const full = nodes.map((item) => item.textContent).join('');
                  const start = full.indexOf(startText);
                  const end = full.indexOf(endText, start) + endText.length;
                  const range = document.createRange();
                  let offset = 0;
                  let started = false;
                  for (const item of nodes) {
                    const next = offset + item.textContent.length;
                    if (!started && start >= offset && start <= next) {
                      range.setStart(item, start - offset);
                      started = true;
                    }
                    if (started && end >= offset && end <= next) {
                      range.setEnd(item, end - offset);
                      break;
                    }
                    offset = next;
                  }
                  const rect = range.getBoundingClientRect();
                  const parent = element.getBoundingClientRect();
                  return {
                    y: rect.y - parent.y,
                    height: rect.height,
                    parentWidth: parent.width
                  };
                }"""
            )
            browser.close()

        intro_image = Image.open(intro_path).convert("RGB")
        question_image = Image.open(question_path).convert("RGB")
        answer_image = Image.open(answer_path).convert("RGB")
        scale = answer_image.width / float(range_rect["parentWidth"])
        top = max(0, round(float(range_rect["y"]) * scale))
        bottom = min(
            answer_image.height,
            round(
                (
                    float(range_rect["y"])
                    + float(range_rect["height"])
                    + 4
                )
                * scale
            ),
        )
        answer_crop = answer_image.crop(
            (0, top, answer_image.width, bottom)
        )
        width = max(
            intro_image.width,
            question_image.width,
            answer_crop.width,
        )
        combined = Image.new(
            "RGB",
            (
                width,
                intro_image.height
                + 24
                + question_image.height
                + 24
                + answer_crop.height,
            ),
            "white",
        )
        combined.paste(intro_image, (0, 0))
        combined.paste(
            question_image,
            (0, intro_image.height + 24),
        )
        combined.paste(
            answer_crop,
            (
                0,
                intro_image.height
                + 24
                + question_image.height
                + 24,
            ),
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        combined.save(destination, optimize=True)


def _build_deterministic_graphics(
    output_dir: Path,
) -> list[tuple[str, Path, list[str]]]:
    graphics_dir = output_dir / "assets" / "graphics"
    graphics_dir.mkdir(parents=True, exist_ok=True)
    hook = graphics_dir / "hook-headline.png"
    code = graphics_dir / "code-focus.png"
    risk = graphics_dir / "risk-path.png"
    product_canvas = graphics_dir / "product-canvas.png"

    canvas = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas, "RGBA")
    serif = _font(
        [
            Path(r"C:\Windows\Fonts\georgiab.ttf"),
            Path(r"C:\Windows\Fonts\timesbd.ttf"),
        ],
        86,
    )
    small = _font(
        [
            Path(r"C:\Windows\Fonts\segoeuib.ttf"),
            Path(r"C:\Windows\Fonts\arialbd.ttf"),
        ],
        24,
    )
    draw.rounded_rectangle(
        (70, 122, 1010, 405),
        radius=30,
        fill=(5, 7, 8, 222),
        outline=(255, 255, 255, 42),
        width=2,
    )
    draw.text(
        (540, 174),
        "FOREX TRADING",
        font=serif,
        fill=(247, 244, 235, 255),
        anchor="ma",
    )
    draw.text(
        (540, 274),
        "ROBOT",
        font=serif,
        fill=(247, 244, 235, 255),
        anchor="ma",
    )
    draw.text(
        (540, 370),
        "REAL SOFTWARE  •  REAL RULES",
        font=small,
        fill=(165, 192, 188, 235),
        anchor="mm",
    )
    canvas.save(hook, optimize=True)

    canvas = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rounded_rectangle(
        (112, 835, 968, 1015),
        radius=22,
        fill=(3, 5, 6, 32),
        outline=(128, 226, 217, 210),
        width=4,
    )
    draw.line(
        (112, 1015, 56, 1095),
        fill=(128, 226, 217, 180),
        width=4,
    )
    canvas.save(code, optimize=True)

    canvas = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.line(
        [(130, 430), (400, 430), (655, 650), (920, 650)],
        fill=(234, 239, 236, 215),
        width=8,
        joint="curve",
    )
    draw.polygon(
        [(920, 650), (875, 622), (878, 680)],
        fill=(234, 239, 236, 230),
    )
    draw.line(
        [(400, 430), (655, 1120), (920, 1325)],
        fill=(226, 92, 77, 230),
        width=10,
        joint="curve",
    )
    draw.polygon(
        [(920, 1325), (871, 1287), (884, 1350)],
        fill=(226, 92, 77, 240),
    )
    canvas.save(risk, optimize=True)

    canvas = Image.new("RGB", (1080, 1920))
    draw = ImageDraw.Draw(canvas, "RGBA")
    top = (245, 242, 233)
    bottom = (192, 213, 210)
    for y in range(canvas.height):
        progress = y / max(1, canvas.height - 1)
        color = tuple(
            round(start + (end - start) * progress)
            for start, end in zip(top, bottom, strict=True)
        )
        draw.line((0, y, canvas.width, y), fill=color)
    for x in range(0, 1080, 120):
        draw.line((x, 0, x, 1920), fill=(35, 92, 93, 14), width=1)
    for y in range(0, 1920, 120):
        draw.line((0, y, 1080, y), fill=(35, 92, 93, 12), width=1)
    draw.ellipse(
        (620, -180, 1290, 490),
        fill=(75, 160, 155, 24),
        outline=(48, 123, 120, 34),
        width=3,
    )
    draw.ellipse(
        (-280, 1310, 390, 1980),
        fill=(239, 183, 91, 20),
        outline=(165, 125, 58, 24),
        width=3,
    )
    draw.rectangle((0, 0, 1080, 18), fill=(65, 157, 151, 220))
    canvas.save(product_canvas, optimize=True)
    return [
        (
            "graphic-hook-headline",
            hook,
            ["headline", "Forex Trading Robot"],
        ),
        (
            "graphic-code-focus",
            code,
            ["code highlight", "deterministic callout"],
        ),
        (
            "graphic-risk-path",
            risk,
            ["risk path", "reversal", "deterministic diagram"],
        ),
        (
            "graphic-product-canvas",
            product_canvas,
            ["clean product canvas", "editorial software framing"],
        ),
    ]


def _build_flow_plates(output_dir: Path) -> None:
    directory = output_dir / "flow-plates"
    directory.mkdir(parents=True, exist_ok=True)
    _mechanical_branch_plate(
        directory / "wrong-rule-start.png",
        wrong=False,
    )
    _mechanical_branch_plate(
        directory / "wrong-rule-end.png",
        wrong=True,
    )
    _risk_balance_plate(
        directory / "physical-risk-start.png",
        unstable=False,
    )
    _risk_balance_plate(
        directory / "physical-risk-end.png",
        unstable=True,
    )
    _reversal_plate(
        directory / "reversal-start.png",
        reversed_direction=False,
    )
    _reversal_plate(
        directory / "reversal-end.png",
        reversed_direction=True,
    )


def _plate_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (1080, 1920))
    background = ImageDraw.Draw(image)
    top = (55, 73, 78)
    bottom = (31, 43, 47)
    for y in range(image.height):
        progress = y / max(1, image.height - 1)
        color = tuple(
            round(start + (end - start) * progress)
            for start, end in zip(top, bottom, strict=True)
        )
        background.line((0, y, image.width, y), fill=color)
    draw = ImageDraw.Draw(image, "RGBA")
    draw.ellipse(
        (80, 245, 1000, 1315),
        fill=(105, 151, 148, 24),
        outline=(174, 216, 209, 48),
        width=5,
    )
    for y in range(0, 1920, 80):
        alpha = max(10, 36 - y // 110)
        draw.line(
            (0, y, 1080, y),
            fill=(185, 216, 210, alpha),
            width=1,
        )
    draw.ellipse(
        (180, 400, 900, 1120),
        fill=(74, 101, 102, 178),
        outline=(157, 205, 197, 118),
        width=5,
    )
    draw.ellipse(
        (260, 480, 820, 1040),
        fill=(94, 125, 124, 38),
        outline=(205, 230, 224, 32),
        width=3,
    )
    return image, draw


def _mechanical_branch_plate(path: Path, *, wrong: bool) -> None:
    image, draw = _plate_canvas()
    steel = (185, 203, 199, 255)
    red = (220, 92, 79, 255)
    draw.line((540, 490, 540, 790), fill=steel, width=24)
    draw.ellipse((500, 735, 580, 815), fill=(78, 101, 99, 255))
    draw.line((540, 790, 310, 1050), fill=steel, width=24)
    draw.line(
        (540, 790, 790, 1050),
        fill=red if wrong else (92, 136, 131, 255),
        width=30 if wrong else 18,
    )
    active_x = 790 if wrong else 310
    draw.ellipse(
        (active_x - 72, 980, active_x + 72, 1124),
        fill=red if wrong else (126, 196, 184, 255),
        outline=(240, 244, 238, 170),
        width=4,
    )
    image.save(path, optimize=True)


def _risk_balance_plate(path: Path, *, unstable: bool) -> None:
    image, draw = _plate_canvas()
    center_y = 900
    tilt = 115 if unstable else 0
    draw.polygon(
        [(510, 1120), (570, 1120), (540, 820)],
        fill=(126, 144, 140, 255),
    )
    draw.line(
        (250, center_y - tilt, 830, center_y + tilt),
        fill=(211, 221, 216, 255),
        width=24,
    )
    draw.rounded_rectangle(
        (230, center_y - tilt - 100, 380, center_y - tilt + 40),
        radius=18,
        fill=(87, 151, 139, 255),
    )
    right_height = 260 if unstable else 140
    draw.rounded_rectangle(
        (
            700,
            center_y + tilt - right_height,
            850,
            center_y + tilt + 40,
        ),
        radius=18,
        fill=(202, 94, 76, 255),
    )
    image.save(path, optimize=True)


def _reversal_plate(path: Path, *, reversed_direction: bool) -> None:
    image, draw = _plate_canvas()
    direction = -1 if reversed_direction else 1
    colors = [
        (89, 141, 130, 190),
        (129, 163, 155, 150),
        (210, 103, 83, 185),
    ]
    for index, color in enumerate(colors):
        x = 260 + index * 230
        if direction > 0:
            points = [(x, 1250), (x, 600), (x - 52, 680), (x + 52, 680)]
        else:
            points = [(x, 600), (x, 1250), (x - 52, 1170), (x + 52, 1170)]
        draw.line(points[:2], fill=color, width=28)
        draw.polygon(points[1:], fill=color)
    image.save(path, optimize=True)


def _write_capture_manifest(
    *,
    output_dir: Path,
    capture_manifest: CaptureManifest,
) -> None:
    entries = []
    for entry in capture_manifest.entries:
        filename = Path(entry.path).name
        entries.append(
            entry.model_copy(
                update={
                    "path": f"assets/product/{filename}",
                }
            )
        )
    updated = capture_manifest.model_copy(update={"entries": entries})
    _write_json(
        output_dir / "capture-manifest.json",
        updated.model_dump(mode="json"),
    )


def _write_asset_manifest(
    *,
    output_dir: Path,
    assets: list[AssetRef],
) -> None:
    _write_json(
        output_dir / "asset-manifest.json",
        {
            "policy": "evidence-first free-licensed",
            "assets": [
                {
                    **asset.model_dump(mode="json"),
                    "checksum_sha256": _sha256(
                        output_dir / asset.path
                    ),
                }
                for asset in assets
            ],
        },
    )


def _copy_reference_review_targets(
    *,
    seed_dir: Path,
    output_dir: Path,
) -> None:
    source_dir = seed_dir / "review"
    destination_dir = output_dir / "review" / "reference-targets"
    names = [
        "reference-10-hook.png",
        "reference-10-code.png",
        "reference-10-evidence.png",
        "reference-10-system-diagram.png",
        "reference-10-late-code.png",
        "reference-10-ending.png",
    ]
    for name in names:
        source = source_dir / name
        if source.is_file():
            _copy_file(source, destination_dir / name)


def _caption_family_at(
    captions: list[CaptionPage],
    time_ms: int,
) -> str | None:
    page = next(
        (
            item
            for item in captions
            if item.start_ms <= time_ms < item.end_ms
        ),
        None,
    )
    return page.family if page else None


def _copy_file(source: Path, destination: Path) -> Path:
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if (
        destination.is_file()
        and destination.stat().st_size == source.stat().st_size
        and _sha256(destination) == _sha256(source)
    ):
        return destination
    shutil.copy2(source, destination)
    return destination


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _font(candidates: list[Path], size: int):
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary, path)
