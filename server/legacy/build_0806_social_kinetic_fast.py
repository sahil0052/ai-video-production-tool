from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from PIL import Image, ImageDraw, ImageFilter


SERVER_DIR = Path(__file__).resolve().parent
WORKSPACE = SERVER_DIR.parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from app.models import (  # noqa: E402
    AssetRef,
    AudioPlan,
    EvidenceItem,
    GainAutomation,
    OutputSpec,
    SfxCue,
    SpeechProtectionWindow,
    VideoMetadata,
)
from app.production_models import (  # noqa: E402
    BlueprintLayerSpec,
    CropSpec,
    DialogueEditSegment,
    EffectKeyframe,
    KineticTextCue,
    LayerBounds,
    MotionEventSpec,
    OpacityKeyframe,
    ProductionBlueprint,
    ProductionJobRecord,
    ProductionStateEvent,
    TransformKeyframe,
)


SOURCE = Path(r"D:\Downloads\0806.mp4")
STYLE_REFERENCE = Path(r"D:\Downloads\Profit Bricks_Reel 04.mp4")
OUTPUT_DIR = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0806-production-v6-social-kinetic-fast"
)
V4_DIR = WORKSPACE / "storage" / "deliverables" / "0806-production-v4"
SOCIAL_SEED_DIR = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0811-production-v1-social-kinetic"
)
DURATION_MS = 41_400


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_deterministic_graphics() -> None:
    graphics_dir = OUTPUT_DIR / "assets" / "graphics"
    graphics_dir.mkdir(parents=True, exist_ok=True)

    backdrop_path = graphics_dir / "product-bright-backdrop.png"
    backdrop = Image.new("RGB", (1080, 1920), "#E7F0EC")
    pixels = backdrop.load()
    for y in range(1920):
        mix = y / 1919
        for x in range(1080):
            horizontal = x / 1079
            pixels[x, y] = (
                round(239 - 24 * mix + 8 * horizontal),
                round(246 - 22 * mix + 4 * horizontal),
                round(242 - 18 * mix + 11 * horizontal),
            )
    draw = ImageDraw.Draw(backdrop, "RGBA")
    for offset, alpha in ((0, 38), (110, 28), (220, 18)):
        draw.arc(
            (-280 + offset, 80 + offset, 1_360 + offset, 1_720 + offset),
            208,
            332,
            fill=(30, 142, 125, alpha),
            width=8,
        )
    for y in range(160, 1820, 120):
        draw.line((90, y, 990, y), fill=(34, 90, 79, 12), width=1)
    for x in range(120, 1020, 120):
        draw.line((x, 120, x, 1840), fill=(34, 90, 79, 10), width=1)
    backdrop.save(backdrop_path)

    panel_path = graphics_dir / "logo-panel.png"
    panel = Image.new("RGBA", (620, 560), (0, 0, 0, 0))
    shadow = Image.new("RGBA", panel.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        (36, 44, 584, 526),
        radius=64,
        fill=(0, 0, 0, 82),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(20))
    panel.alpha_composite(shadow)
    panel_draw = ImageDraw.Draw(panel)
    panel_draw.rounded_rectangle(
        (30, 26, 590, 510),
        radius=64,
        fill=(250, 249, 239, 248),
        outline=(194, 158, 66, 210),
        width=4,
    )
    panel_draw.rounded_rectangle(
        (48, 44, 572, 492),
        radius=52,
        outline=(42, 121, 91, 75),
        width=2,
    )
    panel.save(panel_path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_asset_index(path: Path) -> dict[str, AssetRef]:
    payload = load_json(path)
    return {
        item["id"]: AssetRef.model_validate(item)
        for item in payload["assets"]
    }


def remap_asset(asset: AssetRef, path: str) -> AssetRef:
    return AssetRef.model_validate(
        {
            **asset.model_dump(mode="json"),
            "path": path,
        }
    )


def transform(
    at_ms: int,
    *,
    x: float = 0,
    y: float = 0,
    scale: float = 1,
) -> TransformKeyframe:
    return TransformKeyframe(
        at_ms=at_ms,
        x=x,
        y=y,
        scale=scale,
        rotate_deg=0,
    )


def opacity(at_ms: int, value: float) -> OpacityKeyframe:
    return OpacityKeyframe(at_ms=at_ms, value=value)


def effect(
    at_ms: int,
    *,
    brightness: float,
    contrast: float,
    saturation: float,
    blur_px: float = 0,
) -> EffectKeyframe:
    return EffectKeyframe(
        at_ms=at_ms,
        brightness=brightness,
        contrast=contrast,
        saturation=saturation,
        blur_px=blur_px,
    )


def layer(
    *,
    id: str,
    shot_id: str,
    start_ms: int,
    end_ms: int,
    source_role: str,
    asset_id: str,
    kind: str = "video",
    source_start_ms: int | None = None,
    source_end_ms: int | None = None,
    bounds: tuple[int, int, int, int] = (0, 0, 1080, 1920),
    crop: tuple[float, float, float, float] = (0, 0, 1, 1),
    fit: str = "cover",
    transforms: list[TransformKeyframe] | None = None,
    opacities: list[OpacityKeyframe] | None = None,
    effects: list[EffectKeyframe] | None = None,
    z_index: int = 10,
    playback_rate: float = 1,
    illustrative_label: bool = False,
    border_radius: int = 0,
    reference_role: str = "primary-human",
) -> BlueprintLayerSpec:
    x, y, width, height = bounds
    crop_x, crop_y, crop_width, crop_height = crop
    return BlueprintLayerSpec(
        id=id,
        shot_id=shot_id,
        start_ms=start_ms,
        end_ms=end_ms,
        source_role=source_role,
        kind=kind,
        asset_id=asset_id,
        source_start_ms=source_start_ms,
        source_end_ms=source_end_ms,
        bounds=LayerBounds(x=x, y=y, width=width, height=height),
        crop=CropSpec(
            x=crop_x,
            y=crop_y,
            width=crop_width,
            height=crop_height,
        ),
        fit=fit,
        transform_keyframes=transforms or [transform(0)],
        opacity_keyframes=opacities or [opacity(0, 1)],
        effect_keyframes=effects
        or [
            effect(
                0,
                brightness=1,
                contrast=1,
                saturation=1,
            )
        ],
        z_index=z_index,
        muted=True,
        playback_rate=playback_rate,
        illustrative_label=illustrative_label,
        border_radius=border_radius,
        reference_role=reference_role,
    )


def presenter_layer(
    *,
    id: str,
    shot_id: str,
    start_ms: int,
    end_ms: int,
    scale_start: float,
    scale_end: float,
    brightness: float,
    saturation: float,
) -> BlueprintLayerSpec:
    return layer(
        id=id,
        shot_id=shot_id,
        start_ms=start_ms,
        end_ms=end_ms,
        source_role="presenter",
        asset_id="source-presenter",
        source_start_ms=start_ms,
        source_end_ms=end_ms,
        transforms=[
            transform(0, scale=scale_start),
            transform(end_ms - start_ms, scale=scale_end),
        ],
        effects=[
            effect(
                0,
                brightness=brightness,
                contrast=1.03,
                saturation=saturation,
            )
        ],
        z_index=1,
    )


def media_pip(
    *,
    id: str,
    shot_id: str,
    start_ms: int,
    end_ms: int,
    asset_id: str,
    source_start_ms: int,
    source_end_ms: int,
    opacities: list[OpacityKeyframe] | None = None,
    z_index: int = 24,
) -> BlueprintLayerSpec:
    duration = end_ms - start_ms
    return layer(
        id=id,
        shot_id=shot_id,
        start_ms=start_ms,
        end_ms=end_ms,
        source_role="real-product",
        asset_id=asset_id,
        source_start_ms=source_start_ms,
        source_end_ms=source_end_ms,
        bounds=(80, 1120, 920, 518),
        fit="cover",
        transforms=[
            transform(0, y=34, scale=0.92),
            transform(240, scale=1),
            transform(duration, y=-8, scale=1.035),
        ],
        opacities=opacities or [opacity(0, 0), opacity(150, 1)],
        effects=[
            effect(
                0,
                brightness=1.46,
                contrast=1.05,
                saturation=0.60,
            )
        ],
        z_index=z_index,
        border_radius=30,
    )


def evidence_card(
    *,
    id: str,
    shot_id: str,
    start_ms: int,
    end_ms: int,
    asset_id: str,
    opacities: list[OpacityKeyframe],
) -> BlueprintLayerSpec:
    duration = end_ms - start_ms
    return layer(
        id=id,
        shot_id=shot_id,
        start_ms=start_ms,
        end_ms=end_ms,
        source_role="direct-evidence",
        asset_id=asset_id,
        kind="image",
        bounds=(200, 880, 680, 1007),
        fit="contain",
        transforms=[
            transform(0, y=28, scale=0.94),
            transform(220, scale=1),
            transform(duration, y=-10, scale=1.035),
        ],
        opacities=opacities,
        effects=[
            effect(
                0,
                brightness=1.42,
                contrast=1.03,
                saturation=0.59,
            )
        ],
        z_index=24,
        border_radius=28,
        reference_role="secondary-10",
    )


def product_full_frame_layers(
    *,
    shot_id: str,
    start_ms: int,
    end_ms: int,
    asset_id: str,
    source_start_ms: int,
    source_end_ms: int,
    direction: float,
) -> list[BlueprintLayerSpec]:
    duration = end_ms - start_ms
    return [
        layer(
            id=f"layer-{shot_id}-backdrop",
            shot_id=shot_id,
            start_ms=start_ms,
            end_ms=end_ms,
            source_role="deterministic-graphic",
            asset_id="graphic-product-backdrop",
            kind="image",
            transforms=[
                transform(0, scale=1.02),
                transform(duration, x=direction * 16, scale=1.06),
            ],
            effects=[
                effect(
                    0,
                    brightness=1.34,
                    contrast=1.02,
                    saturation=0.59,
                )
            ],
            z_index=5,
        ),
        layer(
            id=f"layer-{shot_id}-screen",
            shot_id=shot_id,
            start_ms=start_ms,
            end_ms=end_ms,
            source_role="real-product",
            asset_id=asset_id,
            source_start_ms=source_start_ms,
            source_end_ms=source_end_ms,
            bounds=(40, 390, 1000, 563),
            fit="cover",
            transforms=[
                transform(0, y=24, scale=0.96),
                transform(220, scale=1),
                transform(duration, x=direction * 15, scale=1.055),
            ],
            effects=[
                effect(
                    0,
                    brightness=1.50,
                    contrast=1.06,
                    saturation=0.60,
                )
            ],
            z_index=20,
            border_radius=28,
        ),
    ]


def build_assets() -> list[AssetRef]:
    v4 = load_asset_index(V4_DIR / "blueprint.json")
    social = load_asset_index(SOCIAL_SEED_DIR / "blueprint.json")
    assets: list[AssetRef] = []
    for asset_id in (
        "source-presenter",
        "dialogue-original",
        "dialogue-processed",
        "capture-metaeditor-open",
        "capture-metaeditor-rule-highlight",
        "capture-mt5-navigator-ea",
        "capture-mt5-risk-inputs",
        "capture-mt5-attach-ea",
        "capture-mt5-strategy-tester",
        "evidence-history-overview",
        "evidence-history-excerpt",
        "evidence-risk-excerpt",
        "evidence-risk-number",
    ):
        assets.append(v4[asset_id])
    for asset_id in (
        "music-social-kinetic",
        "sfx-snap",
        "sfx-click",
        "sfx-impact",
        "sfx-whoosh",
        "sfx-riser",
        "sfx-pop",
        "brand-logo-original",
    ):
        assets.append(social[asset_id])
    assets.extend(
        [
            AssetRef(
                id="graphic-product-backdrop",
                kind="image",
                path="assets/graphics/product-bright-backdrop.png",
                keywords=["bright product backdrop", "social kinetic"],
                provenance="deterministic-original-graphic",
                license="Original production graphic",
            ),
            AssetRef(
                id="graphic-logo-panel",
                kind="image",
                path="assets/graphics/logo-panel.png",
                keywords=["Profit Bricks logo panel", "brand reveal"],
                provenance="deterministic-original-graphic",
                license="Original production graphic",
            ),
            AssetRef(
                id="flow-wrong-rule",
                kind="video",
                path="assets/flow/wrong-rule.mp4",
                keywords=["wrong rule", "decision branch", "illustrative"],
                provenance="google-flow-veo-illustrative-approved",
                license="User-owned generated asset",
                provider="Google Flow",
                creator="Cutline production",
            ),
            AssetRef(
                id="flow-physical-risk",
                kind="video",
                path="assets/flow/physical-risk.mp4",
                keywords=["physical risk", "illustrative"],
                provenance="google-flow-veo-illustrative-approved",
                license="User-owned generated asset",
                provider="Google Flow",
                creator="Cutline production",
            ),
            AssetRef(
                id="flow-reversal",
                kind="video",
                path="assets/flow/reversal.mp4",
                keywords=["risk reversal", "illustrative"],
                provenance="google-flow-veo-illustrative-approved",
                license="User-owned generated asset",
                provider="Google Flow",
                creator="Cutline production",
            ),
        ]
    )
    path_overrides = {
        "music-social-kinetic": "assets/audio/mixkit-minimal-techno-01-162.mp3",
        "sfx-snap": "assets/audio/sfx-snap-3124.mp3",
        "sfx-click": "assets/audio/sfx-click-1109.mp3",
        "sfx-impact": "assets/audio/sfx-impact-1143.mp3",
        "sfx-whoosh": "assets/audio/sfx-whoosh-1492.mp3",
        "sfx-riser": "assets/audio/sfx-riser-1144.mp3",
        "sfx-pop": "assets/audio/sfx-pop-2354.mp3",
        "brand-logo-original": "assets/brand/profit-bricks-logo.png",
    }
    return [
        remap_asset(asset, path_overrides.get(asset.id, asset.path))
        for asset in assets
    ]


def build_layers() -> list[BlueprintLayerSpec]:
    layers: list[BlueprintLayerSpec] = [
        presenter_layer(
            id="layer-hook-presenter",
            shot_id="shot-01",
            start_ms=0,
            end_ms=2_340,
            scale_start=1.04,
            scale_end=1.11,
            brightness=1.24,
            saturation=0.58,
        ),
        presenter_layer(
            id="layer-meta-presenter",
            shot_id="shot-02",
            start_ms=2_340,
            end_ms=6_820,
            scale_start=1.00,
            scale_end=1.05,
            brightness=1.24,
            saturation=0.58,
        ),
        media_pip(
            id="layer-meta-open-pip",
            shot_id="shot-02",
            start_ms=2_340,
            end_ms=4_600,
            asset_id="capture-metaeditor-open",
            source_start_ms=0,
            source_end_ms=2_260,
            opacities=[
                opacity(0, 0),
                opacity(150, 1),
                opacity(2_100, 1),
                opacity(2_260, 0),
            ],
        ),
        media_pip(
            id="layer-meta-rule-pip",
            shot_id="shot-02",
            start_ms=4_460,
            end_ms=6_820,
            asset_id="capture-metaeditor-rule-highlight",
            source_start_ms=0,
            source_end_ms=2_360,
        ),
        presenter_layer(
            id="layer-ea-presenter",
            shot_id="shot-03",
            start_ms=6_820,
            end_ms=9_300,
            scale_start=1.06,
            scale_end=1.11,
            brightness=1.25,
            saturation=0.58,
        ),
        media_pip(
            id="layer-ea-navigator-pip",
            shot_id="shot-03",
            start_ms=6_820,
            end_ms=9_300,
            asset_id="capture-mt5-navigator-ea",
            source_start_ms=0,
            source_end_ms=2_480,
        ),
        presenter_layer(
            id="layer-reset-presenter",
            shot_id="shot-04",
            start_ms=9_300,
            end_ms=11_780,
            scale_start=1.10,
            scale_end=1.16,
            brightness=1.27,
            saturation=0.58,
        ),
        layer(
            id="layer-wrong-rule-flow",
            shot_id="shot-05",
            start_ms=11_780,
            end_ms=14_250,
            source_role="flow-illustrative",
            asset_id="flow-wrong-rule",
            source_start_ms=0,
            source_end_ms=2_167,
            transforms=[
                transform(0, scale=1.02),
                transform(2_470, x=22, scale=1.10),
            ],
            effects=[
                effect(
                    0,
                    brightness=1.42,
                    contrast=1.05,
                    saturation=0.60,
                )
            ],
            z_index=10,
            playback_rate=2_167 / 2_470,
            illustrative_label=True,
        ),
        presenter_layer(
            id="layer-evidence-presenter",
            shot_id="shot-06",
            start_ms=14_250,
            end_ms=17_650,
            scale_start=1.02,
            scale_end=1.07,
            brightness=1.32,
            saturation=0.57,
        ),
        evidence_card(
            id="layer-evidence-overview",
            shot_id="shot-06",
            start_ms=14_250,
            end_ms=15_100,
            asset_id="evidence-history-overview",
            opacities=[
                opacity(0, 0),
                opacity(100, 1),
                opacity(700, 1),
                opacity(850, 0),
            ],
        ),
        evidence_card(
            id="layer-evidence-history",
            shot_id="shot-06",
            start_ms=14_950,
            end_ms=17_650,
            asset_id="evidence-history-excerpt",
            opacities=[opacity(0, 0), opacity(170, 1)],
        ),
        presenter_layer(
            id="layer-number-presenter",
            shot_id="shot-07",
            start_ms=17_650,
            end_ms=21_550,
            scale_start=1.08,
            scale_end=1.14,
            brightness=1.32,
            saturation=0.57,
        ),
        evidence_card(
            id="layer-number-excerpt",
            shot_id="shot-07",
            start_ms=17_650,
            end_ms=19_450,
            asset_id="evidence-risk-excerpt",
            opacities=[
                opacity(0, 0),
                opacity(150, 1),
                opacity(1_620, 1),
                opacity(1_800, 0),
            ],
        ),
        evidence_card(
            id="layer-number-proof",
            shot_id="shot-07",
            start_ms=19_250,
            end_ms=21_550,
            asset_id="evidence-risk-number",
            opacities=[opacity(0, 0), opacity(180, 1)],
        ),
        layer(
            id="layer-physical-risk-flow",
            shot_id="shot-08",
            start_ms=21_550,
            end_ms=23_700,
            source_role="flow-illustrative",
            asset_id="flow-physical-risk",
            source_start_ms=0,
            source_end_ms=1_767,
            transforms=[
                transform(0, scale=1.02),
                transform(2_150, x=-20, scale=1.10),
            ],
            effects=[
                effect(
                    0,
                    brightness=1.42,
                    contrast=1.05,
                    saturation=0.60,
                )
            ],
            z_index=10,
            playback_rate=1_767 / 2_150,
            illustrative_label=True,
        ),
    ]
    layers.extend(
        product_full_frame_layers(
            shot_id="risk-input",
            start_ms=23_700,
            end_ms=25_800,
            asset_id="capture-mt5-risk-inputs",
            source_start_ms=0,
            source_end_ms=2_100,
            direction=1,
        )
    )
    layers.extend(
        [
            layer(
                id="layer-reversal-flow",
                shot_id="shot-10",
                start_ms=25_800,
                end_ms=27_600,
                source_role="flow-illustrative",
                asset_id="flow-reversal",
                source_start_ms=0,
                source_end_ms=1_800,
                transforms=[
                    transform(0, scale=1.02),
                    transform(1_800, x=-18, scale=1.09),
                ],
                effects=[
                    effect(
                        0,
                        brightness=1.42,
                        contrast=1.05,
                        saturation=0.60,
                    )
                ],
                z_index=10,
                illustrative_label=True,
            ),
            presenter_layer(
                id="layer-lesson-presenter",
                shot_id="shot-11",
                start_ms=27_600,
                end_ms=30_500,
                scale_start=1.12,
                scale_end=1.18,
                brightness=1.28,
                saturation=0.58,
            ),
            presenter_layer(
                id="layer-safe-presenter",
                shot_id="shot-12",
                start_ms=30_500,
                end_ms=32_200,
                scale_start=1.00,
                scale_end=1.05,
                brightness=1.29,
                saturation=0.58,
            ),
            media_pip(
                id="layer-safe-risk-pip",
                shot_id="shot-12",
                start_ms=30_500,
                end_ms=32_200,
                asset_id="capture-mt5-risk-inputs",
                source_start_ms=2_200,
                source_end_ms=3_900,
            ),
            presenter_layer(
                id="layer-reset2-presenter",
                shot_id="shot-13",
                start_ms=32_200,
                end_ms=32_900,
                scale_start=1.10,
                scale_end=1.13,
                brightness=1.30,
                saturation=0.57,
            ),
        ]
    )
    layers.extend(
        product_full_frame_layers(
            shot_id="attach-ea",
            start_ms=32_900,
            end_ms=35_200,
            asset_id="capture-mt5-attach-ea",
            source_start_ms=0,
            source_end_ms=2_300,
            direction=1,
        )
    )
    layers.extend(
        product_full_frame_layers(
            shot_id="strategy-tester",
            start_ms=35_200,
            end_ms=37_000,
            asset_id="capture-mt5-strategy-tester",
            source_start_ms=1_500,
            source_end_ms=3_300,
            direction=-1,
        )
    )
    layers.extend(
        [
            presenter_layer(
                id="layer-cta-presenter",
                shot_id="shot-16",
                start_ms=37_000,
                end_ms=41_400,
                scale_start=1.16,
                scale_end=1.24,
                brightness=1.32,
                saturation=0.57,
            ),
            layer(
                id="layer-logo-panel",
                shot_id="shot-16",
                start_ms=37_800,
                end_ms=38_600,
                source_role="deterministic-graphic",
                asset_id="graphic-logo-panel",
                kind="image",
                bounds=(230, 890, 620, 560),
                fit="contain",
                transforms=[
                    transform(0, y=28, scale=0.88),
                    transform(220, scale=1),
                    transform(800, y=-3, scale=1.02),
                ],
                opacities=[
                    opacity(0, 0),
                    opacity(100, 0.92),
                    opacity(620, 0.92),
                    opacity(800, 0),
                ],
                effects=[
                    effect(
                        0,
                        brightness=1.34,
                        contrast=1.01,
                        saturation=0.59,
                    )
                ],
                z_index=24,
            ),
            layer(
                id="layer-brand-logo",
                shot_id="shot-16",
                start_ms=37_800,
                end_ms=38_600,
                source_role="deterministic-graphic",
                asset_id="brand-logo-original",
                kind="image",
                bounds=(310, 960, 460, 386),
                fit="contain",
                transforms=[
                    transform(0, y=30, scale=0.86),
                    transform(220, scale=1),
                    transform(800, y=-4, scale=1.03),
                ],
                opacities=[
                    opacity(0, 0),
                    opacity(120, 1),
                    opacity(600, 1),
                    opacity(800, 0),
                ],
                effects=[
                    effect(
                        0,
                        brightness=1.32,
                        contrast=1.02,
                        saturation=0.55,
                    )
                ],
                z_index=25,
            ),
        ]
    )
    return layers


def build_text_cues() -> list[KineticTextCue]:
    specifications = [
        (
            "text-forex-robot",
            420,
            1_720,
            "FOREX ROBOT?",
            "hero-condensed",
            1_350,
            "slam",
            None,
        ),
        (
            "text-auto-trades",
            2_340,
            3_340,
            "AUTO TRADES",
            "hero-condensed",
            1_500,
            "slam",
            None,
        ),
        (
            "text-expert-advisor",
            6_820,
            7_970,
            "EXPERT\nADVISOR",
            "outlined-stack",
            1_450,
            "stack",
            None,
        ),
        (
            "text-wrong-rules",
            11_780,
            13_030,
            "WRONG RULES?\nBAD OUTPUT",
            "outlined-stack",
            1_470,
            "stack",
            None,
        ),
        (
            "text-2008",
            14_250,
            15_250,
            "2008",
            "gradient-number",
            1_420,
            "glow",
            "#FFF45A",
        ),
        (
            "text-110k",
            19_320,
            20_620,
            "$110,000",
            "gradient-number",
            1_420,
            "glow",
            "#B8FF52",
        ),
        (
            "text-high-risk",
            23_700,
            24_700,
            "HIGH RISK",
            "correction-symbol",
            1_420,
            "draw",
            None,
        ),
        (
            "text-no-emotions",
            29_200,
            30_300,
            "NO EMOTIONS",
            "hero-condensed",
            1_460,
            "slam",
            None,
        ),
        (
            "text-safe-risk",
            31_200,
            32_100,
            "SAFE RISK?",
            "correction-symbol",
            1_500,
            "draw",
            None,
        ),
        (
            "text-follow-telegram",
            38_740,
            40_540,
            "FOLLOW\nTELEGRAM",
            "cta-quote",
            1_500,
            "quote-pop",
            None,
        ),
    ]
    cues: list[KineticTextCue] = []
    for (
        cue_id,
        start_ms,
        end_ms,
        text,
        family,
        y,
        animation,
        accent,
    ) in specifications:
        secondary_text = None
        if cue_id == "text-high-risk":
            secondary_text = "RESULT ↑"
        elif cue_id == "text-safe-risk":
            secondary_text = "✕"
        cues.append(
            KineticTextCue(
                id=cue_id,
                start_ms=start_ms,
                end_ms=end_ms,
                text=text,
                family=family,
                x=540,
                y=y,
                max_width=960,
                align="center",
                animation=animation,
                accent=accent,
                secondary_text=secondary_text,
                z_index=60,
            )
        )
    return cues


def build_motion_events(
    text_cues: list[KineticTextCue],
) -> list[MotionEventSpec]:
    events = [
        MotionEventSpec(
            id=f"motion-{cue.id}",
            start_ms=cue.start_ms,
            end_ms=min(cue.end_ms, cue.start_ms + 420),
            kind="text-reveal",
            target_id=cue.id,
            intensity=0.68,
        )
        for cue in text_cues
    ]
    extra = [
        ("hook-punch", 0, 420, "punch-crop", "layer-hook-presenter", 0.58),
        ("meta-pip", 2_340, 2_700, "pip-pop", "layer-meta-open-pip", 0.72),
        ("meta-rule", 4_460, 4_820, "pip-pop", "layer-meta-rule-pip", 0.65),
        ("ea-pip", 6_820, 7_180, "pip-pop", "layer-ea-navigator-pip", 0.70),
        ("reset-punch", 9_300, 9_700, "punch-crop", "layer-reset-presenter", 0.48),
        ("wrong-rule", 11_780, 12_180, "punch-crop", "layer-wrong-rule-flow", 0.56),
        ("evidence-overview", 14_250, 14_600, "pip-pop", "layer-evidence-overview", 0.62),
        ("evidence-highlight", 15_100, 16_000, "highlight-sweep", "layer-evidence-history", 0.74),
        ("number-excerpt", 17_650, 18_000, "pip-pop", "layer-number-excerpt", 0.62),
        ("number-proof", 19_250, 19_750, "proof-punch", "layer-number-proof", 0.78),
        ("physical-risk", 21_550, 21_950, "punch-crop", "layer-physical-risk-flow", 0.56),
        ("risk-input", 23_700, 24_100, "proof-punch", "layer-risk-input-screen", 0.68),
        ("reversal", 25_800, 26_200, "directional-jump", "layer-reversal-flow", 0.58),
        ("lesson", 27_600, 28_000, "punch-crop", "layer-lesson-presenter", 0.50),
        ("safe-pip", 30_500, 30_850, "pip-pop", "layer-safe-risk-pip", 0.65),
        ("reset-two", 32_200, 32_550, "punch-crop", "layer-reset2-presenter", 0.42),
        ("attach-ea", 32_900, 33_300, "proof-punch", "layer-attach-ea-screen", 0.67),
        ("strategy", 35_200, 35_600, "proof-punch", "layer-strategy-tester-screen", 0.66),
        ("cta-punch", 37_000, 37_400, "punch-crop", "layer-cta-presenter", 0.50),
        ("logo-build", 37_800, 38_200, "logo-build", "layer-brand-logo", 0.66),
    ]
    events.extend(
        MotionEventSpec(
            id=f"motion-{event_id}",
            start_ms=start_ms,
            end_ms=end_ms,
            kind=kind,
            target_id=target_id,
            intensity=intensity,
            direction="left" if kind == "directional-jump" else "none",
        )
        for (
            event_id,
            start_ms,
            end_ms,
            kind,
            target_id,
            intensity,
        ) in extra
    )
    return events


def build_audio_plan(transcript: list[dict[str, Any]]) -> AudioPlan:
    windows = [
        SpeechProtectionWindow(
            start_ms=max(0, round(float(word["start"]) * 1000) - 100),
            end_ms=min(
                DURATION_MS,
                round(float(word["start"]) * 1000) + 120,
            ),
            word=str(word["text"]),
        )
        for segment in transcript
        for word in segment.get("words", [])
        if round(float(word["start"]) * 1000) < DURATION_MS
    ]

    candidates = [
        ("sfx-hook", "sfx-snap", 420, 0, 60, -17.0, "click", "hook typography"),
        ("sfx-auto", "sfx-impact", 2_340, 260, 90, -15.0, "impact", "automation section"),
        ("sfx-ea", "sfx-whoosh", 6_820, 580, 90, -17.0, "whoosh", "EA identification"),
        ("sfx-ea-settle", "sfx-snap", 7_230, 0, 60, -17.0, "click", "EA title settle"),
        ("sfx-reset", "sfx-click", 9_300, 0, 70, -18.0, "click", "presenter reset"),
        ("sfx-wrong", "sfx-whoosh", 11_780, 580, 90, -16.0, "whoosh", "wrong-rule section"),
        ("sfx-2008", "sfx-impact", 14_160, 260, 90, -15.0, "impact", "2008 evidence reveal"),
        ("sfx-proof-cut", "sfx-impact", 17_650, 260, 70, -14.0, "impact", "primary proof section"),
        ("sfx-number", "sfx-impact", 19_320, 260, 100, -14.0, "impact", "$110,000 reveal"),
        ("sfx-risk", "sfx-impact", 21_550, 300, 70, -17.0, "impact", "risk section"),
        ("sfx-high-risk", "sfx-impact", 23_700, 260, 70, -14.0, "impact", "risk input"),
        ("sfx-reversal", "sfx-impact", 25_800, 260, 70, -14.0, "impact", "result reversal"),
        ("sfx-no-emotions", "sfx-snap", 29_200, 0, 70, -17.0, "click", "lesson reveal"),
        ("sfx-safe-cut", "sfx-click", 30_500, 0, 70, -18.0, "click", "risk correction setup"),
        ("sfx-safe-risk", "sfx-snap", 31_200, 0, 70, -17.0, "click", "safe-risk correction"),
        ("sfx-reset-two", "sfx-impact", 32_200, 300, 70, -18.0, "impact", "CTA setup"),
        ("sfx-attach", "sfx-impact", 32_900, 260, 70, -12.0, "impact", "EA attachment"),
        ("sfx-strategy", "sfx-whoosh", 35_200, 580, 70, -18.0, "whoosh", "Strategy Tester"),
        ("sfx-cta", "sfx-pop", 38_740, 0, 30, -16.0, "notification", "CTA reveal"),
    ]

    def safe_start(desired_ms: int, duration_ms: int) -> int:
        offsets = [0]
        for delta in range(10, 801, 10):
            offsets.extend((-delta, delta))
        for offset in offsets:
            candidate = max(
                0,
                min(DURATION_MS - duration_ms, desired_ms + offset),
            )
            if not any(
                candidate < window.end_ms
                and candidate + duration_ms > window.start_ms
                for window in windows
            ):
                return candidate
        raise ValueError(f"No speech-safe SFX window near {desired_ms}")

    cues = [
        SfxCue(
            id=cue_id,
            asset_id=asset_id,
            start_ms=safe_start(desired_ms, duration_ms),
            source_start_ms=source_start_ms,
            duration_ms=duration_ms,
            volume=0.35,
            gain_db=gain_db,
            kind=kind,
            reason=reason,
        )
        for (
            cue_id,
            asset_id,
            desired_ms,
            source_start_ms,
            duration_ms,
            gain_db,
            kind,
            reason,
        ) in candidates
    ]
    automation = [
        GainAutomation(
            start_ms=max(0, round(float(segment["start"]) * 1000) - 200),
            end_ms=min(
                DURATION_MS,
                round(float(segment["end"]) * 1000) + 120,
            ),
            gain_db=-10,
            reason="Duck music beneath narration",
        )
        for segment in transcript
    ]
    return AudioPlan(
        integrated_lufs=-13.5,
        true_peak_dbtp=-1.4,
        target_lra_lu=2.4,
        music_bpm=126,
        dialogue_asset_id="dialogue-original",
        dialogue_offset_ms=0,
        music_asset_id="music-social-kinetic",
        music_duck_db=10,
        music_base_gain_db=-27,
        music_gain_automation=automation,
        speech_protection_windows=windows,
        sfx_asset_ids=sorted({cue.asset_id for cue in cues}),
        sfx_cues=cues,
    )


def build_storyboard(layers: list[BlueprintLayerSpec]) -> list[dict[str, Any]]:
    shots = [
        ("shot-01", 0, 2_340, "hook", "Do you know what Forex Trading Robot is?"),
        ("shot-02", 2_340, 6_820, "automation explanation", "It is a software that automatically trades on set rules."),
        ("shot-03", 6_820, 9_300, "EA identification", "Professionally, it is called Expert Advisor."),
        ("shot-04", 9_300, 11_780, "presenter reset", "In short, EA."),
        ("shot-05", 11_780, 14_250, "wrong-rule contrast", "But if the rules are wrong,"),
        ("shot-06", 14_250, 17_650, "official 2008 evidence", "In 2008, in the Automated Trading Championship,"),
        ("shot-07", 17_650, 21_550, "verified result", "an Expert Advisor earned $110,000."),
        ("shot-08", 21_550, 23_700, "physical risk metaphor", "Then the risk turned the game."),
        ("shot-09", 23_700, 25_800, "real risk inputs", "The high risk increased the result,"),
        ("shot-10", 25_800, 27_600, "reversal", "and then it turned upside down."),
        ("shot-11", 27_600, 30_500, "lesson", "An Expert Advisor does not trade with emotions."),
        ("shot-12", 30_500, 32_200, "risk correction", "But it does not choose a safe risk."),
        ("shot-13", 32_200, 32_900, "clean reset", "CTA setup."),
        ("shot-14", 32_900, 35_200, "EA attachment", "See how an Expert Advisor trades."),
        ("shot-15", 35_200, 37_000, "Strategy Tester", "Real product demonstration."),
        ("shot-16", 37_000, 41_400, "CTA", "Follow us and join our Telegram group. Thank you."),
    ]
    return [
        {
            "id": shot_id,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "editorial_role": role,
            "spoken_beat": spoken_beat,
            "layer_ids": [
                item.id for item in layers if item.shot_id == shot_id
            ],
            "reference_role": "primary-human",
        }
        for shot_id, start_ms, end_ms, role, spoken_beat in shots
    ]


def main() -> int:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    if not STYLE_REFERENCE.is_file():
        raise FileNotFoundError(STYLE_REFERENCE)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    prepare_deterministic_graphics()

    transcript = load_json(OUTPUT_DIR / "transcript-aligned.json")
    evidence = [
        EvidenceItem.model_validate(item)
        for item in load_json(OUTPUT_DIR / "evidence.json")
    ]
    assets = build_assets()
    layers = build_layers()
    text_cues = build_text_cues()
    motion_events = build_motion_events(text_cues)
    audio = build_audio_plan(transcript)
    metadata = VideoMetadata(
        width=1080,
        height=1920,
        fps=30,
        frame_count=1242,
        duration_seconds=41.4,
    )
    blueprint = ProductionBlueprint(
        source_filename=SOURCE.name,
        source_metadata=metadata,
        output=OutputSpec(width=1080, height=1920, fps=30),
        duration_ms=DURATION_MS,
        assets=assets,
        layers=layers,
        caption_pages=[],
        audio=audio,
        flow_shots=[],
        evidence=evidence,
        reference_profile="social-kinetic",
        story_profile="automation-future",
        style_reference_path=str(STYLE_REFERENCE),
        voice_policy="preserve-verbatim",
        dialogue_edl=[
            DialogueEditSegment(
                id="dialogue-verbatim",
                source_start_ms=0,
                source_end_ms=DURATION_MS,
                output_start_ms=0,
                output_end_ms=DURATION_MS,
                playback_rate=1,
                preserve_pitch=True,
            )
        ],
        kinetic_text_cues=text_cues,
        motion_events=motion_events,
    )
    artifacts = {
        "blueprint": "blueprint.json",
        "storyboard": "storyboard.json",
        "evidence": "evidence.json",
        "reference_profile": "reference-profile.json",
        "dialogue_edl": "dialogue-edl.json",
        "kinetic_text_plan": "kinetic-text-plan.json",
        "motion_events": "motion-events.json",
        "sound_cue_sheet": "sound-cue-sheet.json",
        "flow_shot_plan": "flow-shot-plan.json",
        "flow_instructions": "flow-instructions.json",
        "asset_manifest": "asset-manifest.json",
        "capture_manifest": "capture-manifest.json",
        "caption_plan": "caption-plan.json",
        "production_settings": "production-settings.json",
        "transcript_aligned": "transcript-aligned.json",
    }
    write_json(
        OUTPUT_DIR / "blueprint.json",
        blueprint.model_dump(mode="json"),
    )
    write_json(
        OUTPUT_DIR / "storyboard.json",
        build_storyboard(layers),
    )
    write_json(
        OUTPUT_DIR / "reference-profile.json",
        {
            "name": "social-kinetic",
            "story_profile": "0806-ea-risk-case",
            "primary_reference": {
                "path": str(STYLE_REFERENCE),
                "checksum_sha256": sha256(STYLE_REFERENCE),
                "role": "typography, pacing, color, motion and sound grammar",
            },
            "secondary_reference": {
                "training_reference": 10,
                "role": "factual evidence restraint only",
            },
            "targets": {
                "duration_seconds": [41.35, 41.45],
                "hard_cuts": [13, 16],
                "median_shot_seconds": [2.3, 3.0],
                "presenter_ratio": [0.58, 0.68],
                "flow_ratio_max": 0.18,
                "dark_frame_ratio_max": 0.06,
                "mean_luminance": [95, 108],
                "mean_saturation": [65, 85],
            },
        },
    )
    write_json(
        OUTPUT_DIR / "dialogue-edl.json",
        [item.model_dump(mode="json") for item in blueprint.dialogue_edl],
    )
    write_json(
        OUTPUT_DIR / "kinetic-text-plan.json",
        [item.model_dump(mode="json") for item in text_cues],
    )
    write_json(
        OUTPUT_DIR / "motion-events.json",
        [item.model_dump(mode="json") for item in motion_events],
    )
    write_json(
        OUTPUT_DIR / "sound-cue-sheet.json",
        audio.model_dump(mode="json"),
    )
    write_json(
        OUTPUT_DIR / "caption-plan.json",
        {
            "profile": "social-kinetic",
            "pages": [],
            "reason": "Sparse semantic typography replaces continuous subtitles.",
        },
    )
    write_json(OUTPUT_DIR / "flow-shot-plan.json", [])
    write_json(
        OUTPUT_DIR / "flow-instructions.json",
        {
            "reuse_policy": (
                "Three previously approved 0806 Flow clips are reused with "
                "their accepted silent proxies and remain illustrative."
            ),
            "card": [
                {
                    "text": (
                        "No readable text, UI, code, charts, numbers, "
                        "currencies, documents, captions, logos or watermarks."
                    )
                }
            ],
        },
    )
    manifest_assets = []
    for asset in assets:
        local_path = OUTPUT_DIR / asset.path
        if not local_path.is_file():
            raise FileNotFoundError(local_path)
        manifest_assets.append(
            {
                **asset.model_dump(mode="json"),
                "checksum_sha256": sha256(local_path),
            }
        )
    write_json(
        OUTPUT_DIR / "asset-manifest.json",
        {
            "policy": "evidence-first free-licensed",
            "assets": manifest_assets,
        },
    )
    write_json(
        OUTPUT_DIR / "production-settings.json",
        {
            "style_reference": str(STYLE_REFERENCE),
            "reference_profile": "social-kinetic",
            "story_profile": "0806-ea-risk-case",
            "voice_policy": "preserve-verbatim",
            "flow_operation_budget": 8,
            "new_paid_operations": 0,
            "final_video_filter": "eq=brightness=0.022:saturation=1.04",
            "human_final_approval_required": True,
        },
    )

    now = datetime.now(UTC)
    job = ProductionJobRecord(
        id="production-0806-v6-fast",
        source_path=str(SOURCE),
        output_dir=str(OUTPUT_DIR),
        state="blueprint-ready",
        primary_reference=10,
        secondary_reference=4,
        flow_operation_budget=8,
        approved_paid_operations=0,
        consumed_paid_operations=0,
        flow_profile="sahilsharmabybit2",
        flow_project_id="0806-approved-flow-library",
        flow_repository=str(
            Path(r"C:\Users\HPUSER\Documents\ChatGPT\New project")
        ),
        artifacts=artifacts,
        accepted_clips=[],
        automated_pass=False,
        human_approved=False,
        state_history=[
            ProductionStateEvent(
                state="analyzing",
                at=now,
                detail="Existing complete-frame source analysis reused.",
            ),
            ProductionStateEvent(
                state="blueprint-ready",
                at=now,
                detail=(
                    "Bespoke 16-shot social-kinetic blueprint persisted "
                    "with approved 0806 assets."
                ),
            ),
        ],
        created_at=now,
        updated_at=now,
    )
    write_json(
        OUTPUT_DIR / "production-job.json",
        job.model_dump(mode="json"),
    )
    print(
        json.dumps(
            {
                "output_dir": str(OUTPUT_DIR),
                "asset_count": len(assets),
                "layer_count": len(layers),
                "kinetic_text_count": len(text_cues),
                "motion_event_count": len(motion_events),
                "sfx_count": len(audio.sfx_cues),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
