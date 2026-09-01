import json
from pathlib import Path
import statistics

from app.models import AssetRef, VideoMetadata
from app.editor.training_reference_0806 import (
    DURATION_MS,
    align_caption_specs,
    build_caption_specs,
    build_layers,
    build_shot_schedule,
    build_v7_audio_plan,
    create_blueprint,
    estimate_role_coverage,
    technical_reference_review_targets,
)


def test_v7_schedule_matches_reference_10_technical_pacing() -> None:
    shots = build_shot_schedule()

    assert len(shots) == 20
    assert len(shots) - 1 == 19
    assert shots[0]["start_ms"] == 0
    assert shots[-1]["end_ms"] == DURATION_MS
    assert all(
        current["end_ms"] == following["start_ms"]
        for current, following in zip(shots, shots[1:], strict=False)
    )
    median_ms = statistics.median(
        shot["end_ms"] - shot["start_ms"] for shot in shots
    )
    assert 1800 <= median_ms <= 2300
    assert all(shot["source_role"] != "flow-illustrative" for shot in shots)
    assert sum(
        shot["end_ms"] - shot["start_ms"]
        for shot in shots
        if shot["source_role"] == "presenter"
    ) / DURATION_MS <= 0.20


def test_v7_caption_specs_use_small_reference_10_phrases() -> None:
    pages = build_caption_specs()

    visible_ms = sum(page["end_ms"] - page["start_ms"] for page in pages)
    assert 0.68 <= visible_ms / DURATION_MS <= 0.75
    assert all(350 <= page["end_ms"] - page["start_ms"] <= 1300 for page in pages)
    assert all(1 <= len(page["text"].split()) <= 4 for page in pages)
    assert all(page["transition"] == "hard-cut" for page in pages)
    assert all(
        page["family"]
        in {"technical-mono", "documentary-clean", "compact-pill"}
        for page in pages
    )
    assert all(page["max_width"] <= 500 for page in pages)


def test_v7_layers_match_locked_source_role_distribution() -> None:
    layers = build_layers()
    coverage = estimate_role_coverage(layers)

    assert len({layer.id for layer in layers}) == len(layers)
    assert {layer.shot_id for layer in layers} == {
        f"shot-{index:02d}" for index in range(1, 21)
    }
    assert all(layer.source_role != "flow-illustrative" for layer in layers)
    assert 0.14 <= coverage["presenter"] <= 0.20
    assert 0.30 <= coverage["real-product"] <= 0.40
    assert 0.15 <= coverage["direct-evidence"] <= 0.20
    assert 0.20 <= coverage["deterministic-graphic"] <= 0.30
    assert 0.08 <= coverage["licensed-context"] <= 0.15


def test_v7_layers_create_bright_product_resets_and_camera_motion() -> None:
    layers = {layer.id: layer for layer in build_layers()}

    assert layers["layer-code-backdrop"].asset_id == "graphic-light-backdrop"
    assert layers["layer-attach-backdrop"].asset_id == "graphic-light-backdrop"
    assert layers["layer-tester-backdrop"].asset_id == "graphic-cool-backdrop"
    assert layers["layer-lesson-presenter"].end_ms == 30_200

    moving_layer_ids = {
        "layer-metaeditor-open",
        "layer-code-macro",
        "layer-navigator-ea",
        "layer-evidence-championship",
        "layer-evidence-result",
        "layer-evidence-number",
        "layer-risk-inputs",
        "layer-risk-parameter",
        "layer-attach-ea",
        "layer-strategy-tester",
    }
    for layer_id in moving_layer_ids:
        start, end = layers[layer_id].transform_keyframes
        assert (
            abs(end.x - start.x) >= 20
            or abs(end.y - start.y) >= 20
            or end.scale - start.scale >= 0.06
        )


def test_v7_audio_plan_is_restrained_and_flow_free() -> None:
    audio = build_v7_audio_plan(transcript=[])

    assert audio.music_bpm == 94
    assert audio.integrated_lufs == -14.2
    assert audio.true_peak_dbtp == -1.2
    assert audio.target_lra_lu == 2.8
    assert audio.music_base_gain_db == -28
    assert audio.music_duck_db == 5.5
    assert 8 <= len(audio.sfx_cues) <= 10


def test_v7_audio_cues_trim_to_audible_transients() -> None:
    audio = build_v7_audio_plan(transcript=[])
    cues = {cue.id: cue for cue in audio.sfx_cues}

    assert "sfx-reset" in cues
    assert len(cues) <= 10
    assert cues["sfx-code-open"].source_start_ms >= 40
    assert cues["sfx-code-open"].gain_db >= -14
    assert cues["sfx-code-rule"].source_start_ms >= 40
    assert cues["sfx-paper"].source_start_ms >= 440
    assert cues["sfx-proof"].source_start_ms >= 200
    assert cues["sfx-reversal"].source_start_ms >= 200
    assert cues["sfx-cta"].source_start_ms >= 500
    assert all(cue.duration_ms >= 100 for cue in cues.values())


def test_v7_blueprint_uses_explicit_layers_and_no_flow() -> None:
    layers = build_layers()
    audio = build_v7_audio_plan(transcript=[])
    kinds = {layer.asset_id: layer.kind for layer in layers}
    audio_ids = {
        audio.dialogue_asset_id,
        audio.music_asset_id,
        *audio.sfx_asset_ids,
    }
    assets = [
        AssetRef(
            id=asset_id,
            kind=kind,
            path=f"assets/{asset_id}.{'mp4' if kind == 'video' else 'png'}",
            provenance="test-fixture",
        )
        for asset_id, kind in kinds.items()
    ]
    assets.extend(
        AssetRef(
            id=asset_id,
            kind="audio",
            path=f"assets/{asset_id}.wav",
            provenance="test-fixture",
        )
        for asset_id in audio_ids
        if asset_id is not None
    )

    blueprint = create_blueprint(
        source_filename="0806.mp4",
        source_metadata=VideoMetadata(
            width=1080,
            height=1920,
            fps=30,
            frame_count=1242,
            duration_seconds=41.4,
        ),
        assets=assets,
        evidence=[],
        caption_pages=[],
        transcript=[],
    )

    assert blueprint.reference_profile == "technical-reference"
    assert blueprint.story_profile == "automation-future"
    assert blueprint.voice_policy == "preserve-verbatim"
    assert blueprint.flow_shots == []
    assert len(blueprint.layers) == len(layers)


def test_caption_alignment_preserves_matched_word_timestamps() -> None:
    pages = align_caption_specs(
        specs=[
            {
                "start_ms": 1000,
                "end_ms": 1800,
                "text": "EXPERT ADVISOR",
                "family": "technical-mono",
                "anchor": "center-74",
                "transition": "hard-cut",
                "max_width": 480,
            }
        ],
        transcript=[
            {
                "start": 0.9,
                "end": 1.9,
                "text": "an Expert Advisor",
                "words": [
                    {"start": 0.9, "end": 1.0, "text": "an"},
                    {"start": 1.0, "end": 1.35, "text": "Expert"},
                    {"start": 1.35, "end": 1.8, "text": "Advisor"},
                ],
            }
        ],
    )

    assert [token.text for token in pages[0].tokens] == ["Expert", "Advisor"]
    assert [(token.start_ms, token.end_ms) for token in pages[0].tokens] == [
        (1000, 1350),
        (1350, 1800),
    ]


def test_v7_caption_pages_overlap_real_0806_word_timestamps() -> None:
    workspace = Path(__file__).resolve().parents[2]
    transcript = json.loads(
        (
            workspace
            / "storage"
            / "deliverables"
            / "0806-production-v6-social-kinetic-fast"
            / "transcript-aligned.json"
        ).read_text(encoding="utf-8")
    )

    pages = align_caption_specs(
        specs=build_caption_specs(),
        transcript=transcript,
    )

    assert all(
        token.end_ms > page.start_ms and token.start_ms < page.end_ms
        for page in pages
        for token in page.tokens
    )


def test_v7_review_targets_use_training_reference_ranges() -> None:
    targets = technical_reference_review_targets()

    assert targets["hard_cuts"] == [17, 19]
    assert targets["median_shot_ms"] == [1800, 2300]
    assert targets["presenter_ratio"] == [0.14, 0.20]
    assert targets["flow_ratio_max"] == 0
    assert targets["caption_coverage_ratio"] == [0.68, 0.75]
    assert targets["dark_frame_ratio"] == [0.35, 0.45]
    assert targets["bright_frame_ratio"] == [0.18, 0.28]
    assert targets["luminance_p10"] == [8, 22]
    assert targets["luminance_p90"] == [220, 245]
