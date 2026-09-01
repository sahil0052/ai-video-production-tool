from __future__ import annotations

from typing import Any
import re

from app.models import (
    AssetRef,
    AudioPlan,
    CaptionPage,
    CaptionToken,
    GainAutomation,
    EvidenceItem,
    OutputSpec,
    SfxCue,
    SpeechProtectionWindow,
    VideoMetadata,
)
from app.production_models import (
    BlueprintLayerSpec,
    CropSpec,
    EffectKeyframe,
    LayerBounds,
    DialogueEditSegment,
    MotionEventSpec,
    OpacityKeyframe,
    ProductionBlueprint,
    TransformKeyframe,
)


DURATION_MS = 41_400


def build_shot_schedule() -> list[dict[str, Any]]:
    specifications = [
        (0, 2_340, "hook", "hook-composite", "real-product"),
        (2_340, 4_700, "explanation", "metaeditor-open", "real-product"),
        (4_700, 6_820, "explanation", "rule-code-macro", "real-product"),
        (6_820, 9_420, "demonstration", "navigator-ea", "real-product"),
        (9_420, 12_060, "explanation", "presenter-reset", "presenter"),
        (12_060, 14_160, "contrast", "wrong-rule-branch", "deterministic-graphic"),
        (14_160, 15_200, "evidence", "evidence-overview", "direct-evidence"),
        (15_200, 17_460, "evidence", "championship-excerpt", "direct-evidence"),
        (17_460, 19_500, "evidence", "result-excerpt", "direct-evidence"),
        (19_500, 21_820, "evidence", "result-number", "direct-evidence"),
        (21_820, 24_200, "demonstration", "risk-input", "real-product"),
        (24_200, 25_800, "demonstration", "risk-parameter", "real-product"),
        (25_800, 27_780, "contrast", "risk-reversal", "deterministic-graphic"),
        (27_780, 30_200, "payoff", "presenter-lesson", "presenter"),
        (30_200, 32_200, "explanation", "rules-versus-risk", "deterministic-graphic"),
        (32_200, 33_020, "explanation", "tactile-bridge", "licensed-context"),
        (33_020, 35_200, "demonstration", "attach-ea", "real-product"),
        (35_200, 37_160, "demonstration", "strategy-tester", "real-product"),
        (37_160, 39_800, "cta", "presenter-cta", "presenter"),
        (39_800, 41_400, "cta", "product-presenter-ending", "real-product"),
    ]
    return [
        {
            "id": f"shot-{index:02d}",
            "start_ms": start_ms,
            "end_ms": end_ms,
            "editorial_role": editorial_role,
            "treatment": treatment,
            "source_role": source_role,
            "reference_role": (
                "secondary-4"
                if treatment == "risk-reversal"
                else "primary-10"
            ),
        }
        for index, (
            start_ms,
            end_ms,
            editorial_role,
            treatment,
            source_role,
        ) in enumerate(specifications, start=1)
    ]


def _layer(
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
    z_index: int = 10,
    border_radius: int = 0,
    illustrative_label: bool = False,
    reference_role: str = "primary-10",
    x_start: float = 0,
    y_start: float = 0,
    x_end: float = 0,
    y_end: float = 0,
    scale_start: float = 1,
    scale_end: float = 1.025,
    opacity_start: float = 1,
    opacity_end: float = 1,
    brightness: float = 1,
    contrast: float = 1,
    saturation: float = 1,
    blur_px: float = 0,
    color_filter: str | None = None,
) -> BlueprintLayerSpec:
    duration = end_ms - start_ms
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
        transform_keyframes=[
            TransformKeyframe(
                at_ms=0,
                x=x_start,
                y=y_start,
                scale=scale_start,
            ),
            TransformKeyframe(
                at_ms=duration,
                x=x_end,
                y=y_end,
                scale=scale_end,
            ),
        ],
        opacity_keyframes=(
            [
                OpacityKeyframe(at_ms=0, value=opacity_start),
                OpacityKeyframe(at_ms=duration, value=opacity_end),
            ]
            if opacity_start != opacity_end
            else [OpacityKeyframe(at_ms=0, value=opacity_start)]
        ),
        effect_keyframes=[
            EffectKeyframe(
                at_ms=0,
                brightness=brightness,
                contrast=contrast,
                saturation=saturation,
                blur_px=blur_px,
            )
        ],
        z_index=z_index,
        muted=True,
        playback_rate=1,
        illustrative_label=illustrative_label,
        border_radius=border_radius,
        color_filter=color_filter,
        reference_role=reference_role,
    )


def build_layers() -> list[BlueprintLayerSpec]:
    layers = [
        _layer(
            id="layer-hook-product",
            shot_id="shot-01",
            start_ms=0,
            end_ms=2_340,
            source_role="real-product",
            asset_id="capture-mt5-hook-action",
            source_start_ms=0,
            source_end_ms=2_340,
            bounds=(0, 0, 1080, 1100),
            crop=(0.0, 0.0, 0.58, 1.0),
            x_start=-12,
            y_start=8,
            x_end=12,
            y_end=-8,
            scale_start=1.02,
            scale_end=1.08,
            contrast=1.08,
            saturation=1.08,
        ),
        _layer(
            id="layer-hook-presenter",
            shot_id="shot-01",
            start_ms=0,
            end_ms=2_340,
            source_role="presenter",
            asset_id="source-presenter",
            source_start_ms=0,
            source_end_ms=2_340,
            bounds=(0, 1100, 1080, 820),
            y_start=8,
            y_end=-8,
            scale_start=1.01,
            scale_end=1.06,
            brightness=1.04,
            saturation=1.02,
        ),
        _layer(
            id="layer-hook-title",
            shot_id="shot-01",
            start_ms=240,
            end_ms=2_080,
            source_role="deterministic-graphic",
            asset_id="graphic-hook-title",
            kind="image",
            bounds=(90, 280, 900, 330),
            fit="contain",
            z_index=40,
            scale_end=1.012,
        ),
        _layer(
            id="layer-metaeditor-open",
            shot_id="shot-02",
            start_ms=2_340,
            end_ms=4_700,
            source_role="real-product",
            asset_id="capture-metaeditor-open",
            source_start_ms=0,
            source_end_ms=2_360,
            crop=(0.12, 0.0, 0.62, 1.0),
            x_start=-24,
            y_start=18,
            x_end=24,
            y_end=-18,
            scale_start=1.02,
            scale_end=1.09,
            brightness=1.08,
            contrast=1.08,
            saturation=1.08,
        ),
        _layer(
            id="layer-code-backdrop",
            shot_id="shot-03",
            start_ms=4_700,
            end_ms=6_820,
            source_role="deterministic-graphic",
            asset_id="graphic-light-backdrop",
            kind="image",
            z_index=1,
            scale_end=1,
        ),
        _layer(
            id="layer-code-macro",
            shot_id="shot-03",
            start_ms=4_700,
            end_ms=6_820,
            source_role="real-product",
            asset_id="capture-metaeditor-rule-highlight",
            source_start_ms=0,
            source_end_ms=2_120,
            bounds=(70, 300, 940, 1_180),
            crop=(0.05, 0.0, 0.72, 1.0),
            z_index=10,
            border_radius=22,
            x_start=-22,
            y_start=34,
            x_end=22,
            y_end=-34,
            scale_start=1.02,
            scale_end=1.10,
            brightness=1.08,
            contrast=1.12,
            saturation=1.10,
        ),
        _layer(
            id="layer-navigator-ea",
            shot_id="shot-04",
            start_ms=6_820,
            end_ms=9_420,
            source_role="real-product",
            asset_id="capture-mt5-navigator-ea",
            source_start_ms=0,
            source_end_ms=2_600,
            crop=(0.0, 0.0, 0.50, 1.0),
            x_start=24,
            y_start=14,
            x_end=-28,
            y_end=-18,
            scale_start=1.02,
            scale_end=1.09,
            brightness=1.06,
            contrast=1.08,
            saturation=1.08,
        ),
        _layer(
            id="layer-reset-presenter",
            shot_id="shot-05",
            start_ms=9_420,
            end_ms=12_060,
            source_role="presenter",
            asset_id="source-presenter",
            source_start_ms=9_420,
            source_end_ms=12_060,
            bounds=(0, 0, 1080, 1152),
            x_start=-10,
            y_start=10,
            x_end=10,
            y_end=-10,
            scale_start=1.01,
            scale_end=1.06,
            brightness=1.03,
            saturation=1.02,
        ),
        _layer(
            id="layer-reset-typing",
            shot_id="shot-05",
            start_ms=9_420,
            end_ms=12_060,
            source_role="licensed-context",
            asset_id="licensed-typing",
            source_start_ms=0,
            source_end_ms=2_640,
            bounds=(0, 1152, 1080, 768),
            crop=(0.05, 0.0, 0.9, 1.0),
            x_start=18,
            y_start=8,
            x_end=-18,
            y_end=-8,
            scale_start=1.02,
            scale_end=1.09,
            brightness=1.08,
            contrast=1.06,
            saturation=1.08,
        ),
        _layer(
            id="layer-wrong-rule-context",
            shot_id="shot-06",
            start_ms=12_060,
            end_ms=14_160,
            source_role="licensed-context",
            asset_id="licensed-code-screen",
            source_start_ms=0,
            source_end_ms=2_100,
            contrast=1.08,
            saturation=0.72,
            z_index=1,
        ),
        _layer(
            id="layer-wrong-rule",
            shot_id="shot-06",
            start_ms=12_060,
            end_ms=14_160,
            source_role="deterministic-graphic",
            asset_id="graphic-wrong-rule",
            kind="image",
            bounds=(60, 170, 960, 1_580),
            fit="contain",
            z_index=10,
            illustrative_label=True,
            reference_role="primary-10",
            y_start=24,
            y_end=-24,
            scale_start=1.01,
            scale_end=1.055,
        ),
        _layer(
            id="layer-evidence-overview",
            shot_id="shot-07",
            start_ms=14_160,
            end_ms=15_200,
            source_role="direct-evidence",
            asset_id="evidence-history-overview",
            kind="image",
            fit="contain",
            x_start=-12,
            y_start=24,
            x_end=12,
            y_end=-24,
            scale_start=1.0,
            brightness=1.02,
            contrast=1.03,
            saturation=1.0,
            scale_end=1.07,
        ),
        _layer(
            id="layer-evidence-championship",
            shot_id="shot-08",
            start_ms=15_200,
            end_ms=17_460,
            source_role="direct-evidence",
            asset_id="evidence-championship-excerpt",
            kind="image",
            fit="contain",
            x_start=-28,
            y_start=30,
            x_end=28,
            y_end=-34,
            scale_start=1.01,
            brightness=1.02,
            contrast=1.04,
            saturation=1.0,
            scale_end=1.11,
        ),
        _layer(
            id="layer-evidence-result",
            shot_id="shot-09",
            start_ms=17_460,
            end_ms=19_500,
            source_role="direct-evidence",
            asset_id="evidence-risk-excerpt",
            kind="image",
            fit="contain",
            x_start=26,
            y_start=28,
            x_end=-26,
            y_end=-32,
            scale_start=1.01,
            brightness=1.01,
            contrast=1.05,
            saturation=1.0,
            scale_end=1.10,
        ),
        _layer(
            id="layer-evidence-number",
            shot_id="shot-10",
            start_ms=19_500,
            end_ms=21_820,
            source_role="direct-evidence",
            asset_id="evidence-risk-number",
            kind="image",
            fit="contain",
            x_start=-18,
            y_start=24,
            x_end=18,
            y_end=-30,
            scale_start=1.02,
            brightness=1.01,
            contrast=1.06,
            saturation=1.0,
            scale_end=1.13,
        ),
        _layer(
            id="layer-risk-inputs",
            shot_id="shot-11",
            start_ms=21_820,
            end_ms=24_200,
            source_role="real-product",
            asset_id="capture-mt5-risk-inputs",
            source_start_ms=0,
            source_end_ms=2_380,
            crop=(0.08, 0.0, 0.62, 1.0),
            x_start=-24,
            y_start=18,
            x_end=24,
            y_end=-20,
            scale_start=1.02,
            scale_end=1.09,
            brightness=1.08,
            contrast=1.08,
            saturation=1.10,
        ),
        _layer(
            id="layer-risk-backdrop",
            shot_id="shot-12",
            start_ms=24_200,
            end_ms=25_800,
            source_role="deterministic-graphic",
            asset_id="graphic-light-backdrop",
            kind="image",
            z_index=1,
            scale_end=1,
        ),
        _layer(
            id="layer-risk-parameter",
            shot_id="shot-12",
            start_ms=24_200,
            end_ms=25_800,
            source_role="real-product",
            asset_id="capture-mt5-risk-alternate",
            source_start_ms=500,
            source_end_ms=2_100,
            bounds=(80, 350, 920, 1056),
            crop=(0.05, 0.0, 0.72, 1.0),
            z_index=10,
            border_radius=20,
            x_start=20,
            y_start=30,
            x_end=-20,
            y_end=-30,
            scale_start=1.02,
            scale_end=1.10,
            brightness=1.08,
            contrast=1.08,
            saturation=1.10,
        ),
        _layer(
            id="layer-risk-reversal",
            shot_id="shot-13",
            start_ms=25_800,
            end_ms=27_780,
            source_role="deterministic-graphic",
            asset_id="graphic-risk-reversal",
            kind="image",
            illustrative_label=True,
            reference_role="secondary-4",
            y_start=18,
            y_end=-18,
            scale_start=1.01,
            scale_end=1.06,
        ),
        _layer(
            id="layer-lesson-presenter",
            shot_id="shot-14",
            start_ms=27_780,
            end_ms=30_200,
            source_role="presenter",
            asset_id="source-presenter",
            source_start_ms=27_780,
            source_end_ms=30_200,
            x_start=-12,
            y_start=12,
            x_end=12,
            y_end=-12,
            scale_start=1.01,
            scale_end=1.065,
            brightness=1.03,
            saturation=1.02,
        ),
        _layer(
            id="layer-lesson-context",
            shot_id="shot-14",
            start_ms=29_700,
            end_ms=30_200,
            source_role="licensed-context",
            asset_id="licensed-typing",
            source_start_ms=3_000,
            source_end_ms=3_500,
            bounds=(0, 1_320, 1080, 600),
            crop=(0.05, 0.0, 0.9, 1.0),
            z_index=20,
            x_start=18,
            y_start=12,
            x_end=-18,
            y_end=-12,
            scale_start=1.02,
            scale_end=1.08,
            opacity_start=0,
            opacity_end=0.88,
            brightness=1.08,
            contrast=1.08,
            saturation=1.08,
        ),
        _layer(
            id="layer-rules-risk",
            shot_id="shot-15",
            start_ms=30_200,
            end_ms=32_200,
            source_role="deterministic-graphic",
            asset_id="graphic-rules-versus-risk",
            kind="image",
            illustrative_label=True,
            y_start=22,
            y_end=-22,
            scale_start=1.01,
            scale_end=1.055,
        ),
        _layer(
            id="layer-tactile-bridge",
            shot_id="shot-16",
            start_ms=32_200,
            end_ms=33_020,
            source_role="licensed-context",
            asset_id="licensed-typing",
            source_start_ms=4_000,
            source_end_ms=4_820,
            x_start=24,
            y_start=18,
            x_end=-24,
            y_end=-18,
            scale_start=1.02,
            scale_end=1.10,
            brightness=1.08,
            contrast=1.08,
            saturation=1.10,
        ),
        _layer(
            id="layer-attach-backdrop",
            shot_id="shot-17",
            start_ms=33_020,
            end_ms=35_200,
            source_role="deterministic-graphic",
            asset_id="graphic-light-backdrop",
            kind="image",
            z_index=1,
            scale_end=1,
        ),
        _layer(
            id="layer-attach-context",
            shot_id="shot-17",
            start_ms=33_020,
            end_ms=35_200,
            source_role="licensed-context",
            asset_id="licensed-code-screen",
            source_start_ms=0,
            source_end_ms=2_180,
            bounds=(0, 0, 1080, 360),
            crop=(0.02, 0.0, 0.96, 1.0),
            z_index=5,
            x_start=-20,
            x_end=20,
            scale_start=1.02,
            scale_end=1.09,
            brightness=1.16,
            contrast=1.08,
            saturation=1.10,
        ),
        _layer(
            id="layer-attach-ea",
            shot_id="shot-17",
            start_ms=33_020,
            end_ms=35_200,
            source_role="real-product",
            asset_id="capture-mt5-attach-ea",
            source_start_ms=0,
            source_end_ms=2_180,
            bounds=(50, 340, 980, 1_400),
            crop=(0.0, 0.0, 0.58, 1.0),
            z_index=10,
            border_radius=22,
            x_start=-20,
            y_start=30,
            x_end=20,
            y_end=-30,
            scale_start=1.02,
            scale_end=1.10,
            brightness=1.08,
            contrast=1.08,
            saturation=1.10,
        ),
        _layer(
            id="layer-tester-backdrop",
            shot_id="shot-18",
            start_ms=35_200,
            end_ms=37_160,
            source_role="deterministic-graphic",
            asset_id="graphic-cool-backdrop",
            kind="image",
            z_index=1,
            scale_end=1,
        ),
        _layer(
            id="layer-tester-context",
            shot_id="shot-18",
            start_ms=35_200,
            end_ms=37_160,
            source_role="licensed-context",
            asset_id="licensed-typing",
            source_start_ms=5_000,
            source_end_ms=6_960,
            bounds=(0, 1_500, 1080, 420),
            crop=(0.04, 0.0, 0.92, 1.0),
            z_index=5,
            x_start=20,
            x_end=-20,
            scale_start=1.02,
            scale_end=1.09,
            brightness=1.10,
            contrast=1.08,
            saturation=1.10,
        ),
        _layer(
            id="layer-strategy-tester",
            shot_id="shot-18",
            start_ms=35_200,
            end_ms=37_160,
            source_role="real-product",
            asset_id="capture-mt5-strategy-tester",
            source_start_ms=0,
            source_end_ms=1_960,
            bounds=(40, 240, 1000, 1_350),
            crop=(0.0, 0.0, 0.72, 1.0),
            z_index=10,
            border_radius=22,
            x_start=20,
            y_start=28,
            x_end=-20,
            y_end=-28,
            scale_start=1.02,
            scale_end=1.10,
            brightness=1.08,
            contrast=1.08,
            saturation=1.10,
        ),
        _layer(
            id="layer-cta-presenter",
            shot_id="shot-19",
            start_ms=37_160,
            end_ms=39_800,
            source_role="presenter",
            asset_id="source-presenter",
            source_start_ms=37_160,
            source_end_ms=39_800,
            x_start=-12,
            y_start=10,
            x_end=12,
            y_end=-10,
            scale_start=1.01,
            scale_end=1.07,
            brightness=1.03,
            saturation=1.02,
        ),
        _layer(
            id="layer-ending-product",
            shot_id="shot-20",
            start_ms=39_800,
            end_ms=41_400,
            source_role="real-product",
            asset_id="capture-mt5-hook-action",
            source_start_ms=0,
            source_end_ms=1_600,
            bounds=(0, 0, 1080, 1100),
            crop=(0.0, 0.0, 0.58, 1.0),
            x_start=-12,
            y_start=8,
            x_end=12,
            y_end=-8,
            scale_start=1.02,
            scale_end=1.08,
            brightness=1.06,
            contrast=1.08,
            saturation=1.08,
        ),
        _layer(
            id="layer-ending-presenter",
            shot_id="shot-20",
            start_ms=39_800,
            end_ms=41_400,
            source_role="presenter",
            asset_id="source-presenter",
            source_start_ms=39_800,
            source_end_ms=41_400,
            bounds=(0, 1100, 1080, 820),
            y_start=8,
            y_end=-8,
            scale_start=1.01,
            scale_end=1.06,
            brightness=1.03,
            saturation=1.02,
        ),
        _layer(
            id="layer-ending-logo",
            shot_id="shot-20",
            start_ms=39_900,
            end_ms=41_200,
            source_role="deterministic-graphic",
            asset_id="brand-logo-original",
            kind="image",
            bounds=(830, 70, 180, 180),
            fit="contain",
            z_index=40,
            scale_end=1.02,
        ),
    ]
    return layers


def estimate_role_coverage(
    layers: list[BlueprintLayerSpec],
) -> dict[str, float]:
    roles = [
        "presenter",
        "real-product",
        "direct-evidence",
        "deterministic-graphic",
        "licensed-context",
        "flow-illustrative",
    ]
    coverage = {role: 0.0 for role in roles}
    boundaries = sorted(
        {
            value
            for layer in layers
            for value in (layer.start_ms, layer.end_ms)
        }
    )
    frame_area = 1080 * 1920
    for start_ms, end_ms in zip(boundaries, boundaries[1:], strict=False):
        if end_ms <= start_ms:
            continue
        active = [
            layer
            for layer in layers
            if layer.start_ms <= start_ms and layer.end_ms >= end_ms
        ]
        if not active:
            continue
        grid = [["" for _ in range(108)] for _ in range(192)]
        for layer in sorted(active, key=lambda item: item.z_index):
            left = max(0, min(107, layer.bounds.x // 10))
            top = max(0, min(191, layer.bounds.y // 10))
            right = max(
                left + 1,
                min(108, (layer.bounds.x + layer.bounds.width + 9) // 10),
            )
            bottom = max(
                top + 1,
                min(192, (layer.bounds.y + layer.bounds.height + 9) // 10),
            )
            for row in range(top, bottom):
                for column in range(left, right):
                    grid[row][column] = layer.source_role
        duration = end_ms - start_ms
        counts = {role: 0 for role in roles}
        for row in grid:
            for role in row:
                if role in counts:
                    counts[role] += 1
        for role in roles:
            coverage[role] += counts[role] / (108 * 192) * duration
    return {
        role: round(value / DURATION_MS, 6)
        for role, value in coverage.items()
    }


def build_motion_events() -> list[MotionEventSpec]:
    specifications = [
        ("hook", 0, 420, "punch-crop", "layer-hook-product", 0.38, "none"),
        ("code", 4_700, 5_140, "proof-punch", "layer-code-macro", 0.36, "none"),
        ("navigator", 6_820, 7_300, "punch-crop", "layer-navigator-ea", 0.34, "none"),
        ("wrong-rule", 12_060, 12_620, "proof-punch", "layer-wrong-rule", 0.42, "none"),
        ("overview", 14_160, 14_580, "proof-punch", "layer-evidence-overview", 0.28, "none"),
        ("history", 15_200, 16_050, "highlight-sweep", "layer-evidence-championship", 0.45, "none"),
        ("number", 19_500, 20_080, "proof-punch", "layer-evidence-number", 0.48, "none"),
        ("risk", 21_820, 22_320, "proof-punch", "layer-risk-inputs", 0.36, "none"),
        ("reversal", 25_800, 26_420, "directional-jump", "layer-risk-reversal", 0.32, "down"),
        ("attach", 33_020, 33_500, "proof-punch", "layer-attach-ea", 0.36, "none"),
        ("tester", 35_200, 35_680, "proof-punch", "layer-strategy-tester", 0.34, "none"),
        ("cta", 37_160, 37_640, "punch-crop", "layer-cta-presenter", 0.32, "none"),
    ]
    return [
        MotionEventSpec(
            id=f"motion-{event_id}",
            start_ms=start_ms,
            end_ms=end_ms,
            kind=kind,
            target_id=target_id,
            intensity=intensity,
            direction=direction,
        )
        for (
            event_id,
            start_ms,
            end_ms,
            kind,
            target_id,
            intensity,
            direction,
        ) in specifications
    ]


def create_blueprint(
    *,
    source_filename: str,
    source_metadata: VideoMetadata,
    assets: list[AssetRef],
    evidence: list[EvidenceItem],
    caption_pages: list[CaptionPage],
    transcript: list[dict[str, Any]],
) -> ProductionBlueprint:
    return ProductionBlueprint(
        source_filename=source_filename,
        source_metadata=source_metadata,
        output=OutputSpec(width=1080, height=1920, fps=30),
        duration_ms=DURATION_MS,
        assets=assets,
        layers=build_layers(),
        caption_pages=caption_pages,
        audio=build_v7_audio_plan(transcript),
        flow_shots=[],
        evidence=evidence,
        reference_profile="technical-reference",
        story_profile="automation-future",
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
        kinetic_text_cues=[],
        motion_events=build_motion_events(),
    )


def build_caption_specs() -> list[dict[str, Any]]:
    raw = [
        (0, 620, "DO YOU KNOW", "technical-mono", "center-74"),
        (620, 1_100, "WHAT", "technical-mono", "center-74"),
        (1_100, 2_340, "FOREX TRADING ROBOT", "technical-mono", "center-74"),
        (2_800, 3_700, "IT IS A SOFTWARE", "technical-mono", "center-74"),
        (3_700, 4_640, "THAT", "technical-mono", "center-74"),
        (4_640, 5_940, "AUTOMATICALLY", "technical-mono", "center-74"),
        (6_020, 6_420, "TRADES", "technical-mono", "center-74"),
        (6_420, 6_820, "ON SET RULES", "technical-mono", "center-74"),
        (7_200, 7_840, "PROFESSIONALLY", "technical-mono", "center-74"),
        (8_100, 8_460, "IT IS CALLED", "technical-mono", "center-74"),
        (8_460, 9_560, "EXPERT ADVISOR", "technical-mono", "center-74"),
        (9_560, 10_700, "IN SHORT, EA", "technical-mono", "center-74"),
        (12_060, 12_700, "BUT", "technical-mono", "center-74"),
        (12_700, 13_480, "IF THE", "technical-mono", "center-74"),
        (13_480, 14_160, "RULES ARE WRONG", "technical-mono", "center-74"),
        (14_480, 15_780, "IN 2008", "documentary-clean", "center-71"),
        (16_080, 16_780, "AUTOMATED TRADING", "documentary-clean", "center-71"),
        (16_780, 17_460, "CHAMPIONSHIP", "documentary-clean", "center-71"),
        (17_920, 18_540, "AN EXPERT", "documentary-clean", "center-71"),
        (18_540, 19_260, "ADVISOR EARNED", "documentary-clean", "center-71"),
        (19_260, 20_560, "$110,000", "documentary-clean", "center-71"),
        (21_820, 22_400, "THE RISK", "technical-mono", "center-74"),
        (22_400, 23_140, "TURNED THE GAME", "technical-mono", "center-74"),
        (24_000, 24_820, "HIGH RISK", "technical-mono", "center-74"),
        (24_820, 25_520, "INCREASED THE RESULT", "technical-mono", "center-74"),
        (26_080, 26_780, "THEN IT", "technical-mono", "center-74"),
        (26_780, 27_780, "TURNED UPSIDE DOWN", "technical-mono", "center-74"),
        (27_780, 28_600, "LESSON IS SIMPLE", "technical-mono", "center-74"),
        (28_840, 29_580, "EXPERT ADVISOR", "technical-mono", "center-74"),
        (29_580, 30_420, "DOESN'T TRADE WITH EMOTIONS", "technical-mono", "center-74"),
        (30_900, 31_840, "BUT DOESN'T", "technical-mono", "center-74"),
        (31_840, 32_200, "CHOOSE A SAFE RISK", "technical-mono", "center-74"),
        (33_180, 34_180, "IF YOU WANT", "compact-pill", "center-76"),
        (34_180, 34_720, "TO SEE HOW", "compact-pill", "center-76"),
        (34_720, 35_480, "AN EXPERT ADVISOR", "compact-pill", "center-76"),
        (35_480, 36_380, "TRADES", "compact-pill", "center-76"),
        (36_720, 37_640, "FOLLOW US", "compact-pill", "center-76"),
        (38_620, 39_440, "JOIN OUR TELEGRAM", "compact-pill", "center-76"),
        (39_440, 39_800, "GROUP", "compact-pill", "center-76"),
        (40_620, 41_000, "THANK YOU", "compact-pill", "center-76"),
    ]
    return [
        {
            "start_ms": start_ms,
            "end_ms": end_ms,
            "text": text,
            "family": family,
            "anchor": anchor,
            "transition": "hard-cut",
            "max_width": 500 if family == "documentary-clean" else 480,
        }
        for start_ms, end_ms, text, family, anchor in raw
    ]


def _normalize_token(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def align_caption_specs(
    *,
    specs: list[dict[str, Any]],
    transcript: list[dict[str, Any]],
) -> list[CaptionPage]:
    source_words = [
        word
        for segment in transcript
        for word in segment.get("words", [])
    ]
    source_keys = [_normalize_token(str(word["text"])) for word in source_words]
    cursor = 0
    pages: list[CaptionPage] = []
    for spec in specs:
        phrase_tokens = re.findall(r"[\w$,'?!.]+", str(spec["text"]))
        phrase_keys = [_normalize_token(token) for token in phrase_tokens]
        match_start: int | None = None
        for start in range(cursor, len(source_words) - len(phrase_keys) + 1):
            if source_keys[start : start + len(phrase_keys)] == phrase_keys:
                match_start = start
                break
        if match_start is None:
            raise ValueError(
                f'Caption phrase could not be aligned: {spec["text"]}'
            )
        matched = source_words[
            match_start : match_start + len(phrase_keys)
        ]
        cursor = match_start + len(phrase_keys)
        pages.append(
            CaptionPage(
                start_ms=int(spec["start_ms"]),
                end_ms=int(spec["end_ms"]),
                family=spec["family"],
                anchor=spec["anchor"],
                transition=spec["transition"],
                max_width=int(spec["max_width"]),
                tokens=[
                    CaptionToken(
                        text=str(word["text"]),
                        start_ms=round(float(word["start"]) * 1000),
                        end_ms=max(
                            round(float(word["start"]) * 1000) + 1,
                            round(float(word["end"]) * 1000),
                        ),
                        highlighted=False,
                        confidence=word.get("confidence"),
                    )
                    for word in matched
                ],
            )
        )
    return pages


def _speech_windows(transcript: list[dict[str, Any]]) -> list[SpeechProtectionWindow]:
    windows: list[SpeechProtectionWindow] = []
    for segment in transcript:
        for word in segment.get("words", []):
            start_ms = round(float(word["start"]) * 1000)
            if start_ms >= DURATION_MS:
                continue
            windows.append(
                SpeechProtectionWindow(
                    start_ms=max(0, start_ms - 100),
                    end_ms=min(DURATION_MS, start_ms + 120),
                    word=str(word["text"]),
                )
            )
    return windows


def build_v7_audio_plan(transcript: list[dict[str, Any]]) -> AudioPlan:
    windows = _speech_windows(transcript)
    candidates = [
        ("sfx-hook", "sfx-impact", 520, 220, 100, -18.0, "impact", "hook settle"),
        ("sfx-code-open", "sfx-click", 2_360, 40, 100, -14.0, "click", "MetaEditor open"),
        ("sfx-code-rule", "sfx-click", 4_780, 40, 100, -18.0, "click", "rule highlight"),
        ("sfx-ea", "sfx-snap", 6_900, 0, 100, -18.0, "click", "EA reveal"),
        ("sfx-reset", "sfx-click", 9_340, 40, 100, -18.0, "click", "presenter reset"),
        ("sfx-paper", "sfx-paper", 14_180, 460, 100, -18.0, "whoosh", "evidence overview"),
        ("sfx-proof", "sfx-proof", 19_420, 220, 120, -17.0, "impact", "verified number"),
        ("sfx-reversal", "sfx-reversal", 25_820, 220, 120, -17.0, "impact", "risk reversal"),
        ("sfx-attach", "sfx-click", 32_940, 40, 100, -18.0, "click", "EA attachment"),
        ("sfx-cta", "sfx-riser", 39_680, 500, 180, -20.0, "riser", "CTA lift"),
    ]

    def safe_start(desired_ms: int, duration_ms: int) -> int:
        if not windows:
            return desired_ms
        for delta in [0, *range(10, 701, 10)]:
            for direction in (-1, 1):
                candidate = max(
                    0,
                    min(DURATION_MS - duration_ms, desired_ms + direction * delta),
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
            start_ms=max(0, round(float(segment["start"]) * 1000) - 180),
            end_ms=min(DURATION_MS, round(float(segment["end"]) * 1000) + 120),
            gain_db=-5.5,
            reason="Duck documentary-tech music beneath narration",
        )
        for segment in transcript
    ]
    return AudioPlan(
        integrated_lufs=-14.2,
        true_peak_dbtp=-1.2,
        target_lra_lu=2.8,
        music_bpm=94,
        dialogue_asset_id="dialogue-original",
        dialogue_offset_ms=0,
        music_asset_id="music-technical-documentary",
        music_duck_db=5.5,
        music_base_gain_db=-28,
        music_gain_automation=automation,
        speech_protection_windows=windows,
        sfx_asset_ids=sorted({cue.asset_id for cue in cues}),
        sfx_cues=cues,
    )


def technical_reference_review_targets() -> dict[str, Any]:
    return {
        "hard_cuts": [17, 19],
        "median_shot_ms": [1800, 2300],
        "presenter_ratio": [0.14, 0.20],
        "flow_ratio_max": 0,
        "caption_coverage_ratio": [0.68, 0.75],
        "dark_frame_ratio": [0.35, 0.45],
        "bright_frame_ratio": [0.18, 0.28],
        "luminance_p10": [8, 22],
        "luminance_p90": [220, 245],
        "mean_saturation": [50, 90],
        "real_direct_source_min": 0.50,
        "cut_audio_alignment_min": 90,
    }
