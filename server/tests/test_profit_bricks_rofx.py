from __future__ import annotations

from pathlib import Path
from statistics import median

from PIL import Image

from app.production_models import ProductionBlueprint


def _module():
    from app.editor import profit_bricks_rofx

    return profit_bricks_rofx


def test_rofx_schedule_is_speech_aligned_and_matches_social_kinetic_pacing():
    shots = _module().build_rofx_schedule()

    assert len(shots) == 17
    assert shots[0]["start_ms"] == 0
    assert shots[-1]["end_ms"] == 44_370
    assert all(
        current["end_ms"] == following["start_ms"]
        for current, following in zip(shots, shots[1:], strict=False)
    )
    durations = [shot["end_ms"] - shot["start_ms"] for shot in shots]
    assert 2_300 <= median(durations) <= 3_000

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
    assert 0.56 <= presenter_ms / 44_370 <= 0.66
    assert flow_ms / 44_370 <= 0.12
    assert shots[2]["end_ms"] == shots[3]["start_ms"] == 6_600
    assert shots[5]["end_ms"] == shots[6]["start_ms"] == 14_560
    assert shots[13]["end_ms"] == shots[14]["start_ms"] == 33_120


def test_rofx_text_is_sparse_large_and_uses_only_verified_visible_numbers():
    cues = _module().build_rofx_text_cues()

    assert 9 <= len(cues) <= 14
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
    visible_text = " ".join(cue.text for cue in cues).casefold()
    assert "1100+" in visible_text
    assert "$58m" in visible_text
    assert "$225m" in visible_text
    assert "550 crore" not in visible_text
    assert "2,000 crore" not in visible_text
    assert "no forex trading" in visible_text
    assert all(cue.end_ms <= 44_370 for cue in cues)
    customers = next(cue for cue in cues if cue.id == "text-customers")
    customer_source = next(
        cue for cue in cues if cue.id == "text-customers-source"
    )
    funds = next(cue for cue in cues if cue.id == "text-funds")
    assert customers.y >= 900
    assert customer_source.family == "micro-source"
    assert "1100" in "".join(
        character for character in customer_source.text if character.isalnum()
    )
    assert customer_source.y > customers.y
    assert funds.y >= 600
    assert "OVER $225M" in _module()._SANCTIONS_SOURCE_LINE


def test_rofx_flow_plan_contains_only_two_safe_illustrative_shots(tmp_path):
    shots = _module().build_rofx_flow_shots(tmp_path)

    assert len(shots) == 2
    assert {shot.id for shot in shots} == {
        "flow-rofx-robot",
        "flow-risk-control",
    }
    assert sum(shot.end_ms - shot.start_ms for shot in shots) / 44_370 <= 0.12
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
        not forbidden.intersection(shot.requested_content) for shot in shots
    )
    assert all(
        "no readable text" in " ".join(shot.constraints).casefold()
        for shot in shots
    )


def test_rofx_evidence_uses_official_cftc_and_court_sources(tmp_path):
    items = _module().build_rofx_evidence_items(tmp_path)

    assert len(items) >= 5
    assert all(item.status == "verified" for item in items)
    assert all(
        item.source_url.startswith("https://www.cftc.gov/")
        for item in items
    )
    claims = " ".join(item.claim for item in items).casefold()
    assert "1,100" in claims
    assert "$58 million" in claims
    assert "no rofx forex trading robot" in claims
    assert "$169,086,837.63" in claims


def test_source_card_highlight_blends_without_hiding_source_text(
    tmp_path: Path,
):
    source = tmp_path / "source.png"
    destination = tmp_path / "card.jpg"
    Image.new("RGB", (100, 100), (100, 100, 100)).save(source)

    _module()._build_source_card(
        source=source,
        destination=destination,
        crop=(0, 0, 1, 1),
        label="SOURCE",
        source_line="PRIMARY",
        highlight=(0.2, 0.2, 0.8, 0.8),
    )

    card = Image.open(destination).convert("RGB")
    highlighted = card.getpixel((540, 992))
    assert highlighted[1] < 190
    assert max(highlighted) - min(highlighted) < 90


def test_brand_logo_preparation_removes_connected_white_background(
    tmp_path: Path,
):
    source = tmp_path / "logo-source.png"
    destination = tmp_path / "logo-transparent.png"
    logo = Image.new("RGB", (40, 40), (255, 255, 255))
    for x in range(12, 28):
        for y in range(10, 30):
            logo.putpixel((x, y), (8, 112, 70))
    logo.save(source)

    _module()._prepare_transparent_logo(source, destination)

    prepared = Image.open(destination).convert("RGBA")
    alpha_min, alpha_max = prepared.getchannel("A").getextrema()
    assert alpha_min == 0
    assert alpha_max == 255
    assert prepared.size[0] < logo.size[0]
    assert prepared.size[1] < logo.size[1]


def test_social_kinetic_profile_resolution_does_not_reuse_0810_for_0811():
    from app.editor.production_v4 import resolve_social_kinetic_story_profile

    assert resolve_social_kinetic_story_profile(
        source_name="0810.mp4",
        requested="auto",
    ) == "automation-future"
    assert resolve_social_kinetic_story_profile(
        source_name="0811.mp4",
        requested="auto",
    ) == "rofx-case"
    assert resolve_social_kinetic_story_profile(
        source_name="anything.mp4",
        requested="rofx-case",
    ) == "rofx-case"


def test_rofx_layers_use_real_evidence_and_keep_presenter_pips_below_face():
    layers = _module().build_rofx_layers()

    assert all(layer.muted for layer in layers if layer.kind == "video")
    presenter_layers = [
        layer for layer in layers if layer.source_role == "presenter"
    ]
    assert all(
        layer.effect_keyframes[0].brightness == 0.92
        for layer in presenter_layers
    )
    hook = next(
        layer for layer in layers if layer.id == "layer-hook-presenter"
    )
    assert hook.effect_keyframes[0].saturation == 0.78
    robot = next(
        layer for layer in layers if layer.id == "layer-flow-rofx-robot"
    )
    assert robot.effect_keyframes[0].brightness == 1.12
    assert robot.effect_keyframes[0].saturation == 1.8
    lesson = next(
        layer for layer in layers if layer.id == "layer-lesson-presenter"
    )
    cta = next(
        layer for layer in layers if layer.id == "layer-cta-presenter"
    )
    assert lesson.transform_keyframes[0].scale >= 1.2
    assert cta.transform_keyframes[0].scale >= 1.15
    logo = next(
        layer for layer in layers if layer.id == "layer-brand-logo"
    )
    follow = next(
        cue for cue in _module().build_rofx_text_cues()
        if cue.id == "text-follow"
    )
    assert logo.end_ms <= follow.start_ms + 120
    assert all(
        layer.illustrative_label
        for layer in layers
        if layer.source_role == "flow-illustrative"
    )
    cftc_pip = next(layer for layer in layers if layer.id == "layer-rofx-pip")
    assert cftc_pip.bounds.y >= 1_150
    assert cftc_pip.bounds.height <= 560
    assert cftc_pip.source_role == "direct-evidence"
    assert all(
        layer.end_ms - layer.start_ms <= 3_000
        for layer in layers
        if layer.kind == "image"
    )
    evidence_ids = {
        layer.asset_id
        for layer in layers
        if layer.source_role == "direct-evidence"
    }
    assert {
        "evidence-cftc-2022-claim",
        "evidence-court-no-trading",
        "evidence-court-sanctions",
    }.issubset(evidence_ids)
    for layer_id in (
        "layer-claim-proof",
        "layer-court-no-trading",
        "layer-court-sanctions",
    ):
        layer = next(layer for layer in layers if layer.id == layer_id)
        assert layer.effect_keyframes[0].brightness == 0.9
    assert not any(layer.id == "layer-funds-overview" for layer in layers)
    funds_proof = next(
        layer for layer in layers if layer.id == "layer-funds-proof"
    )
    assert funds_proof.start_ms == 22_050
    assert funds_proof.end_ms == 24_640
    assert funds_proof.bounds.y >= 800
    assert funds_proof.bounds.width < 1_080
    assert funds_proof.asset_id == "evidence-cftc-funds-pip"
    assert funds_proof.opacity_keyframes[-1].at_ms >= 650
    court_presenter = next(
        layer
        for layer in layers
        if layer.id == "layer-court-overview-presenter"
    )
    court_overview = next(
        layer for layer in layers if layer.id == "layer-court-overview"
    )
    assert court_presenter.start_ms == court_overview.start_ms
    assert court_presenter.end_ms == court_overview.end_ms
    assert court_overview.bounds.y >= 1_000
    assert court_overview.bounds.width < 1_080
    assert court_overview.asset_id == "evidence-court-overview-pip"


def test_rofx_audio_preserves_dialogue_and_keeps_music_below_speech():
    source_segments = _module().load_rofx_transcript()
    edl = _module().build_dialogue_edl_from_silences(
        source_duration_ms=47_033,
        target_duration_ms=_module().OUTPUT_DURATION_MS,
        silence_intervals_ms=list(
            _module()._DEFAULT_SILENCE_INTERVALS_MS
        ),
        minimum_retained_silence_ms=70,
    )
    segments = _module()._remap_transcript(source_segments, edl)

    audio = _module().build_rofx_audio_plan(segments)

    assert audio.dialogue_asset_id == "dialogue-original"
    assert audio.music_base_gain_db == -27
    assert audio.music_duck_db == 10
    assert {window.gain_db for window in audio.music_gain_automation} == {-10}
    cues = {cue.id: cue for cue in audio.sfx_cues}
    assert cues["sfx-court"].asset_id == "sfx-impact"
    assert cues["sfx-empty"].source_start_ms == 580
    assert cues["sfx-robot"].source_start_ms == 260
    assert cues["sfx-court"].source_start_ms == 300
    assert cues["sfx-empty"].gain_db == -15
    assert cues["sfx-empty-accent"].asset_id == "sfx-impact"
    assert cues["sfx-empty-accent"].source_start_ms == 260
    assert cues["sfx-empty-accent"].gain_db == -12
    assert cues["sfx-robot"].gain_db == -13
    assert cues["sfx-claim"].asset_id == "sfx-snap"
    assert cues["sfx-claim"].source_start_ms == 0
    assert cues["sfx-claim"].duration_ms == 60
    assert cues["sfx-claim"].gain_db == -12
    assert cues["sfx-court"].gain_db == -12
    assert cues["sfx-order"].gain_db == -12
    assert cues["sfx-lesson"].gain_db == -13.5
    assert 36_750 <= cues["sfx-lesson"].start_ms <= 36_880


def test_rofx_blueprint_writes_bespoke_artifacts_without_0810_story_assets(
    tmp_path,
):
    source = tmp_path / "0811.mp4"
    source.write_bytes(b"source-fixture")
    output = tmp_path / "0811-production-v1-social-kinetic"

    artifacts = _module().build_rofx_blueprint(
        source=source,
        output_dir=output,
        style_reference=_module()._DEFAULT_STYLE_REFERENCE,
        flow_operation_budget=2,
        prepare_media=False,
        acquire_assets=False,
    )

    for key in (
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
        "capture_manifest",
    ):
        assert (output / artifacts[key]).is_file()

    blueprint = ProductionBlueprint.model_validate_json(
        (output / artifacts["blueprint"]).read_text(encoding="utf-8")
    )
    assert blueprint.duration_ms == 44_370
    assert blueprint.reference_profile == "social-kinetic"
    assert blueprint.story_profile == "rofx-case"
    assert blueprint.caption_pages == []
    assert len(blueprint.flow_shots) == 2
    assert 25 <= len(blueprint.motion_events) <= 32
    assert 16 <= len(blueprint.audio.sfx_cues) <= 20
    assert len(blueprint.evidence) >= 5
    serialized = blueprint.model_dump_json().casefold()
    assert "rofx" in serialized
    assert "mql5" not in serialized
    assert "upi" not in serialized
    assert "110k" not in serialized
    assert {
        "evidence-cftc-funds-pip",
        "evidence-court-overview-pip",
    }.issubset({asset.id for asset in blueprint.assets})
    for asset in blueprint.assets:
        assert not asset.path.startswith(("C:/", "D:/", "C:\\", "D:\\"))
        assert (output / asset.path).is_file()
    sfx_assets = [
        asset
        for asset in blueprint.assets
        if asset.id.startswith("sfx-")
    ]
    sfx_hashes = {
        _module()._sha256(output / asset.path)
        for asset in sfx_assets
    }
    assert len(sfx_hashes) == len(sfx_assets)
