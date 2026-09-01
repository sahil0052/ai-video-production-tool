from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np
import pytest

from app import models
from app.editor import reference_production
from app.editor.reference_production import (
    _0806_CORRECTED_TEXTS,
    _build_0806_caption_pages,
    _build_0806_storyboard,
    _build_0806_v3_storyboard,
)
from app.models import (
    ArtifactSpec,
    AudioPlan,
    CaptionPage,
    CaptionToken,
    EvidenceItem,
    ShotSpec,
    SfxCue,
    TranscriptSegment,
    TranscriptWord,
    VisualReview,
    VisualReviewCheck,
)

_0806_TIMES = [
    (0.000, 2.340),
    (2.800, 6.820),
    (7.200, 9.020),
    (9.560, 10.700),
    (12.060, 14.160),
    (14.480, 17.460),
    (17.920, 21.140),
    (21.820, 23.140),
    (24.000, 25.520),
    (26.080, 27.780),
    (27.780, 32.200),
    (33.180, 41.000),
]


def _make_0806_segments() -> list[TranscriptSegment]:
    segments: list[TranscriptSegment] = []
    for text, (start, end) in zip(
        _0806_CORRECTED_TEXTS,
        _0806_TIMES,
        strict=True,
    ):
        tokens = text.split()
        step = (end - start) / len(tokens)
        words = [
            TranscriptWord(
                start=start + index * step,
                end=end if index == len(tokens) - 1 else start + (index + 1) * step,
                text=token,
                confidence=0.99,
            )
            for index, token in enumerate(tokens)
        ]
        segments.append(
            TranscriptSegment(
                start=start,
                end=end,
                text=text,
                words=words,
            )
        )
    return segments


def _write_v3_inputs(tmp_path: Path) -> None:
    import json

    licensed_dir = tmp_path / "licensed-footage"
    licensed_dir.mkdir()
    licensed_entries = []
    for asset_id, filename, source_url in [
        (
            "coverr-coding-developer-7198",
            "coverr-coding-developer-7198.mp4",
            "https://coverr.co/videos/coding-developer-qll3taz5b8",
        ),
        (
            "coverr-developing-coding-sequences-3909",
            "coverr-developing-coding-sequences-3909.mp4",
            "https://coverr.co/videos/developing-coding-sequences-q4fzzdpkhm",
        ),
        (
            "coverr-casual-man-typing-9754",
            "coverr-casual-man-typing-9754.mp4",
            "https://coverr.co/videos/a-casual-man-typing-on-a-laptop-sfb68xu9jv",
        ),
        (
            "coverr-guy-working-pc-18",
            "coverr-guy-working-pc-18.mp4",
            "https://coverr.co/videos/a-guy-working-on-a-pc-4twpodmgbs",
        ),
    ]:
        (licensed_dir / filename).write_bytes(b"licensed-video")
        licensed_entries.append(
            {
                "id": asset_id,
                "kind": "video",
                "path": f"licensed-footage/{filename}",
                "provider": "Coverr",
                "creator": "Coverr",
                "source_url": source_url,
                "license": "Coverr free stock video license",
                "license_url": "https://coverr.co/license",
                "remote_id": asset_id.rsplit("-", 1)[-1],
                "search_query": "programming computer workstation",
            }
        )
    (licensed_dir / "manifest.json").write_text(
        json.dumps({"entries": licensed_entries}),
        encoding="utf-8",
    )

    recordings = tmp_path / "screen-recordings"
    recordings.mkdir()
    capture_ids = [
        "capture-mt5-hook-action",
        "capture-metaeditor-code-macro",
        "capture-metaeditor-rule-highlight",
        "capture-mt5-navigator-ea",
        "capture-mt5-risk-inputs",
        "capture-mt5-risk-alternate",
        "capture-metaeditor-risk-code",
        "capture-mt5-attach-ea",
        "capture-mt5-strategy-tester",
    ]
    capture_entries = []
    for capture_id in capture_ids:
        filename = f"{capture_id}.mp4"
        (recordings / filename).write_bytes(b"capture")
        capture_entries.append(
            {
                "id": capture_id,
                "path": f"screen-recordings/{filename}",
                "source_kind": "screen-recording",
                "application": "MetaTrader 5",
                "width": 1920,
                "height": 1080,
                "fps": 60,
                "codec": "h264",
                "checksum_sha256": "a" * 64,
                "captured_at": "2026-08-08T00:00:00Z",
                "privacy_reviewed": True,
                "privacy_notes": "Safe disposable demo capture.",
            }
        )
    (tmp_path / "capture-manifest.json").write_text(
        json.dumps(
            {
                "profile": "local-metatrader",
                "recorder": "OBS Studio",
                "entries": capture_entries,
            }
        ),
        encoding="utf-8",
    )

    captures = tmp_path / "source-captures"
    captures.mkdir()
    for filename in [
        "metatrader5-automated-trading-definition.png",
        "metatrader4-expert-advisor-definition.png",
        "metatrader5-atc-history.png",
        "mql5-atc-2008-risk.png",
    ]:
        (captures / filename).write_bytes(b"capture-png")


def test_0806_corrected_transcript_is_verbatim_not_grammar_rewritten() -> None:
    assert _0806_CORRECTED_TEXTS[0] == (
        "Do you know what Forex Trading Robot is?"
    )
    assert _0806_CORRECTED_TEXTS[1] == (
        "It is a software that automatically trades on set rules."
    )
    assert _0806_CORRECTED_TEXTS[2] == (
        "Professionally, it is called Expert Advisor."
    )
    assert _0806_CORRECTED_TEXTS[4] == "But if the rules are wrong,"
    assert _0806_CORRECTED_TEXTS[10].startswith("Lesson is simple,")


def test_evidence_contract_requires_https_and_capture_provenance() -> None:
    item = EvidenceItem(
        id="mql5-2008-results",
        claim="The 2008 championship winner finished at $169,585.",
        source_title="Automated Trading Championship 2008: Results",
        source_url="https://www.mql5.com/en/articles/1376",
        source_type="primary",
        capture_path="source-captures/mql5-2008-results.png",
        accessed_at=datetime(2026, 8, 8, tzinfo=UTC),
        status="verified",
    )

    assert item.status == "verified"
    assert item.source_type == "primary"

    invalid = item.model_dump(mode="json")
    invalid["source_url"] = "http://example.com"
    with pytest.raises(ValueError, match="HTTPS"):
        EvidenceItem.model_validate(invalid)


def test_storyboard_and_review_contracts_track_evidence_gates() -> None:
    artifact = ArtifactSpec(
        id="rule-engine-diagram",
        kind="diagram",
        path="artifacts/rule-engine.svg",
        provenance="generated-from-verified-facts",
        evidence_ids=["mql5-ea-definition"],
        illustrative=False,
    )
    shot = ShotSpec(
        id="shot-03",
        start_ms=4800,
        end_ms=8200,
        role="explanation",
        layout="graphic",
        treatment="rule-engine-diagram",
        caption_family="technical-mono",
        evidence_ids=["mql5-ea-definition"],
        artifact_ids=[artifact.id],
    )
    review = VisualReview(
        passed=True,
        checks=[
            VisualReviewCheck(
                name="unsupported-visible-facts",
                passed=True,
                detail="No unsupported numbers are visible.",
            )
        ],
        caption_family_stills=["review/technical-mono.png"],
        sourced_evidence_beats=4,
        unique_visual_treatments=6,
        unsupported_visible_facts=[],
    )

    assert shot.end_ms > shot.start_ms
    assert shot.caption_family == "technical-mono"
    assert review.passed is True


def test_shot_contract_tracks_real_source_kind_and_reference_role() -> None:
    assert {"source_kind", "reference_role"}.issubset(ShotSpec.model_fields)

    shot = ShotSpec(
        id="shot-real-code",
        start_ms=2800,
        end_ms=4100,
        role="demonstration",
        layout="asset-full",
        treatment="real-metaeditor-code",
        caption_family="technical-mono",
        source_kind="screen-recording",
        reference_role="primary-10",
        asset_id="capture-metaeditor-code",
    )

    assert shot.source_kind == "screen-recording"
    assert shot.reference_role == "primary-10"


def test_audio_contract_tracks_gain_automation_and_speech_protection() -> None:
    assert {
        "dialogue_asset_id",
        "dialogue_offset_ms",
        "music_base_gain_db",
        "music_gain_automation",
        "speech_protection_windows",
    }.issubset(AudioPlan.model_fields)
    assert {"duration_ms", "gain_db"}.issubset(SfxCue.model_fields)


def test_reference_audio_build_extracts_voice_and_uses_aligned_speech(
    tmp_path,
) -> None:
    builder = getattr(reference_production, "_build_reference_audio", None)
    assert builder is not None
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    commands: list[list[str]] = []

    def command_runner(command: list[str], _cwd: Path) -> None:
        commands.append(command)
        Path(command[-1]).write_bytes(b"wav")

    assets, audio = builder(
        source=source,
        output_dir=tmp_path,
        duration_ms=3000,
        speech_segments=[
            TranscriptSegment(
                start=0.2,
                end=1.2,
                text="Do you know",
                words=[
                    TranscriptWord(start=0.2, end=0.38, text="Do"),
                    TranscriptWord(start=0.48, end=0.67, text="you"),
                    TranscriptWord(start=0.82, end=1.12, text="know"),
                ],
            )
        ],
        emphasis_times_ms=[0, 2000],
        command_runner=command_runner,
    )

    by_id = {asset.id: asset for asset in assets}
    assert {
        "dialogue-original",
        "dialogue-processed",
        "generated-music",
    }.issubset(by_id)
    assert audio.dialogue_asset_id == "dialogue-processed"
    assert audio.dialogue_offset_ms == -70
    assert audio.music_gain_automation
    assert audio.speech_protection_windows
    assert len(commands) == 2
    assert "-af" not in commands[0]
    assert "afftdn" in commands[1][commands[1].index("-af") + 1]


def test_capture_manifest_requires_safe_real_capture_provenance() -> None:
    CaptureManifest = getattr(models, "CaptureManifest", None)
    CaptureManifestEntry = getattr(models, "CaptureManifestEntry", None)
    assert CaptureManifest is not None
    assert CaptureManifestEntry is not None
    entry = CaptureManifestEntry(
        id="capture-metaeditor-code",
        path="screen-recordings/metaeditor-code.mp4",
        source_kind="screen-recording",
        application="MetaEditor 5",
        width=1920,
        height=1080,
        fps=60,
        codec="h264_nvenc",
        checksum_sha256="a" * 64,
        captured_at=datetime(2026, 8, 8, tzinfo=UTC),
        privacy_reviewed=True,
        privacy_notes="No account identifiers, balances, or results visible.",
    )
    manifest = CaptureManifest(
        profile="local-metatrader",
        recorder="OBS Studio",
        entries=[entry],
    )

    assert manifest.entries[0].privacy_reviewed is True
    assert manifest.entries[0].width == 1920
    assert manifest.entries[0].fps == 60


def test_reference_caption_validation_rejects_short_pages_and_zero_tokens() -> None:
    validator = getattr(
        reference_production,
        "_validate_reference_caption_pages",
        None,
    )
    assert validator is not None

    short_page = CaptionPage(
        start_ms=0,
        end_ms=349,
        tokens=[
            CaptionToken(
                text="DO",
                start_ms=0,
                end_ms=200,
                highlighted=False,
                confidence=0.99,
            )
        ],
        family="technical-mono",
        anchor="center-74",
        transition="hard-cut",
        max_width=900,
    )
    with pytest.raises(ValueError, match="350"):
        validator([short_page])

    zero_token = CaptionPage(
        start_ms=100,
        end_ms=500,
        tokens=[
            CaptionToken(
                text="YOU",
                start_ms=200,
                end_ms=200,
                highlighted=False,
                confidence=0.99,
            )
        ],
        family="technical-mono",
        anchor="center-74",
        transition="hard-cut",
        max_width=900,
    )
    with pytest.raises(ValueError, match="positive duration"):
        validator([zero_token])


def test_reference_caption_validation_rejects_overlaps_and_invisible_tokens() -> None:
    validator = getattr(
        reference_production,
        "_validate_reference_caption_pages",
        None,
    )
    assert validator is not None

    overlapping = [
        CaptionPage(
            start_ms=0,
            end_ms=500,
            tokens=[
                CaptionToken(
                    text="FIRST",
                    start_ms=0,
                    end_ms=300,
                    highlighted=False,
                    confidence=0.99,
                )
            ],
            family="technical-mono",
            anchor="center-74",
            transition="hard-cut",
            max_width=900,
        ),
        CaptionPage(
            start_ms=400,
            end_ms=800,
            tokens=[
                CaptionToken(
                    text="SECOND",
                    start_ms=450,
                    end_ms=700,
                    highlighted=False,
                    confidence=0.99,
                )
            ],
            family="technical-mono",
            anchor="center-74",
            transition="hard-cut",
            max_width=900,
        ),
    ]
    with pytest.raises(ValueError, match="overlap"):
        validator(overlapping)

    invisible_token = CaptionPage(
        start_ms=1000,
        end_ms=1400,
        tokens=[
            CaptionToken(
                text="MISSED",
                start_ms=1500,
                end_ms=1700,
                highlighted=False,
                confidence=0.99,
            )
        ],
        family="technical-mono",
        anchor="center-74",
        transition="hard-cut",
        max_width=900,
    )
    with pytest.raises(ValueError, match="intersect"):
        validator([invisible_token])


def test_visual_review_separates_automation_from_human_release() -> None:
    assert {"automated_pass", "human_approved"}.issubset(
        VisualReview.model_fields
    )
    review = VisualReview(
        passed=False,
        automated_pass=True,
        human_approved=False,
        checks=[
            VisualReviewCheck(
                name="rendered-pixel-gates",
                passed=True,
                detail="All automated pixel gates passed.",
            )
        ],
        caption_family_stills=[],
        sourced_evidence_beats=4,
        unique_visual_treatments=6,
        unsupported_visible_facts=[],
    )

    assert review.automated_pass is True
    assert review.human_approved is False
    assert review.passed is False


def test_rendered_cut_onset_check_enforces_production_target() -> None:
    build_check = getattr(
        reference_production,
        "_build_rendered_cut_onset_check",
        None,
    )
    assert build_check is not None

    failed = build_check(measured_percent=69.23, target_percent=70)
    passed = build_check(measured_percent=76.92, target_percent=70)

    assert failed.passed is False
    assert passed.passed is True
    assert failed.name == "cut-onset-alignment"


def test_rendered_pacing_summary_uses_all_frame_audit_cuts() -> None:
    builder = getattr(
        reference_production,
        "_build_rendered_pacing_summary",
        None,
    )
    assert builder is not None

    summary = builder(
        frame_metrics={
            "cut_timestamps_seconds": [1.25, 2.5, 5.0],
            "median_shot_ms": 1400,
        },
        duration_seconds=30,
    )

    assert summary == {
        "actual_cut_timestamps": [1.25, 2.5, 5.0],
        "actual_cuts_per_minute": 6.0,
        "median_shot_ms": 1400,
    }


def test_reference_caption_structure_allows_grammar_bound_four_word_phrases() -> None:
    checker = getattr(
        reference_production,
        "_reference_caption_structure_ok",
        None,
    )
    assert checker is not None
    segments = [
        TranscriptSegment(
            start=0,
            end=1,
            text="trades on set rules.",
            words=[
                TranscriptWord(
                    start=index * 0.2,
                    end=(index + 1) * 0.2,
                    text=text,
                )
                for index, text in enumerate(
                    ["trades", "on", "set", "rules."]
                )
            ],
        ),
        TranscriptSegment(
            start=1.4,
            end=2,
            text="Next sentence.",
            words=[
                TranscriptWord(start=1.4, end=1.6, text="Next"),
                TranscriptWord(start=1.6, end=2, text="sentence."),
            ],
        ),
    ]
    page = CaptionPage(
        start_ms=0,
        end_ms=1200,
        tokens=[
            CaptionToken(
                text=word.text,
                start_ms=round(word.start * 1000),
                end_ms=round(word.end * 1000),
                highlighted=False,
                confidence=0.99,
            )
            for word in segments[0].words
        ],
        family="technical-mono",
        anchor="center-74",
        transition="hard-cut",
        max_width=900,
    )

    assert checker([page], segments, duration_ms=2000) is True
    disallowed = page.model_copy(
        update={
            "tokens": [
                token.model_copy(update={"text": text})
                for token, text in zip(
                    page.tokens,
                    ["random", "four", "word", "caption"],
                    strict=True,
                )
            ]
        }
    )
    assert checker([disallowed], segments, duration_ms=2000) is False


def test_reference_caption_structure_assigns_shared_boundary_to_next_sentence() -> None:
    checker = getattr(
        reference_production,
        "_reference_caption_structure_ok",
        None,
    )
    assert checker is not None
    segments = [
        TranscriptSegment(
            start=0,
            end=1,
            text="First.",
            words=[
                TranscriptWord(start=0, end=1, text="First."),
            ],
        ),
        TranscriptSegment(
            start=1,
            end=2,
            text="Next sentence.",
            words=[
                TranscriptWord(start=1, end=1.4, text="Next"),
                TranscriptWord(start=1.4, end=2, text="sentence."),
            ],
        ),
    ]
    page = CaptionPage(
        start_ms=1000,
        end_ms=1600,
        tokens=[
            CaptionToken(
                text="Next",
                start_ms=1000,
                end_ms=1400,
                highlighted=False,
                confidence=0.99,
            )
        ],
        family="technical-mono",
        anchor="center-74",
        transition="hard-cut",
        max_width=900,
    )

    assert checker([page], segments, duration_ms=2000) is True


def test_0806_automation_risk_scene_uses_collision_safe_layout(
    tmp_path,
) -> None:
    segments = [
        TranscriptSegment(
            start=index * 2,
            end=index * 2 + 1.8,
            text=f"Segment {index}",
            words=[
                TranscriptWord(
                    start=index * 2 + 0.1,
                    end=index * 2 + 0.5,
                    text=f"Segment{index}",
                    confidence=0.99,
                )
            ],
        )
        for index in range(11)
    ]
    segments.append(
        TranscriptSegment(
            start=22,
            end=23.9,
            text="If then join Thank",
            words=[
                TranscriptWord(
                    start=start,
                    end=start + 0.2,
                    text=text,
                    confidence=0.99,
                )
                for text, start in [
                    ("If", 22.1),
                    ("then", 22.5),
                    ("join", 23.0),
                    ("Thank", 23.5),
                ]
            ],
        )
    )

    _scenes, shots, _assets, _graphics = _build_0806_storyboard(
        retimed_segments=segments,
        duration_ms=24_000,
        output_dir=tmp_path,
    )

    shot = next(
        item for item in shots if item.treatment == "automation-vs-risk"
    )
    assert shot.layout == "asset-full"


def test_0806_timeline_preserves_the_complete_source_duration() -> None:
    builder = getattr(reference_production, "_build_0806_timeline", None)
    assert builder is not None
    timeline = builder(41_401)

    assert len(timeline) == 1
    assert timeline[0].model_dump() == {
        "source_start_ms": 0,
        "source_end_ms": 41_401,
        "output_start_ms": 0,
        "output_end_ms": 41_401,
    }


def test_0806_storyboard_matches_the_locked_reference_structure(
    tmp_path,
) -> None:
    scenes, shots, assets, _graphics = _build_0806_storyboard(
        retimed_segments=_make_0806_segments(),
        duration_ms=41_401,
        output_dir=tmp_path,
    )

    assert scenes[0].start_ms == 0
    assert scenes[-1].end_ms == 41_401
    assert all(
        left.end_ms == right.start_ms
        for left, right in zip(scenes, scenes[1:])
    )

    by_treatment = {
        getattr(scene, "treatment", None): scene
        for scene in scenes
    }
    assert {
        "0806-split-hook",
        "0806-wrong-rule-flow",
        "0806-championship-evidence",
        "0806-mql5-evidence",
        "0806-demo-cta",
        "0806-presenter-ending",
    }.issubset(by_treatment)
    assert (
        by_treatment["0806-split-hook"].start_ms,
        by_treatment["0806-split-hook"].end_ms,
    ) == (0, 2_340)
    assert (
        by_treatment["0806-wrong-rule-flow"].start_ms,
        by_treatment["0806-wrong-rule-flow"].end_ms,
    ) == (12_060, 14_160)
    assert (
        by_treatment["0806-championship-evidence"].start_ms,
        by_treatment["0806-championship-evidence"].end_ms,
    ) == (14_480, 17_460)
    assert (
        by_treatment["0806-mql5-evidence"].start_ms,
        by_treatment["0806-mql5-evidence"].end_ms,
    ) == (17_920, 21_140)
    assert (
        by_treatment["0806-demo-cta"].start_ms,
        by_treatment["0806-demo-cta"].end_ms,
    ) == (33_180, 37_160)
    assert (
        by_treatment["0806-presenter-ending"].start_ms,
        by_treatment["0806-presenter-ending"].end_ms,
    ) == (37_160, 41_000)

    presenter_ms = sum(
        scene.end_ms - scene.start_ms
        for scene in scenes
        if scene.layout in {"presenter", "split-screen", "presenter-pip"}
    )
    presenter_ratio = presenter_ms / 41_401
    assert 0.14 <= presenter_ratio <= 0.20

    moving_ms = sum(
        scene.end_ms - scene.start_ms
        for scene in scenes
        if getattr(scene, "motion", "static") != "static"
    )
    assert moving_ms / 41_401 >= 0.60

    assert len({shot.treatment for shot in shots}) >= 6
    assert all("source-card" not in asset.path for asset in assets)
    direct_captures = [
        asset
        for asset in assets
        if asset.provenance == "official-source-capture"
    ]
    assert len({asset.id for asset in direct_captures}) >= 4
    assert all(Path(asset.path).suffix.lower() == ".png" for asset in direct_captures)


def test_0806_storyboard_uses_aligned_narration_boundaries(
    tmp_path,
) -> None:
    segments = _make_0806_segments()
    shift_seconds = 0.2
    championship = segments[5]
    segments[5] = championship.model_copy(
        update={
            "start": championship.start + shift_seconds,
            "end": championship.end + shift_seconds,
            "words": [
                word.model_copy(
                    update={
                        "start": word.start + shift_seconds,
                        "end": word.end + shift_seconds,
                    }
                )
                for word in championship.words
            ],
        }
    )

    _scenes, shots, _assets, _graphics = _build_0806_storyboard(
        retimed_segments=segments,
        duration_ms=41_401,
        output_dir=tmp_path,
    )

    evidence_shot = next(
        shot
        for shot in shots
        if shot.treatment == "0806-championship-evidence"
    )
    assert evidence_shot.start_ms == 14_680


def test_0806_storyboard_uses_real_capture_sources_when_manifest_exists(
    tmp_path,
) -> None:
    recording_dir = tmp_path / "screen-recordings"
    recording_dir.mkdir()
    capture_ids = [
        "capture-mt5-hook-action",
        "capture-metaeditor-open",
        "capture-metaeditor-code-macro",
        "capture-metaeditor-rule-highlight",
        "capture-mt5-navigator-ea",
        "capture-mt5-risk-inputs",
        "capture-mt5-risk-alternate",
        "capture-metaeditor-risk-code",
        "capture-mt5-attach-ea",
        "capture-mt5-strategy-tester",
    ]
    entries = []
    for capture_id in capture_ids:
        filename = f"{capture_id}.mp4"
        (recording_dir / filename).write_bytes(b"capture")
        entries.append(
            {
                "id": capture_id,
                "path": f"screen-recordings/{filename}",
                "source_kind": "screen-recording",
                "application": "MetaTrader 5",
                "width": 1920,
                "height": 1080,
                "fps": 60,
                "codec": "h264_nvenc",
                "checksum_sha256": "b" * 64,
                "captured_at": "2026-08-08T00:00:00Z",
                "privacy_reviewed": True,
                "privacy_notes": "Safe demo capture.",
            }
        )
    (tmp_path / "capture-manifest.json").write_text(
        __import__("json").dumps(
            {
                "profile": "local-metatrader",
                "recorder": "OBS Studio",
                "entries": entries,
            }
        ),
        encoding="utf-8",
    )

    _scenes, shots, assets, _graphics = _build_0806_storyboard(
        retimed_segments=_make_0806_segments(),
        duration_ms=41_401,
        output_dir=tmp_path,
    )
    audit = __import__(
        "app.editor.production_audit",
        fromlist=["calculate_source_coverage"],
    )
    coverage = audit.calculate_source_coverage(
        shots,
        duration_ms=41_401,
    )

    assert 20 <= len(shots) <= 22
    assert coverage["real_source_ratio"] >= 0.65
    assert coverage["procedural_ratio"] <= 0.25
    assert coverage["visual_source_count"] >= 6
    assert len(
        {
            asset.id
            for asset in assets
            if asset.kind == "video"
            and asset.provenance == "local-safe-demo-capture"
        }
    ) >= 8


def test_0806_v3_storyboard_matches_the_visual_language_audit(
    tmp_path,
) -> None:
    _write_v3_inputs(tmp_path)

    scenes, shots, assets, _graphics = _build_0806_v3_storyboard(
        retimed_segments=_make_0806_segments(),
        duration_ms=41_401,
        output_dir=tmp_path,
    )
    audit = __import__(
        "app.editor.production_audit",
        fromlist=[
            "calculate_visual_language_distribution",
            "evaluate_reference_max_visual_language",
        ],
    )
    distribution = audit.calculate_visual_language_distribution(
        shots,
        duration_ms=41_401,
    )
    evaluation = audit.evaluate_reference_max_visual_language(distribution)

    assert scenes[0].start_ms == 0
    assert scenes[-1].end_ms == 41_401
    assert all(
        left.end_ms == right.start_ms
        for left, right in zip(scenes, scenes[1:])
    )
    assert 26 <= len(shots) <= 30
    assert evaluation["automated_pass"] is True
    assert distribution["ratios"]["literal-desktop-ui"] < 0.20
    assert 0.25 <= distribution["ratios"]["designed-explanation"] <= 0.45
    assert 0.15 <= distribution["ratios"]["cinematic-broll"] <= 0.30
    assert 0.15 <= distribution["ratios"]["edited-evidence"] <= 0.20
    assert all(shot.primary_subject for shot in shots)
    assert all(
        shot.simultaneous_actions <= 1
        for shot in shots
        if shot.visual_category in {
            "literal-desktop-ui",
            "product-macro",
        }
    )
    assert any(
        asset.provenance == "internet:coverr-free-video"
        for asset in assets
    )
    assert any(
        shot.reference_role == "supporting"
        and shot.role == "demonstration"
        for shot in shots
    )
    shots_by_treatment = {shot.treatment: shot for shot in shots}
    assert (
        shots_by_treatment["0806-v3-code-cinematic"].asset_id
        == "coverr-casual-man-typing-9754"
    )
    assert (
        shots_by_treatment["0806-v3-lesson-contrast"].asset_id
        == "coverr-casual-man-typing-9754"
    )
    assert (
        shots_by_treatment["0806-v3-lesson-contrast"].visual_category
        == "cinematic-broll"
    )
    assert (
        shots_by_treatment["0806-v3-demo-input"].asset_id
        == "capture-mt5-risk-inputs"
    )
    assert (
        shots_by_treatment["0806-v3-demo-strategy"].asset_id
        == "capture-mt5-strategy-tester"
    )
    assert (
        shots_by_treatment["0806-v3-demo-input"].visual_category
        == "product-macro"
    )
    assert (
        shots_by_treatment["0806-v3-demo-strategy"].visual_category
        == "product-macro"
    )


def test_0806_v3_risk_control_starts_in_the_clean_narration_pause(
    tmp_path,
) -> None:
    _write_v3_inputs(tmp_path)

    _scenes, shots, _assets, _graphics = _build_0806_v3_storyboard(
        retimed_segments=_make_0806_segments(),
        duration_ms=41_401,
        output_dir=tmp_path,
    )
    shots_by_treatment = {shot.treatment: shot for shot in shots}

    assert shots_by_treatment["0806-v3-risk-turn"].end_ms == 21_550
    assert shots_by_treatment["0806-v3-risk-control"].start_ms == 21_550

    emphasis_times = getattr(
        reference_production,
        "_0806_EMPHASIS_TIMES_MS",
        (),
    )
    assert 21_550 in emphasis_times
    assert 21_820 not in emphasis_times


def test_0806_v3_demo_establishing_starts_on_the_clean_audio_onset(
    tmp_path,
) -> None:
    _write_v3_inputs(tmp_path)

    _scenes, shots, _assets, _graphics = _build_0806_v3_storyboard(
        retimed_segments=_make_0806_segments(),
        duration_ms=41_401,
        output_dir=tmp_path,
    )
    shots_by_treatment = {shot.treatment: shot for shot in shots}

    assert shots_by_treatment["0806-v3-lesson-pipeline"].end_ms == 32_320
    assert shots_by_treatment["0806-v3-demo-establishing"].start_ms == 32_320


def test_0806_caption_pages_use_original_timing_and_short_phrases() -> None:
    segments = _make_0806_segments()
    pages = _build_0806_caption_pages(segments)

    assert pages
    assert max(len(page.tokens) for page in pages) <= 4
    four_word_phrases = {
        " ".join(token.text for token in page.tokens)
        for page in pages
        if len(page.tokens) == 4
    }
    assert four_word_phrases <= {
        "Do you know what",
        "trades on set rules.",
        "doesn't trade with emotions,",
    }
    assert (
        sum(page.family == "technical-mono" for page in pages)
        / len(pages)
        > 0.60
    )
    assert all(page.transition == "hard-cut" for page in pages[:-9])

    source_timings = {
        (word.text, round(word.start * 1000), round(word.end * 1000))
        for segment in segments
        for word in segment.words
    }
    assert all(
        (token.text, token.start_ms, token.end_ms) in source_timings
        for page in pages
        for token in page.tokens
    )

    phrases = [
        " ".join(token.text for token in page.tokens)
        for page in pages
    ]
    assert "SHORT, EA. BUT" not in phrases
    assert "SAFE RISK. IF" not in phrases
    assert "GROUP. THANK YOU!" not in phrases
    assert "what Forex" not in phrases
    assert "to see how an" not in phrases
    assert "Forex Trading Robot" in phrases
    assert "an Expert Advisor" in phrases


def test_0806_caption_pages_meet_reference_hold_and_token_invariants() -> None:
    pages = _build_0806_caption_pages(_make_0806_segments())

    assert all(
        350 <= page.end_ms - page.start_ms <= 1300
        for page in pages
    )
    assert all(
        token.end_ms > token.start_ms
        for page in pages
        for token in page.tokens
    )


def test_0806_caption_pages_do_not_mask_phrases_with_real_alignment_shape() -> None:
    segments = _make_0806_segments()
    segments[1] = TranscriptSegment(
        start=2.8,
        end=6.82,
        text=(
            "It is a software that automatically trades on set rules."
        ),
        words=[
            TranscriptWord(start=2.80, end=3.06, text="It"),
            TranscriptWord(start=3.06, end=3.10, text="is"),
            TranscriptWord(start=3.10, end=3.22, text="a"),
            TranscriptWord(start=3.22, end=3.70, text="software"),
            TranscriptWord(start=3.70, end=4.64, text="that"),
            TranscriptWord(start=4.64, end=6.02, text="automatically"),
            TranscriptWord(start=6.02, end=6.82, text="trades"),
            TranscriptWord(start=6.64, end=6.70, text="on"),
            TranscriptWord(start=6.70, end=6.76, text="set"),
            TranscriptWord(start=6.76, end=6.82, text="rules."),
        ],
    )

    pages = _build_0806_caption_pages(segments)

    assert all(
        left.end_ms <= right.start_ms
        for left, right in zip(pages, pages[1:])
    )
    assert all(
        token.start_ms < page.end_ms
        and token.end_ms > page.start_ms
        for page in pages
        for token in page.tokens
    )


def test_0806_cta_caption_phrases_follow_sentence_grammar() -> None:
    segments: list[TranscriptSegment] = []
    cursor = 0.0
    for text in _0806_CORRECTED_TEXTS:
        words = [
            TranscriptWord(
                start=cursor + index * 0.4,
                end=cursor + (index + 1) * 0.4,
                text=token,
                confidence=0.99,
            )
            for index, token in enumerate(text.split())
        ]
        segments.append(
            TranscriptSegment(
                start=words[0].start,
                end=words[-1].end,
                text=text,
                words=words,
            )
        )
        cursor = words[-1].end + 0.1

    pages = _build_0806_caption_pages(segments)
    cta_start_ms = round(segments[11].start * 1000)
    phrases = [
        " ".join(token.text for token in page.tokens)
        for page in pages
        if page.start_ms >= cta_start_ms
    ]

    assert phrases == [
        "If you want",
        "to see how",
        "an Expert Advisor",
        "trades,",
        "then you can",
        "follow us",
        "and join our",
        "Telegram group.",
        "Thank you!",
    ]


def test_0806_cta_real_alignment_keeps_every_token_visible() -> None:
    segments = _make_0806_segments()
    words = [
        TranscriptWord(start=start, end=end, text=text, confidence=0.99)
        for text, start, end in [
            ("If", 33.18, 33.66),
            ("you", 33.66, 33.84),
            ("want", 33.84, 33.96),
            ("to", 33.96, 34.58),
            ("see", 34.58, 34.66),
            ("how", 34.66, 34.74),
            ("an", 34.58, 34.76),
            ("Expert", 34.76, 34.98),
            ("Advisor", 34.98, 35.48),
            ("trades,", 35.48, 36.38),
            ("then", 36.72, 36.84),
            ("you", 36.84, 37.02),
            ("can", 37.02, 37.16),
            ("follow", 37.16, 37.48),
            ("us", 37.48, 37.64),
            ("and", 37.64, 38.62),
            ("join", 38.62, 38.90),
            ("our", 38.90, 38.94),
            ("Telegram", 38.94, 39.44),
            ("group.", 39.44, 39.68),
            ("Thank", 40.62, 40.78),
            ("you!", 40.78, 41.00),
        ]
    ]
    segments[11] = TranscriptSegment(
        start=words[0].start,
        end=words[-1].end,
        text=_0806_CORRECTED_TEXTS[11],
        words=words,
    )

    pages = _build_0806_caption_pages(segments)
    cta_pages = [page for page in pages if page.start_ms >= 33_180]

    assert all(
        token.start_ms < page.end_ms
        and token.end_ms > page.start_ms
        for page in cta_pages
        for token in page.tokens
    )


@pytest.mark.parametrize(
    "treatment",
    ["0806-split-hook", "0806-v3-hook-physical"],
)
def test_role_comparison_sheet_uses_reference_and_rendered_pixels(
    tmp_path,
    treatment: str,
) -> None:
    builder = getattr(
        reference_production,
        "_create_role_comparison_sheet",
        None,
    )
    assert builder is not None
    review_dir = tmp_path / "review"
    review_dir.mkdir()
    reference = np.full((320, 180, 3), (30, 90, 150), dtype=np.uint8)
    cv2.imwrite(str(review_dir / "reference-hook.png"), reference)
    video = tmp_path / "edited.avi"
    writer = cv2.VideoWriter(
        str(video),
        cv2.VideoWriter_fourcc(*"MJPG"),
        10,
        (180, 320),
    )
    assert writer.isOpened()
    for value in range(20):
        writer.write(
            np.full((320, 180, 3), 50 + value * 3, dtype=np.uint8)
        )
    writer.release()
    output = review_dir / "reference-comparison.jpg"

    builder(
        video=video,
        shots=[
            ShotSpec(
                id="hook",
                start_ms=0,
                end_ms=1000,
                role="hook",
                layout="asset-full",
                treatment=treatment,
                caption_family="technical-mono",
                source_kind="screen-recording",
                reference_role="primary-10",
            )
        ],
        reference_profile={
            "selected_frames": [
                {
                    "role": "hook",
                    "path": "review/reference-hook.png",
                }
            ]
        },
        output=output,
    )

    sheet = cv2.imread(str(output))
    assert sheet is not None
    assert sheet.shape[1] > sheet.shape[0]
