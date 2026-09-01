from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models import (
    AssetRef,
    AudioPlan,
    CaptionPage,
    CaptionToken,
    OutputSpec,
    VideoMetadata,
)
from app.production_models import (
    BlueprintLayerSpec,
    CropSpec,
    EditPlanV2,
    FlowCandidateReview,
    FlowReviewScores,
    FlowShotSpec,
    ProductionBlueprint,
    ProductionJobRecord,
    TransformKeyframe,
    VisualLayerSpec,
    validate_production_transition,
)


def _video_asset(asset_id: str, path: str = "assets/clip.mp4") -> AssetRef:
    return AssetRef(
        id=asset_id,
        kind="video",
        path=path,
        provenance="user-provided",
    )


def _caption() -> CaptionPage:
    return CaptionPage(
        start_ms=0,
        end_ms=800,
        tokens=[
            CaptionToken(
                text="Rules",
                start_ms=0,
                end_ms=400,
                confidence=0.99,
            ),
            CaptionToken(
                text="execute.",
                start_ms=400,
                end_ms=800,
                confidence=0.99,
            ),
        ],
        family="technical-mono",
        anchor="center-74",
        transition="hard-cut",
    )


def test_flow_shot_rejects_factual_or_exact_content_roles() -> None:
    common = {
        "id": "flow-risk",
        "start_ms": 1000,
        "end_ms": 2200,
        "editorial_role": "physical-risk-metaphor",
        "prompt": (
            "A physical balance mechanism tips under increasing pressure. "
            "No text, no UI, no charts, no numbers, no documents."
        ),
        "mode": "i2v",
        "model": "veo-lite",
        "input_plates": ["flow-plates/start.png", "flow-plates/end.png"],
        "constraints": ["No readable text", "Single continuous shot"],
    }

    valid = FlowShotSpec(
        **common,
        requested_content=["physical-metaphor"],
    )
    assert valid.status == "planned"

    for forbidden in (
        "evidence",
        "exact-text",
        "product-ui",
        "code",
        "number",
        "currency",
        "chart",
        "source-document",
        "caption",
    ):
        with pytest.raises(ValidationError, match="Flow cannot generate"):
            FlowShotSpec(
                **common,
                requested_content=[forbidden],
            )


def test_candidate_review_requires_hard_gates_scores_and_usable_window() -> None:
    review = FlowCandidateReview(
        shot_id="flow-risk",
        attempt=1,
        technical_gates={
            "decoded": True,
            "duration_ok": True,
            "no_black_sequence": True,
            "no_frozen_sequence": True,
            "single_continuous_shot": True,
            "safe_framing": True,
            "no_generated_text": True,
        },
        scores=FlowReviewScores(
            prompt_fidelity=4,
            motion_quality=4,
            continuity=4,
            composition=4,
            artifact_integrity=4,
            editorial_usefulness=4,
        ),
        human_accepted=True,
        accepted_start_ms=700,
        accepted_end_ms=2200,
    )

    assert review.accepted is True
    assert review.total_score == 24

    with pytest.raises(ValidationError, match="24/30"):
        FlowCandidateReview(
            shot_id="flow-risk",
            attempt=1,
            technical_gates=review.technical_gates,
            scores=FlowReviewScores(
                prompt_fidelity=3,
                motion_quality=3,
                continuity=3,
                composition=3,
                artifact_integrity=3,
                editorial_usefulness=3,
            ),
            human_accepted=True,
            accepted_start_ms=700,
            accepted_end_ms=2200,
        )

    with pytest.raises(ValidationError, match="700"):
        FlowCandidateReview(
            shot_id="flow-risk",
            attempt=1,
            technical_gates=review.technical_gates,
            scores=review.scores,
            human_accepted=True,
            accepted_start_ms=0,
            accepted_end_ms=600,
        )


def test_edit_plan_v2_enforces_explicit_flow_layer_safety() -> None:
    assets = [
        _video_asset("presenter", "assets/presenter.mp4"),
        _video_asset("flow-risk", "assets/flow-risk.mp4"),
    ]
    layers = [
        VisualLayerSpec(
            id="presenter-layer",
            shot_id="shot-01",
            start_ms=0,
            end_ms=1000,
            source_role="presenter",
            asset_id="presenter",
            source_start_ms=0,
            source_end_ms=1000,
            crop=CropSpec(x=0, y=0, width=1, height=1),
            transform_keyframes=[
                TransformKeyframe(at_ms=0, x=0, y=0, scale=1),
            ],
            muted=True,
            z_index=10,
        ),
        VisualLayerSpec(
            id="flow-layer",
            shot_id="shot-02",
            start_ms=1000,
            end_ms=2000,
            source_role="flow-illustrative",
            asset_id="flow-risk",
            source_start_ms=700,
            source_end_ms=1700,
            muted=True,
            illustrative_label=True,
            z_index=20,
        ),
    ]
    plan = EditPlanV2(
        source_filename="0806.mp4",
        source_metadata=VideoMetadata(
            width=1080,
            height=1920,
            fps=30,
            frame_count=60,
            duration_seconds=2,
        ),
        output=OutputSpec(),
        duration_ms=2000,
        assets=assets,
        visual_layers=layers,
        caption_pages=[_caption()],
        audio=AudioPlan(),
    )

    assert plan.version == "2.0"
    assert plan.visual_layers[1].loop is False

    invalid = plan.model_dump(mode="json")
    invalid["visual_layers"][1]["muted"] = False
    with pytest.raises(ValidationError, match="muted"):
        EditPlanV2.model_validate(invalid)

    invalid = plan.model_dump(mode="json")
    invalid["visual_layers"][1]["illustrative_label"] = False
    with pytest.raises(ValidationError, match="ILLUSTRATIVE"):
        EditPlanV2.model_validate(invalid)

    invalid = plan.model_dump(mode="json")
    invalid["visual_layers"][1]["loop"] = True
    with pytest.raises(ValidationError, match="loop"):
        EditPlanV2.model_validate(invalid)


def test_edit_plan_v2_rejects_training_reference_media_as_output_assets() -> None:
    with pytest.raises(ValidationError, match="Training-video"):
        EditPlanV2(
            source_filename="0806.mp4",
            source_metadata=VideoMetadata(
                width=1080,
                height=1920,
                fps=30,
                frame_count=30,
                duration_seconds=1,
            ),
            output=OutputSpec(),
            duration_ms=1000,
            assets=[
                _video_asset(
                    "reference",
                    "C:/websites/ai video production tool/"
                    "training videos data/reference-10.mp4",
                )
            ],
            visual_layers=[
                VisualLayerSpec(
                    id="reference-layer",
                    shot_id="shot-01",
                    start_ms=0,
                    end_ms=1000,
                    source_role="licensed-context",
                    asset_id="reference",
                    source_start_ms=0,
                    source_end_ms=1000,
                    muted=True,
                )
            ],
            caption_pages=[],
            audio=AudioPlan(),
        )


def test_production_blueprint_accepts_training_parity_story_profile() -> None:
    blueprint = ProductionBlueprint(
        source_filename="0806.mp4",
        source_metadata=VideoMetadata(
            width=1080,
            height=1920,
            fps=30,
            frame_count=30,
            duration_seconds=1,
        ),
        output=OutputSpec(),
        duration_ms=1000,
        assets=[_video_asset("presenter")],
        layers=[
            BlueprintLayerSpec(
                id="presenter-layer",
                shot_id="shot-01",
                start_ms=0,
                end_ms=1000,
                source_role="presenter",
                asset_id="presenter",
                source_start_ms=0,
                source_end_ms=1000,
                muted=True,
            )
        ],
        story_profile="automation-future-parity",
    )

    assert blueprint.story_profile == "automation-future-parity"


def test_edit_plan_v2_rejects_zero_duration_and_overlapping_captions() -> None:
    base = EditPlanV2(
        source_filename="0806.mp4",
        source_metadata=VideoMetadata(
            width=1080,
            height=1920,
            fps=30,
            frame_count=60,
            duration_seconds=2,
        ),
        output=OutputSpec(),
        duration_ms=2000,
        assets=[_video_asset("presenter")],
        visual_layers=[
            VisualLayerSpec(
                id="presenter-layer",
                shot_id="shot-01",
                start_ms=0,
                end_ms=2000,
                source_role="presenter",
                asset_id="presenter",
                source_start_ms=0,
                source_end_ms=2000,
                muted=True,
            )
        ],
        caption_pages=[_caption()],
        audio=AudioPlan(),
    )

    zero_duration = base.model_dump(mode="json")
    zero_duration["caption_pages"][0]["tokens"][0]["start_ms"] = 100
    zero_duration["caption_pages"][0]["tokens"][0]["end_ms"] = 100
    with pytest.raises(ValidationError, match="positive duration"):
        EditPlanV2.model_validate(zero_duration)

    overlapping = base.model_dump(mode="json")
    second = overlapping["caption_pages"][0].copy()
    second["start_ms"] = 700
    second["end_ms"] = 1500
    second["tokens"] = [
        {
            "text": "Second",
            "start_ms": 700,
            "end_ms": 1100,
            "highlighted": False,
            "confidence": 0.99,
        }
    ]
    overlapping["caption_pages"].append(second)
    with pytest.raises(ValidationError, match="overlap"):
        EditPlanV2.model_validate(overlapping)


def test_production_state_machine_only_allows_locked_transitions() -> None:
    assert (
        validate_production_transition(
            "blueprint-ready",
            "awaiting-generation-approval",
        )
        == "awaiting-generation-approval"
    )
    with pytest.raises(ValueError, match="Invalid production transition"):
        validate_production_transition("blueprint-ready", "completed")

    record = ProductionJobRecord(
        id="production-0806",
        source_path="D:/Downloads/0806.mp4",
        output_dir="C:/deliverables/0806-production-v4",
        state="awaiting-generation-approval",
        primary_reference=10,
        secondary_reference=4,
        flow_operation_budget=3,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    assert record.approved_paid_operations == 0

    invalid = record.model_dump(mode="json")
    invalid["flow_operation_budget"] = 9
    with pytest.raises(ValidationError, match="less than or equal to 8"):
        ProductionJobRecord.model_validate(invalid)
