from pathlib import Path

import numpy as np
from PIL import Image

import build_0806_training_parity_v8 as builder
import app.editor.training_parity_0806 as parity
from app.editor.training_parity_0806 import (
    DURATION_MS,
    V8_CAPTURE_OVERRIDES,
    V8_MUSIC_CANDIDATE,
    build_v8_audio_plan,
    build_v8_music_filter,
    build_v8_caption_pages,
    build_v8_layers,
    build_v8_motion_events,
    build_v8_shot_schedule,
    caption_coverage_ratio,
    caption_token_window_violations,
    estimate_role_coverage,
    prepare_v8_evidence_frames,
    prepare_v8_solid_dark_backdrop,
    technical_mono_caption_share,
)


def _uniform_cell_fractions(image: np.ndarray) -> tuple[float, float]:
    gray = np.asarray(Image.fromarray(image).convert("L"))
    cells = gray.reshape(16, 120, 9, 120).transpose(0, 2, 1, 3)
    cell_means = cells.mean(axis=(2, 3))
    cell_stdev = cells.std(axis=(2, 3))
    bright = float(np.mean((cell_means > 175) & (cell_stdev < 8)))
    dark = float(np.mean((cell_means < 28) & (cell_stdev < 8)))
    return bright, dark


def test_v8_captions_use_reference_10_family_and_geometry() -> None:
    pages = build_v8_caption_pages()

    assert pages
    assert all(page.family == "technical-mono" for page in pages)
    assert all(page.anchor == "center-74" for page in pages)
    assert all(page.transition == "hard-cut" for page in pages)
    assert all(page.max_width == 480 for page in pages)
    assert technical_mono_caption_share(pages) >= 0.96


def test_v8_caption_pages_cover_their_tokens_without_oversized_holds() -> None:
    pages = build_v8_caption_pages()

    assert all(
        350 <= page.end_ms - page.start_ms <= 1300
        for page in pages
    )
    assert caption_token_window_violations(pages) == []
    assert 0.70 <= caption_coverage_ratio(pages, DURATION_MS) <= 0.74


def test_v8_long_currency_window_uses_continuous_duplicate_pages() -> None:
    pages = [
        page
        for page in build_v8_caption_pages()
        if "$110,000" in " ".join(token.text for token in page.tokens)
    ]

    assert len(pages) == 2
    assert pages[0].end_ms == pages[1].start_ms
    assert [
        " ".join(token.text for token in page.tokens)
        for page in pages
    ] == ["$110,000.", "$110,000."]


def test_v8_schedule_preserves_reference_10_pacing() -> None:
    shots = build_v8_shot_schedule()

    assert len(shots) == 20
    assert shots[0]["start_ms"] == 0
    assert shots[-1]["end_ms"] == DURATION_MS
    assert all(
        current["end_ms"] == following["start_ms"]
        for current, following in zip(shots, shots[1:], strict=False)
    )


def test_v8_layers_reduce_presenter_and_keep_flow_disabled() -> None:
    layers = build_v8_layers()
    coverage = estimate_role_coverage(layers)

    assert all(layer.source_role != "flow-illustrative" for layer in layers)
    assert 0.12 <= coverage["presenter"] <= 0.16
    assert 0.30 <= coverage["real-product"] <= 0.40
    assert 0.17 <= coverage["direct-evidence"] <= 0.21
    assert 0.17 <= coverage["deterministic-graphic"] <= 0.30
    assert 0.08 <= coverage["licensed-context"] <= 0.15


def test_v8_layers_use_readable_macros_and_restrained_still_motion() -> None:
    layers = {layer.id: layer for layer in build_v8_layers()}

    assert (
        layers["layer-metaeditor-backdrop"].asset_id
        == "graphic-dark-backdrop"
    )
    assert (
        layers["layer-navigator-backdrop"].asset_id
        == "graphic-dark-backdrop"
    )
    assert (
        layers["layer-reset-backdrop"].asset_id
        == "graphic-light-backdrop"
    )
    assert (
        layers["layer-cta-backdrop"].asset_id
        == "graphic-light-backdrop"
    )
    assert layers["layer-code-backdrop"].asset_id == "graphic-dark-backdrop"
    assert (
        layers["layer-code-accent"].asset_id == "graphic-cool-backdrop"
    )
    assert layers["layer-code-accent"].bounds.height <= 440
    assert (
        layers["layer-code-accent"].asset_id
        != layers["layer-metaeditor-backdrop"].asset_id
    )
    assert layers["layer-code-context"].effect_keyframes[0].brightness <= 0.3
    assert layers["layer-code-context"].effect_keyframes[0].contrast <= 0.9
    assert (
        layers["layer-wrong-rule-context"].effect_keyframes[0].brightness
        <= 0.3
    )
    assert layers["layer-reset-presenter"].end_ms == 10_700
    assert layers["layer-lesson-presenter"].end_ms == 29_000
    assert layers["layer-cta-presenter"].end_ms == 38_600
    assert layers["layer-ending-presenter"].bounds.width == 1080
    assert layers["layer-ending-presenter"].bounds.height == 1920
    assert layers["layer-code-macro"].crop.width <= 0.60
    assert layers["layer-code-macro"].bounds.width <= 920
    assert 860 <= layers["layer-code-macro"].bounds.height <= 980
    assert layers["layer-metaeditor-open"].bounds.width <= 1000
    assert layers["layer-metaeditor-open"].bounds.height <= 1600
    assert layers["layer-navigator-ea"].bounds.width <= 1000
    assert layers["layer-navigator-ea"].crop.x == 0
    assert layers["layer-navigator-ea"].crop.width <= 0.24
    assert layers["layer-risk-inputs"].crop.width <= 0.50
    assert layers["layer-attach-ea"].crop.width <= 0.56
    assert layers["layer-strategy-tester"].crop.height <= 0.55

    deterministic_stills = [
        layer
        for layer in layers.values()
        if layer.kind == "image"
        and layer.source_role == "deterministic-graphic"
    ]
    assert all(
        abs(
            layer.transform_keyframes[-1].scale
            - layer.transform_keyframes[0].scale
        )
        <= 0.025
        for layer in deterministic_stills
    )
    overview = layers["layer-evidence-overview"]
    overview_field = layers["layer-evidence-overview-field"]
    assert overview.bounds.width <= 900
    assert overview.bounds.height <= 1_600
    assert overview_field.source_role == "deterministic-graphic"
    assert overview_field.asset_id == "graphic-dark-backdrop"
    overview_scale_delta = (
        overview.transform_keyframes[-1].scale
        - overview.transform_keyframes[0].scale
    )
    assert 0.025 <= overview_scale_delta <= 0.04
    for layer_id in (
        "layer-evidence-championship",
        "layer-evidence-result",
    ):
        layer = layers[layer_id]
        scale_delta = (
            layer.transform_keyframes[-1].scale
            - layer.transform_keyframes[0].scale
        )
        translation = abs(
            layer.transform_keyframes[-1].x
            - layer.transform_keyframes[0].x
        ) + abs(
            layer.transform_keyframes[-1].y
            - layer.transform_keyframes[0].y
        )
        assert abs(scale_delta) <= 0.005
        assert translation <= 2
        assert layer.bounds.width == 840
    assert layers["layer-evidence-number"].bounds.width == 840
    number = layers["layer-evidence-number"]
    assert 0.04 <= (
        number.transform_keyframes[-1].scale
        - number.transform_keyframes[0].scale
    ) <= 0.06
    assert abs(
        number.transform_keyframes[-1].x
        - number.transform_keyframes[0].x
    ) >= 20
    assert all(
        layer.border_radius == 0
        for layer in layers.values()
        if layer.source_role == "direct-evidence"
    )
    assert all(
        layer.effect_keyframes[0].brightness >= 1.18
        for layer in layers.values()
        if layer.source_role == "direct-evidence"
        and not layer.id.endswith("-field")
    )
    assert (
        layers["layer-metaeditor-backdrop"].color_filter
        == "brightness(0.55) saturate(0.60)"
    )
    for layer_id in (
        "layer-code-context",
        "layer-wrong-rule-context",
        "layer-attach-context",
        "layer-tester-backdrop",
    ):
        assert layers[layer_id].opacity_keyframes[0].value <= 0.18
    assert (
        layers["layer-risk-primary-dark-base"].asset_id
        == "graphic-dark-backdrop"
    )
    assert (
        layers["layer-risk-backdrop-primary"].asset_id
        == "graphic-cool-backdrop"
    )
    assert layers["layer-risk-backdrop-primary"].bounds.width == 640
    assert layers["layer-risk-backdrop-primary"].bounds.height == 1_760
    assert (
        layers["layer-risk-backdrop-primary"].color_filter
        == "brightness(1.55) saturate(0.20)"
    )
    assert (
        layers["layer-risk-primary-dark-base"].color_filter
        == "brightness(0.55) saturate(0.55)"
    )
    assert (
        layers["layer-risk-dark-base"].asset_id
        == "graphic-dark-backdrop"
    )
    assert (
        layers["layer-risk-backdrop"].asset_id
        == "graphic-cool-backdrop"
    )
    assert (
        layers["layer-risk-backdrop"].bounds
        == layers["layer-risk-backdrop-primary"].bounds
    )
    assert (
        layers["layer-risk-backdrop"].color_filter
        == layers["layer-risk-backdrop-primary"].color_filter
    )
    assert (
        layers["layer-risk-dark-base"].color_filter
        == layers["layer-risk-primary-dark-base"].color_filter
    )
    assert (
        layers["layer-tester-dark"].asset_id
        == "graphic-dark-backdrop"
    )
    assert (
        layers["layer-tester-light"].asset_id
        == "graphic-light-backdrop"
    )
    assert layers["layer-tester-light"].bounds.height == 520
    assert (
        layers["layer-tester-light"].color_filter
        == "brightness(0.75) saturate(0.50)"
    )
    product_fields = (
        "layer-metaeditor-product-field",
        "layer-code-product-field",
        "layer-navigator-product-field",
        "layer-attach-product-field",
        "layer-tester-product-field",
    )
    assert all(
        layers[layer_id].source_role == "real-product"
        for layer_id in product_fields
    )
    assert all(
        layers[layer_id].effect_keyframes[0].blur_px >= 40
        for layer_id in product_fields
    )
    assert all(
        layers[layer_id].opacity_keyframes[0].value == 0.62
        for layer_id in product_fields
    )
    assert all(
        layers[layer_id].effect_keyframes[0].brightness <= 0.35
        for layer_id in product_fields
    )
    assert all(
        layers[layer_id].color_filter
        == "brightness(0.45) saturate(1.35)"
        for layer_id in product_fields
    )
    for layer_id in (
        "layer-risk-product-field",
        "layer-risk-alt-product-field",
    ):
        assert layers[layer_id].opacity_keyframes[0].value == 0.55
        assert (
            layers[layer_id].color_filter
            == "brightness(0.92) saturate(0.85)"
        )
        assert layers[layer_id].bounds.width == 640
        assert layers[layer_id].bounds.height == 1_760
    assert (
        layers["layer-risk-product-field"].bounds
        == layers["layer-risk-backdrop-primary"].bounds
    )
    assert (
        layers["layer-risk-alt-product-field"].bounds
        == layers["layer-risk-backdrop"].bounds
    )
    assert (
        layers["layer-risk-inputs"].bounds
        == layers["layer-risk-parameter"].bounds
    )
    assert layers["layer-risk-inputs"].bounds.width == 660
    assert layers["layer-risk-inputs"].bounds.height == 1_320
    assert (
        layers["layer-risk-inputs"].color_filter
        == "brightness(1.15) saturate(0.90)"
    )
    assert (
        layers["layer-risk-parameter"].color_filter
        == layers["layer-risk-inputs"].color_filter
    )
    for layer_id in (
        "layer-evidence-championship",
        "layer-evidence-result",
        "layer-evidence-number",
    ):
        assert layers[layer_id].bounds.width == 840
        assert (
            layers[layer_id].effect_keyframes[0].brightness
            == 1.40
        )
        field = layers[f"{layer_id}-field"]
        assert field.effect_keyframes[0].brightness == 0.80
        assert field.effect_keyframes[0].contrast == 0.80
        assert (
            field.color_filter
            == "brightness(0.82) saturate(0.45)"
        )
    for layer_id in (
        "layer-code-product-field",
        "layer-navigator-product-field",
        "layer-attach-product-field",
    ):
        assert layers[layer_id].bounds.width == 780
        assert layers[layer_id].bounds.height == 1_760
    assert layers["layer-tester-product-field"].bounds.width == 1_080
    assert layers["layer-tester-product-field"].bounds.height == 1_400
    assert (
        layers["layer-tester-backdrop"].z_index
        < layers["layer-tester-product-field"].z_index
    )
    for layer_id in (
        "layer-code-macro",
        "layer-navigator-ea",
        "layer-risk-inputs",
        "layer-risk-parameter",
        "layer-attach-ea",
    ):
        layer = layers[layer_id]
        scale_delta = (
            layer.transform_keyframes[-1].scale
            - layer.transform_keyframes[0].scale
        )
        assert 0.045 <= scale_delta <= 0.071
        translation = abs(
            layer.transform_keyframes[-1].x
            - layer.transform_keyframes[0].x
        ) + abs(
            layer.transform_keyframes[-1].y
            - layer.transform_keyframes[0].y
        )
        assert 35 <= translation <= 65
        assert layer.effect_keyframes[0].blur_px <= 0.2
    for layer_id in ("layer-metaeditor-open", "layer-strategy-tester"):
        layer = layers[layer_id]
        assert (
            layer.transform_keyframes[-1].scale
            == layer.transform_keyframes[0].scale
        )
        assert (
            layer.transform_keyframes[-1].x
            == layer.transform_keyframes[0].x
        )
        assert (
            layer.transform_keyframes[-1].y
            == layer.transform_keyframes[0].y
        )
    assert layers["layer-risk-inputs"].bounds.height >= 1_240
    assert layers["layer-risk-parameter"].bounds.height >= 1_240
    assert layers["layer-attach-ea"].bounds.height >= 1_240
    assert layers["layer-strategy-tester"].bounds.height >= 1_140
    assert all(
        layers[layer_id].effect_keyframes[0].brightness >= 1.18
        for layer_id in (
            "layer-code-macro",
            "layer-risk-inputs",
            "layer-risk-parameter",
            "layer-attach-ea",
            "layer-strategy-tester",
        )
    )
    assert layers["layer-lesson-graphic"].source_role == "licensed-context"
    assert layers["layer-lesson-graphic"].asset_id == "licensed-code-screen"
    assert (
        layers["layer-lesson-graphic"].effect_keyframes[0].brightness
        == 1.60
    )
    assert (
        layers["layer-tactile-bridge"].effect_keyframes[0].brightness
        == 1.20
    )
    assert layers["layer-rules-risk-context"].asset_id == "licensed-typing"
    assert layers["layer-rules-risk-context"].bounds.height <= 320
    assert (
        layers["layer-rules-risk-dark-base"].asset_id
        == "graphic-dark-backdrop"
    )
    assert (
        layers["layer-rules-risk-dark-base"].color_filter
        == "brightness(0.45) saturate(0.50)"
    )
    assert (
        layers["layer-rules-risk"].effect_keyframes[0].contrast
        == 0.78
    )
    assert (
        layers["layer-attach-backdrop"].color_filter
        == layers["layer-rules-risk-dark-base"].color_filter
    )
    assert layers["layer-attach-ea"].effect_keyframes[0].contrast == 0.80
    assert (
        layers["layer-risk-reversal"].color_filter
        == "brightness(0.98)"
    )
    assert (
        layers["layer-tester-dark"].color_filter
        == layers["layer-rules-risk-dark-base"].color_filter
    )
    assert layers["layer-rules-risk"].bounds.width <= 900
def test_v8_evidence_frames_preserve_raw_source_pixels(tmp_path: Path) -> None:
    history = tmp_path / "history.png"
    risk = tmp_path / "risk.png"
    history_pixels = np.full((1600, 1440, 3), (12, 34, 56), dtype=np.uint8)
    history_pixels[:, :16] = (220, 20, 30)
    history_pixels[:, -16:] = (20, 210, 40)
    Image.fromarray(history_pixels).save(history)
    Image.new("RGB", (1268, 439), (90, 120, 150)).save(risk)

    outputs = prepare_v8_evidence_frames(
        history_source=history,
        risk_source=risk,
        output_dir=tmp_path / "output",
    )

    assert set(outputs) >= {
        "evidence-history-overview",
        "evidence-championship-excerpt",
        "evidence-risk-excerpt",
        "evidence-risk-number",
    }
    overview = np.asarray(Image.open(outputs["evidence-history-overview"]))
    championship_frame = np.asarray(
        Image.open(outputs["evidence-championship-excerpt"])
    )
    risk_frame = np.asarray(Image.open(outputs["evidence-risk-excerpt"]))
    number_frame = np.asarray(Image.open(outputs["evidence-risk-number"]))
    assert Image.open(outputs["evidence-history-overview"]).size == (
        1080,
        1920,
    )
    assert Image.open(outputs["evidence-risk-number"]).size == (1080, 1920)
    assert np.any(np.all(overview == (12, 34, 56), axis=2))
    assert np.any(np.all(overview == (220, 20, 30), axis=2))
    assert np.any(np.all(overview == (20, 210, 40), axis=2))
    assert np.any(np.all(risk_frame == (90, 120, 150), axis=2))
    assert not np.all(championship_frame[1_350, 540] == (90, 120, 150))
    assert not np.all(risk_frame[300, 540] == (90, 120, 150))
    assert not np.all(number_frame[700, 540] == (90, 120, 150))


def test_v8_risk_reversal_graphic_keeps_all_marks_inside_safe_edges(
    tmp_path: Path,
) -> None:
    output = tmp_path / "risk-reversal.png"

    parity.prepare_v8_risk_reversal_graphic(output)

    image = np.asarray(Image.open(output).convert("RGB"))
    background = image[0, 0]
    assert np.any(np.any(image != background, axis=2))
    assert not np.any(np.any(image[:, -24:] != background, axis=2))
    assert not np.any(np.any(image[-24:, :] != background, axis=2))


def test_v8_solid_dark_backdrop_is_uniform_and_near_black(
    tmp_path: Path,
) -> None:
    output = prepare_v8_solid_dark_backdrop(tmp_path / "dark.png")

    image = np.asarray(Image.open(output).convert("RGB"))

    assert image.shape == (1920, 1080, 3)
    assert int(image.max()) <= 10
    assert np.all(image == image[0, 0])


def test_v8_evidence_frames_use_role_distinct_documentary_surrounds(
    tmp_path: Path,
) -> None:
    history = tmp_path / "history.png"
    risk = tmp_path / "risk.png"
    history_pixels = np.zeros((1600, 1440, 3), dtype=np.uint8)
    history_pixels[:, :, 0] = np.linspace(160, 250, 1440, dtype=np.uint8)
    history_pixels[:, :, 1] = np.linspace(180, 245, 1440, dtype=np.uint8)
    history_pixels[:, :, 2] = 225
    risk_pixels = np.zeros((439, 1268, 3), dtype=np.uint8)
    risk_pixels[:, :, 0] = np.linspace(120, 245, 1268, dtype=np.uint8)
    risk_pixels[:, :, 1] = np.linspace(155, 235, 1268, dtype=np.uint8)
    risk_pixels[:, :, 2] = np.linspace(205, 245, 1268, dtype=np.uint8)
    Image.fromarray(history_pixels).save(history)
    Image.fromarray(risk_pixels).save(risk)

    outputs = prepare_v8_evidence_frames(
        history_source=history,
        risk_source=risk,
        output_dir=tmp_path / "output",
    )

    championship = np.asarray(
        Image.open(outputs["evidence-championship-excerpt"]).convert("RGB")
    )
    risk_frame = np.asarray(
        Image.open(outputs["evidence-risk-excerpt"]).convert("RGB")
    )
    number = np.asarray(
        Image.open(outputs["evidence-risk-number"]).convert("RGB")
    )
    championship_bright, championship_dark = _uniform_cell_fractions(
        championship
    )
    risk_bright, risk_dark = _uniform_cell_fractions(risk_frame)
    number_bright, number_dark = _uniform_cell_fractions(number)

    assert 190 <= float(np.mean(championship)) <= 235
    assert 190 <= float(np.mean(risk_frame)) <= 235
    assert 190 <= float(np.mean(number)) <= 235
    assert np.linalg.norm(
        championship[650, 200].astype(float)
        - championship[650, 296].astype(float)
    ) >= 2
    assert np.linalg.norm(
        number[650, 200].astype(float)
        - number[650, 296].astype(float)
    ) >= 2
    assert championship_bright <= 0.43
    assert risk_bright <= 0.43
    assert number_bright <= 0.43
    assert 0.05 <= championship_dark <= 0.30
    assert 0.05 <= risk_dark <= 0.30
    assert 0.05 <= number_dark <= 0.30


def test_v8_uses_real_privacy_safe_capture_overrides() -> None:
    assert V8_CAPTURE_OVERRIDES == {
        "capture-mt5-hook-action": "mt5-hook-action-v2.mp4",
        "capture-metaeditor-open": "metaeditor-compile-action-v2.mp4",
        "capture-metaeditor-rule-highlight": (
            "metaeditor-rule-highlight-v2.mp4"
        ),
        "capture-mt5-navigator-ea": "mt5-navigator-action-v2.mp4",
        "capture-mt5-risk-inputs": "mt5-risk-input-action-v2.mp4",
        "capture-mt5-risk-alternate": (
            "mt5-risk-alternate-action-v2.mp4"
        ),
        "capture-mt5-attach-ea": "mt5-attach-action-v2.mp4",
        "capture-mt5-strategy-tester": (
            "mt5-strategy-tester-action-v2.mp4"
        ),
    }
    assert len(set(V8_CAPTURE_OVERRIDES.values())) == 8


def test_v8_music_selects_slower_uninterrupted_candidate() -> None:
    assert V8_MUSIC_CANDIDATE["file"] == "feedback-dreams-588.mp3"
    assert 93 <= V8_MUSIC_CANDIDATE["estimated_bpm"] <= 96
    assert V8_MUSIC_CANDIDATE["selection_start_seconds"] == 50
    audio_filter = build_v8_music_filter()
    assert "aloop" not in audio_filter
    assert "atrim=duration=41.4" in audio_filter
    assert "aresample=48000" in audio_filter


def test_v8_audio_and_motion_are_restrained() -> None:
    audio = build_v8_audio_plan([])
    motion = build_v8_motion_events()

    assert audio.music_bpm == 95
    assert audio.music_base_gain_db == -7
    assert audio.music_duck_db == 10
    assert all(
        window.gain_db == -10
        for window in audio.music_gain_automation
    )
    cues = {cue.id: cue for cue in audio.sfx_cues}
    assert cues["sfx-reset"].start_ms == 9_360
    assert cues["sfx-reset"].gain_db >= -16
    assert cues["sfx-code-rule"].start_ms == 10_700
    assert cues["sfx-code-rule"].gain_db >= -16
    assert 8 <= len(audio.sfx_cues) <= 10
    assert len(motion) == 17
    assert all(event.intensity >= 0.65 for event in motion)
    assert all(event.end_ms - event.start_ms <= 420 for event in motion)
    assert sum(event.kind == "directional-jump" for event in motion) >= 7
    targets = {event.target_id for event in motion}
    assert {
        "layer-code-macro",
        "layer-risk-inputs",
        "layer-strategy-tester",
    } <= targets


def test_v8_builder_copies_reference_review_targets(tmp_path: Path) -> None:
    source = tmp_path / "v7"
    output = tmp_path / "v8"
    target_dir = source / "review" / "reference-targets"
    target_dir.mkdir(parents=True)
    Image.new("RGB", (20, 30), "red").save(
        target_dir / "reference-10-hook.png"
    )
    Image.new("RGB", (20, 30), "blue").save(
        target_dir / "reference-10-code.png"
    )

    copied = builder.copy_reference_targets(
        source_dir=source,
        output_dir=output,
    )

    assert {path.name for path in copied} == {
        "reference-10-hook.png",
        "reference-10-code.png",
    }
    assert all(path.is_file() for path in copied)


def test_v8_reports_document_the_full_reference_grammar() -> None:
    pattern = builder.build_training_pattern_report()
    gap = builder.build_v7_gap_audit_report()

    for heading in (
        "## Visual selection",
        "## Composition",
        "## Motion and pacing",
        "## Typography",
        "## Evidence",
        "## Sound",
        "## Release gates",
    ):
        assert heading in pattern
    assert len(pattern) >= 2_000
    assert "0.1173" in gap
    assert "113.5 BPM" in gap
    assert "Root causes" in gap
