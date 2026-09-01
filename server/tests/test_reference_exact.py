import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image
import numpy as np

from app.editor.reference_exact import (
    EXACT_REFERENCE_CUTS_MS,
    EXACT_REFERENCE_DURATION_MS,
    build_reference_overlays,
    build_exact_reference_blueprint,
    build_exact_audio_mux_command,
    build_exact_reference_layers,
    evaluate_exact_reference_match,
    _recover_gradient_text_overlay,
    assemble_exact_reference,
    measure_frame_pair_similarity,
    render_exact_reference_plan,
)
from app.models import AssetRef, AudioPlan, OutputSpec, VideoMetadata
from app.production_models import (
    EditPlanV2,
    ProductionBlueprint,
    VisualLayerSpec,
)


def test_exact_reference_layers_follow_the_supplied_edit_timeline() -> None:
    layers = build_exact_reference_layers()
    base_layers = [
        layer
        for layer in layers
        if layer.source_role != "deterministic-graphic"
    ]

    assert EXACT_REFERENCE_DURATION_MS == 34933
    assert EXACT_REFERENCE_CUTS_MS == [
        2267,
        5733,
        9533,
        11767,
        14433,
        18167,
        19700,
        22633,
        23667,
        25667,
        27400,
        30433,
    ]
    assert [layer.start_ms for layer in base_layers] == [
        0,
        2_267,
        5_733,
        9_533,
        10_200,
        11_767,
        14_433,
        18_167,
        18_933,
        19_700,
        22_633,
        23_667,
        25_667,
        27_400,
        30_433,
        30_633,
    ]
    assert [layer.end_ms for layer in base_layers] == [
        2_267,
        5_733,
        9_533,
        10_200,
        11_767,
        14_433,
        18_167,
        18_933,
        19_700,
        22_633,
        23_667,
        25_667,
        27_400,
        30_433,
        30_633,
        EXACT_REFERENCE_DURATION_MS,
    ]
    presenter_ms = sum(
        layer.end_ms - layer.start_ms
        for layer in base_layers
        if layer.source_role == "presenter"
    )
    assert presenter_ms / EXACT_REFERENCE_DURATION_MS == pytest.approx(
        0.7176,
        abs=0.001,
    )
    typography_layers = [
        layer
        for layer in layers
        if layer.id.startswith(
            (
                "exact-hook-",
                "exact-ea-",
                "exact-number-",
            )
        )
    ]
    vignette_layers = [
        layer for layer in layers if layer.id.endswith("-vignette")
    ]
    assert len(typography_layers) == 6
    assert len(vignette_layers) == 7
    assert all(layer.z_index < 100 for layer in vignette_layers)
    assert not any(layer.illustrative_label for layer in layers)


def test_exact_reference_presenter_conform_uses_take_specific_rates() -> None:
    layers = {
        layer.id: layer
        for layer in build_exact_reference_layers()
    }

    assert layers["exact-presenter-hook"].source_start_ms == 167
    assert layers["exact-presenter-hook"].source_end_ms == 2_433
    assert layers["exact-presenter-hook"].playback_rate == 1
    assert layers["exact-presenter-ea"].source_start_ms == 7_233
    assert layers["exact-presenter-ea"].source_end_ms == 11_033
    assert layers["exact-presenter-ea"].playback_rate == 1
    assert layers["exact-presenter-number"].source_start_ms == 17_967
    assert layers["exact-presenter-number"].source_end_ms == 21_700
    assert layers["exact-presenter-number"].playback_rate == 1
    assert layers["exact-presenter-cta"].source_start_ms == 33_467
    assert layers["exact-presenter-cta"].source_end_ms == 36_500
    assert layers["exact-presenter-cta"].playback_rate == 1
    assert layers["exact-reference-wrong-punch"].asset_id == (
        "reference-master"
    )
    assert layers["exact-presenter-wrong"].source_start_ms == 13_133
    assert layers["exact-reference-ending-flash"].asset_id == (
        "reference-master"
    )
    assert layers["exact-presenter-ending"].source_start_ms == 36_900
    assert layers["exact-presenter-ending"].source_end_ms == 41_200
    assert layers["exact-presenter-ending"].playback_rate == 1

    assert layers["exact-presenter-wrong"].transform_keyframes[
        0
    ].scale == pytest.approx(1.143, abs=0.002)
    assert layers["exact-presenter-wrong"].transform_keyframes[
        -1
    ].scale == pytest.approx(1.218, abs=0.002)
    assert layers["exact-presenter-risk-a"].transform_keyframes[
        0
    ].scale == pytest.approx(1.0)
    assert layers["exact-presenter-risk-a"].transform_keyframes[
        -1
    ].scale == pytest.approx(1.16)
    assert layers["exact-presenter-risk-a"].source_start_ms == 21_867
    assert layers["exact-presenter-risk-b"].source_start_ms == 22_900
    assert layers["exact-presenter-risk-b"].source_end_ms == 23_667
    assert layers["exact-presenter-ending"].transform_keyframes[
        0
    ].scale == pytest.approx(1.0)
    assert all(
        layer.color_filter is None
        for layer in layers.values()
        if layer.source_role == "presenter"
    )


def test_exact_reference_overlay_motion_matches_measured_entrances() -> None:
    layers = {
        layer.id: layer
        for layer in build_exact_reference_layers()
    }

    assert layers["exact-hook-accent"].start_ms == 867
    assert layers["exact-hook-white"].start_ms == 967

    number = layers["exact-number-accent"]
    assert number.start_ms == 15_767
    assert [
        (keyframe.at_ms, keyframe.value)
        for keyframe in number.opacity_keyframes
    ] == [(0, 1)]
    assert [
        (keyframe.at_ms, keyframe.y)
        for keyframe in number.transform_keyframes[:5]
    ] == [
        (0, 420),
        (33, 351),
        (133, 200),
        (233, 123),
        (333, 78),
    ]
    assert number.transform_keyframes[-2].at_ms == 1_133
    assert number.transform_keyframes[-2].y == 0
    assert number.transform_keyframes[-1].at_ms == 2_400
    assert number.transform_keyframes[-1].y == 0

    preflash = layers["exact-reference-ending-prefire"]
    assert preflash.start_ms == 30_367
    assert preflash.end_ms == 30_433
    assert preflash.source_start_ms == 30_367
    assert preflash.source_end_ms == 30_433
    assert preflash.source_role == "deterministic-graphic"
    assert preflash.z_index == 90


def test_exact_audio_mux_copies_reference_audio_stream() -> None:
    command = build_exact_audio_mux_command(
        executable=Path("ffmpeg.exe"),
        rendered=Path("rendered.mp4"),
        reference=Path("reference.mp4"),
        output=Path("edited.mp4"),
    )

    assert command[command.index("-map") + 1] == "0:v:0"
    second_map = command.index("-map", command.index("-map") + 1)
    assert command[second_map + 1] == "1:a:0"
    assert command[command.index("-c:v") + 1] == "copy"
    assert command[command.index("-c:a") + 1] == "copy"
    assert "-shortest" in command


def test_exact_blueprint_writes_sparse_reference_assets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "0806.mp4"
    reference = tmp_path / "reference.mp4"
    source.write_bytes(b"source")
    reference.write_bytes(b"reference")
    output = tmp_path / "production-v5"

    monkeypatch.setattr(
        "app.editor.reference_exact.probe_video",
        lambda _path: VideoMetadata(
            width=1080,
            height=1920,
            fps=30,
            frame_count=1242,
            duration_seconds=41.4,
        ),
    )

    def fake_overlays(
        _reference: Path,
        output_dir: Path,
    ) -> dict[str, Path]:
        assets: dict[str, Path] = {}
        for asset_id in (
            "overlay-hook-white",
            "overlay-hook-accent",
            "overlay-ea-white",
            "overlay-ea-accent",
            "overlay-number-white",
            "overlay-number-accent",
            "overlay-presenter-vignette",
        ):
            path = output_dir / "assets" / "overlays" / f"{asset_id}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGBA", (1080, 1920), (0, 0, 0, 0)).save(path)
            assets[asset_id] = path
        return assets

    artifacts = build_exact_reference_blueprint(
        source=source,
        reference=reference,
        output_dir=output,
        overlay_builder=fake_overlays,
    )

    blueprint = ProductionBlueprint.model_validate_json(
        (output / artifacts["blueprint"]).read_text(encoding="utf-8")
    )
    assert blueprint.duration_ms == EXACT_REFERENCE_DURATION_MS
    assert blueprint.caption_pages == []
    assert blueprint.flow_shots == []
    assert len(blueprint.layers) == 30
    assets = {asset.id: asset for asset in blueprint.assets}
    assert assets["reference-master"].provenance == (
        "user-provided-reference"
    )
    assert assets["source-presenter"].provenance == "user-provided"
    assert (output / "production-job.json").is_file()
    storyboard = {
        shot["id"]: shot
        for shot in json.loads(
            (output / artifacts["storyboard"]).read_text(encoding="utf-8")
        )
    }
    assert storyboard["exact-shot-04"]["start_ms"] == 9_533
    assert storyboard["exact-shot-04"]["end_ms"] == 11_767
    assert storyboard["exact-shot-04"]["asset_ids"] == [
        "reference-master",
        "source-presenter",
    ]
    assert storyboard["exact-shot-13"]["start_ms"] == 30_433
    assert storyboard["exact-shot-13"]["end_ms"] == 34_933


def test_exact_blueprint_passes_raw_source_to_default_overlay_builder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "0806.mp4"
    reference = tmp_path / "reference.mp4"
    source.write_bytes(b"source")
    reference.write_bytes(b"reference")
    output = tmp_path / "production-v5"
    received: dict[str, Path] = {}

    monkeypatch.setattr(
        "app.editor.reference_exact.probe_video",
        lambda _path: VideoMetadata(
            width=1080,
            height=1920,
            fps=30,
            frame_count=1242,
            duration_seconds=41.4,
        ),
    )

    def fake_default_builder(
        built_reference: Path,
        output_dir: Path,
        built_source: Path,
    ) -> dict[str, Path]:
        received["reference"] = built_reference
        received["source"] = built_source
        assets: dict[str, Path] = {}
        for asset_id in (
            "overlay-hook-white",
            "overlay-hook-accent",
            "overlay-ea-white",
            "overlay-ea-accent",
            "overlay-number-white",
            "overlay-number-accent",
            "overlay-presenter-vignette",
        ):
            path = output_dir / "assets" / "overlays" / f"{asset_id}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGBA", (1080, 1920), (0, 0, 0, 0)).save(path)
            assets[asset_id] = path
        return assets

    monkeypatch.setattr(
        "app.editor.reference_exact.build_reference_overlays",
        fake_default_builder,
    )

    build_exact_reference_blueprint(
        source=source,
        reference=reference,
        output_dir=output,
    )

    assert received == {
        "reference": reference.resolve(),
        "source": source.resolve(),
    }


def test_reference_overlays_are_clean_text_only_alpha(
    tmp_path: Path,
) -> None:
    overlays = build_reference_overlays(
        tmp_path / "unused-reference.mp4",
        tmp_path,
    )

    expected_bounds = {
        "overlay-hook-white": (170, 1220, 930, 1400),
        "overlay-hook-accent": (220, 1360, 880, 1545),
        "overlay-ea-white": (210, 1260, 870, 1420),
        "overlay-ea-accent": (390, 1510, 690, 1705),
        "overlay-number-white": (130, 1260, 950, 1420),
        "overlay-number-accent": (100, 1350, 980, 1570),
    }
    for asset_id, target in expected_bounds.items():
        path = overlays[asset_id]
        with Image.open(path) as image:
            alpha = np.asarray(image.getchannel("A"))
        ys, xs = np.where(alpha > 8)
        assert xs.size > 100
        assert float((alpha > 8).mean()) < 0.08
        actual = (
            int(xs.min()),
            int(ys.min()),
            int(xs.max()) + 1,
            int(ys.max()) + 1,
        )
        assert actual[0] >= target[0]
        assert actual[1] >= target[1]
        assert actual[2] <= target[2]
        assert actual[3] <= target[3]

    with Image.open(overlays["overlay-presenter-vignette"]) as image:
        alpha = np.asarray(image.getchannel("A"))
    assert int(alpha[:1000].max()) == 0
    assert int(np.median(alpha[1500:1580])) in range(75, 95)
    assert int(np.median(alpha[-40:])) >= 205


def test_gradient_text_recovery_keeps_glyph_geometry_and_color_ramp() -> None:
    background = np.full((120, 200, 3), (45, 55, 65), dtype=np.uint8)
    reference = background.copy()
    for y in range(35, 90):
        progress = (y - 35) / 54
        color = np.asarray(
            (
                round(20 + 190 * progress),
                round(238 + 15 * progress),
                252,
            ),
            dtype=np.float32,
        )
        reference[y, 60:140] = color.astype(np.uint8)

    overlay = _recover_gradient_text_overlay(
        background=background,
        reference=reference,
        bounds=(40, 20, 160, 110),
        kind="yellow",
    )
    rgba = np.asarray(overlay)

    assert int(rgba[50, 80, 3]) >= 245
    assert int(rgba[80, 80, 2]) - int(rgba[45, 80, 2]) >= 100
    assert int(rgba[:15, :, 3].max()) == 0
    assert int(rgba[:, :20, 3].max()) == 0


def test_exact_reference_match_rejects_v4_pacing() -> None:
    reference = {
        "frame_count": 1048,
        "rendered_cut_count": 12,
        "median_shot_ms": 2667,
        "motion_score": 4.463,
        "dark_frame_ratio": 0.245,
        "mean_luminance": 73.906,
        "mean_saturation": 79.557,
    }
    passing = evaluate_exact_reference_match(
        reference=reference,
        rendered=reference,
        similarity={
            "mean_ssim": 0.84,
            "p10_ssim": 0.69,
            "minimum_ssim": 0.78,
            "mean_rgb_similarity": 0.91,
        },
        audio={
            "delay_passed": True,
            "duration_passed": True,
            "spectral_passed": True,
        },
        metadata=SimpleNamespace(duration_seconds=34.933),
    )
    v4 = evaluate_exact_reference_match(
        reference=reference,
        rendered={
            **reference,
            "frame_count": 1242,
            "rendered_cut_count": 23,
            "median_shot_ms": 1600,
            "mean_luminance": 85.2,
        },
        similarity={
            "mean_ssim": 0.45,
            "p10_ssim": 0.25,
            "minimum_ssim": 0.1,
            "mean_rgb_similarity": 0.6,
        },
        audio={
            "delay_passed": True,
            "duration_passed": True,
            "spectral_passed": True,
        },
        metadata=SimpleNamespace(duration_seconds=41.4),
    )

    assert passing["automated_pass"] is True
    assert v4["automated_pass"] is False
    assert {
        check["name"]
        for check in v4["checks"]
        if not check["passed"]
    } >= {
        "duration",
        "hard-cuts",
        "median-shot",
        "mean-ssim",
        "minimum-ssim",
    }


def test_frame_pair_similarity_rewards_identical_pixels() -> None:
    reference = np.zeros((240, 135, 3), dtype=np.uint8)
    reference[50:180, 35:105] = (40, 180, 240)
    altered = reference.copy()
    altered[90:200, 55:125] = (220, 30, 25)

    identical = measure_frame_pair_similarity(reference, reference)
    different = measure_frame_pair_similarity(reference, altered)

    assert identical["ssim"] == pytest.approx(1, abs=1e-6)
    assert identical["rgb_similarity"] == pytest.approx(1, abs=1e-6)
    assert different["ssim"] < 0.9
    assert different["rgb_similarity"] < 0.95


def test_exact_assembly_stops_at_human_approval_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "0806.mp4"
    reference = tmp_path / "reference.mp4"
    source.write_bytes(b"source")
    reference.write_bytes(b"reference")
    output = tmp_path / "production-v5"

    monkeypatch.setattr(
        "app.editor.reference_exact.probe_video",
        lambda _path: VideoMetadata(
            width=1080,
            height=1920,
            fps=30,
            frame_count=1242,
            duration_seconds=41.4,
        ),
    )

    def fake_overlays(
        _reference: Path,
        output_dir: Path,
    ) -> dict[str, Path]:
        assets: dict[str, Path] = {}
        for asset_id in (
            "overlay-hook-white",
            "overlay-hook-accent",
            "overlay-ea-white",
            "overlay-ea-accent",
            "overlay-number-white",
            "overlay-number-accent",
            "overlay-presenter-vignette",
        ):
            path = output_dir / "assets" / "overlays" / f"{asset_id}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGBA", (1080, 1920), (0, 0, 0, 0)).save(path)
            assets[asset_id] = path
        return assets

    build_exact_reference_blueprint(
        source=source,
        reference=reference,
        output_dir=output,
        overlay_builder=fake_overlays,
    )

    def fake_renderer(*, output: Path, **_kwargs: object) -> None:
        output.write_bytes(b"rendered")

    def fake_muxer(*, output: Path, **_kwargs: object) -> None:
        output.write_bytes(b"exact")

    def fake_masterer(*, output: Path, **_kwargs: object) -> None:
        output.write_bytes(b"safe")

    def fake_reviewer(**_kwargs: object) -> dict[str, object]:
        return {
            "automated_pass": True,
            "human_approved": False,
            "checks": [],
        }

    result = assemble_exact_reference(
        output_dir=output,
        renderer=fake_renderer,
        exact_muxer=fake_muxer,
        safe_masterer=fake_masterer,
        reviewer=fake_reviewer,
    )

    assert result["state"] == "awaiting-final-approval"
    assert result["automated_pass"] is True
    assert result["human_approved"] is False
    assert (output / "rendered-v5.mp4").read_bytes() == b"rendered"
    assert (output / "edited-exact.mp4").read_bytes() == b"exact"
    assert (output / "edited.mp4").read_bytes() == b"safe"


def test_exact_renderer_proxies_only_the_hevc_presenter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    presenter = tmp_path / "presenter-hevc.mp4"
    reference = tmp_path / "reference-h264.mp4"
    presenter.write_bytes(b"hevc")
    reference.write_bytes(b"h264")
    plan = EditPlanV2(
        source_filename="0806.mp4",
        source_metadata=VideoMetadata(
            width=1080,
            height=1920,
            fps=30,
            frame_count=1242,
            duration_seconds=41.4,
        ),
        output=OutputSpec(),
        duration_ms=1000,
        assets=[
            AssetRef(
                id="source-presenter",
                kind="video",
                path=str(presenter),
                provenance="user-provided",
            ),
            AssetRef(
                id="reference-master",
                kind="video",
                path=str(reference),
                provenance="user-provided-reference",
            ),
        ],
        visual_layers=[
            VisualLayerSpec(
                id="presenter",
                shot_id="shot",
                start_ms=0,
                end_ms=1000,
                source_role="presenter",
                asset_id="source-presenter",
                source_start_ms=0,
                source_end_ms=1000,
            )
        ],
        audio=AudioPlan(),
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "app.editor.ffmpeg.probe_stream_codecs",
        lambda path: (
            ("hevc", "aac")
            if path == presenter
            else ("h264", "aac")
        ),
    )

    def fake_proxy(**kwargs: object) -> None:
        captured["proxy"] = kwargs
        proxy_path = Path(kwargs["output"])
        proxy_path.parent.mkdir(parents=True, exist_ok=True)
        proxy_path.write_bytes(b"proxy")

    def fake_render(**kwargs: object) -> None:
        captured["render"] = kwargs

    monkeypatch.setattr(
        "app.editor.remotion.prepare_renderer_source_proxy",
        fake_proxy,
    )
    monkeypatch.setattr(
        "app.editor.production_assembly.render_production_plan",
        fake_render,
    )

    render_exact_reference_plan(
        output_dir=tmp_path,
        plan=plan,
        output=tmp_path / "rendered.mp4",
    )

    proxy = captured["proxy"]
    assert proxy["source"] == presenter
    assert proxy["fps"] == 30
    rendered_plan = captured["render"]["plan"]
    assets = {asset.id: asset for asset in rendered_plan.assets}
    assert Path(assets["source-presenter"].path).read_bytes() == b"proxy"
    assert Path(assets["reference-master"].path) == reference
