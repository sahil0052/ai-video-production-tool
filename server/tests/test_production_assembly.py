from datetime import UTC, datetime
import hashlib
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from app.editor.production_assembly import (
    _review_thresholds_for_plan,
    _measure_asr_retention,
    _measure_audio_continuity,
    assemble_production,
    build_production_master_command,
    calculate_layer_coverage,
    compile_production_plan,
    run_automated_production_review,
)
from app.editor.production_v4 import ProductionStore
from app.models import (
    AssetRef,
    AudioPlan,
    OutputSpec,
    TranscriptSegment,
    TranscriptWord,
    VideoMetadata,
)
from app.production_models import (
    BlueprintLayerSpec,
    CropSpec,
    EditPlanV2,
    FlowAcceptedClip,
    FlowColorCorrection,
    FlowShotSpec,
    ProductionBlueprint,
    ProductionJobRecord,
    VisualLayerSpec,
)


def _write_blueprint(output: Path, *, accepted: bool) -> None:
    presenter = output / "assets" / "presenter.mp4"
    background = output / "assets" / "background.png"
    flow = output / "accepted.mp4"
    presenter.parent.mkdir(parents=True)
    presenter.write_bytes(b"presenter")
    background.write_bytes(b"background")
    flow.write_bytes(b"flow")
    flow_shot = FlowShotSpec(
        id="flow-risk",
        start_ms=1000,
        end_ms=2000,
        editorial_role="physical-risk",
        prompt=(
            "A physical mechanism moves in one shot with no readable text, "
            "UI, code, charts, numbers or documents."
        ),
        mode="i2v",
        model="veo-lite",
        input_plates=[str(output / "start.png")],
        requested_content=["physical-metaphor"],
        constraints=["No readable text"],
        status="accepted" if accepted else "planned",
    )
    blueprint = ProductionBlueprint(
        source_filename="0806.mp4",
        source_metadata=VideoMetadata(
            width=1080,
            height=1920,
            fps=30,
            frame_count=90,
            duration_seconds=3,
        ),
        output=OutputSpec(),
        duration_ms=3000,
        assets=[
            AssetRef(
                id="presenter",
                kind="video",
                path="assets/presenter.mp4",
                provenance="user-provided",
            ),
            AssetRef(
                id="background",
                kind="image",
                path="assets/background.png",
                provenance="deterministic-test-background",
            ),
        ],
        layers=[
            BlueprintLayerSpec(
                id="background-layer",
                shot_id="shot-01",
                start_ms=0,
                end_ms=3000,
                source_role="deterministic-graphic",
                kind="image",
                asset_id="background",
                muted=True,
                z_index=1,
            ),
            BlueprintLayerSpec(
                id="presenter-layer",
                shot_id="shot-01",
                start_ms=0,
                end_ms=3000,
                source_role="presenter",
                asset_id="presenter",
                source_start_ms=0,
                source_end_ms=3000,
                muted=True,
            ),
            BlueprintLayerSpec(
                id="flow-layer",
                shot_id="shot-02",
                start_ms=1000,
                end_ms=2000,
                source_role="flow-illustrative",
                flow_shot_id="flow-risk",
                muted=True,
                illustrative_label=True,
                z_index=20,
            ),
        ],
        audio=AudioPlan(),
        flow_shots=[flow_shot],
    )
    (output / "blueprint.json").write_text(
        blueprint.model_dump_json(indent=2),
        encoding="utf-8",
    )
    now = datetime.now(UTC)
    clips = (
        [
            FlowAcceptedClip(
                shot_id="flow-risk",
                attempt=1,
                untouched_path=str(flow),
                proxy_path=str(flow),
                trim_start_ms=700,
                trim_end_ms=1700,
                crop=CropSpec(
                    x=0.05,
                    y=0.05,
                    width=0.9,
                    height=0.9,
                ),
                color_correction=FlowColorCorrection(
                    brightness=1.1,
                    contrast=1.05,
                    saturation=1.2,
                ),
                checksum_sha256=hashlib.sha256(
                    flow.read_bytes()
                ).hexdigest(),
            )
        ]
        if accepted
        else []
    )
    ProductionStore(output).create(
        ProductionJobRecord(
            id="production-0806",
            source_path="D:/Downloads/0806.mp4",
            output_dir=str(output),
            state="awaiting-candidate-review",
            primary_reference=10,
            secondary_reference=4,
            flow_operation_budget=3,
            approved_paid_operations=1,
            consumed_paid_operations=1,
            accepted_clips=clips,
            created_at=now,
            updated_at=now,
        )
    )


def test_0806_training_reference_review_uses_v7_targets() -> None:
    targets = _review_thresholds_for_plan(
        SimpleNamespace(
            reference_profile="technical-reference",
            story_profile="automation-future",
            source_filename="0806.mp4",
        )
    )

    assert targets["cut_min"] == 17
    assert targets["cut_max"] == 19
    assert targets["median_min_ms"] == 1800
    assert targets["median_max_ms"] == 2300
    assert targets["flow_max"] == 0
    assert targets["darkness_min"] == 0.35
    assert targets["darkness_max"] == 0.45
    assert targets["bright_min"] == 0.18
    assert targets["bright_max"] == 0.28


def test_0806_v8_review_uses_training_parity_targets() -> None:
    targets = _review_thresholds_for_plan(
        SimpleNamespace(
            reference_profile="technical-reference",
            story_profile="automation-future-parity",
            source_filename="0806.mp4",
        )
    )

    assert targets["profile"] == "0806-training-parity-v8"
    assert targets["presenter_min"] == 0.12
    assert targets["presenter_max"] == 0.16
    assert targets["flow_max"] == 0
    assert targets["composition_parity"] is True


def test_0806_v8_video_filter_preserves_dark_negative_space() -> None:
    import app.editor.production_assembly as assembly

    video_filter = assembly._production_video_filter(
        SimpleNamespace(
            reference_profile="technical-reference",
            story_profile="automation-future-parity",
            source_filename="0806.mp4",
        )
    )

    assert video_filter == (
        "eq=brightness=0.033:saturation=0.96,"
        "unsharp=5:5:1.0:5:5:0"
    )


def test_0806_v8_review_enforces_full_training_parity_gates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.editor.production_assembly as assembly

    caption_pages = [
        SimpleNamespace(
            start_ms=index * 900,
            end_ms=(index + 1) * 900,
            family="technical-mono",
            tokens=[
                SimpleNamespace(
                    text=f"WORD-{index}",
                    start_ms=index * 900,
                    end_ms=(index + 1) * 900,
                )
            ],
        )
        for index in range(8)
    ]
    plan = SimpleNamespace(
        reference_profile="technical-reference",
        story_profile="automation-future-parity",
        source_filename="0806.mp4",
        duration_ms=10_000,
        output=SimpleNamespace(width=1080, height=1920, fps=30),
        visual_layers=[],
        caption_pages=caption_pages,
        kinetic_text_cues=[],
        motion_events=[],
        audio=SimpleNamespace(
            sfx_cues=[],
            speech_protection_windows=[],
        ),
    )
    monkeypatch.setattr(
        assembly,
        "verify_render",
        lambda *_args, **_kwargs: SimpleNamespace(
            width=1080,
            height=1920,
            fps=30,
            duration_seconds=10,
        ),
    )
    monkeypatch.setattr(
        assembly,
        "measure_frame_audit",
        lambda *_args, **_kwargs: {
            "rendered_cut_count": 20,
            "cut_timestamps_seconds": [float(index) / 2 for index in range(20)],
            "median_shot_ms": 2000,
            "dark_frame_ratio": 0.4,
            "bright_frame_ratio": 0.2,
            "mean_luminance": 95,
            "luminance_p10": 15,
            "luminance_p90": 230,
            "mean_saturation": 65,
            "motion_score": 5,
        },
    )
    monkeypatch.setattr(
        assembly,
        "calculate_layer_coverage",
        lambda *_args, **_kwargs: {
            "real_direct_source_ratio": 0.6,
            "flow_ratio": 0,
            "deterministic_graphic_ratio": 0.25,
            "presenter_ratio": 0.14,
            "visual_source_count": 8,
        },
    )
    monkeypatch.setattr(
        assembly,
        "measure_loudness_for_master",
        lambda *_args, **_kwargs: SimpleNamespace(
            input_i=-14.2,
            input_tp=-1.1,
            input_lra=2.8,
        ),
    )
    monkeypatch.setattr(
        assembly,
        "_measure_audio_continuity",
        lambda **_kwargs: {
            "delay_passed": True,
            "duration_passed": True,
            "spectral_passed": True,
        },
    )
    monkeypatch.setattr(
        assembly,
        "_measure_asr_retention",
        lambda **_kwargs: {
            "retention_ratio": 0.995,
            "protected_terms_ok": True,
            "missing_protected_terms": [],
        },
    )
    acoustic_calls = 0

    def measure_acoustic(**_kwargs):
        nonlocal acoustic_calls
        acoustic_calls += 1
        return {
            "retention_ratio": 1,
            "verified_word_count": 102,
            "word_count": 102,
        }

    monkeypatch.setattr(
        assembly,
        "_measure_acoustic_word_retention",
        measure_acoustic,
    )
    monkeypatch.setattr(
        assembly,
        "_measure_evidence_ocr",
        lambda *_args, **_kwargs: {
            "passed": True,
            "terms": {
                "2008": True,
                "championship": True,
                "110000": True,
            },
        },
    )
    monkeypatch.setattr(
        assembly,
        "_measure_visual_diversity",
        lambda *_args, **_kwargs: {"unique_hashes": 8},
    )
    monkeypatch.setattr(
        assembly,
        "measure_composition_parity",
        lambda *_args, **_kwargs: {
            "edge_density_mean": 0.073,
            "near_static_pair_ratio": 0.41,
            "bright_uniform_blank_p90": 0.41,
            "dark_uniform_blank_mean": 0.36,
        },
    )
    monkeypatch.setattr(
        assembly,
        "_create_contact_sheet",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        assembly,
        "_create_reference_comparison",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        assembly,
        "measure_cut_onsets_for_video",
        lambda *_args, **_kwargs: 95,
    )
    monkeypatch.setattr(
        assembly,
        "_measure_rendered_bed_pulse",
        lambda **_kwargs: {
            "pulse_bpm": 90,
            "dialogue_scale": 1,
            "estimated_delay_ms": 0,
        },
        raising=False,
    )

    report = run_automated_production_review(
        output_dir=tmp_path,
        plan=plan,
        edited=tmp_path / "edited.mp4",
    )

    checks = {check["name"]: check for check in report["checks"]}
    assert acoustic_calls == 1
    assert checks["duration"]["passed"] is True
    assert checks["caption-coverage"]["passed"] is True
    assert checks["technical-mono-caption-share"]["passed"] is True
    assert checks["caption-token-containment"]["passed"] is True
    assert checks["bright-frame-ratio"]["passed"] is True
    assert checks["luminance-p10"]["passed"] is True
    assert checks["luminance-p90"]["passed"] is True
    assert checks["cut-audio-alignment"]["passed"] is True
    assert checks["mixed-audio-pulse"]["passed"] is True
    assert report["mixed_audio_pulse_bpm"] == 90
    assert report["automated_pass"] is True


def test_rendered_bed_pulse_subtracts_dialogue_before_tempo_analysis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.editor.production_assembly as assembly

    sample_rate = 48_000
    duration_seconds = 20
    time = np.arange(sample_rate * duration_seconds) / sample_rate
    dialogue = (
        4_000 * np.sin(2 * np.pi * 185 * time)
        + 1_500 * np.sin(2 * np.pi * 370 * time)
    )
    bed = np.zeros_like(dialogue)
    beat_interval = round(sample_rate * 60 / 90)
    pulse = np.hanning(960) * 4_000
    for start in range(0, bed.size - pulse.size, beat_interval):
        bed[start : start + pulse.size] += pulse
    final = dialogue * 1.8 + bed
    dialogue_path = Path("C:/audio/dialogue-original.wav")
    edited_path = Path("C:/video/edited.mp4")
    monkeypatch.setattr(
        assembly,
        "_extract_pcm",
        lambda path: dialogue if path == dialogue_path else final,
    )
    plan = SimpleNamespace(
        assets=[
            SimpleNamespace(
                id="dialogue-original",
                path=str(dialogue_path),
            )
        ]
    )

    result = assembly._measure_rendered_bed_pulse(
        plan=plan,
        edited=edited_path,
    )

    assert 89 <= result["pulse_bpm"] <= 91
    assert result["dialogue_scale"] == pytest.approx(1.8, abs=0.01)


def test_0806_v7_review_uses_acoustic_narration_retention(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = SimpleNamespace(
        reference_profile="technical-reference",
        story_profile="automation-future",
        source_filename="0806.mp4",
        duration_ms=41_400,
        output=SimpleNamespace(width=1080, height=1920, fps=30),
        visual_layers=[],
        caption_pages=[
            SimpleNamespace(start_ms=0, end_ms=29_808),
        ],
        audio=SimpleNamespace(
            sfx_cues=[],
            speech_protection_windows=[],
        ),
    )
    monkeypatch.setattr(
        "app.editor.production_assembly.verify_render",
        lambda *_args, **_kwargs: SimpleNamespace(
            width=1080,
            height=1920,
            fps=30,
            duration_seconds=41.4,
        ),
    )
    monkeypatch.setattr(
        "app.editor.production_assembly.measure_frame_audit",
        lambda *_args, **_kwargs: {
            "rendered_cut_count": 18,
            "cut_timestamps_seconds": [float(index * 2) for index in range(1, 19)],
            "median_shot_ms": 2100,
            "dark_frame_ratio": 0.4,
            "bright_frame_ratio": 0.2,
            "mean_luminance": 95,
            "luminance_p10": 15,
            "luminance_p90": 230,
            "mean_saturation": 65,
            "motion_score": 5.5,
        },
    )
    monkeypatch.setattr(
        "app.editor.production_assembly.calculate_layer_coverage",
        lambda *_args, **_kwargs: {
            "real_direct_source_ratio": 0.6,
            "flow_ratio": 0,
            "deterministic_graphic_ratio": 0.25,
            "presenter_ratio": 0.18,
            "visual_source_count": 6,
        },
    )
    monkeypatch.setattr(
        "app.editor.production_assembly.measure_loudness_for_master",
        lambda *_args, **_kwargs: SimpleNamespace(
            input_i=-14.2,
            input_tp=-1.1,
            input_lra=2.8,
        ),
    )
    monkeypatch.setattr(
        "app.editor.production_assembly._measure_audio_continuity",
        lambda **_kwargs: {
            "delay_passed": True,
            "duration_passed": True,
            "spectral_passed": True,
        },
    )
    monkeypatch.setattr(
        "app.editor.production_assembly._measure_asr_retention",
        lambda **_kwargs: {
            "retention_ratio": 0.981,
            "protected_terms_ok": True,
            "missing_protected_terms": [],
        },
    )
    acoustic_calls = 0

    def measure_acoustic(**_kwargs):
        nonlocal acoustic_calls
        acoustic_calls += 1
        return {
            "retention_ratio": 1,
            "verified_word_count": 101,
            "word_count": 101,
        }

    monkeypatch.setattr(
        "app.editor.production_assembly._measure_acoustic_word_retention",
        measure_acoustic,
    )
    monkeypatch.setattr(
        "app.editor.production_assembly._measure_evidence_ocr",
        lambda *_args, **_kwargs: {
            "passed": True,
            "terms": {
                "2008": True,
                "championship": True,
                "110000": True,
            },
        },
    )
    monkeypatch.setattr(
        "app.editor.production_assembly._measure_visual_diversity",
        lambda *_args, **_kwargs: {"unique_hashes": 6},
    )
    monkeypatch.setattr(
        "app.editor.production_assembly._create_contact_sheet",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        "app.editor.production_assembly._create_reference_comparison",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        "app.editor.production_assembly.measure_cut_onsets_for_video",
        lambda *_args, **_kwargs: 95,
    )

    report = run_automated_production_review(
        output_dir=tmp_path,
        plan=plan,
        edited=tmp_path / "edited.mp4",
    )

    narration = next(
        check
        for check in report["checks"]
        if check["name"] == "narration-retention"
    )
    assert acoustic_calls == 1
    assert narration["passed"] is True
    assert narration["measured"]["acoustic_words"]["retention_ratio"] == 1
    assert narration["measured"]["asr_token_retention_ratio"] == 0.981
    assert report["automated_pass"] is True


def test_compile_production_plan_resolves_accepted_flow_without_looping(
    tmp_path: Path,
) -> None:
    output = tmp_path / "production"
    output.mkdir()
    _write_blueprint(output, accepted=True)

    plan = compile_production_plan(output)

    flow = next(
        layer
        for layer in plan.visual_layers
        if layer.source_role == "flow-illustrative"
    )
    assert flow.muted is True
    assert flow.loop is False
    assert flow.illustrative_label is True
    assert flow.source_start_ms == 0
    assert flow.source_end_ms == 1000
    assert flow.playback_rate == 1
    assert flow.crop.x == pytest.approx(0.05)
    assert flow.crop.width == pytest.approx(0.9)
    assert "brightness(1.1)" in str(flow.color_filter)
    assert "contrast(1.05)" in str(flow.color_filter)
    assert "saturate(1.2)" in str(flow.color_filter)
    assert Path(
        next(asset for asset in plan.assets if asset.id == flow.asset_id).path
    ).is_file()

    coverage = calculate_layer_coverage(plan)
    assert coverage["coverage_method"] == "visible-layer-alpha-raster"
    assert coverage["presenter_ratio"] == pytest.approx(2 / 3, abs=0.01)
    assert coverage["flow_ratio"] == pytest.approx(1 / 3, abs=0.01)
    assert coverage["deterministic_graphic_ratio"] == pytest.approx(
        0,
        abs=0.01,
    )
    assert (
        coverage["presenter_ratio"] + coverage["flow_ratio"]
        <= 1.001
    )


def test_compile_production_plan_reuses_one_reviewed_flow_clip_across_layers(
    tmp_path: Path,
) -> None:
    output = tmp_path / "production"
    output.mkdir()
    _write_blueprint(output, accepted=True)
    blueprint_path = output / "blueprint.json"
    blueprint = json.loads(blueprint_path.read_text(encoding="utf-8"))
    original = next(
        layer
        for layer in blueprint["layers"]
        if layer.get("flow_shot_id") == "flow-risk"
    )
    original["end_ms"] = 1500
    original["source_start_ms"] = 0
    original["source_end_ms"] = 500
    original["crop"] = {
        "x": 0.1,
        "y": 0.2,
        "width": 0.5,
        "height": 0.6,
    }
    duplicate = {
        **original,
        "id": "flow-layer-detail",
        "start_ms": 1500,
        "end_ms": 2000,
        "source_start_ms": 500,
        "source_end_ms": 1000,
        "crop": {
            "x": 0.4,
            "y": 0.1,
            "width": 0.5,
            "height": 0.5,
        },
    }
    blueprint["layers"].append(duplicate)
    blueprint_path.write_text(
        json.dumps(blueprint),
        encoding="utf-8",
    )

    plan = compile_production_plan(output)
    flow_layers = [
        layer
        for layer in plan.visual_layers
        if layer.source_role == "flow-illustrative"
    ]

    assert len(flow_layers) == 2
    assert len(
        {
            asset.id
            for asset in plan.assets
            if asset.provenance == "google-flow-veo-illustrative"
        }
    ) == 1
    assert [
        (layer.source_start_ms, layer.source_end_ms)
        for layer in flow_layers
    ] == [(0, 500), (500, 1000)]
    composed_crops = [
        (
            layer.crop.x,
            layer.crop.y,
            layer.crop.width,
            layer.crop.height,
        )
        for layer in flow_layers
    ]
    assert composed_crops[0] == pytest.approx(
        (0.14, 0.23, 0.45, 0.54)
    )
    assert composed_crops[1] == pytest.approx(
        (0.41, 0.14, 0.45, 0.45)
    )


def test_compile_production_plan_blocks_unreviewed_flow(tmp_path: Path) -> None:
    output = tmp_path / "production"
    output.mkdir()
    _write_blueprint(output, accepted=False)

    with pytest.raises(ValueError, match="human-accepted Flow"):
        compile_production_plan(output)


def test_layer_coverage_uses_transparent_image_pixels(
    tmp_path: Path,
) -> None:
    alpha_path = tmp_path / "half-transparent.png"
    pixels = Image.new("RGBA", (100, 100), (255, 255, 255, 0))
    pixels.paste((255, 255, 255, 255), (0, 0, 50, 100))
    pixels.save(alpha_path)
    plan = EditPlanV2(
        source_filename="source.mp4",
        source_metadata=VideoMetadata(
            width=100,
            height=100,
            fps=30,
            frame_count=30,
            duration_seconds=1,
        ),
        output=OutputSpec(width=100, height=100, fps=30),
        duration_ms=1000,
        assets=[
            AssetRef(
                id="overlay",
                kind="image",
                path=str(alpha_path),
                provenance="deterministic-test-overlay",
            )
        ],
        visual_layers=[
            VisualLayerSpec(
                id="overlay-layer",
                shot_id="shot-01",
                start_ms=0,
                end_ms=1000,
                source_role="deterministic-graphic",
                kind="image",
                asset_id="overlay",
                bounds={
                    "x": 0,
                    "y": 0,
                    "width": 100,
                    "height": 100,
                },
                muted=True,
                fit="fill",
            )
        ],
        audio=AudioPlan(),
    )

    coverage = calculate_layer_coverage(plan)

    assert coverage["deterministic_graphic_ratio"] == pytest.approx(
        0.5,
        abs=0.02,
    )


def test_production_master_preserves_rendered_video_pixels(tmp_path: Path) -> None:
    command = build_production_master_command(
        executable=Path("ffmpeg.exe"),
        rendered=tmp_path / "rendered.mp4",
        output=tmp_path / "edited.mp4",
        measurement={
            "input_i": -18.2,
            "input_tp": -3.4,
            "input_lra": 3.2,
            "input_thresh": -28.0,
            "target_offset": 0.1,
        },
        duration_seconds=41.4,
    )

    assert command[command.index("-c:v") + 1] == "copy"
    assert "-vf" not in command
    assert "loudnorm=I=-14.2:TP=-1.2" in command[
        command.index("-af") + 1
    ]
    assert command[command.index("-ar") + 1] == "48000"


def test_production_master_accepts_social_kinetic_loudness_targets(
    tmp_path: Path,
) -> None:
    command = build_production_master_command(
        executable=Path("ffmpeg.exe"),
        rendered=tmp_path / "rendered.mp4",
        output=tmp_path / "edited.mp4",
        measurement={
            "input_i": -18.2,
            "input_tp": -3.4,
            "input_lra": 3.2,
            "input_thresh": -28.0,
            "target_offset": 0.1,
        },
        duration_seconds=44.37,
        target_lufs=-13.5,
        target_true_peak=-1.0,
        target_lra=2.4,
    )

    audio_filter = command[command.index("-af") + 1]
    assert "I=-13.5" in audio_filter
    assert "TP=-1" in audio_filter
    assert "LRA=2.4" in audio_filter


def test_production_master_uses_the_external_mix_instead_of_remotion_audio(
    tmp_path: Path,
) -> None:
    assert "audio_mix" in inspect.signature(
        build_production_master_command
    ).parameters

    command = build_production_master_command(
        executable=Path("ffmpeg.exe"),
        rendered=tmp_path / "rendered.mp4",
        audio_mix=tmp_path / "audio-mix.wav",
        output=tmp_path / "edited.mp4",
        measurement={
            "input_i": -18.2,
            "input_tp": -3.4,
            "input_lra": 3.2,
            "input_thresh": -28.0,
            "target_offset": 0.1,
        },
        duration_seconds=44.37,
    )

    assert str(tmp_path / "audio-mix.wav") in command
    mapped_audio = command.index("-map", command.index("-map") + 1)
    assert command[mapped_audio + 1] == "1:a:0"


def test_audio_mix_command_preserves_dialogue_and_schedules_music_and_sfx(
    tmp_path: Path,
) -> None:
    import app.editor.production_assembly as assembly

    builder = getattr(assembly, "build_production_audio_mix_command", None)
    assert builder is not None
    dialogue = tmp_path / "dialogue.wav"
    music = tmp_path / "music.mp3"
    effect = tmp_path / "effect.mp3"
    plan = SimpleNamespace(
        assets=[
            SimpleNamespace(
                id="dialogue",
                kind="audio",
                path=str(dialogue),
            ),
            SimpleNamespace(
                id="music",
                kind="audio",
                path=str(music),
            ),
            SimpleNamespace(
                id="effect",
                kind="audio",
                path=str(effect),
            ),
        ],
        audio=SimpleNamespace(
            dialogue_asset_id="dialogue",
            dialogue_offset_ms=0,
            music_asset_id="music",
            music_base_gain_db=-18,
            music_gain_automation=[
                SimpleNamespace(
                    start_ms=0,
                    end_ms=1_000,
                    gain_db=-6,
                )
            ],
            sfx_cues=[
                SimpleNamespace(
                    asset_id="effect",
                    start_ms=750,
                    source_start_ms=340,
                    duration_ms=100,
                    volume=0.35,
                    gain_db=-16,
                )
            ],
        ),
    )

    command = builder(
        executable=Path("ffmpeg.exe"),
        plan=plan,
        output=tmp_path / "audio-mix.wav",
        duration_seconds=3,
    )
    filter_graph = command[command.index("-filter_complex") + 1]

    assert str(dialogue) in command
    assert str(music) in command
    assert str(effect) in command
    assert "atrim=start=0.340:end=0.440" in filter_graph
    assert "adelay=750|750" in filter_graph
    assert "amix=inputs=3:normalize=0" in filter_graph
    assert command[command.index("-map") + 1] == "[mix]"


@pytest.mark.parametrize(
    "story_profile",
    ["automation-future", "automation-future-parity"],
)
def test_0806_technical_audio_mix_controls_loudness_range(
    tmp_path: Path,
    story_profile: str,
) -> None:
    import app.editor.production_assembly as assembly

    dialogue = tmp_path / "dialogue.wav"
    plan = SimpleNamespace(
        reference_profile="technical-reference",
        story_profile=story_profile,
        source_filename="0806.mp4",
        assets=[
            SimpleNamespace(
                id="dialogue",
                kind="audio",
                path=str(dialogue),
            )
        ],
        audio=SimpleNamespace(
            dialogue_asset_id="dialogue",
            dialogue_offset_ms=0,
            music_asset_id=None,
            music_base_gain_db=-28,
            music_gain_automation=[],
            sfx_cues=[],
        ),
    )

    command = assembly.build_production_audio_mix_command(
        executable=Path("ffmpeg.exe"),
        plan=plan,
        output=tmp_path / "audio-mix.wav",
        duration_seconds=41.4,
    )
    filter_graph = command[command.index("-filter_complex") + 1]

    assert "acompressor=" in filter_graph


@pytest.mark.parametrize(
    "story_profile",
    ["automation-future", "automation-future-parity"],
)
def test_0806_technical_master_uses_calibrated_reference_grade(
    story_profile: str,
) -> None:
    import app.editor.production_assembly as assembly

    plan = SimpleNamespace(
        reference_profile="technical-reference",
        story_profile=story_profile,
        source_filename="0806.mp4",
        voice_policy="preserve-verbatim",
    )

    assert (
        assembly._production_video_filter(plan)
        == (
            "eq=brightness=0.033:saturation=0.96,"
            "unsharp=5:5:1.0:5:5:0"
        )
    )


def test_social_kinetic_review_uses_role_timestamps_and_story_terms():
    import app.editor.production_assembly as assembly

    timestamp_builder = getattr(
        assembly,
        "_evidence_review_timestamps",
        None,
    )
    terms_builder = getattr(
        assembly,
        "_protected_terms_for_plan",
        None,
    )
    assert timestamp_builder is not None
    assert terms_builder is not None
    plan = SimpleNamespace(
        reference_profile="social-kinetic",
        visual_layers=[
            SimpleNamespace(
                start_ms=5_650,
                end_ms=6_450,
                source_role="direct-evidence",
            )
        ],
    )

    assert timestamp_builder(plan) == [6.05]
    terms, aliases = terms_builder(plan)
    assert "Profit Bricks" in terms
    assert "demo" in terms
    assert "Telegram group" not in terms
    assert "EA" in aliases
    assert "3-month" in aliases["3 months"]


def test_rofx_review_uses_rofx_evidence_and_narration_requirements():
    import app.editor.production_assembly as assembly

    evidence_builder = getattr(
        assembly,
        "_evidence_terms_for_plan",
        None,
    )
    assert evidence_builder is not None
    plan = SimpleNamespace(
        reference_profile="social-kinetic",
        story_profile="rofx-case",
        source_filename="0811.mp4",
    )

    protected_terms, protected_aliases = assembly._protected_terms_for_plan(
        plan
    )
    evidence_terms = evidence_builder(plan)

    assert protected_terms == [
        "Zomato",
        "ROFX",
        "forex trading",
        "1,100",
        "federal court",
        "April 2024",
        "transparent",
        "follow us",
    ]
    assert protected_aliases["1,100"] == ["1100"]
    assert set(evidence_terms) == {
        "1100",
        "58m",
        "no-forex-trading",
        "225m",
    }
    assert "2008" not in evidence_terms


def test_acoustic_word_retention_verifies_each_aligned_spoken_window(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.editor.production_assembly as assembly

    measurer = getattr(
        assembly,
        "_measure_acoustic_word_retention",
        None,
    )
    assert measurer is not None
    (tmp_path / "transcript-aligned.json").write_text(
        json.dumps(
            [
                {
                    "start": 0,
                    "end": 0.2,
                    "text": "hello world",
                    "words": [
                        {
                            "start": 0,
                            "end": 0.1,
                            "text": "hello",
                            "confidence": None,
                        },
                        {
                            "start": 0.1,
                            "end": 0.2,
                            "text": "world",
                            "confidence": None,
                        },
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    source_path = Path("C:/audio/dialogue-original.wav")
    edited_path = Path("C:/video/edited.mp4")
    signal = [
        ((index % 31) - 15) * (1 if index % 2 else -1)
        for index in range(9_600)
    ]
    monkeypatch.setattr(
        assembly,
        "_extract_pcm",
        lambda path: signal if path in {source_path, edited_path} else [],
    )
    monkeypatch.setattr(
        assembly,
        "estimate_audio_delay_ms",
        lambda *_args, **_kwargs: 0,
    )
    plan = SimpleNamespace(
        assets=[
            SimpleNamespace(
                id="dialogue-original",
                path=str(source_path),
            )
        ]
    )

    report = measurer(
        output_dir=tmp_path,
        plan=plan,
        edited=edited_path,
    )

    assert report["retention_ratio"] == 1
    assert report["verified_word_count"] == 2


def test_social_kinetic_acoustic_retention_verifies_protected_terms(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.editor.production_assembly as assembly

    words = [
        "2008",
        "teen",
        "mahine",
        "Forex",
        "robot",
        "EA",
        "UPI",
        "Profit",
        "Bricks",
        "risk",
        "demo",
    ]
    (tmp_path / "transcript-aligned.json").write_text(
        json.dumps(
            [
                {
                    "start": 0,
                    "end": len(words) * 0.1,
                    "text": " ".join(words),
                    "words": [
                        {
                            "start": index * 0.1,
                            "end": (index + 1) * 0.1,
                            "text": word,
                            "confidence": None,
                        }
                        for index, word in enumerate(words)
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    source_path = Path("C:/audio/dialogue-original.wav")
    edited_path = Path("C:/video/edited.mp4")
    signal = [
        ((index % 41) - 20) * (1 if index % 3 else -1)
        for index in range(60_000)
    ]
    monkeypatch.setattr(
        assembly,
        "_extract_pcm",
        lambda path: signal if path in {source_path, edited_path} else [],
    )
    monkeypatch.setattr(
        assembly,
        "estimate_audio_delay_ms",
        lambda *_args, **_kwargs: 0,
    )
    plan = SimpleNamespace(
        reference_profile="social-kinetic",
        assets=[
            SimpleNamespace(
                id="dialogue-original",
                path=str(source_path),
            )
        ],
    )

    report = assembly._measure_acoustic_word_retention(
        output_dir=tmp_path,
        plan=plan,
        edited=edited_path,
    )

    assert report["protected_terms_ok"] is True
    assert report["missing_protected_terms"] == []


def test_social_kinetic_mastering_calibrates_dynamic_loudnorm_target():
    import app.editor.production_assembly as assembly

    calibrator = getattr(assembly, "_mastering_lufs_target", None)
    peak_calibrator = getattr(
        assembly,
        "_mastering_true_peak_target",
        None,
    )
    assert calibrator is not None
    assert peak_calibrator is not None
    assert calibrator(-13.5, 2.4) == -13.5
    assert calibrator(-14.2, 5.0) == -14.2
    assert peak_calibrator(-1.0, 2.4) == -1.1
    assert peak_calibrator(-1.2, 5.0) == -1.2


def test_rofx_evidence_review_samples_verified_kinetic_numbers():
    import app.editor.production_assembly as assembly

    plan = SimpleNamespace(
        story_profile="rofx-case",
        visual_layers=[],
        kinetic_text_cues=[
            SimpleNamespace(
                start_ms=18_500,
                end_ms=19_600,
                text="1,100+ CUSTOMERS",
            ),
            SimpleNamespace(
                start_ms=22_000,
                end_ms=23_100,
                text="AT LEAST $58M",
            ),
            SimpleNamespace(
                start_ms=26_300,
                end_ms=27_700,
                text="NO FOREX TRADING",
            ),
            SimpleNamespace(
                start_ms=33_400,
                end_ms=34_900,
                text="OVER $225M ORDERED",
            ),
        ],
    )

    timestamps = assembly._evidence_review_timestamps(plan)

    assert timestamps == [19.05, 22.55, 27.0, 34.15]


def test_evidence_ocr_uses_grayscale_and_thresholded_variants():
    import app.editor.production_assembly as assembly

    frame = np.zeros((20, 30, 3), dtype=np.uint8)
    variants = assembly._evidence_ocr_variants(frame)

    assert set(variants) == {"original", "grayscale", "otsu"}
    assert variants["original"].shape == (20, 30, 3)
    assert variants["grayscale"].shape == (20, 30)
    assert variants["otsu"].shape == (20, 30)


def test_automated_review_blocks_failed_spectral_continuity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = SimpleNamespace(
        output=SimpleNamespace(width=1080, height=1920, fps=30),
        visual_layers=[],
        audio=SimpleNamespace(
            sfx_cues=[],
            speech_protection_windows=[],
        ),
    )
    frame_audit = {
        "rendered_cut_count": 21,
        "median_shot_ms": 1600,
        "dark_frame_ratio": 0.2,
        "mean_luminance": 95,
        "mean_saturation": 65,
        "motion_score": 5.4,
    }
    coverage = {
        "real_direct_source_ratio": 0.6,
        "flow_ratio": 0.1,
        "deterministic_graphic_ratio": 0.2,
        "presenter_ratio": 0.16,
        "visual_source_count": 6,
    }
    audio_continuity = {
        "delay_passed": True,
        "duration_passed": True,
        "spectral_passed": False,
        "spectral_continuity_db": 12.5,
    }
    monkeypatch.setattr(
        "app.editor.production_assembly.verify_render",
        lambda *_args, **_kwargs: SimpleNamespace(
            width=1080,
            height=1920,
            fps=30,
            duration_seconds=41.4,
        ),
    )
    monkeypatch.setattr(
        "app.editor.production_assembly.measure_frame_audit",
        lambda *_args, **_kwargs: frame_audit,
    )
    monkeypatch.setattr(
        "app.editor.production_assembly.calculate_layer_coverage",
        lambda *_args, **_kwargs: coverage,
    )
    monkeypatch.setattr(
        "app.editor.production_assembly.measure_loudness_for_master",
        lambda *_args, **_kwargs: SimpleNamespace(
            input_i=-14.2,
            input_tp=-1.1,
        ),
    )
    monkeypatch.setattr(
        "app.editor.production_assembly._measure_audio_continuity",
        lambda **_kwargs: audio_continuity,
    )
    monkeypatch.setattr(
        "app.editor.production_assembly._measure_asr_retention",
        lambda **_kwargs: {
            "retention_ratio": 1,
            "protected_terms_ok": True,
            "missing_protected_terms": [],
        },
    )
    monkeypatch.setattr(
        "app.editor.production_assembly._measure_acoustic_word_retention",
        lambda **_kwargs: {
            "retention_ratio": 1,
            "verified_word_count": 100,
            "word_count": 100,
        },
    )
    monkeypatch.setattr(
        "app.editor.production_assembly._measure_evidence_ocr",
        lambda *_args, **_kwargs: {
            "passed": True,
            "terms": {
                "2008": True,
                "championship": True,
                "110000": True,
            },
        },
    )
    monkeypatch.setattr(
        "app.editor.production_assembly._measure_visual_diversity",
        lambda *_args, **_kwargs: {"unique_hashes": 6},
    )
    monkeypatch.setattr(
        "app.editor.production_assembly._create_contact_sheet",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        "app.editor.production_assembly._create_reference_comparison",
        lambda **_kwargs: None,
    )

    report = run_automated_production_review(
        output_dir=tmp_path,
        plan=plan,
        edited=tmp_path / "edited.mp4",
    )

    continuity_check = next(
        check
        for check in report["checks"]
        if check["name"] == "audio-continuity"
    )
    assert continuity_check["passed"] is False
    assert report["automated_pass"] is False


def test_social_kinetic_review_uses_human_reference_thresholds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = SimpleNamespace(
        reference_profile="social-kinetic",
        duration_ms=44_370,
        output=SimpleNamespace(width=1080, height=1920, fps=30),
        visual_layers=[],
        kinetic_text_cues=[
            SimpleNamespace(start_ms=0, end_ms=9_000),
            SimpleNamespace(start_ms=2_000, end_ms=8_000),
        ],
        motion_events=[SimpleNamespace() for _ in range(28)],
        audio=SimpleNamespace(
            sfx_cues=[],
            speech_protection_windows=[],
        ),
    )
    monkeypatch.setattr(
        "app.editor.production_assembly.verify_render",
        lambda *_args, **_kwargs: SimpleNamespace(
            width=1080,
            height=1920,
            fps=30,
            duration_seconds=44.37,
        ),
    )
    monkeypatch.setattr(
        "app.editor.production_assembly.measure_frame_audit",
        lambda *_args, **_kwargs: {
            "rendered_cut_count": 15,
            "cut_timestamps_seconds": [3.4, 5.65, 7.2],
            "median_shot_ms": 2700,
            "dark_frame_ratio": 0.03,
            "mean_luminance": 101,
            "mean_saturation": 75,
            "motion_score": 5.2,
        },
    )
    monkeypatch.setattr(
        "app.editor.production_assembly.calculate_layer_coverage",
        lambda *_args, **_kwargs: {
            "real_direct_source_ratio": 0.75,
            "flow_ratio": 0.16,
            "deterministic_graphic_ratio": 0.09,
            "presenter_ratio": 0.62,
            "visual_source_count": 7,
        },
    )
    monkeypatch.setattr(
        "app.editor.production_assembly.measure_loudness_for_master",
        lambda *_args, **_kwargs: SimpleNamespace(
            input_i=-13.5,
            input_tp=-1.1,
            input_lra=2.4,
        ),
    )
    monkeypatch.setattr(
        "app.editor.production_assembly._measure_audio_continuity",
        lambda **_kwargs: {
            "delay_passed": True,
            "duration_passed": True,
            "spectral_passed": True,
        },
    )
    monkeypatch.setattr(
        "app.editor.production_assembly._measure_asr_retention",
        lambda **_kwargs: {
            "retention_ratio": 1,
            "protected_terms_ok": True,
            "missing_protected_terms": [],
        },
    )
    monkeypatch.setattr(
        "app.editor.production_assembly._measure_acoustic_word_retention",
        lambda **_kwargs: {
            "retention_ratio": 1,
            "verified_word_count": 100,
            "word_count": 100,
        },
    )
    monkeypatch.setattr(
        "app.editor.production_assembly._measure_evidence_ocr",
        lambda *_args, **_kwargs: {
            "passed": True,
            "terms": {
                "2008": True,
                "championship": True,
                "110000": True,
            },
        },
    )
    monkeypatch.setattr(
        "app.editor.production_assembly._measure_visual_diversity",
        lambda *_args, **_kwargs: {"unique_hashes": 7},
    )
    monkeypatch.setattr(
        "app.editor.production_assembly._create_contact_sheet",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        "app.editor.production_assembly._create_reference_comparison",
        lambda **_kwargs: None,
    )
    measured_cut_times: list[int] = []

    def fake_cut_alignment(_path: Path, event_times_ms: list[int]) -> float:
        measured_cut_times.extend(event_times_ms)
        return 87.5

    monkeypatch.setattr(
        "app.editor.production_assembly.measure_cut_onsets_for_video",
        fake_cut_alignment,
        raising=False,
    )

    report = run_automated_production_review(
        output_dir=tmp_path,
        plan=plan,
        edited=tmp_path / "edited.mp4",
    )

    checks = {check["name"]: check for check in report["checks"]}
    assert checks["rendered-hard-cuts"]["target"] == "13-16"
    assert checks["median-shot"]["target"] == "2300-3000 ms"
    assert checks["presenter-pixels"]["target"] == "0.58-0.68"
    assert checks["flow-pixels"]["target"] == "<= 0.18"
    assert checks["semantic-text-coverage"]["passed"] is True
    assert checks["motion-event-density"]["passed"] is True
    assert checks["duration"]["passed"] is True
    assert checks["loudness"]["passed"] is True
    assert checks["hero-text-height"]["passed"] is True
    assert checks["outlined-text-height"]["passed"] is True
    assert checks["cut-audio-alignment"]["passed"] is True
    assert report["typography"] == {
        "hero_text_height_px": 196,
        "outlined_text_height_px": 114,
        "measurement_method": "renderer-profile-computed-style",
    }
    assert report["audio_alignment"] == {
        "cut_audio_alignment_percent": 87.5,
        "window_ms": 100,
        "cut_count": 3,
    }
    assert measured_cut_times == [3400, 5650, 7200]
    assert report["automated_pass"] is True


def test_failed_automated_review_returns_to_actionable_revision_state(
    tmp_path: Path,
) -> None:
    output = tmp_path / "production"
    output.mkdir()
    _write_blueprint(output, accepted=True)

    def fake_renderer(**kwargs) -> None:
        kwargs["output"].write_bytes(b"rendered")

    def fake_masterer(**kwargs) -> None:
        kwargs["output"].write_bytes(b"edited")

    result = assemble_production(
        output_dir=output,
        renderer=fake_renderer,
        masterer=fake_masterer,
        reviewer=lambda **_kwargs: {"automated_pass": False},
    )

    assert result["state"] == "awaiting-candidate-review"
    record = ProductionStore(output).load()
    assert record.state == "awaiting-candidate-review"
    assert record.automated_pass is False


def test_render_failure_restores_an_actionable_revision_state(
    tmp_path: Path,
) -> None:
    output = tmp_path / "production"
    output.mkdir()
    _write_blueprint(output, accepted=True)

    def failing_renderer(**_kwargs) -> None:
        raise RuntimeError("render failed")

    with pytest.raises(RuntimeError, match="render failed"):
        assemble_production(
            output_dir=output,
            renderer=failing_renderer,
        )

    assert ProductionStore(output).load().state == (
        "awaiting-candidate-review"
    )


def test_audio_continuity_uses_untouched_dialogue_as_the_source_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extracted: list[Path] = []

    def fake_extract(path: Path):
        extracted.append(path)
        return [1.0] * 4800

    monkeypatch.setattr(
        "app.editor.production_assembly._extract_pcm",
        fake_extract,
    )
    monkeypatch.setattr(
        "app.editor.production_assembly.build_audio_continuity_report",
        lambda *_args, **_kwargs: {"delay_passed": True},
    )
    plan = SimpleNamespace(
        assets=[
            SimpleNamespace(
                id="dialogue-original",
                path="C:/audio/dialogue-original.wav",
            ),
            SimpleNamespace(
                id="dialogue-processed",
                path="C:/audio/dialogue-processed.wav",
            ),
        ],
        audio=SimpleNamespace(dialogue_asset_id="dialogue-processed"),
    )

    _measure_audio_continuity(
        plan=plan,
        edited=Path("C:/video/edited.mp4"),
    )

    assert extracted == [
        Path("C:/audio/dialogue-original.wav"),
        Path("C:/video/edited.mp4"),
    ]


def test_asr_retention_uses_untouched_dialogue_as_the_source_baseline(
    tmp_path: Path,
) -> None:
    aligned = TranscriptSegment(
        start=0,
        end=1,
        text="The high risk increased the result.",
        words=[],
    )
    (tmp_path / "transcript-aligned.json").write_text(
        json.dumps([aligned.model_dump(mode="json")]),
        encoding="utf-8",
    )
    transcribed: list[Path] = []

    def fake_transcriber(path: Path) -> list[TranscriptSegment]:
        transcribed.append(path)
        return [
            TranscriptSegment(
                start=0,
                end=1,
                text="The high risk increased the returns.",
                words=[],
            )
        ]

    plan = SimpleNamespace(
        assets=[
            SimpleNamespace(
                id="dialogue-original",
                path="C:/audio/dialogue-original.wav",
            ),
            SimpleNamespace(
                id="dialogue-processed",
                path="C:/audio/dialogue-processed.wav",
            ),
        ],
        audio=SimpleNamespace(dialogue_asset_id="dialogue-processed"),
    )

    report = _measure_asr_retention(
        output_dir=tmp_path,
        plan=plan,
        edited=Path("C:/video/edited.mp4"),
        transcriber=fake_transcriber,
    )

    assert transcribed == [
        Path("C:/audio/dialogue-original.wav"),
        Path("C:/video/edited.mp4"),
    ]
    assert report["retention_ratio"] == 1
    assert report["source_text"] == "The high risk increased the returns."


def test_0806_v8_asr_review_forces_english_transcription(
    tmp_path: Path,
    monkeypatch,
) -> None:
    transcribed: list[tuple[Path, str]] = []
    text = (
        "Do Forex Trading Robot Expert Advisor 2008 110000 "
        "Telegram group Thank you"
    )

    def fake_fixed_language(
        path: Path,
        *,
        language: str,
    ) -> list[TranscriptSegment]:
        transcribed.append((path, language))
        return [
            TranscriptSegment(
                start=0,
                end=1,
                text=text,
                words=[],
            )
        ]

    monkeypatch.setattr(
        "app.editor.pipeline.transcribe_video_fixed_language",
        fake_fixed_language,
    )
    plan = SimpleNamespace(
        reference_profile="technical-reference",
        story_profile="automation-future-parity",
        source_filename="0806.mp4",
        assets=[
            SimpleNamespace(
                id="dialogue-original",
                path="C:/audio/dialogue-original.wav",
            )
        ],
    )

    report = _measure_asr_retention(
        output_dir=tmp_path,
        plan=plan,
        edited=Path("C:/video/edited.mp4"),
        transcriber=None,
    )

    assert transcribed == [
        (Path("C:/audio/dialogue-original.wav"), "en"),
        (Path("C:/video/edited.mp4"), "en"),
    ]
    assert report["retention_ratio"] == 1
    assert report["protected_terms_ok"] is True


def test_asr_retention_ignores_unaligned_source_asr_tokens(
    tmp_path: Path,
) -> None:
    source_segment = TranscriptSegment(
        start=0,
        end=1,
        text="But what if the rules are wrong?",
        words=[
            TranscriptWord(start=0, end=0.2, text="But"),
            TranscriptWord(start=0.2, end=0.2, text="what"),
            TranscriptWord(start=0.2, end=0.4, text="if"),
            TranscriptWord(start=0.4, end=0.5, text="the"),
            TranscriptWord(start=0.5, end=0.7, text="rules"),
            TranscriptWord(start=0.7, end=0.8, text="are"),
            TranscriptWord(start=0.8, end=1, text="wrong"),
        ],
    )
    final_segment = TranscriptSegment(
        start=0,
        end=1,
        text="But if the rules are wrong.",
        words=[],
    )

    def fake_transcriber(path: Path) -> list[TranscriptSegment]:
        if path.name == "dialogue-original.wav":
            return [source_segment]
        return [final_segment]

    plan = SimpleNamespace(
        assets=[
            SimpleNamespace(
                id="dialogue-original",
                path="C:/audio/dialogue-original.wav",
            )
        ],
    )

    report = _measure_asr_retention(
        output_dir=tmp_path,
        plan=plan,
        edited=Path("C:/video/edited.mp4"),
        transcriber=fake_transcriber,
    )

    assert report["retention_ratio"] == 1
    assert report["ignored_unaligned_source_tokens"] == ["what"]
    assert report["raw_source_token_count"] == 7
    assert report["source_token_count"] == 6
    assert report["source_text"] == "But what if the rules are wrong?"
    assert report["source_token_policy"] == (
        "exclude-missing-zero-duration-source-tokens"
    )
