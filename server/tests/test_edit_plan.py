import statistics

import pytest

from app.editor.planning import (
    build_caption_pages,
    build_edit_plan,
    build_timeline_map,
    classify_sentence,
    choose_style_variant,
    remove_isolated_fillers,
    snap_to_beat_ms,
    _technical_scene_boundaries,
    _technical_visual_for_text,
)
from app.models import EditPlanV1, TranscriptSegment, TranscriptWord, VideoMetadata


def make_segment(words: list[tuple[float, float, str]]) -> TranscriptSegment:
    transcript_words = [
        TranscriptWord(start=start, end=end, text=text, confidence=0.95)
        for start, end, text in words
    ]
    return TranscriptSegment(
        start=transcript_words[0].start,
        end=transcript_words[-1].end,
        text=" ".join(word.text for word in transcript_words),
        words=transcript_words,
    )


def make_acceptance_segment() -> TranscriptSegment:
    text = (
        "Important point hai ye Forex trading robot kya hota hai Ye ek "
        "software hai jo set rules par automatically trade karta hai "
        "Professionally ise Expert Advisor kehte hain short mein EA Lekin "
        "agar rules hi galat hon toh 2008 ke Automated Trading Championship "
        "mein ek Expert Advisor ne 110000 dollars earn kiye then risk ne game "
        "palat diya Jis high risk ne result badhaya wahi baad mein ulta pad "
        "gaya Lesson simple hai Expert Advisor emotion se guide nahi hota par "
        "safe risk khud choose bhi nahi karta Agar aapko live dekhna hai "
        "Telegram group join kar sakte hain"
    )
    words = text.split()
    return make_segment(
        [
            (index * 0.36, index * 0.36 + 0.31, word)
            for index, word in enumerate(words)
        ]
    )


def test_build_timeline_map_trims_edges_and_compresses_long_pauses() -> None:
    segment = make_segment(
        [
            (0.40, 0.70, "This"),
            (1.20, 1.50, "works"),
            (1.55, 1.85, "fast"),
        ]
    )

    timeline = build_timeline_map(
        [segment],
        source_duration_ms=2300,
        max_pause_ms=120,
        kept_pause_ms=60,
    )

    assert len(timeline) == 2
    assert timeline[0].source_start_ms == 320
    assert timeline[0].source_end_ms == 730
    assert timeline[1].source_start_ms == 1170
    assert timeline[1].source_end_ms == 1930
    assert timeline[0].output_start_ms == 0
    assert timeline[1].output_start_ms == timeline[0].output_end_ms
    assert timeline[-1].output_end_ms == 1170


def test_choose_style_variant_uses_topic_signals() -> None:
    assert (
        choose_style_variant("This CPU algorithm fixes a compiler bottleneck")
        == "technical-explanation"
    )
    assert (
        choose_style_variant("Watch me test this new phone app and its camera")
        == "product-demo"
    )
    assert (
        choose_style_variant("This humanoid robot hand is new hardware")
        == "hardware-launch"
    )
    assert (
        choose_style_variant(
            "This Forex trading robot follows risk rules and a strategy"
        )
        == "technical-explanation"
    )


def test_technical_style_uses_reference_aware_qc_pacing() -> None:
    plan = build_edit_plan(
        source_filename="source.mp4",
        metadata=VideoMetadata(
            width=1080,
            height=1920,
            fps=30,
            frame_count=300,
            duration_seconds=10,
        ),
        transcript=[
            make_segment(
                [
                    (0.0, 0.35, "Forex"),
                    (0.4, 0.75, "trading"),
                    (0.8, 1.15, "algorithm"),
                    (1.2, 1.55, "controls"),
                    (1.6, 1.95, "risk"),
                ]
            )
        ],
    )

    assert plan.style_variant == "technical-explanation"
    assert plan.qc_targets.min_cuts_per_minute == 15
    assert plan.qc_targets.max_cuts_per_minute == 50
    assert plan.qc_targets.max_median_shot_ms == 2600


def test_snap_to_beat_ms_aligns_major_visual_events() -> None:
    assert snap_to_beat_ms(1180, bpm=120) == 1000
    assert snap_to_beat_ms(1260, bpm=120) == 1500


def test_classify_sentence_assigns_editorial_roles() -> None:
    assert classify_sentence("Watch how this works", index=0, total=4) == "hook"
    assert (
        classify_sentence("The benchmark data proves it", index=1, total=4)
        == "evidence"
    )
    assert (
        classify_sentence("But unlike the old model, this is faster", index=2, total=4)
        == "contrast"
    )
    assert classify_sentence("Try it now", index=3, total=4) == "cta"


def test_build_caption_pages_uses_clause_aware_short_beats() -> None:
    segment = make_segment(
        [
            (0.00, 0.20, "This"),
            (0.20, 0.45, "AI"),
            (0.45, 0.70, "model"),
            (0.70, 1.00, "changes"),
            (1.00, 1.30, "everything"),
        ]
    )

    pages = build_caption_pages([segment])

    assert [len(page.tokens) for page in pages] == [3, 2]
    assert all(
        token.highlighted is False
        for page in pages
        for token in page.tokens
    )
    assert all(len(page.tokens) <= 3 for page in pages)
    assert all(page.family == "compact-pill" for page in pages)


def test_caption_pages_never_cross_sentence_boundaries() -> None:
    segment = make_segment(
        [
            (0.00, 0.25, "Rules"),
            (0.25, 0.50, "execute."),
            (0.50, 0.75, "Risk"),
            (0.75, 1.00, "changes"),
            (1.00, 1.25, "everything."),
        ]
    )

    pages = build_caption_pages([segment], family="technical-mono")

    assert [" ".join(token.text for token in page.tokens) for page in pages] == [
        "Rules execute.",
        "Risk changes everything.",
    ]
    assert all(page.family == "technical-mono" for page in pages)
    assert all(page.transition == "hard-cut" for page in pages)


def test_caption_pages_keep_names_and_currency_together() -> None:
    segment = make_segment(
        [
            (0.00, 0.25, "An"),
            (0.25, 0.50, "Expert"),
            (0.50, 0.80, "Advisor"),
            (0.80, 1.05, "earned"),
            (1.05, 1.35, "$110,000."),
        ]
    )

    pages = build_caption_pages([segment], family="documentary-clean")
    phrases = [
        " ".join(token.text for token in page.tokens)
        for page in pages
    ]

    assert any("Expert Advisor" in phrase for phrase in phrases)
    assert any("$110,000." in phrase for phrase in phrases)
    assert all(page.family == "documentary-clean" for page in pages)


def test_caption_family_defaults_match_measured_reference_geometry() -> None:
    segment = make_segment(
        [(0.00, 0.40, "IF"), (0.40, 0.80, "STATEMENTS.")]
    )

    page = build_caption_pages(
        [segment],
        family="technical-mono",
    )[0]

    assert page.anchor == "center-74"
    assert page.transition == "hard-cut"
    assert page.max_width == 900


def test_caption_pages_allow_a_four_word_clause_when_grammar_requires() -> None:
    segment = make_segment(
        [
            (0.00, 0.24, "The"),
            (0.24, 0.48, "lesson"),
            (0.48, 0.70, "is"),
            (0.70, 0.96, "simple:"),
            (1.02, 1.28, "risk"),
            (1.28, 1.60, "matters."),
        ]
    )

    phrases = [
        " ".join(token.text for token in page.tokens)
        for page in build_caption_pages(
            [segment],
            family="technical-mono",
        )
    ]

    assert phrases == ["The lesson is simple:", "risk matters."]


def test_edit_plan_preserves_zero_duration_transcript_words() -> None:
    segment = make_segment(
        [
            (0.00, 0.30, "Do"),
            (0.30, 0.30, "you"),
            (0.30, 0.62, "know"),
            (0.62, 0.86, "what"),
        ]
    )
    plan = build_edit_plan(
        source_filename="source.mp4",
        metadata=VideoMetadata(
            width=720,
            height=1280,
            fps=30,
            frame_count=30,
            duration_seconds=1,
        ),
        transcript=[segment],
    )
    tokens = [
        token for page in plan.caption_pages for token in page.tokens
    ]

    assert [token.text for token in tokens] == ["Do", "you", "know", "what"]
    assert all(token.end_ms > token.start_ms for token in tokens)
    assert all(
        left.start_ms <= right.start_ms
        for left, right in zip(tokens, tokens[1:])
    )


def test_generic_metric_visual_does_not_publish_unsourced_numbers() -> None:
    visual = _technical_visual_for_text(
        "an expert advisor earned $110 ,000 dollars",
        "forex trading expert advisor earned $110,000 dollars",
        index=8,
        start_ms=10_000,
        end_ms=11_700,
        previous_kind=None,
    )

    assert visual.kind == "metric-reveal"
    assert visual.value is None
    assert "verified source" in visual.subtitle.lower()


def test_generic_metric_visual_requires_source_even_before_risk_copy() -> None:
    visual = _technical_visual_for_text(
        "$110,000. Then the risk changed the game.",
        "an expert advisor earned $110,000 then risk changed the game",
        index=7,
        start_ms=10_000,
        end_ms=12_400,
        previous_kind=None,
    )

    assert visual.kind == "metric-reveal"
    assert visual.value is None


def test_remove_isolated_fillers_only_drops_confident_standalone_fillers() -> None:
    segment = make_segment(
        [
            (0.00, 0.25, "This"),
            (0.36, 0.50, "um"),
            (0.62, 0.90, "works"),
            (0.94, 1.10, "like"),
            (1.12, 1.40, "magic"),
        ]
    )

    cleaned = remove_isolated_fillers([segment])

    assert [word.text for word in cleaned[0].words] == [
        "This",
        "works",
        "like",
        "magic",
    ]
    assert cleaned[0].text == "This works like magic"


def test_build_edit_plan_produces_valid_autonomous_fallback_edit() -> None:
    transcript = [
        make_segment(
            [
                (0.00, 0.30, "This"),
                (0.30, 0.60, "AI"),
                (0.60, 0.95, "chip"),
                (1.30, 1.65, "runs"),
                (1.65, 2.00, "faster"),
            ]
        )
    ]
    metadata = VideoMetadata(
        width=720,
        height=1280,
        fps=30,
        frame_count=90,
        duration_seconds=3,
    )

    plan = build_edit_plan(
        source_filename="source.mp4",
        metadata=metadata,
        transcript=transcript,
    )

    assert plan.version == "1.0"
    assert plan.profile == "tech-story-v1"
    assert plan.output.width == 1080
    assert plan.output.height == 1920
    assert plan.output.fps == 30
    assert plan.duration_ms == plan.timeline[-1].output_end_ms
    assert plan.style_variant == "technical-explanation"
    assert plan.scenes[0].role == "hook"
    assert plan.scenes[-1].end_ms == plan.duration_ms
    assert plan.caption_pages
    assert plan.qc_targets.integrated_lufs == -14.2
    assert plan.qc_targets.max_silence_ms == 120
    assert plan.qc_targets.max_freeze_frame_ratio == 0.14
    assert any(cue.kind == "headline" for cue in plan.graphics)
    assert all(asset.provenance != "training-video" for asset in plan.assets)


def test_build_edit_plan_selects_semantic_graphic_templates() -> None:
    transcript = [
        make_segment(
            [
                (0.00, 0.25, "Watch"),
                (0.25, 0.50, "this"),
                (0.50, 0.75, "phone"),
                (0.75, 1.00, "app"),
                (1.00, 1.25, "demo"),
                (1.25, 1.50, "now"),
            ]
        )
    ]
    metadata = VideoMetadata(
        width=720,
        height=1280,
        fps=30,
        frame_count=60,
        duration_seconds=2,
    )

    plan = build_edit_plan(
        source_filename="source.mp4",
        metadata=metadata,
        transcript=transcript,
    )

    assert plan.style_variant == "product-demo"
    assert any(cue.kind in {"browser", "phone"} for cue in plan.graphics)


def test_technical_plan_builds_a_semantic_editorial_storyboard() -> None:
    transcript = [make_acceptance_segment()]
    metadata = VideoMetadata(
        width=1080,
        height=1920,
        fps=30,
        frame_count=1242,
        duration_seconds=41.4,
    )

    plan = build_edit_plan(
        source_filename="source.mp4",
        metadata=metadata,
        transcript=transcript,
    )

    visuals = getattr(plan, "editorial_visuals", [])
    visual_kinds = {visual.kind for visual in visuals}
    scene_visual_ids = {
        getattr(scene, "visual_id", None)
        for scene in plan.scenes
        if getattr(scene, "visual_id", None)
    }

    assert plan.style_variant == "technical-explanation"
    assert {
        "trading-chart",
        "rule-flow",
        "code-terminal",
        "evidence-card",
        "metric-reveal",
        "risk-meter",
        "comparison",
        "chat-cta",
    }.issubset(visual_kinds)
    assert scene_visual_ids == {visual.id for visual in visuals}
    assert {"graphic", "split-screen", "presenter-pip"}.issubset(
        {scene.layout for scene in plan.scenes}
    )
    assert all(
        cue.kind == "headline"
        for cue in plan.graphics
    )


def test_technical_storyboard_targets_reference_visual_coverage() -> None:
    from app.editor.pipeline import _calculate_visual_coverage

    plan = build_edit_plan(
        source_filename="source.mp4",
        metadata=VideoMetadata(
            width=1080,
            height=1920,
            fps=30,
            frame_count=1242,
            duration_seconds=41.4,
        ),
        transcript=[make_acceptance_segment()],
    )

    coverage = _calculate_visual_coverage(plan)

    assert 0.55 <= coverage <= 0.8


def test_trading_storyboard_avoids_adjacent_duplicate_templates() -> None:
    text = (
        "Do know what Forex Trading Robot is It is a software that "
        "automatically trades Professionally it called Expert Advisor In "
        "short EA But if the rules are wrong in 2008 automated trading "
        "championship an expert advisor earned 110000 dollars Then the risk "
        "turned the game The high risk increased the result and then it "
        "upside down Lesson is simple an expert advisor does not emotions "
        "but does not safe risk If you want to an expert advisor trades then "
        "you can follow us and join our telegram group Thank you"
    )
    words = text.split()
    plan = build_edit_plan(
        source_filename="source.mp4",
        metadata=VideoMetadata(
            width=1080,
            height=1920,
            fps=30,
            frame_count=1200,
            duration_seconds=40,
        ),
        transcript=[
            make_segment(
                [
                    (index * 0.4, index * 0.4 + 0.34, word)
                    for index, word in enumerate(words)
                ]
            )
        ],
    )
    visual_by_id = {
        visual.id: visual.kind for visual in plan.editorial_visuals
    }
    scene_kinds = [
        visual_by_id.get(scene.visual_id)
        for scene in plan.scenes
    ]
    first_visual = next(kind for kind in scene_kinds if kind is not None)

    assert first_visual == "trading-chart"
    assert all(
        left is None or right is None or left != right
        for left, right in zip(scene_kinds, scene_kinds[1:])
    )


def test_technical_scene_boundaries_do_not_create_tail_flashes() -> None:
    boundaries = _technical_scene_boundaries(35_080)
    durations = [
        end - start
        for start, end in zip(boundaries, boundaries[1:])
    ]

    assert durations[-1] == 700
    assert min(durations[:-1]) >= 800


def test_technical_scene_boundaries_match_slower_reference_pacing() -> None:
    pages = build_caption_pages([make_acceptance_segment()])
    boundaries = _technical_scene_boundaries(35_080, pages)
    durations = [
        end - start
        for start, end in zip(boundaries, boundaries[1:])
    ]

    assert 13 <= len(durations) <= 16
    assert statistics.median(durations[:-1]) >= 2000


def test_technical_scene_boundaries_align_to_spoken_word_onsets() -> None:
    segment = make_segment(
        [
            (index * 0.31, index * 0.31 + 0.24, f"word{index}")
            for index in range(32)
        ]
    )
    pages = build_caption_pages([segment])
    boundaries = _technical_scene_boundaries(10_000, pages)
    word_starts = {
        token.start_ms for page in pages for token in page.tokens
    }

    assert boundaries[1:-2]
    assert all(
        boundary in word_starts
        for boundary in boundaries[1:-2]
    )


def test_graphic_windows_do_not_overlap_and_leave_a_clean_ending() -> None:
    transcript = [
        make_segment(
            [
                (index * 0.28, index * 0.28 + 0.24, word)
                for index, word in enumerate(
                    [
                        "This",
                        "new",
                        "AI",
                        "product",
                        "changes",
                        "how",
                        "the",
                        "app",
                        "works",
                        "today",
                        "for",
                        "everyone",
                    ]
                )
            ]
        )
    ]
    metadata = VideoMetadata(
        width=720,
        height=1280,
        fps=30,
        frame_count=120,
        duration_seconds=4,
    )

    plan = build_edit_plan(
        source_filename="source.mp4",
        metadata=metadata,
        transcript=transcript,
    )
    hook = next(cue for cue in plan.graphics if cue.kind == "headline")
    template = next(
        cue for cue in plan.graphics if cue.id == "graphic-template"
    )

    assert hook.end_ms <= template.start_ms
    assert template.end_ms <= plan.duration_ms - 400


def test_edit_plan_rejects_noncontiguous_output_timeline() -> None:
    transcript = [
        make_segment(
            [
                (0.00, 0.25, "This"),
                (0.25, 0.50, "works"),
                (1.20, 1.45, "very"),
                (1.45, 1.70, "well"),
            ]
        )
    ]
    metadata = VideoMetadata(
        width=720,
        height=1280,
        fps=30,
        frame_count=90,
        duration_seconds=3,
    )
    payload = build_edit_plan(
        source_filename="source.mp4",
        metadata=metadata,
        transcript=transcript,
    ).model_dump(mode="json")
    payload["timeline"][1]["output_start_ms"] += 1
    payload["timeline"][1]["output_end_ms"] += 1
    payload["duration_ms"] += 1

    with pytest.raises(ValueError, match="contiguous"):
        EditPlanV1.model_validate(payload)


def test_edit_plan_rejects_layers_outside_output_duration() -> None:
    transcript = [make_segment([(0.00, 0.30, "AI"), (0.30, 0.60, "works")])]
    metadata = VideoMetadata(
        width=720,
        height=1280,
        fps=30,
        frame_count=60,
        duration_seconds=2,
    )
    payload = build_edit_plan(
        source_filename="source.mp4",
        metadata=metadata,
        transcript=transcript,
    ).model_dump(mode="json")
    payload["scenes"][0]["end_ms"] = payload["duration_ms"] + 1

    with pytest.raises(ValueError, match="output duration"):
        EditPlanV1.model_validate(payload)


def test_edit_plan_rejects_training_media_assets() -> None:
    transcript = [make_segment([(0.00, 0.30, "AI"), (0.30, 0.60, "works")])]
    metadata = VideoMetadata(
        width=720,
        height=1280,
        fps=30,
        frame_count=60,
        duration_seconds=2,
    )
    payload = build_edit_plan(
        source_filename="source.mp4",
        metadata=metadata,
        transcript=transcript,
    ).model_dump(mode="json")
    payload["assets"] = [
        {
            "id": "forbidden-reference",
            "kind": "video",
            "path": "C:/training videos data/reference.mp4",
            "keywords": ["reference"],
            "provenance": "training-video",
            "license": None,
            "start_ms": 0,
            "end_ms": min(500, payload["duration_ms"]),
        }
    ]

    with pytest.raises(ValueError, match="Training-video"):
        EditPlanV1.model_validate(payload)


def test_edit_plan_rejects_out_of_range_word_confidence() -> None:
    transcript = [make_segment([(0.00, 0.30, "AI"), (0.30, 0.60, "works")])]
    metadata = VideoMetadata(
        width=720,
        height=1280,
        fps=30,
        frame_count=60,
        duration_seconds=2,
    )
    payload = build_edit_plan(
        source_filename="source.mp4",
        metadata=metadata,
        transcript=transcript,
    ).model_dump(mode="json")
    payload["caption_pages"][0]["tokens"][0]["confidence"] = 1.1

    with pytest.raises(ValueError, match="less than or equal to 1"):
        EditPlanV1.model_validate(payload)
