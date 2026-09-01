from __future__ import annotations

from statistics import median

from app.models import TranscriptSegment, TranscriptWord
from app.production_models import ProductionBlueprint
from PIL import Image, ImageChops


def _module():
    from app.editor import human_reference_0810

    return human_reference_0810


def test_0810_social_kinetic_schedule_matches_the_human_reference_profile():
    shots = _module().build_social_kinetic_schedule()

    assert len(shots) == 16
    assert shots[0]["start_ms"] == 0
    assert shots[-1]["end_ms"] == 44_370
    assert all(
        left["end_ms"] == right["start_ms"]
        for left, right in zip(shots, shots[1:], strict=False)
    )
    durations = [
        shot["end_ms"] - shot["start_ms"]
        for shot in shots
    ]
    assert 2_300 <= median(durations) <= 3_000
    assert len(shots) - 1 == 15

    presenter_ms = sum(
        shot["end_ms"] - shot["start_ms"]
        for shot in shots
        if shot["source_role"] == "presenter"
    )
    flow_ms = sum(
        shot["end_ms"] - shot["start_ms"]
        for shot in shots
        if shot["source_role"] == "flow-illustrative"
    )
    assert 0.58 <= presenter_ms / 44_370 <= 0.68
    assert flow_ms / 44_370 <= 0.18


def test_0810_visual_resets_land_on_the_measured_dialogue_onsets():
    shots = _module().build_social_kinetic_schedule()
    boundaries = {shot["start_ms"] for shot in shots[1:]}

    assert {
        10_400,
        11_340,
        15_900,
        18_520,
        24_680,
        27_120,
    }.issubset(boundaries)
    assert {
        10_100,
        11_100,
        15_670,
        18_120,
        24_470,
        26_930,
    }.isdisjoint(boundaries)


def test_0810_social_kinetic_text_is_sparse_semantic_and_reference_sized():
    cues = _module().build_social_kinetic_text_cues()

    assert 7 <= len(cues) <= 14
    assert {
        "hero-condensed",
        "outlined-stack",
        "cyan-secondary",
        "gradient-number",
        "correction-symbol",
        "cta-quote",
        "micro-source",
    }.issubset({cue.family for cue in cues})
    visible_ms = _module().measure_visible_interval_duration(cues)
    assert 0.18 <= visible_ms / 44_370 <= 0.30
    assert all(cue.end_ms <= 44_370 for cue in cues)
    assert all(cue.start_ms < cue.end_ms for cue in cues)
    assert all(
        not (cue.y < 1_100 and cue.family in {"hero-condensed", "cta-quote"})
        for cue in cues
    )
    number = next(cue for cue in cues if cue.family == "gradient-number")
    assert "$110K" in number.text
    assert "FINAL" not in number.text.upper()
    hook_stack = {
        cue.text
        for cue in cues
        if cue.start_ms <= 2_500 < cue.end_ms
    }
    assert {
        "3 MONTHS",
        "AUTOMATED",
        "TRADING",
        "CONTEST",
    }.issubset(hook_stack)
    monitor = next(cue for cue in cues if cue.text == "MONITOR")
    assert monitor.animation == "hard-cut"


def test_0810_upi_phone_card_does_not_repeat_the_upi_label(tmp_path):
    destination = tmp_path / "upi-phone-card.png"

    _module()._build_upi_phone_card(
        source=_module()._DEFAULT_UPI_LOGO,
        destination=destination,
    )

    image = Image.open(destination).convert("RGB")
    label_region = image.crop((250, 825, 550, 915))
    dark_pixels = sum(
        1
        for red, green, blue in label_region.getdata()
        if (red + green + blue) / 3 < 100
    )
    assert dark_pixels < 200


def test_0810_logo_card_removes_near_white_source_box(tmp_path):
    destination = tmp_path / "logo-card.jpg"

    _module()._build_logo_card(
        source=_module()._DEFAULT_BRAND_LOGO,
        destination=destination,
    )

    card = Image.open(destination).convert("RGB")
    edge_pairs = [
        ((75, 650), (95, 650)),
        ((185, 540), (185, 560)),
        ((985, 650), (1_005, 650)),
    ]
    distances = [
        sum(
            abs(left - right)
            for left, right in zip(
                card.getpixel(outside),
                card.getpixel(inside),
                strict=True,
            )
        )
        for outside, inside in edge_pairs
    ]
    assert max(distances) < 15


def test_0810_social_kinetic_motion_density_uses_internal_events_not_overcuts():
    events = _module().build_social_kinetic_motion_events()

    assert 25 <= len(events) <= 32
    assert {
        "punch-crop",
        "text-reveal",
        "pip-pop",
        "logo-build",
        "directional-jump",
        "highlight-sweep",
    }.issubset({event.kind for event in events})
    assert all(event.end_ms <= 44_370 for event in events)
    assert len({event.target_id for event in events}) >= 8


def test_0810_motion_events_reference_renderable_targets():
    layers = _module().build_social_kinetic_layers()
    cues = _module().build_social_kinetic_text_cues()
    known_targets = {
        *(layer.id for layer in layers),
        *(cue.id for cue in cues),
        "composition",
    }

    assert not [
        event.id
        for event in _module().build_social_kinetic_motion_events()
        if event.target_id not in known_targets
    ]


def test_0810_dialogue_edl_removes_only_silence_and_hits_exact_duration():
    edl = _module().build_dialogue_edl_from_silences(
        source_duration_ms=1_000,
        target_duration_ms=700,
        silence_intervals_ms=[
            (100, 300),
            (500, 800),
        ],
        minimum_retained_silence_ms=100,
    )

    assert edl[0].source_start_ms == 0
    assert edl[-1].source_end_ms == 1_000
    assert edl[0].output_start_ms == 0
    assert edl[-1].output_end_ms == 700
    assert all(
        left.output_end_ms == right.output_start_ms
        for left, right in zip(edl, edl[1:], strict=False)
    )
    assert all(segment.playback_rate == 1 for segment in edl)
    assert sum(
        segment.source_end_ms - segment.source_start_ms
        for segment in edl
    ) == 700


def test_0810_audio_plan_has_reference_bpm_semantic_cues_and_safe_onsets():
    words = [
        TranscriptWord(
            start=index * 2,
            end=index * 2 + 0.8,
            text=f"word-{index}",
        )
        for index in range(23)
    ]
    segments = [
        TranscriptSegment(
            start=words[0].start,
            end=words[-1].end,
            text=" ".join(word.text for word in words),
            words=words,
        )
    ]

    audio = _module().build_social_kinetic_audio_plan(segments)

    assert audio.music_bpm == 126
    assert audio.integrated_lufs == -13.5
    assert audio.target_lra_lu == 2.4
    assert 16 <= len(audio.sfx_cues) <= 20
    assert {
        "impact",
        "whoosh",
        "click",
        "riser",
        "notification",
    }.issubset({cue.kind for cue in audio.sfx_cues})
    assert all(-18 <= cue.gain_db <= -12 for cue in audio.sfx_cues)
    assert not [
        cue.id
        for cue in audio.sfx_cues
        if any(
            cue.start_ms < window.end_ms
            and cue.start_ms + cue.duration_ms > window.start_ms
            for window in audio.speech_protection_windows
        )
    ]


def test_0810_flow_plan_uses_three_safe_illustrative_sequences(
    tmp_path,
):
    shots = _module().build_social_kinetic_flow_shots(tmp_path)

    assert len(shots) == 3
    assert {shot.id for shot in shots} == {
        "flow-robot-trading",
        "flow-robot-boardroom",
        "flow-robot-action",
    }
    assert all(shot.model == "veo-lite" for shot in shots)
    assert all(shot.mode == "i2v" for shot in shots)
    assert all(len(shot.input_plates) == 2 for shot in shots)
    forbidden = {
        "evidence",
        "exact-text",
        "product-ui",
        "code",
        "number",
        "currency",
        "chart",
        "source-document",
        "caption",
    }
    assert all(
        not forbidden.intersection(shot.requested_content)
        for shot in shots
    )
    assert all(
        "no readable text" in " ".join(shot.constraints).casefold()
        for shot in shots
    )


def test_0810_explicit_layers_keep_pips_below_face_and_flow_under_18_percent():
    layers = _module().build_social_kinetic_layers()

    flow_ms = sum(
        layer.end_ms - layer.start_ms
        for layer in layers
        if layer.source_role == "flow-illustrative"
        and layer.z_index == 10
    )
    assert flow_ms / 44_370 <= 0.18
    upi = next(layer for layer in layers if layer.id == "layer-upi-pip")
    assert upi.bounds.y >= 1_180
    assert upi.bounds.width == 400
    assert upi.bounds.height <= 500
    assert upi.kind == "image"
    assert upi.asset_id == "graphic-upi-phone"
    evidence = next(
        layer for layer in layers if layer.id == "layer-evidence-proof"
    )
    assert evidence.transform_keyframes[-1].scale >= 1.1
    assert evidence.end_ms - evidence.start_ms <= 850
    assert all(
        layer.muted for layer in layers if layer.kind == "video"
    )
    assert all(
        layer.illustrative_label
        for layer in layers
        if layer.source_role == "flow-illustrative"
    )
    layer_ids = {layer.id for layer in layers}
    assert "layer-robot-transition" not in layer_ids
    assert "layer-boardroom-tail" not in layer_ids
    for layer_id in (
        "layer-hook-vignette",
        "layer-correction-vignette",
        "layer-cta-vignette",
    ):
        vignette = next(layer for layer in layers if layer.id == layer_id)
        assert vignette.opacity_keyframes[-1].value == 0
        assert (
            vignette.opacity_keyframes[-1].at_ms
            - vignette.opacity_keyframes[-2].at_ms
            >= 300
        )
    correction_vignette = next(
        layer
        for layer in layers
        if layer.id == "layer-correction-vignette"
    )
    assert correction_vignette.opacity_keyframes[0].value == 0
    assert correction_vignette.opacity_keyframes[1].value == 1
    assert correction_vignette.opacity_keyframes[1].at_ms >= 300
    correction_presenter = next(
        layer
        for layer in layers
        if layer.id == "layer-correction-presenter"
    )
    cta_presenter = next(
        layer for layer in layers if layer.id == "layer-cta-presenter"
    )
    assert (
        correction_presenter.transform_keyframes[-1].scale
        == cta_presenter.transform_keyframes[0].scale
    )
    logo = next(layer for layer in layers if layer.id == "layer-logo")
    assert logo.end_ms - logo.start_ms <= 3_000
    assert logo.opacity_keyframes[-1].value == 0
    assert (
        logo.opacity_keyframes[-1].at_ms
        - logo.opacity_keyframes[-2].at_ms
        >= 500
    )
    assert logo.end_ms - correction_presenter.start_ms >= 500
    assert correction_presenter.opacity_keyframes[0].value == 0
    assert correction_presenter.opacity_keyframes[-1].value == 1
    assert correction_presenter.opacity_keyframes[-1].at_ms >= 500
    robot_wide = next(
        layer for layer in layers if layer.id == "layer-flow-robot-a"
    )
    boardroom = next(
        layer for layer in layers if layer.id == "layer-flow-boardroom"
    )
    assert robot_wide.end_ms == 5_650
    assert robot_wide.source_end_ms == 2_200
    assert boardroom.end_ms == 13_630
    assert boardroom.source_end_ms == 2_200
    assert all(
        layer.end_ms - layer.start_ms <= 3_000
        for layer in layers
        if layer.id in {"layer-hook-vignette", "layer-cta-vignette"}
    )


def test_0810_dialogue_processing_compensates_filter_latency():
    builder = getattr(_module(), "build_dialogue_processing_filter", None)

    assert builder is not None
    audio_filter = builder(44.37)
    assert "apad=pad_dur=0.10" in audio_filter
    assert "atrim=start=0.030:duration=44.370" in audio_filter
    assert audio_filter.endswith("asetpts=PTS-STARTPTS")


def test_0810_human_reference_blueprint_writes_the_staged_artifacts(
    tmp_path,
):
    source = tmp_path / "0810.mp4"
    source.write_bytes(b"source-fixture")
    output = tmp_path / "0810-production-v2-human-reference"
    seed = (
        _module()._WORKSPACE_ROOT
        / "storage"
        / "deliverables"
        / "0810-production-v1-internet-sourced"
    )

    artifacts = _module().build_human_reference_blueprint(
        source=source,
        output_dir=output,
        style_reference=_module()._DEFAULT_STYLE_REFERENCE,
        flow_operation_budget=8,
        seed_dir=seed,
        prepare_media=False,
        acquire_assets=False,
    )

    for artifact in (
        "blueprint",
        "storyboard",
        "evidence",
        "reference_profile",
        "dialogue_edl",
        "kinetic_text_plan",
        "motion_events",
        "sound_cue_sheet",
        "flow_shot_plan",
        "asset_manifest",
    ):
        assert (output / artifacts[artifact]).is_file()

    blueprint = ProductionBlueprint.model_validate_json(
        (output / artifacts["blueprint"]).read_text(encoding="utf-8")
    )
    assert blueprint.duration_ms == 44_370
    assert blueprint.reference_profile == "social-kinetic"
    assert blueprint.voice_policy == "reference-compressed"
    assert blueprint.caption_pages == []
    assert len(blueprint.flow_shots) == 3
    assert len(blueprint.kinetic_text_cues) == 14
    assert 25 <= len(blueprint.motion_events) <= 32
    assert len(blueprint.audio.sfx_cues) == 18
    assert blueprint.audio.target_lra_lu == 2.4
    assert len(blueprint.evidence) == 4
    risk_asset = next(
        asset for asset in blueprint.assets if asset.id == "licensed-risk-manager"
    )
    assert risk_asset.remote_id == "22966"
    assert "engineer" in " ".join(risk_asset.keywords).casefold()
    upi_asset = next(
        asset for asset in blueprint.assets if asset.id == "graphic-upi-phone"
    )
    assert upi_asset.license == "Public domain"
    for asset in blueprint.assets:
        assert not asset.path.startswith(("C:/", "D:/", "C:\\", "D:\\"))
        assert (output / asset.path).is_file()
        assert "training videos data" not in asset.path.casefold()
    assert len(list((output / "flow-plates").glob("*.png"))) == 6

    logo_card = Image.open(
        output / "assets" / "graphics" / "profit-bricks-logo-card.jpg"
    ).convert("RGB")
    difference = ImageChops.difference(
        logo_card,
        Image.new("RGB", logo_card.size, (255, 255, 255)),
    ).convert("L")
    content_box = difference.point(
        lambda value: 255 if value > 18 else 0
    ).getbbox()
    assert content_box is not None
    assert content_box[2] - content_box[0] >= 820
    assert content_box[3] - content_box[1] >= 640
