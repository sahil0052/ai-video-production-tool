from __future__ import annotations

import importlib
import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import median

from app.models import AssetRef, AudioPlan, OutputSpec
from PIL import Image
from app.production_models import (
    BlueprintLayerSpec,
    LayerBounds,
    ProductionBlueprint,
    ProductionJobRecord,
    ProductionStateEvent,
)


def _module():
    return importlib.import_module("app.editor.reference_story_v2")


def test_v2_schedule_covers_story_and_adds_visual_resets():
    shots = _module().build_0809_v2_schedule()

    assert shots[0]["start_ms"] == 0
    assert shots[-1]["end_ms"] == 50_833
    assert all(
        left["end_ms"] == right["start_ms"]
        for left, right in zip(shots, shots[1:], strict=False)
    )
    assert 28 <= len(shots) <= 35
    long_shots = [
        shot
        for shot in shots
        if shot["end_ms"] - shot["start_ms"] > 3_000
    ]
    assert [
        (
            shot["source_role"],
            shot["editorial_role"],
            shot["end_ms"] - shot["start_ms"],
        )
        for shot in long_shots
    ] == [("presenter", "forex-lesson", 3_600)]
    assert max(
        shot["end_ms"] - shot["start_ms"]
        for shot in shots
        if shot["source_role"] != "presenter"
    ) <= 3_000
    assert sum(
        shot["end_ms"] - shot["start_ms"]
        for shot in shots
        if shot["source_role"] == "flow-illustrative"
    ) == 5_700


def test_v2_schedule_merges_continuations_to_match_reference_pacing():
    shots = _module().build_0809_v2_schedule()
    boundaries_ms = {shot["start_ms"] for shot in shots[1:]}
    durations_ms = [
        shot["end_ms"] - shot["start_ms"]
        for shot in shots
    ]

    assert len(shots) == 29
    assert {21_150, 23_800, 28_350, 38_300}.isdisjoint(boundaries_ms)
    assert median(durations_ms) >= 1_500


def test_v2_flow_shots_are_short_non_factual_i2v_slots(tmp_path: Path):
    shots = _module().build_0809_v2_flow_shots(tmp_path)

    assert [shot.id for shot in shots] == [
        "flow-update-module",
        "flow-server-propagation",
        "flow-risk-containment",
    ]
    assert sum(shot.end_ms - shot.start_ms for shot in shots) == 5_700
    assert all(shot.mode == "i2v" for shot in shots)
    assert all(len(shot.input_plates) == 2 for shot in shots)
    assert all(
        shot.requested_content
        in (["physical-metaphor"], ["abstract-motion"])
        for shot in shots
    )
    forbidden_words = {
        "evidence",
        "exact text",
        "software ui",
        "code",
        "chart",
        "number",
        "currency",
        "document",
    }
    assert all(
        all(term in " ".join(shot.constraints).lower() for term in forbidden_words)
        for shot in shots
    )


def test_v2_layers_apply_flow_labels_and_keep_full_base_coverage():
    module = _module()
    schedule = module.build_0809_v2_schedule()
    layers = module.build_0809_v2_layers()
    base_layers = sorted(
        (layer for layer in layers if layer.z_index == 10),
        key=lambda layer: layer.start_ms,
    )
    flow_layers = [layer for layer in layers if layer.flow_shot_id]

    assert len(base_layers) == len(schedule)
    assert base_layers[0].start_ms == 0
    assert base_layers[-1].end_ms == 50_833
    assert all(
        left.end_ms == right.start_ms
        for left, right in zip(base_layers, base_layers[1:], strict=False)
    )
    assert len(flow_layers) == 3
    assert all(layer.muted for layer in flow_layers)
    assert all(layer.illustrative_label for layer in flow_layers)
    assert all(layer.asset_id is None for layer in flow_layers)


def test_v2_layers_split_control_and_cta_overlays_into_short_beats():
    layers = _module().build_0809_v2_layers()
    overlays = {
        layer.asset_id: layer
        for layer in layers
        if layer.z_index >= 50 and layer.asset_id is not None
    }

    required = {
        "overlay-hook-date-v2": (0, 900),
        "overlay-market-open-v2": (2_200, 4_500),
        "overlay-update-question-v2": (12_800, 14_800),
        "overlay-control-order-v2": (34_900, 36_000),
        "overlay-control-automation-v2": (36_000, 37_100),
        "overlay-control-equity-v2": (37_100, 39_800),
        "overlay-damage-limited-v2": (41_800, 42_500),
        "overlay-cta-setup-v2": (42_500, 45_200),
        "overlay-cta-card-v2": (47_200, 50_200),
    }
    assert required.keys() <= overlays.keys()
    assert "overlay-risk-zero-v2" not in overlays
    for asset_id, timing in required.items():
        layer = overlays[asset_id]
        assert (layer.start_ms, layer.end_ms) == timing
        assert layer.end_ms - layer.start_ms <= 3_000


def test_v2_layers_include_a_source_pixel_reset_before_the_forex_bridge():
    layers = _module().build_0809_v2_layers()
    reset = next(
        layer
        for layer in layers
        if layer.id == "evidence-bridge-reset"
    )

    assert reset.source_role == "direct-evidence"
    assert reset.asset_id == "evidence-sec-deployment-highlight"
    assert (reset.start_ms, reset.end_ms) == (25_600, 26_400)
    planned_evidence_ms = sum(
        layer.end_ms - layer.start_ms
        for layer in layers
        if layer.z_index in {10, 20}
        and layer.source_role == "direct-evidence"
    )
    assert planned_evidence_ms / 50_833 >= 0.15


def test_v2_layers_do_not_cover_every_presenter_shot_with_global_vignette():
    layers = _module().build_0809_v2_layers()

    assert not [
        layer
        for layer in layers
        if layer.asset_id == "overlay-presenter-vignette"
    ]


def test_v2_review_requires_stronger_visual_metrics():
    report = _module().evaluate_reference_story_v2(
        frame_audit={
            "rendered_cut_count": 26,
            "median_shot_ms": 1900,
            "motion_score": 4.6,
            "dark_frame_ratio": 0.25,
            "mean_luminance": 82,
            "mean_saturation": 76,
        },
        coverage={
            "real_direct_source_ratio": 0.58,
            "flow_ratio": 0.11,
            "deterministic_graphic_ratio": 0.22,
            "direct_evidence_ratio": 0.17,
        },
        audio={
            "delay_passed": True,
            "duration_passed": True,
            "spectral_passed": True,
        },
        loudness={
            "integrated_lufs": -14.2,
            "true_peak_dbtp": -1.3,
        },
        narration={
            "token_retention": 1,
            "protected_tokens_missing": [],
        },
        metadata={
            "duration_seconds": 50.833,
            "frame_count": 1525,
            "width": 1080,
            "height": 1920,
            "fps": 30,
        },
    )

    assert report["automated_pass"] is True
    assert not [check for check in report["checks"] if not check["passed"]]


def test_v2_review_blocks_generic_low_motion_presenter_heavy_result():
    report = _module().evaluate_reference_story_v2(
        frame_audit={
            "rendered_cut_count": 18,
            "median_shot_ms": 3000,
            "motion_score": 3.1,
            "dark_frame_ratio": 0.25,
            "mean_luminance": 82,
            "mean_saturation": 76,
        },
        coverage={
            "real_direct_source_ratio": 0.58,
            "flow_ratio": 0.02,
            "deterministic_graphic_ratio": 0.3,
            "direct_evidence_ratio": 0.12,
        },
        audio={
            "delay_passed": True,
            "duration_passed": True,
            "spectral_passed": True,
        },
        loudness={
            "integrated_lufs": -14.2,
            "true_peak_dbtp": -1.3,
        },
        narration={
            "token_retention": 1,
            "protected_tokens_missing": [],
        },
        metadata={
            "duration_seconds": 50.833,
            "frame_count": 1525,
            "width": 1080,
            "height": 1920,
            "fps": 30,
        },
    )

    failed = {
        check["name"]
        for check in report["checks"]
        if not check["passed"]
    }
    assert {
        "rendered-hard-cuts",
        "median-shot",
        "motion",
        "flow-coverage",
        "deterministic-graphic-coverage",
        "direct-evidence-coverage",
    }.issubset(failed)


def test_v2_blueprint_requests_generation_and_persists_flow_contracts(
    tmp_path: Path,
):
    module = _module()

    def fake_seed_builder(*, source: Path, output_dir: Path, **_kwargs):
        output_dir.mkdir(parents=True, exist_ok=True)
        asset = AssetRef(
            id="source-presenter",
            kind="video",
            path="assets/presenter/source-presenter.mp4",
            provenance="user-provided",
        )
        blueprint = ProductionBlueprint(
            source_filename=source.name,
            source_metadata={
                "width": 1080,
                "height": 1920,
                "fps": 30,
                "frame_count": 1525,
                "duration_seconds": 50.833333333333336,
            },
            output=OutputSpec(),
            duration_ms=50_833,
            assets=[asset],
            layers=[
                BlueprintLayerSpec(
                    id="seed-layer",
                    shot_id="seed-shot",
                    start_ms=0,
                    end_ms=50_833,
                    source_role="presenter",
                    kind="video",
                    asset_id="source-presenter",
                    bounds=LayerBounds(),
                    muted=True,
                )
            ],
            audio=AudioPlan(),
        )
        (output_dir / "blueprint.json").write_text(
            blueprint.model_dump_json(indent=2),
            encoding="utf-8",
        )
        for filename, payload in (
            ("storyboard.json", []),
            ("evidence.json", []),
            ("caption-plan.json", []),
            ("asset-manifest.json", {"assets": [asset.model_dump(mode="json")]}),
        ):
            (output_dir / filename).write_text(
                json.dumps(payload),
                encoding="utf-8",
            )
        now = datetime.now(UTC)
        record = ProductionJobRecord(
            id="seed",
            source_path=str(source),
            output_dir=str(output_dir),
            state="blueprint-ready",
            primary_reference=10,
            secondary_reference=4,
            flow_operation_budget=0,
            artifacts={"blueprint": "blueprint.json"},
            state_history=[
                ProductionStateEvent(
                    state="blueprint-ready",
                    at=now,
                    detail="seed",
                )
            ],
            created_at=now,
            updated_at=now,
        )
        from app.editor.production_v4 import ProductionStore

        ProductionStore(output_dir).create(record)
        return {"blueprint": "blueprint.json"}

    def fake_visual_asset_builder(*, output_dir: Path, base_assets):
        created = []
        for asset_id in {
            str(shot["asset_id"])
            for shot in module.build_0809_v2_schedule()
            if shot["source_role"] in {
                "deterministic-graphic",
                "direct-evidence",
            }
            and str(shot["asset_id"])
            not in {asset.id for asset in base_assets}
        }:
            path = output_dir / "assets" / "graphics" / f"{asset_id}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"test-image")
            created.append(
                AssetRef(
                    id=asset_id,
                    kind="image",
                    path=path.relative_to(output_dir).as_posix(),
                    provenance="deterministic-test",
                )
            )
        return created

    def fake_flow_plate_builder(*, output_dir: Path):
        for shot in module.build_0809_v2_flow_shots(output_dir):
            for raw_path in shot.input_plates:
                path = Path(raw_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"test-plate")

    result = module.build_reference_story_v2_blueprint(
        source=Path("D:/Downloads/0809.mp4"),
        output_dir=tmp_path,
        seed_builder=fake_seed_builder,
        visual_asset_builder=fake_visual_asset_builder,
        flow_plate_builder=fake_flow_plate_builder,
    )

    from app.editor.production_v4 import ProductionStore

    job = ProductionStore(tmp_path).load()
    blueprint = ProductionBlueprint.model_validate_json(
        (tmp_path / "blueprint.json").read_text(encoding="utf-8")
    )
    flow_plan = json.loads(
        (tmp_path / "flow-shot-plan.json").read_text(encoding="utf-8")
    )

    assert job.id == "production-0809-visual-upgrade-v2"
    assert job.state == "awaiting-generation-approval"
    assert job.flow_operation_budget == 5
    assert job.flow_repository.endswith(
        "Documents\\ChatGPT\\New project"
    )
    assert len(blueprint.flow_shots) == 3
    assert len(flow_plan) == 3
    assert result["flow_shot_plan"] == "flow-shot-plan.json"
    assert (tmp_path / "flow-instructions.json").is_file()


def test_v2_planner_reuses_a_completed_v1_seed_after_v2_asset_failure(
    tmp_path: Path,
):
    from app.editor.production_v4 import ProductionStore

    (tmp_path / "blueprint.json").write_text("{}", encoding="utf-8")
    now = datetime.now(UTC)
    ProductionStore(tmp_path).create(
        ProductionJobRecord(
            id="production-0809-reference-style-v1",
            source_path="D:/Downloads/0809.mp4",
            output_dir=str(tmp_path),
            state="blueprint-ready",
            primary_reference=10,
            secondary_reference=4,
            artifacts={
                "blueprint": "blueprint.json",
                "storyboard": "storyboard.json",
            },
            state_history=[
                ProductionStateEvent(
                    state="blueprint-ready",
                    at=now,
                    detail="seed complete",
                )
            ],
            created_at=now,
            updated_at=now,
        )
    )

    reusable = _module()._load_reusable_seed_artifacts(tmp_path)

    assert reusable == {
        "blueprint": "blueprint.json",
        "storyboard": "storyboard.json",
    }


def test_v2_visual_assets_and_flow_plates_are_portrait_production_size(
    tmp_path: Path,
):
    module = _module()
    base_assets = []
    for asset_id in (
        "evidence-sec-overview",
        "evidence-sec-email",
        "evidence-sec-deployment",
    ):
        path = tmp_path / "seed" / f"{asset_id}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1080, 1920), (238, 236, 232)).save(path)
        base_assets.append(
            AssetRef(
                id=asset_id,
                kind="image",
                path=str(path),
                provenance="test-evidence",
            )
        )
    brand_path = tmp_path / "seed" / "brand.png"
    Image.new("RGBA", (520, 120), (132, 104, 220, 255)).save(brand_path)
    base_assets.append(
        AssetRef(
            id="brand-profit-bricks-logo",
            kind="image",
            path=str(brand_path),
            provenance="test-brand",
        )
    )

    assets = module._build_v2_visual_assets(
        output_dir=tmp_path,
        base_assets=base_assets,
    )
    module._build_v2_flow_plates(output_dir=tmp_path)

    required = {
        "graphic-order-lanes",
        "evidence-sec-overview-highlight",
        "graphic-eight-servers-v2",
        "evidence-sec-email-highlight",
        "graphic-incident-bridge",
        "evidence-sec-deployment-highlight",
        "graphic-repeat-timeline",
        "graphic-control-recap",
        "overlay-hook-date-v2",
        "overlay-market-open-v2",
        "overlay-update-question-v2",
        "overlay-control-order-v2",
        "overlay-control-automation-v2",
        "overlay-control-equity-v2",
        "overlay-damage-limited-v2",
        "overlay-cta-setup-v2",
        "overlay-cta-card-v2",
    }
    by_id = {asset.id: asset for asset in assets}
    assert required.issubset(by_id)
    assert "overlay-risk-zero-v2" not in by_id
    for asset_id in required:
        path = tmp_path / by_id[asset_id].path
        assert path.is_file()
        assert Image.open(path).size == (1080, 1920)
    for filename in (
        "update-start.png",
        "update-end.png",
        "server-start.png",
        "server-end.png",
        "risk-start.png",
        "risk-end.png",
    ):
        path = tmp_path / "flow-plates" / filename
        assert path.is_file()
        assert Image.open(path).size == (1080, 1920)


def test_v2_assembly_advances_only_to_awaiting_final_approval(
    tmp_path: Path,
):
    module = _module()
    from app.editor.production_v4 import ProductionStore

    now = datetime.now(UTC)
    store = ProductionStore(tmp_path)
    store.create(
        ProductionJobRecord(
            id="production-0809-visual-upgrade-v2",
            source_path="D:/Downloads/0809.mp4",
            output_dir=str(tmp_path),
            state="awaiting-candidate-review",
            primary_reference=10,
            secondary_reference=4,
            flow_operation_budget=5,
            approved_paid_operations=3,
            consumed_paid_operations=3,
            artifacts={"blueprint": "blueprint.json"},
            state_history=[
                ProductionStateEvent(
                    state="awaiting-candidate-review",
                    at=now,
                    detail="ready",
                )
            ],
            created_at=now,
            updated_at=now,
        )
    )
    plan = object()

    def fake_compile(output_dir):
        assert output_dir == tmp_path.resolve()
        return plan

    def fake_render(*, output_dir, plan, output):
        assert output_dir == tmp_path.resolve()
        assert plan is not None
        output.write_bytes(b"rendered")

    def fake_master(*, plan, rendered, output):
        assert rendered.read_bytes() == b"rendered"
        output.write_bytes(b"edited")
        return {"applied_leading_trim_ms": 0}

    def fake_review(*, output_dir, plan, edited):
        assert edited.read_bytes() == b"edited"
        return {
            "automated_pass": True,
            "human_approved": False,
            "checks": [],
        }

    result = module.assemble_reference_story_v2(
        output_dir=tmp_path,
        compiler=fake_compile,
        renderer=fake_render,
        masterer=fake_master,
        reviewer=fake_review,
    )

    record = store.load()
    assert record.state == "awaiting-final-approval"
    assert record.automated_pass is True
    assert record.human_approved is False
    assert result["edited_video"] == "edited.mp4"
    assert (tmp_path / "review-report.json").is_file()
