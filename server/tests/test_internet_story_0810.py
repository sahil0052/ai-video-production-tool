from __future__ import annotations

import importlib
import json
from pathlib import Path
from statistics import median

import numpy as np
from app.models import TranscriptSegment, TranscriptWord
from PIL import Image, ImageStat


def _module():
    return importlib.import_module("app.editor.internet_story_0810")


def _segment(
    start: float,
    words: list[tuple[str, float]],
) -> TranscriptSegment:
    cursor = start
    transcript_words: list[TranscriptWord] = []
    for text, duration in words:
        transcript_words.append(
            TranscriptWord(
                start=cursor,
                end=cursor + duration,
                text=text,
            )
        )
        cursor += duration
    return TranscriptSegment(
        start=start,
        end=cursor,
        text=" ".join(word.text for word in transcript_words),
        words=transcript_words,
    )


def test_0810_schedule_is_source_only_reference_paced_and_word_aligned():
    shots = _module().build_0810_schedule()

    assert len(shots) == 23
    assert shots[0]["start_ms"] == 0
    assert shots[-1]["end_ms"] == 49_500
    assert all(
        left["end_ms"] == right["start_ms"]
        for left, right in zip(shots, shots[1:], strict=False)
    )
    assert all(shot["source_role"] != "flow-illustrative" for shot in shots)
    assert sum(
        shot["end_ms"] - shot["start_ms"]
        for shot in shots
        if shot["source_role"] == "direct-evidence"
    ) / 49_500 >= 0.15
    durations = [
        shot["end_ms"] - shot["start_ms"]
        for shot in shots
    ]
    assert 1_800 <= median(durations) <= 2_400
    assert not any(
        first["asset_id"] == second["asset_id"] == third["asset_id"]
        for first, second, third in zip(
            shots,
            shots[1:],
            shots[2:],
            strict=False,
        )
    )
    by_role = {shot["editorial_role"]: shot for shot in shots}
    assert by_role["upi-payment"]["start_ms"] == 14_980
    assert by_role["upi-payment"]["end_ms"] == 17_260
    assert by_role["upi-analogy"]["asset_id"] == "robot-line-47257"
    assert by_role["upi-analogy"]["start_ms"] == 17_260
    assert by_role["fewer-clicks"]["asset_id"] == "charts-tablet-45706"
    assert by_role["fewer-clicks"]["start_ms"] == 19_840
    assert by_role["fewer-clicks"]["end_ms"] == 23_360
    assert by_role["robot-actions"]["start_ms"] == 23_360
    assert by_role["orders-execute"]["start_ms"] == 25_280


def test_0810_captions_use_large_static_yellow_reference_emphasis():
    segments = [
        _segment(
            0,
            [
                ("2008", 0.42),
                ("mein", 0.34),
                ("teen", 0.38),
                ("mahine", 0.52),
            ],
        ),
        _segment(
            11,
            [
                ("Lekin", 0.42),
                ("sawal", 0.38),
                ("yeh", 0.28),
                ("hai?", 0.36),
            ],
        ),
        _segment(
            20,
            [
                ("robots", 0.34),
                ("multiple", 0.42),
                ("pairs", 0.34),
                ("scan", 0.28),
                ("karenge.", 0.44),
            ],
        ),
        _segment(
            32,
            [
                ("robot", 0.32),
                ("managers", 0.48),
                ("jaise", 0.32),
                ("honge.", 0.42),
            ],
        ),
        _segment(
            41,
            [
                ("comment", 0.36),
                ("mein", 0.26),
                ("DEMO", 0.34),
                ("likhe.", 0.42),
            ],
        ),
    ]

    pages = _module().build_0810_caption_pages(segments)

    assert pages
    assert all(350 <= page.end_ms - page.start_ms <= 1_400 for page in pages)
    assert all(1 <= len(page.tokens) <= 4 for page in pages)
    assert all(
        left.end_ms <= right.start_ms
        for left, right in zip(pages, pages[1:], strict=False)
    )
    assert all(page.family == "outlined-demo" for page in pages)
    assert all(page.anchor == "lower-82" for page in pages)
    assert all(page.max_width == 940 for page in pages)
    assert all(
        sum(token.highlighted for token in page.tokens) == 1
        for page in pages
    )
    rendered_tokens = [
        token.text
        for page in pages
        for token in page.tokens
    ]
    source_tokens = [
        word.text
        for segment in segments
        for word in segment.words
    ]
    assert rendered_tokens == source_tokens


def test_0810_layers_cover_the_story_without_generated_visuals():
    module = _module()
    schedule = module.build_0810_schedule()
    layers = module.build_0810_layers()
    base_layers = sorted(
        (layer for layer in layers if layer.z_index == 10),
        key=lambda layer: layer.start_ms,
    )

    assert len(base_layers) == len(schedule)
    assert all(
        left.end_ms == right.start_ms
        for left, right in zip(base_layers, base_layers[1:], strict=False)
    )
    assert base_layers[0].start_ms == 0
    assert base_layers[-1].end_ms == 49_500
    assert not [layer for layer in layers if layer.flow_shot_id]
    assert all(layer.muted for layer in layers if layer.kind == "video")
    assert all(
        layer.source_start_ms == layer.start_ms
        and layer.source_end_ms == layer.end_ms
        for layer in base_layers
        if layer.asset_id == "source-presenter"
    )
    layer_ids = {layer.id for layer in layers}
    assert {
        "overlay-hook-year",
        "overlay-upi-logo",
        "evidence-atc-proof-punch",
        "fewer-clicks-action-punch",
        "brand-logo-focus",
        "overlay-cta-demo",
    }.issubset(layer_ids)
    assert all(
        layer.z_index < 40
        for layer in layers
        if layer.id.startswith("overlay-") or layer.id == "brand-logo-focus"
    )
    atc_punch = next(
        layer for layer in layers if layer.id == "evidence-atc-proof-punch"
    )
    assert atc_punch.asset_id == "evidence-atc-three-months-proof"
    assert atc_punch.start_ms == 1_600
    assert atc_punch.end_ms == 3_000
    assert (
        atc_punch.transform_keyframes[-1].scale
        > atc_punch.transform_keyframes[0].scale
    )
    upi = next(layer for layer in layers if layer.id == "overlay-upi-logo")
    assert upi.start_ms == 15_140
    assert upi.end_ms == 17_260
    action_punch = next(
        layer for layer in layers
        if layer.id == "fewer-clicks-action-punch"
    )
    assert action_punch.asset_id == "charts-tablet-45706"
    assert action_punch.kind == "video"
    assert action_punch.start_ms == 21_840
    assert action_punch.end_ms == 23_360
    assert action_punch.muted
    assert (
        action_punch.transform_keyframes[-1].scale
        > action_punch.transform_keyframes[0].scale
    )
    brand = next(layer for layer in layers if layer.id == "brand-logo-focus")
    assert brand.start_ms == 36_440
    assert brand.bounds.model_dump() == {
        "x": 315,
        "y": 70,
        "width": 450,
        "height": 300,
    }


def test_0810_evidence_records_reject_the_final_balance_claim(
    tmp_path: Path,
):
    capture_dir = tmp_path / "source-captures"
    capture_dir.mkdir(parents=True)
    for filename in (
        "mql5-110k-mobile-excerpt.png",
        "mql5-risk-mobile-excerpt.png",
        "mt5-three-months-mobile-excerpt.png",
        "mt5-robot-actions-mobile-excerpt.png",
    ):
        (capture_dir / filename).write_bytes(b"source pixels")

    evidence = _module().build_0810_evidence_items(tmp_path)

    assert len(evidence) == 4
    assert all(item.status == "verified" for item in evidence)
    assert all(item.source_url.startswith("https://") for item in evidence)
    peak = next(item for item in evidence if item.id == "mql5-110k-peak")
    assert "$110,000" in peak.claim
    assert "at one point" in peak.claim
    assert "not a verified final balance" in (peak.notes or "")


def test_0810_editorial_cards_preserve_source_pixels_at_portrait_size(
    tmp_path: Path,
):
    capture_dir = tmp_path / "source-captures"
    capture_dir.mkdir(parents=True)
    for filename in (
        "mql5-110k-mobile-excerpt.png",
        "mql5-risk-mobile-excerpt.png",
        "mt5-three-months-mobile-excerpt.png",
        "mt5-robot-actions-mobile-excerpt.png",
    ):
        Image.new("RGB", (1_360, 240), "#F7F7F4").save(
            capture_dir / filename
        )

    assets = _module().build_0810_editorial_cards(tmp_path)
    by_id = {asset.id: asset for asset in assets}

    required = {
        "evidence-atc-three-months",
        "evidence-atc-three-months-proof",
        "evidence-mql5-110k",
        "evidence-mql5-risk",
        "evidence-mt5-robot-actions",
        "hook-year-overlay",
        "cta-demo-overlay",
    }
    assert required == set(by_id)
    for asset_id in required:
        path = tmp_path / by_id[asset_id].path
        assert path.is_file()
        assert Image.open(path).size == (1_080, 1_920)
    assert all(
        by_id[asset_id].provenance.startswith(
            "official-source-capture-derived"
        )
        for asset_id in required
        if asset_id.startswith("evidence-")
    )
    for asset_id in required:
        if not asset_id.startswith("evidence-"):
            continue
        image = Image.open(tmp_path / by_id[asset_id].path).convert("RGB")
        source_region = image.crop((36, 300, 1_044, 1_355))
        statistics = ImageStat.Stat(source_region)
        assert max(statistics.stddev) >= 24
    hook = Image.open(tmp_path / by_id["hook-year-overlay"].path).convert(
        "RGBA"
    )
    alpha_bbox = hook.getchannel("A").getbbox()
    assert alpha_bbox is not None
    assert alpha_bbox[1] >= 1_240


def test_0810_atc_proof_macro_uses_the_verified_lower_left_phrase(
    tmp_path: Path,
):
    source = tmp_path / "source.png"
    destination = tmp_path / "proof.png"
    excerpt = Image.new("RGB", (1_408, 182), "#FFFFFF")
    for x in range(0, 600):
        for y in (*range(94, 108), *range(154, 170)):
            excerpt.putpixel((x, y), (220, 20, 20))
    for x in range(0, 520):
        for y in range(108, 154):
            excerpt.putpixel((x, y), (12, 12, 12))
    excerpt.save(source)

    _module()._build_atc_proof_card(
        source=source,
        destination=destination,
    )

    proof = Image.open(destination).convert("RGB")
    source_macro = proof.crop((80, 590, 1_000, 940))
    assert sum(
        max(red, green, blue) < 64
        for red, green, blue in source_macro.get_flattened_data()
    ) > 20_000
    assert sum(
        red > 180 and green < 60 and blue < 60
        for red, green, blue in source_macro.get_flattened_data()
    ) < 100


def test_0810_contact_sheet_grid_pads_an_incomplete_final_row():
    cells = [
        np.full((480, 270, 3), index, dtype=np.uint8)
        for index in range(5)
    ]

    grid = _module()._contact_sheet_grid(cells, columns=4)

    assert grid.shape == (960, 1_080, 3)
    assert np.all(grid[480:, :270] == 4)
    assert np.all(grid[480:, 270:] == 0)


def test_0810_transcript_loader_keeps_source_word_timing_and_safe_text():
    output_dir = (
        Path(__file__).resolve().parents[2]
        / "storage"
        / "deliverables"
        / "0810-production-v1-internet-sourced"
    )
    raw = json.loads(
        (output_dir / "transcript-groq-raw.json").read_text(
            encoding="utf-8"
        )
    )

    segments = _module().load_0810_transcript(output_dir)
    words = [word for segment in segments for word in segment.words]

    assert len(segments) == 8
    assert len(words) == len(raw["words"]) == 155
    assert "final balance" not in segments[0].text.casefold()
    assert "1 crore ke aas paas" in segments[0].text.casefold()
    assert "free live demo" in segments[-1].text.casefold()
    assert all(word.end > word.start for word in words)
    assert all(
        left.end <= right.start
        for left, right in zip(words, words[1:], strict=False)
    )


def test_0810_brand_logo_removes_white_background(tmp_path: Path):
    source = tmp_path / "logo.png"
    output = tmp_path / "processed.png"
    image = Image.new("RGB", (200, 160), "#FFFFFF")
    for x in range(60, 140):
        for y in range(30, 130):
            image.putpixel((x, y), (0, 105, 70))
    image.save(source)

    _module()._prepare_0810_brand_logo(source=source, output=output)

    processed = Image.open(output).convert("RGBA")
    assert processed.size[0] < image.size[0]
    assert processed.size[1] < image.size[1]
    assert max(processed.getchannel("A").getextrema()) == 255
    assert not any(
        alpha > 0 and min(red, green, blue) > 248
        for red, green, blue, alpha in processed.get_flattened_data()
    )
