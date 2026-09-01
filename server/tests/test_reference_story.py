from __future__ import annotations

import importlib
from datetime import UTC, datetime
from pathlib import Path

from app.models import TranscriptSegment, TranscriptWord


def _story_module():
    return importlib.import_module("app.editor.reference_story")


def test_0809_schedule_covers_the_full_story_without_base_gaps():
    module = _story_module()

    shots = module.build_0809_story_schedule()

    assert len(shots) == 22
    assert shots[0]["start_ms"] == 0
    assert shots[-1]["end_ms"] == 50_833
    assert all(
        left["end_ms"] == right["start_ms"]
        for left, right in zip(shots, shots[1:], strict=False)
    )
    assert 1_800 <= sorted(
        shot["end_ms"] - shot["start_ms"] for shot in shots
    )[len(shots) // 2] <= 2_600
    assert sum(
        shot["end_ms"] - shot["start_ms"]
        for shot in shots
        if shot["source_role"] == "presenter"
    ) / 50_833 >= 0.55


def test_0809_schedule_uses_evidence_and_real_context_without_reference_media():
    module = _story_module()

    shots = module.build_0809_story_schedule()
    asset_ids = {shot["asset_id"] for shot in shots}

    assert "reference-master" not in asset_ids
    assert "licensed-stock-market-mockup" not in asset_ids
    assert {
        "evidence-sec-overview",
        "evidence-sec-email",
        "evidence-sec-controls",
        "licensed-mixkit-trader",
        "licensed-mixkit-forex-screen",
        "licensed-mixkit-server",
    }.issubset(asset_ids)


def test_story_audio_plan_protects_speech_and_keeps_sfx_in_real_gaps():
    module = _story_module()
    segments = [
        TranscriptSegment(
            start=0.0,
            end=0.6,
            text="First sentence.",
            words=[
                TranscriptWord(
                    start=0.0,
                    end=0.25,
                    text="First",
                    confidence=1,
                ),
                TranscriptWord(
                    start=0.3,
                    end=0.6,
                    text="sentence.",
                    confidence=1,
                ),
            ],
        ),
        TranscriptSegment(
            start=1.2,
            end=1.8,
            text="Second sentence.",
            words=[
                TranscriptWord(
                    start=1.2,
                    end=1.45,
                    text="Second",
                    confidence=1,
                ),
                TranscriptWord(
                    start=1.5,
                    end=1.8,
                    text="sentence.",
                    confidence=1,
                ),
            ],
        ),
    ]

    plan = module.build_story_audio_plan(
        segments,
        duration_ms=2_000,
        sfx_specs=[
            {
                "id": "safe-gap",
                "asset_id": "sfx-click",
                "start_ms": 800,
                "duration_ms": 120,
                "volume": 0.4,
                "gain_db": -16,
                "kind": "click",
                "reason": "sentence gap",
            }
        ],
    )

    assert plan.dialogue_asset_id == "dialogue-processed"
    assert plan.music_asset_id == "music-reference-score"
    assert plan.music_gain_automation
    assert plan.speech_protection_windows
    assert all(
        not (
            cue.start_ms < window.end_ms
            and cue.start_ms + cue.duration_ms > window.start_ms
        )
        for cue in plan.sfx_cues
        for window in plan.speech_protection_windows
    )


def test_reference_style_review_requires_audio_and_pacing_gates():
    module = _story_module()
    passing = module.evaluate_reference_style_story(
        metadata={
            "duration_seconds": 50.833,
            "frame_count": 1525,
            "width": 1080,
            "height": 1920,
            "fps": 30,
        },
        frame_audit={
            "rendered_cut_count": 20,
            "median_shot_ms": 2300,
            "motion_score": 4.1,
            "dark_frame_ratio": 0.24,
            "mean_luminance": 78,
            "mean_saturation": 72,
        },
        audio={
            "delay_passed": True,
            "duration_passed": True,
            "spectral_passed": True,
        },
        loudness={"integrated_lufs": -14.2, "true_peak_dbtp": -1.1},
        narration={"token_retention": 0.995, "protected_tokens_missing": []},
    )
    failing = module.evaluate_reference_style_story(
        metadata={
            "duration_seconds": 50.833,
            "frame_count": 1525,
            "width": 1080,
            "height": 1920,
            "fps": 30,
        },
        frame_audit={
            "rendered_cut_count": 7,
            "median_shot_ms": 6000,
            "motion_score": 1.2,
            "dark_frame_ratio": 0.7,
            "mean_luminance": 40,
            "mean_saturation": 140,
        },
        audio={
            "delay_passed": False,
            "duration_passed": True,
            "spectral_passed": True,
        },
        loudness={"integrated_lufs": -18, "true_peak_dbtp": -0.2},
        narration={"token_retention": 0.9, "protected_tokens_missing": ["First"]},
    )

    assert passing["automated_pass"] is True
    assert not [check for check in passing["checks"] if not check["passed"]]
    assert failing["automated_pass"] is False
    assert {check["name"] for check in failing["checks"] if not check["passed"]} >= {
        "rendered-hard-cuts",
        "median-shot",
        "audio-continuity",
        "loudness",
        "narration-retention",
    }


def test_reference_story_master_removes_encoder_pad_and_preserves_tail(
    tmp_path: Path,
):
    module = _story_module()

    command = module.build_reference_story_master_command(
        executable=Path("ffmpeg.exe"),
        rendered=tmp_path / "rendered.mp4",
        output=tmp_path / "edited.mp4",
        measurement={
            "input_i": -19.88,
            "input_tp": -5.61,
            "input_lra": 4.5,
            "input_thresh": -30.06,
            "target_offset": 0.82,
        },
        duration_seconds=50.833,
        leading_trim_ms=42,
    )

    audio_filter = command[command.index("-af") + 1]
    assert command[command.index("-c:v") + 1] == "copy"
    assert "atrim=start=0.042000" in audio_filter
    assert "asetpts=PTS-STARTPTS" in audio_filter
    assert "loudnorm=I=-14.2:TP=-1.5" in audio_filter
    assert "apad=pad_dur=0.042000" in audio_filter
    assert command[command.index("-t") + 1] == "50.875"


def test_story_asr_unverifiable_tokens_include_zero_duration_and_low_confidence():
    module = _story_module()
    segments = [
        TranscriptSegment(
            start=0,
            end=1,
            text="The company was called Knight Capital.",
            words=[
                TranscriptWord(start=0, end=0.2, text="The", confidence=0.9),
                TranscriptWord(
                    start=0.2,
                    end=0.2,
                    text="company",
                    confidence=0.9,
                ),
                TranscriptWord(
                    start=0.2,
                    end=0.3,
                    text="called",
                    confidence=0.11,
                ),
                TranscriptWord(
                    start=0.3,
                    end=0.6,
                    text="Knight",
                    confidence=0.8,
                ),
                TranscriptWord(
                    start=0.6,
                    end=1,
                    text="Capital",
                    confidence=0.8,
                ),
            ],
        )
    ]

    assert module.story_unverifiable_source_tokens(segments) == [
        "company",
        "called",
    ]


def test_style_comparison_labels_are_ascii_safe():
    module = _story_module()

    assert module._comparison_sheet_label("HOOK", "REF") == "HOOK | REF"


def test_story_layers_are_explicit_muted_non_looping_and_include_key_graphics():
    module = _story_module()

    layers = module.build_0809_story_layers()
    base_layers = [layer for layer in layers if layer.z_index == 10]
    identifiers = {layer.id for layer in layers}

    assert len(base_layers) == 22
    assert all(layer.muted for layer in layers)
    assert all(
        left.end_ms == right.start_ms
        for left, right in zip(base_layers, base_layers[1:], strict=False)
    )
    assert {
        "overlay-hook-white",
        "overlay-hook-accent",
        "overlay-loss-white",
        "overlay-loss-accent",
        "overlay-alerts",
        "overlay-brand-controls",
        "overlay-containment",
        "overlay-cta",
    }.issubset(identifiers)


def test_story_evidence_maps_every_visible_number_to_the_official_sec_order():
    module = _story_module()

    evidence = module.build_0809_evidence_items(
        accessed_at=datetime(2026, 8, 10, tzinfo=UTC)
    )

    assert len(evidence) >= 5
    assert all(item.status == "verified" for item in evidence)
    assert all(item.source_type == "official" for item in evidence)
    assert all(item.source_url.startswith("https://www.sec.gov/") for item in evidence)
    joined_claims = " ".join(item.claim for item in evidence)
    assert "4 million" in joined_claims
    assert "$460 million" in joined_claims
    assert "97" in joined_claims
    assert "one of eight" in joined_claims
