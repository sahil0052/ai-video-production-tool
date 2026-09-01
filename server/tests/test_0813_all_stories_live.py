from __future__ import annotations

import importlib
import json
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[2]


def _module(name: str):
    return importlib.import_module(name)


def _assert_story_contract(module_name: str, take: int) -> None:
    build = _module(module_name)
    from caption_transliteration_0813 import romanize_word

    assert build.SOURCE == Path(fr"D:\Downloads\0813 ({take}).mp4")
    assert build.OUTPUT.name == (
        "0813-production-v7-semantic-visuals"
        + (f"-take-{take}" if take > 1 else "")
    )
    assert build.DURATION_MS == 46_000
    assert build.PLAYBACK_RATE == 1.06
    assert build.TRANSCRIPT_PATH.is_file()
    assert len(build.BOUNDARIES) == len(build.SHOT_SPECS) + 1
    assert build.BOUNDARIES[0] == 0
    assert build.BOUNDARIES[-1] == build.DURATION_MS

    durations = [
        end - start
        for start, end in zip(
            build.BOUNDARIES[:-1],
            build.BOUNDARIES[1:],
            strict=True,
        )
    ]
    assert 14 <= len(build.SHOT_SPECS) <= 17
    assert 2_300 <= median(durations) <= 3_300
    assert all(700 <= duration <= 6_300 for duration in durations)
    assert all(shot["kind"] == "video" for shot in build.SHOT_SPECS)
    assert all(shot["visual_job"] for shot in build.SHOT_SPECS)

    edl = build.dialogue_edl()
    assert edl[0].output_start_ms == 0
    assert edl[-1].output_end_ms == build.DURATION_MS
    assert all(
        left.output_end_ms == right.output_start_ms
        for left, right in zip(edl, edl[1:])
    )
    assert all(segment.playback_rate == build.PLAYBACK_RATE for segment in edl)

    transcript = json.loads(build.TRANSCRIPT_PATH.read_text(encoding="utf-8"))
    captions = build.build_caption_pages(transcript, edl)
    assert len(captions) >= 38
    assert all(
        350 <= page["end_ms"] - page["start_ms"] <= 1_300
        for page in captions
    )
    assert all(len(page["text"].split()) <= 4 for page in captions)
    assert all(page["family"] == "modern-outline" for page in captions)
    assert all(page["font_size"] == 58 for page in captions)
    assert all(page["max_width"] == 900 for page in captions)
    covered_indices: list[int] = []
    for page in captions:
        start = int(page["source_word_start"])
        end = int(page["source_word_end"])
        expected = [
            romanize_word(str(transcript["words"][index]["word"])).upper()
            for index in range(start, end + 1)
        ]
        assert str(page["text"]).split() == expected
        covered_indices.extend(range(start, end + 1))
    assert covered_indices == list(range(len(transcript["words"])))
    assert all(
        left["end_ms"] <= right["start_ms"]
        for left, right in zip(captions, captions[1:])
    )


def test_backtest_story_has_a_bespoke_real_footage_timeline() -> None:
    _assert_story_contract("build_0813_backtest_live", 2)
    build = _module("build_0813_backtest_live")

    shots_by_role = {
        shot["editorial_role"]: shot
        for shot in build.SHOT_SPECS
    }
    asset_ids = {shot["asset_id"] for shot in build.SHOT_SPECS}
    assert {"pixabay-281621", "pixabay-138691"} <= asset_ids
    assert {
        "pexels-38870320",
        "pexels-33314914",
        "mt5-strategy-tester",
        "student-writing",
    } <= asset_ids
    assert {
        "mt5-hook-action",
        "metaeditor-rule-highlight",
    }.isdisjoint(asset_ids)
    assert (
        shots_by_role["forward-test-demo"]["crop_y"] >= 0.75
    )
    assert shots_by_role["forward-test-demo"]["zoom"] >= 1.18
    assert any(
        shot["editorial_role"] == "forward-test-demo"
        for shot in build.SHOT_SPECS
    )


def test_lot_size_story_has_real_pizza_and_mt5_risk_visuals() -> None:
    _assert_story_contract("build_0813_lotsize_live", 3)
    build = _module("build_0813_lotsize_live")

    shots_by_role = {
        shot["editorial_role"]: shot
        for shot in build.SHOT_SPECS
    }
    assert shots_by_role["one-pizza"]["asset_id"] == "pexels-13441351"
    assert (
        shots_by_role["many-pizzas-and-total"]["asset_id"]
        == "pexels-7362641"
    )
    assert (
        shots_by_role["many-pizzas-and-total"]["secondary_asset_id"]
        == "presenter-edl"
    )
    asset_ids = {shot["asset_id"] for shot in build.SHOT_SPECS}
    assert {
        "pixabay-17177",
        "pixabay-353257",
        "pixabay-43658",
    }.isdisjoint(asset_ids)
    assert {"mt5-risk-inputs", "mt5-risk-alternate"} <= asset_ids
    assert "mt5-attach-ea" in asset_ids
    assert "mt5-navigator-ea" not in asset_ids
    assert (
        shots_by_role["lot-size-product-hook"]["source_start_ms"]
        >= 1_500
    )
    assert (
        shots_by_role["large-position-and-impact"]["source_start_ms"]
        >= 1_800
    )
    assert (
        shots_by_role["entry-versus-lot-product-bridge"][
            "source_start_ms"
        ]
        >= 2_000
    )
    assert all(
        shots_by_role[role]["zoom"] >= 1.15
        for role in (
            "lot-size-product-hook",
            "large-position-and-impact",
            "entry-versus-lot-product-bridge",
        )
    )
    assert any(
        shot["editorial_role"] == "wrong-setting-repeat"
        for shot in build.SHOT_SPECS
    )


def test_story_audio_cues_avoid_protected_word_onsets() -> None:
    for module_name in (
        "build_0813_backtest_live",
        "build_0813_lotsize_live",
    ):
        build = _module(module_name)
        transcript = json.loads(
            build.TRANSCRIPT_PATH.read_text(encoding="utf-8")
        )
        audio = build.build_audio_plan(transcript, build.dialogue_edl())

        assert 8 <= len(audio["sfx_cues"]) <= 10
        assert audio["music_base_gain_db"] <= -26
        assert audio["music_duck_db"] >= 5
        for cue in audio["sfx_cues"]:
            cue_end = cue["start_ms"] + cue["duration_ms"]
            assert all(
                not (
                    cue["start_ms"] < window["end_ms"]
                    and cue_end > window["start_ms"]
                )
                for window in audio["speech_protection_windows"]
            )


def test_renderer_can_select_a_story_build_module() -> None:
    render = _module("render_0813_ppi_live")

    build = render.load_build_module("build_0813_backtest_live")

    assert build.STORY_ID == "backtest"
    assert render.OUTPUT == build.OUTPUT


def test_renderer_adds_a_restrained_push_to_product_footage() -> None:
    render = _module("render_0813_ppi_live")

    x_expression, y_expression = render.dynamic_crop_expressions(
        {
            "asset_id": "mt5-risk-inputs",
            "crop_x": 0.5,
            "crop_y": 0.5,
        },
        frame_count=45,
    )

    assert "22.0000*(n/45-0.5)" in x_expression
    assert "12.1000*(n/45-0.5)" in y_expression


def test_renderer_lifts_dark_product_ui_for_phone_readability() -> None:
    render = _module("render_0813_ppi_live")

    grade = render._grade("mt5-risk-inputs")

    assert "brightness=0.075" in grade
    assert "contrast=0.98" in grade
    assert "gamma=1.20" in grade


def test_secondary_story_beats_use_temporal_full_frames_not_vertical_halves() -> None:
    render = _module("render_0813_ppi_live")

    render.load_build_module("build_0813_backtest_live")
    assert render.secondary_layout_for_shot(8, has_secondary=True) == (
        "alternating-full"
    )
    render.load_build_module("build_0813_lotsize_live")
    assert render.secondary_layout_for_shot(8, has_secondary=True) == (
        "alternating-full"
    )


def test_every_story_meets_the_requested_presenter_visual_balance() -> None:
    render = _module("render_0813_ppi_live")

    for module_name in (
        "build_0813_backtest_live",
        "build_0813_lotsize_live",
    ):
        render.load_build_module(module_name)
        coverage = render.presenter_coverage_metrics()

        assert 0.58 <= coverage["presenter_pixel_ratio"] <= 0.68
        assert 0.32 <= coverage["visual_pixel_ratio"] <= 0.42
        assert coverage["longest_without_presenter_ms"] <= 3_800


def test_non_presenter_visuals_are_unique_across_all_three_reels() -> None:
    modules = [
        _module("build_0813_ppi_live"),
        _module("build_0813_backtest_live"),
        _module("build_0813_lotsize_live"),
    ]
    asset_ids = [
        str(shot["asset_id"])
        for build in modules
        for shot in build.SHOT_SPECS
        if shot["asset_id"] != "presenter-edl"
    ]
    secondary_ids = [
        str(shot["secondary_asset_id"])
        for build in modules
        for shot in build.SHOT_SPECS
        if shot.get("secondary_asset_id")
        and shot["secondary_asset_id"] != "presenter-edl"
    ]

    all_non_presenter = asset_ids + secondary_ids
    assert len(all_non_presenter) == len(set(all_non_presenter))


def test_all_configured_presenter_seeks_match_their_timeline() -> None:
    for module_name in (
        "build_0813_backtest_live",
        "build_0813_lotsize_live",
    ):
        build = _module(module_name)

        for start_ms, shot in zip(
            build.BOUNDARIES[:-1],
            build.SHOT_SPECS,
            strict=True,
        ):
            if shot["asset_id"] == "presenter-edl":
                assert shot["source_start_ms"] == start_ms
            if shot.get("secondary_asset_id") == "presenter-edl":
                assert shot["secondary_source_start_ms"] == start_ms
