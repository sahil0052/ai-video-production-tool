import json
from pathlib import Path

import numpy as np
from PIL import Image

from app.editor.production_blueprint import (
    _build_evidence_derivatives,
    build_production_blueprint,
)
from app.production_models import ProductionBlueprint


def test_0806_blueprint_uses_verified_inputs_and_explicit_layers(
    tmp_path: Path,
) -> None:
    source = tmp_path / "0806.mp4"
    source.write_bytes(b"raw-presenter-fixture")
    output = tmp_path / "0806-production-v4"
    seed = Path(
        r"C:\websites\ai video production tool\storage\deliverables"
        r"\0806-production-v3"
    )

    artifacts = build_production_blueprint(
        source=source,
        output_dir=output,
        primary_reference=10,
        secondary_reference=4,
        seed_dir=seed,
        refresh_evidence=False,
        prepare_media=False,
    )

    blueprint = ProductionBlueprint.model_validate_json(
        (output / artifacts["blueprint"]).read_text(encoding="utf-8")
    )
    assert blueprint.duration_ms == 41400
    assert len({layer.shot_id for layer in blueprint.layers}) == 24
    assert len(blueprint.flow_shots) == 3
    licensed_layers = [
        layer
        for layer in blueprint.layers
        if layer.source_role == "licensed-context"
    ]
    assert {
        layer.asset_id for layer in licensed_layers
    } == {
        "licensed-mixkit-microchip",
        "licensed-mixkit-code-screen",
        "licensed-mixkit-screen-glasses",
        "licensed-mixkit-typing",
    }
    assert sum(
        layer.end_ms - layer.start_ms for layer in licensed_layers
    ) >= 5000
    assert sum(
        shot.end_ms - shot.start_ms for shot in blueprint.flow_shots
    ) / blueprint.duration_ms <= 0.22

    flow_layers = [
        layer
        for layer in blueprint.layers
        if layer.source_role == "flow-illustrative"
    ]
    assert len(flow_layers) == 3
    assert all(layer.muted for layer in flow_layers)
    assert all(layer.illustrative_label for layer in flow_layers)
    assert all(layer.bounds.width == 1080 for layer in flow_layers)
    assert all(layer.bounds.height >= 1500 for layer in flow_layers)
    assert all(
        max(keyframe.value for keyframe in layer.opacity_keyframes) == 1
        for layer in flow_layers
    )
    assert all(
        "brightness(1.08)" in str(layer.color_filter)
        and "saturate(1.15)" in str(layer.color_filter)
        for layer in flow_layers
    )
    assert all(
        "saturate(1.22)" in str(layer.color_filter)
        for layer in blueprint.layers
        if layer.source_role == "real-product"
    )

    layers_by_id = {layer.id: layer for layer in blueprint.layers}
    assert layers_by_id["layer-hook-context"].end_ms == 650
    assert "layer-hook-action" not in layers_by_id
    assert layers_by_id["layer-hook-split"].start_ms == 650
    assert layers_by_id["layer-hook-presenter"].start_ms == 650
    assert layers_by_id["layer-hook-split"].bounds.model_dump() == {
        "x": 0,
        "y": 0,
        "width": 1080,
        "height": 960,
    }
    assert layers_by_id["layer-hook-presenter"].bounds.model_dump() == {
        "x": 0,
        "y": 960,
        "width": 1080,
        "height": 960,
    }
    assert "brightness(1.08)" in str(
        layers_by_id["layer-hook-presenter"].color_filter
    )
    assert all(
        "brightness(1.1)" in str(layer.color_filter)
        for layer in blueprint.layers
        if layer.source_role == "presenter"
        and layer.id != "layer-hook-presenter"
    )
    assert all(
        layer.bounds.height >= 1500
        for layer in blueprint.layers
        if layer.source_role == "direct-evidence"
    )
    assert all(
        layer.transform_keyframes[-1].scale >= 1.05
        for layer in blueprint.layers
        if layer.source_role == "direct-evidence"
    )
    for layer_id in (
        "layer-metaeditor-open",
        "layer-code-macro",
        "layer-risk-code-detail",
        "layer-ea-identification",
        "layer-risk-input-detail",
        "layer-lesson-parameters",
        "layer-attach-ea",
        "layer-strategy-tester",
    ):
        foreground = layers_by_id[layer_id]
        backdrop = layers_by_id[f"{layer_id}-backdrop"]
        assert foreground.fit == "cover"
        assert foreground.bounds.width >= 1040
        assert foreground.bounds.height >= 1200
        assert foreground.border_radius >= 24
        assert backdrop.asset_id == "graphic-product-canvas"
        assert backdrop.source_role == "deterministic-graphic"
        assert backdrop.fit == "fill"
        assert backdrop.bounds.width == 1080
        assert backdrop.bounds.height == 1920
        assert backdrop.z_index < foreground.z_index
        assert foreground.transform_keyframes[1].at_ms <= 150
        assert foreground.transform_keyframes[1].scale >= 1.05
        assert foreground.transform_keyframes[-1].scale >= 1.13
        detail = layers_by_id[f"{layer_id}-detail"]
        assert detail.asset_id == foreground.asset_id
        assert detail.source_role == foreground.source_role
        assert detail.z_index > foreground.z_index
        assert detail.crop.width < foreground.crop.width
        assert detail.opacity_keyframes[0].value == 0
        assert max(
            keyframe.value for keyframe in detail.opacity_keyframes
        ) >= 0.9
        assert detail.opacity_keyframes[-1].value == 0

    for layer in blueprint.layers:
        if layer.source_role == "direct-evidence":
            assert layer.transform_keyframes[1].at_ms <= 150
            assert layer.transform_keyframes[1].scale >= 1.04
            assert 1.06 <= layer.transform_keyframes[-1].scale <= 1.08
            assert abs(layer.transform_keyframes[-1].x) <= 10
        if layer.source_role == "flow-illustrative":
            assert layer.transform_keyframes[1].at_ms <= 150
            assert layer.transform_keyframes[1].scale >= 1.04
            assert layer.transform_keyframes[-1].scale >= 1.12
            assert abs(layer.transform_keyframes[-1].x) >= 20

    evidence_pages = [
        page
        for page in blueprint.caption_pages
        if 14160 <= page.start_ms < 21140
    ]
    assert evidence_pages
    assert all(page.family == "documentary-clean" for page in evidence_pages)
    assert all(
        page.family == "compact-pill"
        for page in blueprint.caption_pages
        if page.start_ms < 2340 or page.start_ms >= 37160
    )
    assert blueprint.audio.dialogue_asset_id == "dialogue-processed"
    assert blueprint.audio.dialogue_offset_ms == -70

    for asset in blueprint.assets:
        path = Path(asset.path)
        assert not path.is_absolute()
        assert (output / path).is_file()
        assert "training videos data" not in asset.path.lower()

    manifest = json.loads(
        (output / artifacts["asset_manifest"]).read_text(encoding="utf-8")
    )
    assert all(item["checksum_sha256"] for item in manifest["assets"])
    licensed_assets = [
        item
        for item in manifest["assets"]
        if item["provenance"].startswith("internet:")
    ]
    assert len(licensed_assets) == 4
    assert all(item["provider"] == "Mixkit" for item in licensed_assets)
    assert all(item["source_url"] for item in licensed_assets)
    assert all(item["license_url"] for item in licensed_assets)
    instructions = json.loads(
        (output / artifacts["flow_instructions"]).read_text(encoding="utf-8")
    )
    instruction_text = instructions["card"][0]["text"].casefold()
    assert "well-exposed" in instruction_text
    assert "cyan" in instruction_text
    assert (output / "flow-plates" / "wrong-rule-start.png").is_file()
    assert (output / "assets" / "graphics" / "hook-headline.png").is_file()
    canvas_path = output / "assets" / "graphics" / "product-canvas.png"
    assert canvas_path.is_file()
    with Image.open(canvas_path) as product_canvas:
        canvas_pixels = np.asarray(
            product_canvas.convert("L"),
            dtype=np.float32,
        )
    assert float(canvas_pixels.mean()) >= 221.5


def test_flow_input_plates_are_well_exposed_and_retain_shadow_detail(
    tmp_path: Path,
) -> None:
    source = tmp_path / "0806.mp4"
    source.write_bytes(b"raw-presenter-fixture")
    output = tmp_path / "0806-production-v4"
    seed = Path(
        r"C:\websites\ai video production tool\storage\deliverables"
        r"\0806-production-v3"
    )

    build_production_blueprint(
        source=source,
        output_dir=output,
        primary_reference=10,
        secondary_reference=4,
        seed_dir=seed,
        refresh_evidence=False,
        prepare_media=False,
    )

    for plate_path in sorted((output / "flow-plates").glob("*.png")):
        with Image.open(plate_path) as plate:
            pixels = np.asarray(plate.convert("RGB"), dtype=np.float32)
        luminance = (
            pixels[:, :, 0] * 0.2126
            + pixels[:, :, 1] * 0.7152
            + pixels[:, :, 2] * 0.0722
        )
        assert float(luminance.mean()) >= 48
        assert float((luminance < 32).mean()) <= 0.35


def test_blueprint_rebuild_preserves_flow_attempts_and_status(
    tmp_path: Path,
) -> None:
    source = tmp_path / "0806.mp4"
    source.write_bytes(b"raw-presenter-fixture")
    output = tmp_path / "0806-production-v4"
    seed = Path(
        r"C:\websites\ai video production tool\storage\deliverables"
        r"\0806-production-v3"
    )
    build_production_blueprint(
        source=source,
        output_dir=output,
        primary_reference=10,
        secondary_reference=4,
        seed_dir=seed,
        refresh_evidence=False,
        prepare_media=False,
    )
    flow_plan_path = output / "flow-shot-plan.json"
    flow_plan = json.loads(flow_plan_path.read_text(encoding="utf-8"))
    flow_plan[0]["status"] = "accepted"
    flow_plan[0]["attempts"] = [
        {
            "attempt": 1,
            "command": ["gflow", "video"],
            "project_id": "project-1",
            "media_id": "media-1",
            "started_at": "2026-08-10T00:00:00Z",
            "completed_at": "2026-08-10T00:01:00Z",
            "result_json": {"status": "ok"},
            "untouched_path": "C:/candidate.mp4",
            "checksum_sha256": "a" * 64,
            "reconciliation_state": "not-needed",
        }
    ]
    flow_plan_path.write_text(
        json.dumps(flow_plan),
        encoding="utf-8",
    )

    build_production_blueprint(
        source=source,
        output_dir=output,
        primary_reference=10,
        secondary_reference=4,
        seed_dir=seed,
        refresh_evidence=False,
        prepare_media=False,
    )

    rebuilt_plan = json.loads(flow_plan_path.read_text(encoding="utf-8"))
    assert rebuilt_plan[0]["status"] == "accepted"
    assert rebuilt_plan[0]["attempts"][0]["media_id"] == "media-1"
    rebuilt_blueprint = json.loads(
        (output / "blueprint.json").read_text(encoding="utf-8")
    )
    assert rebuilt_blueprint["flow_shots"][0]["status"] == "accepted"
    assert (
        rebuilt_blueprint["flow_shots"][0]["attempts"][0]["media_id"]
        == "media-1"
    )


def test_readable_risk_number_derivative_is_phone_legible(
    tmp_path: Path,
) -> None:
    history = tmp_path / "history.png"
    risk = tmp_path / "risk.png"
    Image.new("RGB", (1440, 1600), "white").save(history)
    Image.new("RGB", (1268, 439), "white").save(risk)

    derivatives = dict(
        (asset_id, path)
        for asset_id, path, _keywords in _build_evidence_derivatives(
            output_dir=tmp_path,
            history_source=history,
            risk_source=risk,
        )
    )

    with Image.open(derivatives["evidence-risk-number"]) as number_card:
        assert number_card.size == (1080, 1600)

    with Image.open(
        derivatives["evidence-history-excerpt"]
    ) as history_card:
        assert history_card.size == (1080, 1600)
        history_pixels = np.asarray(
            history_card.convert("RGB"),
            dtype=np.int16,
        )
        history_background = np.array([241, 235, 221], dtype=np.int16)
        history_callout_band = history_pixels[820:1240, 48:1032]
        history_difference = np.max(
            np.abs(history_callout_band - history_background),
            axis=2,
        )
        assert float((history_difference > 20).mean()) >= 0.01

    with Image.open(
        derivatives["evidence-risk-excerpt"]
    ) as risk_card:
        assert risk_card.size == (1080, 1600)
        risk_pixels = np.asarray(
            risk_card.convert("RGB"),
            dtype=np.int16,
        )
        risk_background = np.array([23, 34, 56], dtype=np.int16)
        risk_callout_band = risk_pixels[820:1240, 48:1032]
        risk_difference = np.max(
            np.abs(risk_callout_band - risk_background),
            axis=2,
        )
        assert float((risk_difference > 20).mean()) >= 0.01
