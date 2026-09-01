from __future__ import annotations

from pathlib import Path
import shutil
from uuid import uuid4

import pytest
from PIL import Image, ImageChops, ImageStat

from app.editor.v8_graphics import (
    render_evidence_crop,
    render_graphic,
)
from build_0813_ppi_v8 import build_blueprint
from build_0813_v8_pipeline import (
    _copy,
    _hook_cue,
    is_node_spawn_eperm,
    music_candidate_paths,
    ppi_video_filter,
    score_music_candidate,
)


@pytest.fixture
def workspace_tmp() -> Path:
    parent = (Path(__file__).parent / ".tmp_v8_artifacts").resolve()
    root = parent / uuid4().hex
    root.mkdir(parents=True)
    try:
        yield root
    finally:
        resolved = root.resolve()
        if resolved.is_relative_to(parent):
            shutil.rmtree(resolved, ignore_errors=True)


def test_copy_replaces_same_size_stale_asset(
    workspace_tmp: Path,
) -> None:
    source = workspace_tmp / "source.bin"
    destination = workspace_tmp / "destination.bin"
    source.write_bytes(b"fresh-asset")
    destination.write_bytes(b"stale-asset")

    _copy(source, destination)

    assert destination.read_bytes() == b"fresh-asset"


def test_serif_hook_holds_for_full_first_two_seconds() -> None:
    cue = _hook_cue(build_blueprint())

    assert cue["start_ms"] == 0
    assert cue["end_ms"] == 2_000


def test_music_candidate_scoring_rewards_target_pulse_and_low_masking() -> None:
    strong = score_music_candidate(
        bpm=98,
        target_bpm=(92, 100),
        speech_masking_ratio=0.30,
        brightness_ratio=0.12,
        section_stability_cv=0.10,
    )
    weak = score_music_candidate(
        bpm=120,
        target_bpm=(92, 100),
        speech_masking_ratio=0.70,
        brightness_ratio=0.42,
        section_stability_cv=0.60,
    )

    assert strong["total"] > weak["total"]
    assert all(
        0 <= strong[key] <= 5
        for key in ("pulse", "speech_masking", "brightness", "stability")
    )


def test_each_story_reviews_five_tracks_including_the_selected_track() -> None:
    candidates = music_candidate_paths("ppi")

    assert len(candidates) == 5
    assert len(set(candidates)) == 5
    assert Path(candidates[0]).name == "close-up-1167.mp3"


def test_ppi_grade_preserves_bright_evidence_and_restores_color() -> None:
    filters = ppi_video_filter()

    assert "1/0.98" in filters
    assert "saturation=0.84" in filters


def test_deterministic_graphic_is_portrait_and_visually_nonempty(
    workspace_tmp: Path,
) -> None:
    output = workspace_tmp / "risk.png"

    render_graphic("graphic-risk-equation", output)

    with Image.open(output) as image:
        assert image.size == (1080, 1920)
        assert ImageStat.Stat(image.convert("L")).stddev[0] > 20


def test_evidence_crop_preserves_source_pixels_at_phone_size(
    workspace_tmp: Path,
) -> None:
    source = Path(
        r"C:\websites\ai video production tool\storage\assets"
        r"\0813-stories\bls-ppi-july-2026-excerpt.png"
    )
    output = workspace_tmp / "goods.png"

    render_evidence_crop(source, output, "goods")

    with Image.open(output) as image:
        assert image.size == (1080, 1920)
        grayscale = image.convert("L")
        stats = ImageStat.Stat(grayscale)
        assert stats.stddev[0] > 18
        assert stats.mean[0] < 150
        assert (
            sum(1 for value in grayscale.getdata() if value < 45)
            / (1080 * 1920)
            >= 0.30
        )


def test_actual_evidence_uses_a_bright_news_page_treatment(
    workspace_tmp: Path,
) -> None:
    source = Path(
        r"C:\websites\ai video production tool\storage\assets"
        r"\0813-stories\bls-ppi-july-2026-excerpt.png"
    )
    output = workspace_tmp / "actual.png"

    render_evidence_crop(source, output, "actual")

    with Image.open(output) as image:
        stats = ImageStat.Stat(image.convert("L"))
        assert stats.mean[0] >= 165


def test_reversal_and_balance_graphics_have_distinct_compositions(
    workspace_tmp: Path,
) -> None:
    reversal = workspace_tmp / "reversal.png"
    balance = workspace_tmp / "balance.png"
    render_graphic("graphic-opposing-arrows", reversal)
    render_graphic("graphic-net-zero", balance)

    with Image.open(reversal) as left, Image.open(balance) as right:
        difference = ImageStat.Stat(
            ImageChops.difference(left, right).convert("L")
        ).mean[0]

    assert difference >= 18


def test_ffmpeg_fallback_is_limited_to_node_spawn_eperm() -> None:
    assert is_node_spawn_eperm(
        RuntimeError("Error: spawn EPERM at ChildProcess.spawn")
    )
    assert not is_node_spawn_eperm(
        RuntimeError("Caption overflow in technical-mono")
    )
