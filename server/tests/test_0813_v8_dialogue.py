from __future__ import annotations

from pathlib import Path

from app.editor.dialogue_mastering import (
    DialoguePolicy,
    build_audio_plan,
    build_dialogue_plan,
    build_dialogue_plan_from_ranges,
    build_stereo_master_command,
    dialogue_filter_chain,
)
from build_0813_v8_pipeline import (
    _remap_words,
    encoded_master_filter,
)


def test_speech_segments_remain_at_one_x() -> None:
    plan = build_dialogue_plan(
        source=Path(r"D:\Downloads\0813 (2).mp4"),
        words=[
            {"text": "Backtest", "start_ms": 0, "end_ms": 420},
            {"text": "simple", "start_ms": 650, "end_ms": 970},
            {"text": "language", "start_ms": 1_040, "end_ms": 1_420},
        ],
    )

    assert all(segment.playback_rate == 1.0 for segment in plan.segments)
    assert plan.output_duration_ms == 1_260
    assert plan.channels == 2


def test_processed_dialogue_is_the_mix_source() -> None:
    plan = build_audio_plan(
        [
            {
                "id": "dialogue-source-untouched",
                "kind": "audio",
                "path": "assets/audio/dialogue-source-untouched.wav",
            },
            {
                "id": "dialogue-processed",
                "kind": "audio",
                "path": "assets/audio/dialogue-processed.wav",
            },
        ]
    )

    assert plan.dialogue_asset_id == "dialogue-processed"
    assert (
        plan.untouched_dialogue_asset_id
        == "dialogue-source-untouched"
    )


def test_master_stays_stereo() -> None:
    command = build_stereo_master_command(
        ffmpeg=Path("ffmpeg.exe"),
        silent_video=Path("rendered-silent.mp4"),
        dialogue=Path("dialogue-processed.wav"),
        music=Path("music.wav"),
        output=Path("edited.mp4"),
        duration_ms=48_800,
    )

    assert command[command.index("-ac") + 1] == "2"
    assert command[command.index("-ar") + 1] == "48000"
    assert command[command.index("-b:a") + 1] == "256k"


def test_dialogue_filter_is_conservative_and_does_not_accelerate() -> None:
    filters = dialogue_filter_chain()

    assert "highpass=f=72" in filters
    assert "afftdn=nr=7:nf=-32:tn=1" in filters
    assert "deesser=i=0.10:m=0.25:f=0.48" in filters
    assert "acompressor=" in filters
    assert "atempo" not in filters


def test_dialogue_policy_locks_natural_speed_and_short_gap() -> None:
    policy = DialoguePolicy()

    assert policy.speech_playback_rate == 1.0
    assert policy.collapse_gap_over_ms == 120
    assert policy.replacement_gap_ms == 70
    assert policy.edit_crossfade_ms == 12
    assert policy.preserve_channels == 2


def test_locked_source_ranges_expand_only_with_real_source_pause() -> None:
    plan = build_dialogue_plan_from_ranges(
        source=Path("source.mp4"),
        source_ranges=[(0, 1_000), (1_500, 2_500)],
        target_output_ms=2_300,
    )

    assert [
        (segment.source_start_ms, segment.source_end_ms)
        for segment in plan.segments
    ] == [(0, 1_300), (1_500, 2_500)]
    assert plan.output_duration_ms == 2_300
    assert all(segment.playback_rate == 1.0 for segment in plan.segments)


def test_caption_words_are_romanized_without_changing_timestamps() -> None:
    plan = build_dialogue_plan_from_ranges(
        source=Path("source.mp4"),
        source_ranges=[(0, 1_000)],
        target_output_ms=1_000,
    )
    words = _remap_words(
        [{"word": "सोचिए", "start": 0.1, "end": 0.4}],
        plan,
    )

    assert words == [
        {
            "text": "sochiye",
            "start_ms": 100,
            "end_ms": 400,
            "confidence": None,
        }
    ]


def test_encoded_master_limiter_never_auto_boosts_true_peak() -> None:
    filters = encoded_master_filter(3.2)

    assert "volume=3.2000dB" in filters
    assert "limit=0.820000" in filters
    assert "level=0" in filters
