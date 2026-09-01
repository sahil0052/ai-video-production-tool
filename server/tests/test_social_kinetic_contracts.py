from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models import AssetRef, AudioPlan, OutputSpec, VideoMetadata
from app.production_models import (
    DialogueEditSegment,
    EditPlanV2,
    EffectKeyframe,
    KineticTextCue,
    MotionEventSpec,
    ProductionJobRecord,
    VisualLayerSpec,
)


def _base_plan() -> EditPlanV2:
    return EditPlanV2(
        source_filename="0810.mp4",
        source_metadata=VideoMetadata(
            width=1080,
            height=1920,
            fps=30,
            frame_count=1331,
            duration_seconds=44.37,
        ),
        output=OutputSpec(),
        duration_ms=44_370,
        assets=[
            AssetRef(
                id="presenter",
                kind="video",
                path="assets/presenter.mp4",
                provenance="user-provided",
            )
        ],
        visual_layers=[
            VisualLayerSpec(
                id="presenter-layer",
                shot_id="shot-01",
                start_ms=0,
                end_ms=44_370,
                source_role="presenter",
                asset_id="presenter",
                source_start_ms=0,
                source_end_ms=44_370,
                effect_keyframes=[
                    EffectKeyframe(at_ms=0),
                    EffectKeyframe(
                        at_ms=44_370,
                        brightness=1.03,
                        contrast=1.02,
                        saturation=0.96,
                    ),
                ],
                reference_role="primary-human",
            )
        ],
        caption_pages=[],
        audio=AudioPlan(),
        reference_profile="social-kinetic",
        style_reference_path="D:/Downloads/Profit Bricks_Reel 04.mp4",
        voice_policy="reference-compressed",
        dialogue_edl=[
            DialogueEditSegment(
                id="dialogue-001",
                source_start_ms=0,
                source_end_ms=1_000,
                output_start_ms=0,
                output_end_ms=1_000,
                playback_rate=1,
            )
        ],
        kinetic_text_cues=[
            KineticTextCue(
                id="hook-year",
                start_ms=200,
                end_ms=900,
                text="2008",
                family="hero-condensed",
                x=540,
                y=1_330,
                max_width=900,
                animation="slam",
            )
        ],
        motion_events=[
            MotionEventSpec(
                id="hook-punch",
                start_ms=0,
                end_ms=240,
                kind="punch-crop",
                target_id="presenter-layer",
                intensity=0.55,
            )
        ],
    )


def test_social_kinetic_contracts_are_backward_compatible_and_validated():
    plan = _base_plan()

    assert plan.reference_profile == "social-kinetic"
    assert plan.kinetic_text_cues[0].family == "hero-condensed"
    assert plan.visual_layers[0].effect_keyframes[-1].saturation == 0.96
    assert plan.dialogue_edl[0].output_end_ms == 1_000
    assert AudioPlan(target_lra_lu=2.4).target_lra_lu == 2.4

    legacy = plan.model_dump(mode="json")
    for key in (
        "reference_profile",
        "style_reference_path",
        "voice_policy",
        "dialogue_edl",
        "kinetic_text_cues",
        "motion_events",
    ):
        legacy.pop(key, None)
    for layer in legacy["visual_layers"]:
        layer.pop("effect_keyframes", None)
    parsed = EditPlanV2.model_validate(legacy)
    assert parsed.dialogue_edl == []
    assert parsed.kinetic_text_cues == []
    assert parsed.motion_events == []
    assert parsed.visual_layers[0].effect_keyframes[0].at_ms == 0


def test_social_kinetic_timed_contracts_reject_invalid_ranges_and_targets():
    with pytest.raises(ValidationError, match="positive duration"):
        DialogueEditSegment(
            id="bad",
            source_start_ms=100,
            source_end_ms=100,
            output_start_ms=0,
            output_end_ms=100,
            playback_rate=1,
        )

    with pytest.raises(ValidationError, match="positive duration"):
        KineticTextCue(
            id="bad",
            start_ms=800,
            end_ms=800,
            text="DEMO",
            family="cta-quote",
            x=540,
            y=1_520,
        )

    payload = _base_plan().model_dump(mode="json")
    payload["motion_events"][0]["target_id"] = "missing-layer"
    with pytest.raises(ValidationError, match="unknown target"):
        EditPlanV2.model_validate(payload)


def test_social_kinetic_flow_budget_supports_eight_explicit_operations():
    now = datetime.now(UTC)
    record = ProductionJobRecord(
        id="production-0810-human-reference",
        source_path="D:/Downloads/0810.mp4",
        output_dir="storage/deliverables/0810-production-v2-human-reference",
        state="awaiting-generation-approval",
        primary_reference=10,
        secondary_reference=10,
        flow_operation_budget=8,
        approved_paid_operations=8,
        consumed_paid_operations=0,
        created_at=now,
        updated_at=now,
    )

    assert record.flow_operation_budget == 8
    with pytest.raises(ValidationError, match="less than or equal to 8"):
        ProductionJobRecord.model_validate(
            {
                **record.model_dump(mode="json"),
                "flow_operation_budget": 9,
            }
        )
