from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable

from app.models import AssetRef
from app.production_models import (
    BlueprintLayerSpec,
    EditPlanV2,
    FlowShotSpec,
    LayerBounds,
    OpacityKeyframe,
    ProductionBlueprint,
    ProductionJobRecord,
    TransformKeyframe,
)
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


STORY_DURATION_MS = 50_833
_FLOW_REPOSITORY = Path(
    r"C:\Users\HPUSER\Documents\ChatGPT\New project"
)
_FLOW_PROFILE = "sahilsharmabybit2"


SeedBuilder = Callable[..., dict[str, str]]
VisualAssetBuilder = Callable[..., list[AssetRef]]
FlowPlateBuilder = Callable[..., object]


def build_0809_v2_schedule() -> list[dict[str, Any]]:
    specs = [
        (0, 900, "presenter", "source-presenter", "hook-date"),
        (900, 2200, "deterministic-graphic", "graphic-order-lanes", "hook-orders"),
        (2200, 4500, "licensed-context", "licensed-mixkit-trader", "market-open"),
        (4500, 6800, "presenter", "source-presenter", "order-scale"),
        (6800, 9500, "licensed-context", "licensed-mixkit-forex-screen", "loss"),
        (9500, 11000, "presenter", "source-presenter", "question-reset"),
        (
            11000,
            12800,
            "flow-illustrative",
            "flow-update-module",
            "software-update-flow",
        ),
        (
            12800,
            14800,
            "licensed-context",
            "licensed-mixkit-code",
            "software-update-code",
        ),
        (
            14800,
            15550,
            "direct-evidence",
            "evidence-sec-overview",
            "company-overview",
        ),
        (
            15550,
            16700,
            "direct-evidence",
            "evidence-sec-overview-highlight",
            "company-highlight",
        ),
        (
            16700,
            18600,
            "flow-illustrative",
            "flow-server-propagation",
            "server-propagation",
        ),
        (
            18600,
            20300,
            "deterministic-graphic",
            "graphic-eight-servers-v2",
            "missed-server",
        ),
        (
            20300,
            22000,
            "direct-evidence",
            "evidence-sec-email-highlight",
            "email-highlight",
        ),
        (22000, 25600, "presenter", "source-presenter", "forex-lesson"),
        (
            25600,
            27500,
            "deterministic-graphic",
            "graphic-incident-bridge",
            "forex-bridge",
        ),
        (
            27500,
            29250,
            "direct-evidence",
            "evidence-sec-deployment-highlight",
            "deployment-highlight",
        ),
        (
            29250,
            30100,
            "deterministic-graphic",
            "graphic-repeat-timeline",
            "repeated-error",
        ),
        (30100, 32100, "presenter", "source-presenter", "verification"),
        (
            32100,
            33600,
            "direct-evidence",
            "evidence-sec-controls",
            "missing-controls",
        ),
        (33600, 34900, "presenter", "source-presenter", "emergency-stop"),
        (
            34900,
            36000,
            "presenter",
            "source-presenter",
            "brand-order-limits",
        ),
        (
            36000,
            37100,
            "presenter",
            "source-presenter",
            "brand-controlled-automation",
        ),
        (
            37100,
            39800,
            "presenter",
            "source-presenter",
            "brand-equity-protection",
        ),
        (
            39800,
            41800,
            "flow-illustrative",
            "flow-risk-containment",
            "risk-containment",
        ),
        (41800, 42500, "presenter", "source-presenter", "damage-limited"),
        (42500, 45200, "presenter", "source-presenter", "cta-setup"),
        (
            45200,
            47200,
            "deterministic-graphic",
            "graphic-control-recap",
            "cta-recap",
        ),
        (47200, 50200, "presenter", "source-presenter", "cta-card"),
        (50200, STORY_DURATION_MS, "presenter", "source-presenter", "clean-ending"),
    ]
    return [
        {
            "id": f"v2-shot-{index:02d}",
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


def build_0809_v2_flow_shots(output_dir: Path) -> list[FlowShotSpec]:
    plates = output_dir.expanduser().resolve() / "flow-plates"
    constraints = [
        "One continuous shot with no internal edit",
        "No evidence or source-document appearance",
        "No exact text, letters, symbols or watermarks",
        "No software UI, interface, dashboard or product screen",
        "No code or terminal content",
        "No chart, graph or plotted data",
        "No number, percentage or count",
        "No currency, balance or financial result",
        "No document, article, report or source page",
        "Keep the primary subject inside the portrait center-safe region",
        "Use well-exposed graphite materials with restrained accent color",
    ]
    return [
        FlowShotSpec(
            id="flow-update-module",
            start_ms=11000,
            end_ms=12800,
            editorial_role="software-update-mechanism",
            prompt=(
                "Portrait cinematic macro shot of a precision graphite module "
                "sliding into a clean mechanical system and locking into "
                "place. A cool cyan signal travels through the mechanism with "
                "one restrained amber reflection. One continuous controlled "
                "camera push, physically plausible movement, crisp material "
                "separation, no readable content."
            ),
            mode="i2v",
            model="veo-lite",
            input_plates=[
                str(plates / "update-start.png"),
                str(plates / "update-end.png"),
            ],
            requested_content=["physical-metaphor"],
            constraints=constraints,
        ),
        FlowShotSpec(
            id="flow-server-propagation",
            start_ms=16700,
            end_ms=18600,
            editorial_role="server-propagation",
            prompt=(
                "Portrait cinematic travel through a clean server corridor. "
                "A cyan light pulse propagates through connected hardware "
                "paths while one side branch stays dark and inactive. One "
                "continuous camera move, restrained documentary lighting, "
                "well-exposed details, no readable indicators."
            ),
            mode="i2v",
            model="veo-lite",
            input_plates=[
                str(plates / "server-start.png"),
                str(plates / "server-end.png"),
            ],
            requested_content=["physical-metaphor"],
            constraints=constraints,
        ),
        FlowShotSpec(
            id="flow-risk-containment",
            start_ms=39800,
            end_ms=41800,
            editorial_role="risk-containment",
            prompt=(
                "Portrait macro shot of an unstable restrained red energy "
                "load moving inside a precision safety mechanism. A cool "
                "cyan mechanical ring closes around the load and stabilizes "
                "it without eliminating it. One continuous shot, clean "
                "graphite materials, subtle camera push, no readable content."
            ),
            mode="i2v",
            model="veo-lite",
            input_plates=[
                str(plates / "risk-start.png"),
                str(plates / "risk-end.png"),
            ],
            requested_content=["abstract-motion"],
            constraints=constraints,
        ),
    ]


def build_0809_v2_layers() -> list[BlueprintLayerSpec]:
    layers: list[BlueprintLayerSpec] = []
    for index, shot in enumerate(build_0809_v2_schedule(), start=1):
        start_ms = int(shot["start_ms"])
        end_ms = int(shot["end_ms"])
        role = str(shot["source_role"])
        asset_id = str(shot["asset_id"])
        duration_ms = end_ms - start_ms
        start_scale = 1.0
        end_scale = 1.035
        start_x = 0.0
        end_x = 0.0
        color_filter: str | None = None
        if role == "presenter":
            scale_cycle = (1.0, 1.075, 1.12, 1.045)
            start_scale = scale_cycle[(index - 1) % len(scale_cycle)]
            end_scale = start_scale + 0.025
            start_x = (-18.0, 0.0, 16.0)[(index - 1) % 3]
            end_x = start_x * -0.35
            color_filter = (
                "brightness(1.035) contrast(1.025) saturate(1.015)"
            )
            if shot["editorial_role"] == "question-reset":
                color_filter = (
                    "grayscale(1) brightness(0.91) contrast(1.12)"
                )
        elif role == "licensed-context":
            end_scale = 1.055
            color_filter = "brightness(0.96) contrast(1.08) saturate(0.9)"
        elif role == "direct-evidence":
            end_scale = 1.025
        elif role == "flow-illustrative":
            end_scale = 1.025
            color_filter = "brightness(1.02) contrast(1.06) saturate(0.94)"
        common = {
            "id": f"base-{shot['editorial_role']}",
            "shot_id": str(shot["id"]),
            "start_ms": start_ms,
            "end_ms": end_ms,
            "source_role": role,
            "bounds": LayerBounds(),
            "transform_keyframes": [
                TransformKeyframe(
                    at_ms=0,
                    x=start_x,
                    scale=start_scale,
                ),
                TransformKeyframe(
                    at_ms=duration_ms,
                    x=end_x,
                    scale=end_scale,
                ),
            ],
            "opacity_keyframes": [OpacityKeyframe(at_ms=0, value=1)],
            "z_index": 10,
            "muted": True,
            "color_filter": color_filter,
            "reference_role": "primary-10",
        }
        if role == "flow-illustrative":
            layers.append(
                BlueprintLayerSpec(
                    **common,
                    kind="video",
                    flow_shot_id=asset_id,
                    illustrative_label=True,
                    fit="cover",
                )
            )
            continue
        kind = "video" if role in {"presenter", "licensed-context"} else "image"
        source_start_ms: int | None = None
        source_end_ms: int | None = None
        playback_rate = 1.0
        if role == "presenter":
            source_start_ms = start_ms
            source_end_ms = end_ms
        elif asset_id == "licensed-mixkit-trader":
            source_start_ms, source_end_ms = 1_000, 3_300
        elif asset_id == "licensed-mixkit-forex-screen":
            source_start_ms, source_end_ms = 2_000, 4_700
        elif asset_id == "licensed-mixkit-code":
            source_start_ms, source_end_ms = 1_000, 3_000
        if source_start_ms is not None and source_end_ms is not None:
            playback_rate = (source_end_ms - source_start_ms) / duration_ms
        layers.append(
            BlueprintLayerSpec(
                **common,
                kind=kind,
                asset_id=asset_id,
                source_start_ms=source_start_ms,
                source_end_ms=source_end_ms,
                playback_rate=playback_rate,
                fit="cover" if kind == "video" else "fill",
            )
        )
    layers.append(
        BlueprintLayerSpec(
            id="evidence-bridge-reset",
            shot_id="v2-shot-15",
            start_ms=25_600,
            end_ms=26_400,
            source_role="direct-evidence",
            kind="image",
            asset_id="evidence-sec-deployment-highlight",
            bounds=LayerBounds(),
            fit="fill",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, scale=1.035),
                TransformKeyframe(at_ms=800, scale=1.075),
            ],
            opacity_keyframes=[OpacityKeyframe(at_ms=0, value=1)],
            z_index=20,
            muted=True,
            reference_role="primary-10",
        )
    )
    overlay_specs = [
        (
            "overlay-hook-date-v2",
            "v2-shot-01",
            0,
            900,
        ),
        (
            "overlay-market-open-v2",
            "v2-shot-03",
            2_200,
            4_500,
        ),
        (
            "overlay-update-question-v2",
            "v2-shot-08",
            12_800,
            14_800,
        ),
        (
            "overlay-control-order-v2",
            "v2-shot-21",
            34_900,
            36_000,
        ),
        (
            "overlay-control-automation-v2",
            "v2-shot-22",
            36_000,
            37_100,
        ),
        (
            "overlay-control-equity-v2",
            "v2-shot-23",
            37_100,
            39_800,
        ),
        (
            "overlay-damage-limited-v2",
            "v2-shot-25",
            41_800,
            42_500,
        ),
        (
            "overlay-cta-setup-v2",
            "v2-shot-26",
            42_500,
            45_200,
        ),
        (
            "overlay-cta-card-v2",
            "v2-shot-28",
            47_200,
            50_200,
        ),
    ]
    layers.extend(
        _v2_overlay_layer(
            asset_id=asset_id,
            shot_id=shot_id,
            start_ms=start_ms,
            end_ms=end_ms,
        )
        for asset_id, shot_id, start_ms, end_ms in overlay_specs
    )
    return layers


def _v2_overlay_layer(
    *,
    asset_id: str,
    shot_id: str,
    start_ms: int,
    end_ms: int,
    entrance_ms: int = 130,
    z_index: int = 100,
) -> BlueprintLayerSpec:
    duration_ms = end_ms - start_ms
    entrance_ms = min(max(1, entrance_ms), duration_ms)
    return BlueprintLayerSpec(
        id=f"{asset_id}-{shot_id}",
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
                y=18 if entrance_ms > 1 else 0,
                scale=0.97 if entrance_ms > 1 else 1,
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
            OpacityKeyframe(
                at_ms=0,
                value=0 if entrance_ms > 1 else 1,
            ),
            OpacityKeyframe(
                at_ms=min(90, duration_ms),
                value=1,
            ),
        ],
        z_index=z_index,
        muted=True,
        reference_role="primary-10",
    )


def _build_v2_visual_assets(
    *,
    output_dir: Path,
    base_assets: list[AssetRef],
) -> list[AssetRef]:
    output_dir = output_dir.expanduser().resolve()
    graphics_dir = output_dir / "assets" / "graphics-v2"
    graphics_dir.mkdir(parents=True, exist_ok=True)
    base_by_id = {asset.id: asset for asset in base_assets}
    created: list[AssetRef] = []

    def save(
        asset_id: str,
        image: Image.Image,
        *,
        provenance: str = "deterministic-production-graphic-v2",
        keywords: list[str] | None = None,
    ) -> None:
        if image.size != (1080, 1920):
            raise ValueError(
                f"{asset_id} must be 1080x1920, got {image.size}"
            )
        path = graphics_dir / f"{asset_id}.png"
        image.save(path, format="PNG", optimize=True)
        created.append(
            AssetRef(
                id=asset_id,
                kind="image",
                path=path.relative_to(output_dir).as_posix(),
                keywords=keywords
                or ["0809", "reference-style", "deterministic graphic"],
                provenance=provenance,
            )
        )

    overview = _required_asset_image(
        output_dir,
        base_by_id,
        "evidence-sec-overview",
    )
    email = _required_asset_image(
        output_dir,
        base_by_id,
        "evidence-sec-email",
    )
    deployment = _required_asset_image(
        output_dir,
        base_by_id,
        "evidence-sec-deployment",
    )
    brand = _optional_asset_image(
        output_dir,
        base_by_id.get("brand-profit-bricks-logo"),
    )

    save("graphic-order-lanes", _order_lanes_graphic())
    save(
        "evidence-sec-overview-highlight",
        _evidence_highlight_graphic(
            overview,
            eyebrow="SEC ORDER 34-70694",
            headline="4 MILLION EXECUTIONS",
            supporting="$460 MILLION LOSS",
            crop_box=(58, 730, 1022, 1305),
            highlight_bands=((0.27, 0.39), (0.39, 0.47)),
            accent="#D9FF45",
        ),
        provenance="official-source-capture-derived-editorial-highlight",
        keywords=["SEC", "Knight Capital", "official evidence", "highlight"],
    )
    save("graphic-eight-servers-v2", _eight_servers_v2_graphic())
    save(
        "evidence-sec-email-highlight",
        _evidence_highlight_graphic(
            email,
            eyebrow="SEC ORDER 34-70694",
            headline="97 AUTOMATED E-MAILS",
            supporting="THE ALERTS WERE NOT REVIEWED",
            crop_box=(58, 760, 1022, 1285),
            highlight_bands=((0.44, 0.57),),
            accent="#FF625F",
        ),
        provenance="official-source-capture-derived-editorial-highlight",
        keywords=["SEC", "Knight Capital", "official evidence", "e-mail"],
    )
    save("graphic-incident-bridge", _incident_bridge_graphic())
    save(
        "evidence-sec-deployment-highlight",
        _evidence_highlight_graphic(
            deployment,
            eyebrow="SEC ORDER 34-70694",
            headline="ONE SERVER MISSED",
            supporting="NO SECOND TECHNICIAN REVIEW",
            crop_box=(58, 605, 1022, 1360),
            highlight_bands=((0.11, 0.23), (0.31, 0.43)),
            accent="#FF625F",
        ),
        provenance="official-source-capture-derived-editorial-highlight",
        keywords=["SEC", "Knight Capital", "official evidence", "deployment"],
    )
    save("graphic-repeat-timeline", _repeat_timeline_graphic())
    save("graphic-control-recap", _control_recap_graphic(brand))
    save(
        "overlay-hook-date-v2",
        _minimal_overlay(
            eyebrow="AUGUST 1, 2012",
            headline="A 45-MINUTE FAILURE",
            accent="#F4EA58",
        ),
    )
    save(
        "overlay-market-open-v2",
        _minimal_overlay(
            eyebrow="MARKET OPEN",
            headline="THE SYSTEM WENT LIVE",
            accent="#D9FF45",
        ),
    )
    save(
        "overlay-update-question-v2",
        _minimal_overlay(
            eyebrow="NORMAL UPDATE",
            headline="HOW DID IT CAUSE THIS?",
            accent="#F4EA58",
        ),
    )
    save(
        "overlay-control-order-v2",
        _control_overlay(
            number="01",
            title="ORDER LIMITS",
            detail="CAP THE BLAST RADIUS",
            accent="#B8B5F2",
        ),
    )
    save(
        "overlay-control-automation-v2",
        _control_overlay(
            number="02",
            title="CONTROLLED AUTOMATION",
            detail="VERIFY BEFORE RELEASE",
            accent="#8EDADD",
        ),
    )
    save(
        "overlay-control-equity-v2",
        _control_overlay(
            number="03",
            title="EQUITY PROTECTION",
            detail="STOP REPEATED DAMAGE",
            accent="#FFFFFF",
        ),
    )
    save(
        "overlay-damage-limited-v2",
        _minimal_overlay(
            eyebrow="THE GOAL",
            headline="LIMIT REPEATED DAMAGE",
            accent="#8EDADD",
        ),
    )
    save(
        "overlay-cta-setup-v2",
        _minimal_overlay(
            eyebrow="SEE THE CONTROLS LIVE",
            headline="FREE LIVE DEMO",
            accent="#B8B5F2",
        ),
    )
    save("overlay-cta-card-v2", _cta_card_v2(brand))
    return created


def _build_v2_flow_plates(*, output_dir: Path) -> None:
    output_dir = output_dir.expanduser().resolve()
    plates_dir = output_dir / "flow-plates"
    plates_dir.mkdir(parents=True, exist_ok=True)
    plates = {
        "update-start.png": _update_plate(progress=0.08),
        "update-end.png": _update_plate(progress=0.92),
        "server-start.png": _server_plate(progress=0.1),
        "server-end.png": _server_plate(progress=0.88),
        "risk-start.png": _risk_plate(containment=0.18),
        "risk-end.png": _risk_plate(containment=0.9),
    }
    for filename, image in plates.items():
        if image.size != (1080, 1920):
            raise ValueError(
                f"{filename} must be 1080x1920, got {image.size}"
            )
        image.save(plates_dir / filename, format="PNG", optimize=True)


def build_reference_story_v2_blueprint(
    *,
    source: Path,
    output_dir: Path,
    seed_builder: SeedBuilder | None = None,
    visual_asset_builder: VisualAssetBuilder | None = None,
    flow_plate_builder: FlowPlateBuilder | None = None,
) -> dict[str, str]:
    from app.editor.production_v4 import ProductionStore

    source = source.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    store = ProductionStore(output_dir)
    if store.record_path.is_file():
        existing = store.load()
        if (
            existing.id == "production-0809-visual-upgrade-v2"
            and (output_dir / "flow-shot-plan.json").is_file()
            and existing.state
            in {
                "awaiting-generation-approval",
                "generating",
                "awaiting-candidate-review",
                "assembling",
                "automated-review",
                "awaiting-final-approval",
                "completed",
            }
        ):
            return dict(existing.artifacts)
    if seed_builder is None:
        from app.editor.reference_story import (
            build_reference_story_blueprint,
        )

        seed_builder = build_reference_story_blueprint
    if visual_asset_builder is None:
        visual_asset_builder = _build_v2_visual_assets
    if flow_plate_builder is None:
        flow_plate_builder = _build_v2_flow_plates

    seed_artifacts = _load_reusable_seed_artifacts(output_dir)
    if seed_artifacts is None:
        seed_artifacts = seed_builder(source=source, output_dir=output_dir)
    blueprint_path = output_dir / "blueprint.json"
    seeded_blueprint = ProductionBlueprint.model_validate_json(
        blueprint_path.read_text(encoding="utf-8")
    )
    v2_assets = visual_asset_builder(
        output_dir=output_dir,
        base_assets=seeded_blueprint.assets,
    )
    flow_plate_builder(output_dir=output_dir)

    assets_by_id = {
        asset.id: asset
        for asset in [*seeded_blueprint.assets, *v2_assets]
    }
    assets = list(assets_by_id.values())
    layers = build_0809_v2_layers()
    flow_shots = build_0809_v2_flow_shots(output_dir)
    blueprint = ProductionBlueprint.model_validate(
        seeded_blueprint.model_copy(
            update={
                "duration_ms": STORY_DURATION_MS,
                "assets": assets,
                "layers": layers,
                "caption_pages": [],
                "flow_shots": flow_shots,
            }
        ).model_dump(mode="json")
    )

    artifacts = {
        **seed_artifacts,
        "blueprint": "blueprint.json",
        "storyboard": "storyboard.json",
        "evidence": "evidence.json",
        "caption_plan": "caption-plan.json",
        "asset_manifest": "asset-manifest.json",
        "production_settings": "production-settings.json",
        "flow_shot_plan": "flow-shot-plan.json",
        "flow_instructions": "flow-instructions.json",
    }
    _write_json(blueprint_path, blueprint.model_dump(mode="json"))
    _write_json(
        output_dir / artifacts["flow_shot_plan"],
        [shot.model_dump(mode="json") for shot in flow_shots],
    )
    _write_json(
        output_dir / artifacts["flow_instructions"],
        _v2_flow_instructions(),
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
                "evidence_ids": _v2_evidence_ids(
                    str(shot["editorial_role"])
                ),
                "caption_family": _v2_caption_family(
                    str(shot["editorial_role"])
                ),
            }
            for shot in build_0809_v2_schedule()
        ],
    )
    _write_json(
        output_dir / artifacts["caption_plan"],
        {
            "continuous_captions": False,
            "typography_layers": [
                layer.id
                for layer in layers
                if layer.id.startswith("overlay-")
            ],
            "policy": (
                "Reference-role typography only; narration remains "
                "unobstructed and verbatim."
            ),
        },
    )
    _write_json(
        output_dir / artifacts["asset_manifest"],
        _asset_manifest_payload(
            output_dir=output_dir,
            assets=assets,
        ),
    )
    settings_path = output_dir / artifacts["production_settings"]
    settings = _read_json(settings_path, default={})
    settings.update(
        {
            "primary_reference": 10,
            "secondary_reference": 4,
            "quality_target": "reference-style-visual-upgrade-v2",
            "asset_policy": "official-free-licensed-and-reviewed-flow",
            "voice_policy": "preserve-verbatim-v1-master-path",
            "flow_policy": (
                "three-short-illustrative-i2v-plates-no-factual-content"
            ),
            "flow_operation_budget": 5,
            "flow_repository": str(_FLOW_REPOSITORY.resolve()),
            "flow_profile": _FLOW_PROFILE,
        }
    )
    _write_json(settings_path, settings)

    seeded_record = store.load()
    prepared_record = ProductionJobRecord.model_validate(
        seeded_record.model_copy(
            update={
                "id": "production-0809-visual-upgrade-v2",
                "source_path": str(source),
                "output_dir": str(output_dir),
                "flow_operation_budget": 5,
                "approved_paid_operations": 0,
                "consumed_paid_operations": 0,
                "flow_profile": _FLOW_PROFILE,
                "flow_project_id": None,
                "flow_repository": str(_FLOW_REPOSITORY.resolve()),
                "artifacts": artifacts,
                "accepted_clips": [],
                "automated_pass": False,
                "human_approved": False,
                "final_reviewer": None,
                "error": None,
                "updated_at": datetime.now(UTC),
            }
        ).model_dump(mode="json")
    )
    store.save(prepared_record)
    if prepared_record.state == "blueprint-ready":
        store.transition(
            "awaiting-generation-approval",
            detail=(
                "Three policy-safe Flow plates are planned; no paid "
                "operation has been submitted."
            ),
            updates={"artifacts": artifacts},
        )
    elif prepared_record.state != "awaiting-generation-approval":
        raise ValueError(
            "V2 planning requires a blueprint-ready seed job, got "
            f"{prepared_record.state}"
        )
    return artifacts


def _load_reusable_seed_artifacts(
    output_dir: Path,
) -> dict[str, str] | None:
    from app.editor.production_v4 import ProductionStore

    output_dir = output_dir.expanduser().resolve()
    store = ProductionStore(output_dir)
    if not store.record_path.is_file():
        return None
    record = store.load()
    blueprint_name = record.artifacts.get("blueprint")
    if (
        record.id != "production-0809-reference-style-v1"
        or record.state != "blueprint-ready"
        or not blueprint_name
        or not (output_dir / blueprint_name).is_file()
    ):
        return None
    return dict(record.artifacts)


def assemble_reference_story_v2(
    *,
    output_dir: Path,
    compiler: Callable[[Path], Any] | None = None,
    renderer: Callable[..., object] | None = None,
    masterer: Callable[..., dict[str, Any]] | None = None,
    reviewer: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    from app.editor.production_v4 import ProductionStore

    if compiler is None:
        from app.editor.production_assembly import compile_production_plan

        compiler = compile_production_plan
    if renderer is None:
        from app.editor.production_assembly import render_production_plan

        renderer = render_production_plan
    if masterer is None:
        from app.editor.reference_story import master_reference_story_render

        masterer = master_reference_story_render
    if reviewer is None:
        reviewer = run_reference_story_v2_review

    output_dir = output_dir.expanduser().resolve()
    store = ProductionStore(output_dir)
    record = store.load()
    if record.state not in {
        "awaiting-candidate-review",
        "automated-review",
        "awaiting-final-approval",
    }:
        raise ValueError(
            f"V2 assembly is not allowed from state {record.state}"
        )
    store.transition(
        "assembling",
        detail="0809 V2 explicit layers and accepted Flow clips are assembling.",
        updates={
            "automated_pass": False,
            "human_approved": False,
            "final_reviewer": None,
            "error": None,
        },
    )
    rendered = output_dir / "rendered-story.mp4"
    edited = output_dir / "edited.mp4"
    try:
        plan = compiler(output_dir)
        renderer(
            output_dir=output_dir,
            plan=plan,
            output=rendered,
        )
        masterer(
            plan=plan,
            rendered=rendered,
            output=edited,
        )
        store.transition(
            "automated-review",
            detail=(
                "0809 V2 render complete; visual, evidence, audio, and "
                "narration gates are running."
            ),
        )
        report = reviewer(
            output_dir=output_dir,
            plan=plan,
            edited=edited,
        )
        _write_json(output_dir / "review-report.json", report)
    except Exception:
        current = store.load()
        if current.state in {"assembling", "automated-review"}:
            store.transition(
                "awaiting-candidate-review",
                detail=(
                    "0809 V2 assembly failed; accepted candidates and "
                    "the blueprint were preserved for repair."
                ),
                updates={
                    "automated_pass": False,
                    "human_approved": False,
                    "error": "0809 V2 assembly failed.",
                },
            )
        raise

    return _finalize_v2_review_state(
        store=store,
        original_record=record,
        report=report,
    )


def remaster_reference_story_v2(
    *,
    output_dir: Path,
    masterer: Callable[..., dict[str, Any]] | None = None,
    reviewer: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    from app.editor.production_v4 import ProductionStore

    if masterer is None:
        from app.editor.reference_story import master_reference_story_render

        masterer = master_reference_story_render
    if reviewer is None:
        reviewer = run_reference_story_v2_review

    output_dir = output_dir.expanduser().resolve()
    store = ProductionStore(output_dir)
    record = store.load()
    if record.state not in {
        "awaiting-candidate-review",
        "automated-review",
        "awaiting-final-approval",
    }:
        raise ValueError(
            f"V2 remaster is not allowed from state {record.state}"
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
        detail="0809 V2 visual master is receiving an audio-only remaster.",
        updates={
            "automated_pass": False,
            "human_approved": False,
            "final_reviewer": None,
            "error": None,
        },
    )
    try:
        masterer(plan=plan, rendered=rendered, output=edited)
        store.transition(
            "automated-review",
            detail="0809 V2 remaster complete; all release gates rerun.",
        )
        report = reviewer(
            output_dir=output_dir,
            plan=plan,
            edited=edited,
        )
        _write_json(output_dir / "review-report.json", report)
    except Exception:
        current = store.load()
        if current.state in {"assembling", "automated-review"}:
            store.transition(
                "awaiting-candidate-review",
                detail=(
                    "0809 V2 remaster failed; the existing visual master "
                    "and accepted candidates were preserved."
                ),
                updates={
                    "automated_pass": False,
                    "human_approved": False,
                    "error": "0809 V2 remaster failed.",
                },
            )
        raise
    return _finalize_v2_review_state(
        store=store,
        original_record=record,
        report=report,
    )


def _finalize_v2_review_state(
    *,
    store: Any,
    original_record: ProductionJobRecord,
    report: dict[str, Any],
) -> dict[str, Any]:
    artifacts = {
        **original_record.artifacts,
        "audio_master": "audio-master.json",
        "edit_plan": "edit-plan.json",
        "rendered_video": "rendered-story.mp4",
        "edited_video": "edited.mp4",
        "frame_audit": "frame-audit.json",
        "audio_continuity": "audio-continuity.json",
        "asr_retention": "asr-retention.json",
        "review_report": "review-report.json",
        "comparison_sheet": "review/style-comparison-sheet.jpg",
        "contact_sheet": "review/contact-sheet-story-v2.jpg",
    }
    if report["automated_pass"]:
        record = store.transition(
            "awaiting-final-approval",
            detail=(
                "0809 V2 automated gates passed; explicit human approval "
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
            "awaiting-candidate-review",
            detail=(
                "0809 V2 automated gates blocked release; revise the "
                "visual blueprint or candidate selection and rerender."
            ),
            updates={
                "automated_pass": False,
                "human_approved": False,
                "artifacts": artifacts,
                "error": (
                    "0809 V2 automated gates failed. Review "
                    "review-report.json."
                ),
            },
        )
    return {
        **record.model_dump(mode="json"),
        "edited_video": "edited.mp4",
        "review_report": "review-report.json",
    }


def run_reference_story_v2_review(
    *,
    output_dir: Path,
    plan: EditPlanV2,
    edited: Path,
) -> dict[str, Any]:
    from app.editor.ffmpeg import (
        measure_loudness_for_master,
        verify_render,
    )
    from app.editor.pipeline import transcribe_video_fixed_language
    from app.editor.production_assembly import (
        _measure_audio_continuity,
        calculate_layer_coverage,
    )
    from app.editor.production_audit import (
        compare_asr_tokens,
        measure_frame_audit,
    )
    from app.editor.reference_story import (
        _create_story_contact_sheet,
        _create_style_comparison_sheet,
        story_unverifiable_source_tokens,
    )
    from app.editor.production_v4 import ProductionStore

    output_dir = output_dir.expanduser().resolve()
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
        raise ValueError("Untouched dialogue master is missing from V2")
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
    report = evaluate_reference_story_v2(
        metadata=metadata_dict,
        frame_audit=frame_audit,
        coverage=coverage,
        audio=audio,
        loudness=loudness,
        narration=narration,
    )
    evidence_records = _read_json(
        output_dir / "evidence.json",
        default=[],
    )
    record = ProductionStore(output_dir).load()
    flow_layers = [
        layer
        for layer in plan.visual_layers
        if layer.source_role == "flow-illustrative"
    ]
    additional_checks = [
        _check(
            "verified-evidence-records",
            len(evidence_records) >= 5
            and all(
                item.get("status") == "verified"
                for item in evidence_records
            ),
            len(evidence_records),
            ">= 5 records, all verified",
        ),
        _check(
            "accepted-flow-candidates",
            len(record.accepted_clips) == 3,
            len(record.accepted_clips),
            3,
        ),
        _check(
            "flow-labels-and-mute",
            len(flow_layers) == 3
            and all(
                layer.illustrative_label and layer.muted and not layer.loop
                for layer in flow_layers
            ),
            {
                "flow_layers": len(flow_layers),
                "valid": sum(
                    1
                    for layer in flow_layers
                    if layer.illustrative_label
                    and layer.muted
                    and not layer.loop
                ),
            },
            "3 muted, non-looping, visibly labelled Flow layers",
        ),
        _check(
            "continuous-captions",
            not plan.caption_pages,
            len(plan.caption_pages),
            0,
        ),
        _check(
            "visual-source-diversity",
            int(coverage["visual_source_count"]) >= 12,
            coverage["visual_source_count"],
            ">= 12 visible source assets",
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
        output=output_dir / "review" / "contact-sheet-story-v2.jpg",
    )
    settings = _read_json(
        output_dir / "production-settings.json",
        default={},
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


def evaluate_reference_story_v2(
    *,
    metadata: dict[str, Any],
    frame_audit: dict[str, Any],
    coverage: dict[str, Any],
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
            24 <= int(frame_audit["rendered_cut_count"]) <= 30,
            frame_audit["rendered_cut_count"],
            "24-30",
        ),
        _check(
            "median-shot",
            1_500 <= float(frame_audit["median_shot_ms"]) <= 2_400,
            frame_audit["median_shot_ms"],
            "1500-2400 ms",
        ),
        _check(
            "motion",
            4.0 <= float(frame_audit["motion_score"]) <= 6.5,
            frame_audit["motion_score"],
            "4.0-6.5",
        ),
        _check(
            "darkness",
            float(frame_audit["dark_frame_ratio"]) <= 0.45,
            frame_audit["dark_frame_ratio"],
            "<= 0.45",
        ),
        _check(
            "luminance",
            65 <= float(frame_audit["mean_luminance"]) <= 105,
            frame_audit["mean_luminance"],
            "65-105",
        ),
        _check(
            "saturation",
            45 <= float(frame_audit["mean_saturation"]) <= 110,
            frame_audit["mean_saturation"],
            "45-110",
        ),
        _check(
            "real-direct-source-coverage",
            float(coverage["real_direct_source_ratio"]) >= 0.55,
            coverage["real_direct_source_ratio"],
            ">= 0.55",
        ),
        _check(
            "flow-coverage",
            0.08 <= float(coverage["flow_ratio"]) <= 0.14,
            coverage["flow_ratio"],
            "0.08-0.14",
        ),
        _check(
            "deterministic-graphic-coverage",
            float(coverage["deterministic_graphic_ratio"]) <= 0.25,
            coverage["deterministic_graphic_ratio"],
            "<= 0.25",
        ),
        _check(
            "direct-evidence-coverage",
            0.15 <= float(coverage["direct_evidence_ratio"]) <= 0.20,
            coverage["direct_evidence_ratio"],
            "0.15-0.20",
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
            ">= 99% content tokens; no protected terms missing",
        ),
    ]
    return {
        "automated_pass": all(check["passed"] for check in checks),
        "human_approved": False,
        "checks": checks,
    }


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


def _required_asset_image(
    output_dir: Path,
    assets: dict[str, AssetRef],
    asset_id: str,
) -> Image.Image:
    asset = assets.get(asset_id)
    if asset is None:
        raise KeyError(f"Missing required V2 source asset: {asset_id}")
    path = _asset_path(output_dir, asset)
    if not path.is_file():
        raise FileNotFoundError(path)
    return Image.open(path).convert("RGB")


def _optional_asset_image(
    output_dir: Path,
    asset: AssetRef | None,
) -> Image.Image | None:
    if asset is None:
        return None
    path = _asset_path(output_dir, asset)
    if not path.is_file():
        return None
    return Image.open(path).convert("RGBA")


def _asset_path(output_dir: Path, asset: AssetRef) -> Path:
    path = Path(asset.path)
    return path if path.is_absolute() else output_dir / path


def _order_lanes_graphic() -> Image.Image:
    image = _dark_canvas()
    draw = ImageDraw.Draw(image, "RGBA")
    draw.text(
        (72, 128),
        "AUTOMATED ORDER ROUTING",
        font=_v2_font(27, bold=True),
        fill="#9EACB8",
    )
    draw.text(
        (72, 195),
        "ONE SIGNAL.",
        font=_v2_font(76, bold=True),
        fill="#FFFFFF",
    )
    draw.text(
        (72, 286),
        "MILLIONS OF EXECUTIONS.",
        font=_v2_font(54, bold=True),
        fill="#F4EA58",
    )
    lane_top = 505
    lane_gap = 144
    for lane in range(7):
        y = lane_top + lane * lane_gap
        alpha = 235 - lane * 16
        draw.rounded_rectangle(
            (84, y, 996, y + 76),
            radius=38,
            fill=(20, 29, 37, alpha),
            outline=(78, 104, 120, 150),
            width=2,
        )
        draw.line(
            (145, y + 38, 900, y + 38),
            fill=(142, 218, 221, 215),
            width=5,
        )
        head_x = 246 + lane * 89
        draw.ellipse(
            (head_x - 17, y + 21, head_x + 17, y + 55),
            fill=(217, 255, 69, 255),
        )
        draw.polygon(
            (
                (902, y + 20),
                (950, y + 38),
                (902, y + 56),
            ),
            fill=(142, 218, 221, 235),
        )
    draw.rounded_rectangle(
        (78, 1578, 1002, 1842),
        radius=34,
        fill=(247, 245, 239, 248),
    )
    draw.text(
        (126, 1614),
        "VERIFIED SCALE",
        font=_v2_font(23, bold=True),
        fill="#68737B",
    )
    draw.text(
        (126, 1665),
        "4 MILLION+",
        font=_v2_font(64, bold=True),
        fill="#10161C",
    )
    draw.text(
        (126, 1760),
        "EXECUTIONS IN ABOUT 45 MINUTES",
        font=_v2_font(21, bold=True),
        fill="#39444C",
    )
    return image


def _evidence_highlight_graphic(
    source: Image.Image,
    *,
    eyebrow: str,
    headline: str,
    supporting: str,
    crop_box: tuple[int, int, int, int],
    highlight_bands: tuple[tuple[float, float], ...],
    accent: str,
) -> Image.Image:
    canvas = Image.new("RGB", (1080, 1920), "#F2F0EA")
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rounded_rectangle(
        (34, 38, 1046, 1882),
        radius=36,
        fill=(249, 248, 244, 255),
        outline=(189, 184, 174, 255),
        width=2,
    )
    draw.rounded_rectangle(
        (62, 70, 1018, 352),
        radius=28,
        fill=(16, 22, 28, 255),
    )
    draw.rectangle((62, 70, 76, 352), fill=accent)
    draw.text(
        (100, 112),
        eyebrow,
        font=_v2_font(23, bold=True),
        fill="#9EACB8",
    )
    draw.text(
        (100, 178),
        headline,
        font=_fit_font(
            headline,
            max_width=850,
            preferred_size=56,
            bold=True,
        ),
        fill="#FFFFFF",
    )
    draw.text(
        (100, 266),
        supporting,
        font=_fit_font(
            supporting,
            max_width=850,
            preferred_size=29,
            bold=True,
        ),
        fill=accent,
    )
    crop = source.crop(crop_box)
    crop = ImageOps.contain(crop, (912, 1185), Image.Resampling.LANCZOS)
    paper = Image.new(
        "RGB",
        (crop.width + 44, crop.height + 44),
        "#FFFFFF",
    )
    paper.paste(crop, (22, 22))
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow, "RGBA")
    left = (1080 - paper.width) // 2
    top = 436 + max(0, (1110 - paper.height) // 2)
    shadow_draw.rounded_rectangle(
        (left + 8, top + 18, left + paper.width + 8, top + paper.height + 18),
        radius=18,
        fill=(0, 0, 0, 68),
    )
    canvas = Image.alpha_composite(
        canvas.convert("RGBA"),
        shadow.filter(ImageFilter.GaussianBlur(16)),
    ).convert("RGB")
    canvas.paste(paper, (left, top))
    draw = ImageDraw.Draw(canvas, "RGBA")
    inner_top = top + 22
    inner_height = crop.height
    for start, end in highlight_bands:
        y0 = inner_top + round(inner_height * start)
        y1 = inner_top + round(inner_height * end)
        draw.rounded_rectangle(
            (left + 28, y0, left + paper.width - 28, y1),
            radius=8,
            fill=_hex_rgba(accent, 72),
            outline=_hex_rgba(accent, 190),
            width=3,
        )
    draw.rounded_rectangle(
        (112, 1690, 968, 1790),
        radius=26,
        fill=(16, 22, 28, 255),
    )
    draw.text(
        (540, 1740),
        "DIRECT SEC EVIDENCE  •  EDITED FOR LEGIBILITY",
        font=_v2_font(23, bold=True),
        fill="#FFFFFF",
        anchor="mm",
    )
    return canvas


def _eight_servers_v2_graphic() -> Image.Image:
    image = _dark_canvas()
    draw = ImageDraw.Draw(image, "RGBA")
    draw.text(
        (70, 130),
        "DEPLOYMENT PATH",
        font=_v2_font(25, bold=True),
        fill="#8EDADD",
    )
    draw.text(
        (70, 192),
        "SEVEN UPDATED.",
        font=_v2_font(68, bold=True),
        fill="#FFFFFF",
    )
    draw.text(
        (70, 276),
        "ONE STAYED OLD.",
        font=_v2_font(68, bold=True),
        fill="#FF625F",
    )
    center_x = 540
    y_positions = [490, 650, 810, 970, 1130, 1290, 1450, 1610]
    draw.line(
        (center_x, y_positions[0], center_x, y_positions[-1]),
        fill=(83, 118, 133, 170),
        width=8,
    )
    for index, y in enumerate(y_positions):
        missed = index == 7
        node_x = center_x + (130 if index % 2 else -130)
        draw.line(
            (center_x, y, node_x, y),
            fill=(255, 98, 95, 230)
            if missed
            else (142, 218, 221, 220),
            width=6,
        )
        draw.ellipse(
            (center_x - 13, y - 13, center_x + 13, y + 13),
            fill="#FF625F" if missed else "#8EDADD",
        )
        box = (
            node_x - 220,
            y - 58,
            node_x + 220,
            y + 58,
        )
        draw.rounded_rectangle(
            box,
            radius=24,
            fill=(49, 22, 26, 245)
            if missed
            else (19, 31, 40, 245),
            outline=(255, 98, 95, 255)
            if missed
            else (110, 168, 169, 230),
            width=4 if missed else 2,
        )
        draw.text(
            (node_x, y - 11),
            f"SERVER {index + 1}",
            font=_v2_font(25, bold=True),
            fill="#FFFFFF",
            anchor="mm",
        )
        draw.text(
            (node_x, y + 27),
            "OLD CODE ACTIVE" if missed else "NEW CODE",
            font=_v2_font(18, bold=True),
            fill="#FF625F" if missed else "#8EDADD",
            anchor="mm",
        )
    draw.text(
        (540, 1810),
        "ILLUSTRATIVE  •  BASED ON SEC ORDER 34-70694",
        font=_v2_font(20, bold=True),
        fill="#98A5AF",
        anchor="mm",
    )
    return image


def _incident_bridge_graphic() -> Image.Image:
    image = _dark_canvas()
    draw = ImageDraw.Draw(image, "RGBA")
    draw.text(
        (70, 130),
        "THE FOREX LESSON",
        font=_v2_font(25, bold=True),
        fill="#B8B5F2",
    )
    draw.text(
        (70, 194),
        "THE FAILURE WASN'T",
        font=_v2_font(63, bold=True),
        fill="#FFFFFF",
    )
    draw.text(
        (70, 276),
        "THE MARKET.",
        font=_v2_font(78, bold=True),
        fill="#F4EA58",
    )
    stages = [
        ("DEPLOY", "CHANGE RELEASED", "#8EDADD"),
        ("VERIFY", "ONE PATH MISSED", "#FF625F"),
        ("LIMIT", "NO FAST STOP", "#FF625F"),
        ("PROTECT", "CONTAIN DAMAGE", "#B8B5F2"),
    ]
    for index, (title, detail, color) in enumerate(stages):
        top = 520 + index * 280
        draw.rounded_rectangle(
            (82, top, 998, top + 196),
            radius=30,
            fill=(20, 29, 38, 245),
            outline=_hex_rgba(color, 210),
            width=3,
        )
        draw.rounded_rectangle(
            (110, top + 34, 246, top + 162),
            radius=24,
            fill=_hex_rgba(color, 38),
            outline=_hex_rgba(color, 220),
            width=2,
        )
        draw.text(
            (178, top + 98),
            f"{index + 1:02d}",
            font=_v2_font(42, bold=True),
            fill=color,
            anchor="mm",
        )
        draw.text(
            (292, top + 56),
            title,
            font=_v2_font(33, bold=True),
            fill=color,
        )
        draw.text(
            (292, top + 112),
            detail,
            font=_v2_font(29, bold=True),
            fill="#FFFFFF",
        )
        if index < len(stages) - 1:
            draw.line(
                (540, top + 196, 540, top + 280),
                fill=(105, 121, 133, 170),
                width=5,
            )
    draw.text(
        (540, 1776),
        "ILLUSTRATIVE CONTROL CHAIN",
        font=_v2_font(20, bold=True),
        fill="#98A5AF",
        anchor="mm",
    )
    return image


def _repeat_timeline_graphic() -> Image.Image:
    image = _dark_canvas()
    draw = ImageDraw.Draw(image, "RGBA")
    draw.text(
        (70, 128),
        "WITHOUT A VERIFIED STOP",
        font=_v2_font(25, bold=True),
        fill="#FF625F",
    )
    draw.text(
        (70, 198),
        "THE SAME ERROR",
        font=_v2_font(68, bold=True),
        fill="#FFFFFF",
    )
    draw.text(
        (70, 286),
        "KEPT REPEATING.",
        font=_v2_font(68, bold=True),
        fill="#FFFFFF",
    )
    start_x, end_x = 120, 960
    y = 920
    draw.line((start_x, y, end_x, y), fill=(96, 116, 130, 255), width=12)
    for index, x in enumerate((120, 330, 540, 750, 960)):
        draw.ellipse(
            (x - 27, y - 27, x + 27, y + 27),
            fill="#FF625F" if index == 4 else "#8EDADD",
        )
        draw.text(
            (x, y - 82),
            ("OPEN", "REPEAT", "REPEAT", "REPEAT", "STOP")[index],
            font=_v2_font(20, bold=True),
            fill="#FFFFFF",
            anchor="mm",
        )
    draw.text(
        (540, 1165),
        "≈ 45 MINUTES",
        font=_v2_font(104, bold=True),
        fill="#F4EA58",
        anchor="mm",
    )
    draw.rounded_rectangle(
        (118, 1328, 962, 1570),
        radius=34,
        fill=(22, 31, 40, 245),
        outline=(255, 98, 95, 205),
        width=3,
    )
    draw.text(
        (540, 1405),
        "AUTOMATION AMPLIFIES",
        font=_v2_font(34, bold=True),
        fill="#FF625F",
        anchor="mm",
    )
    draw.text(
        (540, 1484),
        "UNVERIFIED MISTAKES",
        font=_v2_font(48, bold=True),
        fill="#FFFFFF",
        anchor="mm",
    )
    draw.text(
        (540, 1776),
        "ILLUSTRATIVE  •  DURATION VERIFIED BY SEC ORDER",
        font=_v2_font(20, bold=True),
        fill="#98A5AF",
        anchor="mm",
    )
    return image


def _control_recap_graphic(brand: Image.Image | None) -> Image.Image:
    image = _dark_canvas().convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    if brand is not None:
        draw.rounded_rectangle(
            (258, 62, 822, 252),
            radius=34,
            fill=(247, 245, 239, 246),
            outline=(184, 181, 242, 160),
            width=2,
        )
        logo = brand.copy()
        logo.thumbnail((510, 145), Image.Resampling.LANCZOS)
        image.alpha_composite(
            logo,
            ((1080 - logo.width) // 2, 82),
        )
    else:
        draw.text(
            (540, 160),
            "PROFIT BRICKS",
            font=_v2_font(42, bold=True),
            fill="#B8B5F2",
            anchor="mm",
        )
    draw.text(
        (540, 330),
        "THE CONTROL STACK",
        font=_v2_font(58, bold=True),
        fill="#FFFFFF",
        anchor="mm",
    )
    controls = [
        ("01", "ORDER LIMITS", "CAP THE BLAST RADIUS", "#B8B5F2"),
        ("02", "CONTROLLED AUTOMATION", "VERIFY EACH RELEASE", "#8EDADD"),
        ("03", "EQUITY PROTECTION", "STOP REPEATED DAMAGE", "#FFFFFF"),
    ]
    for index, (number, title, detail, color) in enumerate(controls):
        top = 520 + index * 350
        draw.rounded_rectangle(
            (72, top, 1008, top + 270),
            radius=38,
            fill=(21, 30, 39, 250),
            outline=_hex_rgba(color, 180),
            width=3,
        )
        draw.text(
            (122, top + 65),
            number,
            font=_v2_font(30, bold=True),
            fill=color,
        )
        draw.text(
            (122, top + 126),
            title,
            font=_fit_font(
                title,
                max_width=830,
                preferred_size=46,
                bold=True,
            ),
            fill="#FFFFFF",
        )
        draw.text(
            (122, top + 200),
            detail,
            font=_fit_font(
                detail,
                max_width=830,
                preferred_size=27,
                bold=True,
            ),
            fill=color,
        )
    draw.text(
        (540, 1746),
        "DESIGNED CONTROL MODEL",
        font=_v2_font(20, bold=True),
        fill="#98A5AF",
        anchor="mm",
    )
    return image


def _minimal_overlay(
    *,
    eyebrow: str,
    headline: str,
    accent: str,
) -> Image.Image:
    image = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle(
        (76, 1260, 1004, 1572),
        radius=34,
        fill=(9, 14, 20, 222),
        outline=_hex_rgba(accent, 150),
        width=2,
    )
    draw.rectangle((76, 1260, 91, 1572), fill=accent)
    draw.text(
        (132, 1322),
        eyebrow,
        font=_fit_font(
            eyebrow,
            max_width=800,
            preferred_size=27,
            bold=True,
        ),
        fill=accent,
    )
    draw.text(
        (132, 1400),
        headline,
        font=_fit_font(
            headline,
            max_width=800,
            preferred_size=57,
            bold=True,
        ),
        fill="#FFFFFF",
    )
    draw.line(
        (132, 1508, 948, 1508),
        fill=_hex_rgba(accent, 170),
        width=3,
    )
    return image


def _control_overlay(
    *,
    number: str,
    title: str,
    detail: str,
    accent: str,
) -> Image.Image:
    image = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle(
        (70, 1145, 1010, 1650),
        radius=40,
        fill=(9, 14, 20, 228),
        outline=_hex_rgba(accent, 175),
        width=3,
    )
    draw.rounded_rectangle(
        (112, 1190, 248, 1326),
        radius=26,
        fill=_hex_rgba(accent, 34),
        outline=_hex_rgba(accent, 200),
        width=2,
    )
    draw.text(
        (180, 1258),
        number,
        font=_v2_font(43, bold=True),
        fill=accent,
        anchor="mm",
    )
    draw.text(
        (112, 1380),
        title,
        font=_fit_font(
            title,
            max_width=820,
            preferred_size=54,
            bold=True,
        ),
        fill="#FFFFFF",
    )
    draw.text(
        (112, 1470),
        detail,
        font=_fit_font(
            detail,
            max_width=820,
            preferred_size=29,
            bold=True,
        ),
        fill=accent,
    )
    draw.rounded_rectangle(
        (112, 1565, 948, 1581),
        radius=8,
        fill=_hex_rgba(accent, 210),
    )
    return image


def _cta_card_v2(brand: Image.Image | None) -> Image.Image:
    image = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle(
        (104, 1035, 976, 1765),
        radius=48,
        fill=(9, 14, 20, 232),
        outline=(184, 181, 242, 190),
        width=3,
    )
    if brand is not None:
        draw.rounded_rectangle(
            (230, 1080, 850, 1268),
            radius=34,
            fill=(247, 245, 239, 248),
            outline=(184, 181, 242, 170),
            width=2,
        )
        logo = brand.copy()
        logo.thumbnail((560, 135), Image.Resampling.LANCZOS)
        image.alpha_composite(
            logo,
            ((1080 - logo.width) // 2, 1106),
        )
    else:
        draw.text(
            (540, 1170),
            "PROFIT BRICKS",
            font=_v2_font(42, bold=True),
            fill="#B8B5F2",
            anchor="mm",
        )
    draw.text(
        (540, 1376),
        "FREE LIVE DEMO",
        font=_v2_font(68, bold=True),
        fill="#FFFFFF",
        anchor="mm",
    )
    draw.text(
        (540, 1460),
        "SEE THE SAFETY CONTROLS",
        font=_v2_font(27, bold=True),
        fill="#8EDADD",
        anchor="mm",
    )
    draw.rounded_rectangle(
        (210, 1540, 870, 1652),
        radius=34,
        fill="#FFFFFF",
    )
    draw.text(
        (540, 1596),
        "DETAILS IN DM",
        font=_v2_font(31, bold=True),
        fill="#10161C",
        anchor="mm",
    )
    return image


def _update_plate(*, progress: float) -> Image.Image:
    image = _flow_canvas()
    draw = ImageDraw.Draw(image, "RGBA")
    slot = (220, 610, 860, 1310)
    draw.rounded_rectangle(
        slot,
        radius=72,
        fill=(15, 24, 32, 255),
        outline=(91, 135, 149, 210),
        width=7,
    )
    for inset, alpha in ((50, 80), (105, 55), (160, 35)):
        draw.rounded_rectangle(
            (
                slot[0] + inset,
                slot[1] + inset,
                slot[2] - inset,
                slot[3] - inset,
            ),
            radius=max(18, 72 - inset // 3),
            outline=(142, 218, 221, alpha),
            width=4,
        )
    module_y = round(1450 - progress * 700)
    module = (340, module_y, 740, module_y + 280)
    draw.rounded_rectangle(
        module,
        radius=54,
        fill=(44, 58, 69, 255),
        outline=(142, 218, 221, 230),
        width=8,
    )
    draw.rounded_rectangle(
        (390, module_y + 52, 690, module_y + 228),
        radius=36,
        fill=(18, 30, 39, 255),
        outline=(240, 183, 95, 160),
        width=4,
    )
    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow, "RGBA")
    glow_draw.ellipse(
        (450, module_y + 80, 630, module_y + 260),
        fill=(142, 218, 221, round(70 + progress * 100)),
    )
    return Image.alpha_composite(
        image.convert("RGBA"),
        glow.filter(ImageFilter.GaussianBlur(34)),
    ).convert("RGB")


def _server_plate(*, progress: float) -> Image.Image:
    image = _flow_canvas()
    draw = ImageDraw.Draw(image, "RGBA")
    vanishing = (540, 820)
    for side in (-1, 1):
        for depth in range(7):
            t = depth / 7
            near_y = 1780 - depth * 155
            half_width = round(410 * (1 - t * 0.72))
            x_center = 540 + side * half_width
            width = round(245 * (1 - t * 0.56))
            height = round(310 * (1 - t * 0.5))
            box = (
                x_center - width // 2,
                near_y - height,
                x_center + width // 2,
                near_y,
            )
            draw.rounded_rectangle(
                box,
                radius=max(12, 28 - depth * 2),
                fill=(16, 25, 33, 255),
                outline=(70, 95, 110, 210),
                width=3,
            )
            for row in range(4):
                light_y = box[1] + 42 + row * max(28, height // 5)
                active = not (side == 1 and depth == 4)
                color = (
                    (142, 218, 221, 220)
                    if active
                    else (44, 54, 61, 170)
                )
                draw.ellipse(
                    (
                        box[0] + 26,
                        light_y,
                        box[0] + 39,
                        light_y + 13,
                    ),
                    fill=color,
                )
            draw.line(
                (box[0], box[3], vanishing[0], vanishing[1]),
                fill=(43, 61, 73, 80),
                width=2,
            )
    pulse_y = round(1680 - progress * 760)
    draw.line(
        (540, 1760, 540, 820),
        fill=(75, 108, 123, 150),
        width=9,
    )
    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow, "RGBA")
    glow_draw.ellipse(
        (458, pulse_y - 82, 622, pulse_y + 82),
        fill=(142, 218, 221, 190),
    )
    return Image.alpha_composite(
        image.convert("RGBA"),
        glow.filter(ImageFilter.GaussianBlur(42)),
    ).convert("RGB")


def _risk_plate(*, containment: float) -> Image.Image:
    image = _flow_canvas()
    draw = ImageDraw.Draw(image, "RGBA")
    center = (540, 1040)
    energy_radius = round(245 - containment * 105)
    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow, "RGBA")
    glow_draw.ellipse(
        (
            center[0] - energy_radius,
            center[1] - energy_radius,
            center[0] + energy_radius,
            center[1] + energy_radius,
        ),
        fill=(255, 70, 73, 185),
    )
    image = Image.alpha_composite(
        image.convert("RGBA"),
        glow.filter(ImageFilter.GaussianBlur(48)),
    )
    draw = ImageDraw.Draw(image, "RGBA")
    ring_radius = round(370 - containment * 78)
    for offset, width, alpha in ((0, 18, 230), (70, 8, 150), (138, 5, 85)):
        radius = ring_radius + offset
        draw.ellipse(
            (
                center[0] - radius,
                center[1] - radius,
                center[0] + radius,
                center[1] + radius,
            ),
            outline=(142, 218, 221, alpha),
            width=width,
        )
    for angle_index in range(8):
        angle = angle_index * 45
        marker = Image.new("RGBA", image.size, (0, 0, 0, 0))
        marker_draw = ImageDraw.Draw(marker, "RGBA")
        marker_draw.rounded_rectangle(
            (
                center[0] - 34,
                center[1] - ring_radius - 90,
                center[0] + 34,
                center[1] - ring_radius + 18,
            ),
            radius=18,
            fill=(47, 68, 78, 255),
            outline=(142, 218, 221, 200),
            width=3,
        )
        image = Image.alpha_composite(
            image,
            marker.rotate(angle, center=center),
        )
    return image.convert("RGB")


def _dark_canvas() -> Image.Image:
    base = Image.new("RGB", (1080, 1920), "#0A0F15")
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow, "RGBA")
    draw.ellipse((-260, -180, 780, 860), fill=(48, 88, 100, 74))
    draw.ellipse((390, 1030, 1370, 2100), fill=(83, 58, 110, 50))
    return Image.alpha_composite(
        base.convert("RGBA"),
        glow.filter(ImageFilter.GaussianBlur(110)),
    ).convert("RGB")


def _flow_canvas() -> Image.Image:
    base = Image.new("RGB", (1080, 1920), "#0C131A")
    gradient = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient, "RGBA")
    draw.ellipse((-180, 150, 800, 1220), fill=(36, 91, 100, 72))
    draw.ellipse((430, 770, 1280, 1880), fill=(60, 42, 67, 48))
    return Image.alpha_composite(
        base.convert("RGBA"),
        gradient.filter(ImageFilter.GaussianBlur(120)),
    ).convert("RGB")


def _v2_font(
    size: int,
    *,
    bold: bool = False,
    serif: bool = False,
) -> ImageFont.FreeTypeFont:
    if serif:
        candidates = [
            Path(r"C:\Windows\Fonts\georgiab.ttf")
            if bold
            else Path(r"C:\Windows\Fonts\georgia.ttf"),
        ]
    else:
        candidates = [
            Path(r"C:\Windows\Fonts\segoeuib.ttf")
            if bold
            else Path(r"C:\Windows\Fonts\segoeui.ttf"),
            Path(r"C:\Windows\Fonts\arialbd.ttf")
            if bold
            else Path(r"C:\Windows\Fonts\arial.ttf"),
        ]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    raise FileNotFoundError("A production system font is required")


def _fit_font(
    text: str,
    *,
    max_width: int,
    preferred_size: int,
    bold: bool,
) -> ImageFont.FreeTypeFont:
    size = preferred_size
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    while size > 20:
        font = _v2_font(size, bold=bold)
        box = measure.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= max_width:
            return font
        size -= 2
    return _v2_font(20, bold=bold)


def _hex_rgba(color: str, alpha: int) -> tuple[int, int, int, int]:
    value = color.lstrip("#")
    return (
        int(value[0:2], 16),
        int(value[2:4], 16),
        int(value[4:6], 16),
        alpha,
    )


def _v2_flow_instructions() -> dict[str, Any]:
    return {
        "card": [
            {
                "title": "0809 precision-system motion grammar",
                "text": (
                    "Create portrait 9:16, single-shot cinematic motion "
                    "plates with physically plausible movement, crisp "
                    "graphite materials, clean shape separation, controlled "
                    "cyan light and only restrained amber or risk-red accents. "
                    "Keep the primary subject center-safe and well exposed. "
                    "Never create text, letters, symbols, numbers, logos, "
                    "watermarks, software UI, code, charts, documents, "
                    "evidence, captions or internal edits."
                ),
                "ref": [],
                "enabled": True,
            }
        ]
    }


def _v2_evidence_ids(editorial_role: str) -> list[str]:
    return {
        "company-overview": ["sec-four-million", "sec-loss-460m"],
        "company-highlight": ["sec-four-million", "sec-loss-460m"],
        "missed-server": ["sec-one-of-eight"],
        "email-overview": ["sec-97-emails"],
        "email-highlight": ["sec-97-emails"],
        "deployment-overview": ["sec-one-of-eight"],
        "deployment-highlight": ["sec-one-of-eight"],
        "repeated-error": ["sec-one-of-eight"],
        "missing-controls": ["sec-missing-controls"],
    }.get(editorial_role, [])


def _v2_caption_family(editorial_role: str) -> str:
    if editorial_role in {
        "hook-date",
        "hook-orders",
        "loss",
        "risk-reset",
        "damage-limited",
        "cta-setup",
        "cta-card",
    }:
        return "display-emphasis"
    if "overview" in editorial_role or "highlight" in editorial_role:
        return "documentary-clean"
    return "technical-mono"


def _asset_manifest_payload(
    *,
    output_dir: Path,
    assets: list[AssetRef],
) -> dict[str, Any]:
    return {
        "assets": [
            {
                **asset.model_dump(mode="json"),
                "checksum_sha256": _checksum_if_present(
                    _asset_path(output_dir, asset)
                ),
            }
            for asset in assets
        ]
    }


def _checksum_if_present(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path, *, default: Any) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary, path)
