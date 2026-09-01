from datetime import UTC, datetime
import json
from pathlib import Path
import statistics

import pytest

from app.editor.production_v4 import (
    ProductionStore,
    build_0806_flow_shots,
    build_0806_shot_schedule,
    generate_flow_candidates,
    review_flow_candidate,
)
from app.production_models import (
    FlowGenerationAttempt,
    FlowShotSpec,
    ProductionJobRecord,
)


def test_0806_golden_schedule_meets_locked_pacing_and_flow_coverage(
    tmp_path: Path,
) -> None:
    shots = build_0806_shot_schedule()
    flow_shots = build_0806_flow_shots(tmp_path)

    assert len(shots) == 24
    assert len(shots) - 1 == 23
    assert shots[0]["start_ms"] == 0
    assert shots[-1]["end_ms"] == 41400
    assert all(
        current["end_ms"] == following["start_ms"]
        for current, following in zip(shots, shots[1:], strict=False)
    )
    median_ms = statistics.median(
        shot["end_ms"] - shot["start_ms"] for shot in shots
    )
    assert 1400 <= median_ms <= 1800

    assert len(flow_shots) == 3
    flow_by_id = {shot.id: shot for shot in flow_shots}
    assert (
        flow_by_id["flow-wrong-rule-branch"].start_ms,
        flow_by_id["flow-wrong-rule-branch"].end_ms,
    ) == (12050, 14160)
    assert (
        flow_by_id["flow-physical-risk"].start_ms,
        flow_by_id["flow-physical-risk"].end_ms,
    ) == (21820, 23140)
    assert (
        flow_by_id["flow-reversal-texture"].start_ms,
        flow_by_id["flow-reversal-texture"].end_ms,
    ) == (24650, 27780)
    flow_duration_ms = sum(
        shot.end_ms - shot.start_ms for shot in flow_shots
    )
    assert 6000 <= flow_duration_ms <= 8000
    assert flow_duration_ms / 41400 <= 0.22
    assert all(shot.model == "veo-lite" for shot in flow_shots)
    assert all(shot.mode == "i2v" for shot in flow_shots)
    assert all("well-exposed" in shot.prompt.casefold() for shot in flow_shots)
    assert all(
        any(
            color in shot.prompt.casefold()
            for color in ("cyan", "teal", "amber", "red")
        )
        for shot in flow_shots
    )
    assert all(
        any(
            constraint.startswith("No crushed blacks")
            for constraint in shot.constraints
        )
        for shot in flow_shots
    )


def test_production_store_persists_atomic_state_transitions(
    tmp_path: Path,
) -> None:
    store = ProductionStore(tmp_path)
    now = datetime.now(UTC)
    record = ProductionJobRecord(
        id="production-0806",
        source_path="D:/Downloads/0806.mp4",
        output_dir=str(tmp_path),
        state="analyzing",
        primary_reference=10,
        secondary_reference=4,
        flow_operation_budget=3,
        created_at=now,
        updated_at=now,
    )

    store.create(record)
    transitioned = store.transition(
        "blueprint-ready",
        detail="Golden blueprint persisted.",
    )

    assert store.record_path.is_file()
    assert not store.record_path.with_suffix(".tmp").exists()
    assert transitioned.state == "blueprint-ready"
    assert store.load().state_history[-1].detail == (
        "Golden blueprint persisted."
    )

    with pytest.raises(ValueError, match="Invalid production transition"):
        store.transition("completed")


def test_production_store_instances_share_one_job_lock(
    tmp_path: Path,
) -> None:
    first = ProductionStore(tmp_path)
    second = ProductionStore(tmp_path)

    assert first._lock is second._lock


def test_generation_requires_explicit_budget_and_stops_at_approved_count(
    tmp_path: Path,
) -> None:
    output = tmp_path / "production"
    output.mkdir()
    plates = output / "flow-plates"
    plates.mkdir()
    for name in (
        "wrong-rule-start.png",
        "wrong-rule-end.png",
        "physical-risk-start.png",
        "physical-risk-end.png",
        "reversal-start.png",
        "reversal-end.png",
    ):
        (plates / name).write_bytes(b"plate")

    shots = build_0806_flow_shots(output)
    (output / "flow-shot-plan.json").write_text(
        json.dumps(
            [shot.model_dump(mode="json") for shot in shots],
            indent=2,
        ),
        encoding="utf-8",
    )
    now = datetime.now(UTC)
    ProductionStore(output).create(
        ProductionJobRecord(
            id="production-0806",
            source_path="D:/Downloads/0806.mp4",
            output_dir=str(output),
            state="awaiting-generation-approval",
            primary_reference=10,
            secondary_reference=4,
            flow_operation_budget=3,
            flow_repository=str(tmp_path / "gflow"),
            created_at=now,
            updated_at=now,
        )
    )

    class FakeAdapter:
        def __init__(self) -> None:
            self.generated: list[str] = []

        def create_project(self, *, title: str):
            return {
                "status": "ok",
                "project_id": "project-123",
                "title": title,
            }

        def apply_instructions(self, **_kwargs) -> None:
            return None

        def generate(
            self,
            *,
            project_id: str,
            shot: FlowShotSpec,
            output_dir: Path,
        ):
            self.generated.append(shot.id)
            candidate = output_dir / f"{shot.id}.mp4"
            candidate.parent.mkdir(parents=True, exist_ok=True)
            candidate.write_bytes(b"candidate")
            return (
                ["uv", "run", "gflow", "video", "i2v"],
                {
                    "status": "ok",
                    "media_id": f"media-{shot.id}",
                    "local_path": str(candidate),
                    "project_id": project_id,
                },
            )

        def reconcile_media(self, **_kwargs):
            return None

    adapter = FakeAdapter()

    with pytest.raises(ValueError, match="explicit paid-operation approval"):
        generate_flow_candidates(
            output_dir=output,
            approve_paid_ops=0,
            adapter=adapter,
            candidate_preparer=lambda **_kwargs: None,
        )

    result = generate_flow_candidates(
        output_dir=output,
        approve_paid_ops=2,
        adapter=adapter,
        candidate_preparer=lambda **_kwargs: None,
    )

    assert adapter.generated == [shots[0].id, shots[1].id]
    assert result["state"] == "awaiting-candidate-review"
    assert result["consumed_paid_operations"] == 2
    persisted_shots = [
        FlowShotSpec.model_validate(item)
        for item in json.loads(
            (output / "flow-shot-plan.json").read_text(encoding="utf-8")
        )
    ]
    assert len(persisted_shots[0].attempts) == 1
    assert persisted_shots[0].attempts[0].media_id is not None
    assert persisted_shots[2].attempts == []


def test_generation_setup_failure_returns_to_paid_approval_state(
    tmp_path: Path,
) -> None:
    output = tmp_path / "production"
    output.mkdir()
    shots = build_0806_flow_shots(output)
    (output / "flow-shot-plan.json").write_text(
        json.dumps(
            [shot.model_dump(mode="json") for shot in shots],
            indent=2,
        ),
        encoding="utf-8",
    )
    now = datetime.now(UTC)
    ProductionStore(output).create(
        ProductionJobRecord(
            id="production-0806",
            source_path="D:/Downloads/0806.mp4",
            output_dir=str(output),
            state="awaiting-generation-approval",
            primary_reference=10,
            secondary_reference=4,
            flow_operation_budget=3,
            flow_repository=str(tmp_path / "gflow"),
            created_at=now,
            updated_at=now,
        )
    )

    class FailingAdapter:
        def create_project(self, *, title: str):
            raise RuntimeError(f"Unable to create {title}")

    with pytest.raises(RuntimeError, match="Unable to create"):
        generate_flow_candidates(
            output_dir=output,
            approve_paid_ops=1,
            adapter=FailingAdapter(),
            candidate_preparer=lambda **_kwargs: None,
        )

    record = ProductionStore(output).load()
    assert record.state == "awaiting-generation-approval"
    assert record.consumed_paid_operations == 0


def test_candidate_decision_requires_human_scores_and_persists_accepted_clip(
    tmp_path: Path,
) -> None:
    output = tmp_path / "production"
    output.mkdir()
    proxy = output / "flow-candidates" / "proxies" / "candidate.mp4"
    proxy.parent.mkdir(parents=True)
    proxy.write_bytes(b"proxy")
    untouched = output / "flow-candidates" / "raw" / "candidate.mp4"
    untouched.parent.mkdir(parents=True)
    untouched.write_bytes(b"untouched")
    review_path = (
        output
        / "flow-candidates"
        / "reviews"
        / "flow-wrong-rule-branch-attempt-1-automated.json"
    )
    review_path.parent.mkdir(parents=True)
    review_path.write_text(
        json.dumps(
            {
                "technical_gates": {
                    "decoded": True,
                    "duration_ok": True,
                    "no_black_sequence": True,
                    "no_frozen_sequence": True,
                    "single_continuous_shot": True,
                    "safe_framing": True,
                    "no_generated_text": False,
                },
                "metrics": {"duration_ms": 2500},
                "proxy_path": str(proxy),
                "untouched_path": str(untouched),
            }
        ),
        encoding="utf-8",
    )
    shot = FlowShotSpec(
        id="flow-wrong-rule-branch",
        start_ms=11050,
        end_ms=13250,
        editorial_role="wrong-rule-branch",
        prompt=(
            "A physical mechanism chooses a wrong branch in one shot. "
            "No readable text, UI, code, chart, number or document."
        ),
        mode="i2v",
        model="veo-lite",
        input_plates=[str(tmp_path / "start.png")],
        requested_content=["physical-metaphor"],
        constraints=["No readable text"],
        attempts=[
            FlowGenerationAttempt(
                attempt=1,
                command=["uv", "run", "gflow"],
                project_id="project",
                media_id="media",
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                result_json={
                    "candidate_review": {
                        "automated_report_path": str(review_path)
                    }
                },
                untouched_path=str(untouched),
                checksum_sha256="a" * 64,
            )
        ],
        status="awaiting-review",
    )
    (output / "flow-shot-plan.json").write_text(
        json.dumps([shot.model_dump(mode="json")], indent=2),
        encoding="utf-8",
    )
    now = datetime.now(UTC)
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
            created_at=now,
            updated_at=now,
        )
    )

    def fake_transcoder(**kwargs) -> Path:
        destination = kwargs["output"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"accepted")
        return destination

    selection_calls: list[dict[str, object]] = []

    def fake_selection_preparer(**kwargs) -> dict[str, object]:
        selection_calls.append(kwargs)
        selection_proxy = (
            output
            / "flow-candidates"
            / "selections"
            / "selected.mp4"
        )
        selection_sheet = (
            output
            / "flow-candidates"
            / "contact-sheets"
            / "selected.jpg"
        )
        selection_report = (
            output
            / "flow-candidates"
            / "reviews"
            / "selected-automated.json"
        )
        selection_proxy.parent.mkdir(parents=True, exist_ok=True)
        selection_sheet.parent.mkdir(parents=True, exist_ok=True)
        selection_report.parent.mkdir(parents=True, exist_ok=True)
        selection_proxy.write_bytes(b"selection")
        selection_sheet.write_bytes(b"sheet")
        report = {
            "technical_gates": {
                "decoded": True,
                "duration_ok": True,
                "no_black_sequence": True,
                "no_frozen_sequence": True,
                "single_continuous_shot": True,
                "safe_framing": True,
                "no_generated_text": True,
            },
            "metrics": {"duration_ms": 1500},
            "proxy_path": str(selection_proxy),
            "contact_sheet_path": str(selection_sheet),
            "report_path": str(selection_report),
            "hard_gate_passed": True,
        }
        selection_report.write_text(json.dumps(report), encoding="utf-8")
        return report

    with pytest.raises(ValueError, match="candidate duration"):
        review_flow_candidate(
            output_dir=output,
            shot_id=shot.id,
            attempt=1,
            accepted=True,
            scores={
                "prompt_fidelity": 4,
                "motion_quality": 4,
                "continuity": 4,
                "composition": 4,
                "artifact_integrity": 4,
                "editorial_usefulness": 4,
            },
            accepted_start_ms=2000,
            accepted_end_ms=3500,
            reviewer="user",
            transcoder=fake_transcoder,
            selection_preparer=fake_selection_preparer,
        )

    result = review_flow_candidate(
        output_dir=output,
        shot_id=shot.id,
        attempt=1,
        accepted=True,
        scores={
            "prompt_fidelity": 4,
            "motion_quality": 4,
            "continuity": 4,
            "composition": 4,
            "artifact_integrity": 4,
            "editorial_usefulness": 4,
        },
        accepted_start_ms=700,
        accepted_end_ms=2200,
        reviewer="user",
        crop={
            "x": 0.05,
            "y": 0.05,
            "width": 0.9,
            "height": 0.9,
        },
        color_correction={
            "brightness": 1.1,
            "contrast": 1.05,
            "saturation": 1.2,
        },
        transcoder=fake_transcoder,
        selection_preparer=fake_selection_preparer,
    )

    assert result["accepted"] is True
    assert len(selection_calls) == 1
    assert selection_calls[0]["start_ms"] == 700
    assert selection_calls[0]["end_ms"] == 2200
    assert selection_calls[0]["crop"]["height"] == pytest.approx(0.9)
    record = ProductionStore(output).load()
    assert len(record.accepted_clips) == 1
    assert Path(record.accepted_clips[0].proxy_path).is_file()
    assert record.accepted_clips[0].crop.x == pytest.approx(0.05)
    assert record.accepted_clips[0].color_correction.saturation == (
        pytest.approx(1.2)
    )
    persisted = FlowShotSpec.model_validate(
        json.loads(
            (output / "flow-shot-plan.json").read_text(encoding="utf-8")
        )[0]
    )
    assert persisted.status == "accepted"
    candidate_review = (
        persisted.attempts[0].result_json or {}
    )["candidate_review"]
    assert candidate_review["selection_hard_gate_passed"] is True
    assert candidate_review["selection_report_path"].endswith(
        "selected-automated.json"
    )


def test_rejected_candidate_submits_a_second_attempt_instead_of_reusing_first(
    tmp_path: Path,
) -> None:
    output = tmp_path / "production"
    output.mkdir()
    shots = build_0806_flow_shots(output)
    rejected = shots[0]
    old_candidate = output / "flow-candidates" / "raw" / "old.mp4"
    old_candidate.parent.mkdir(parents=True)
    old_candidate.write_bytes(b"old")
    rejected.attempts = [
        FlowGenerationAttempt(
            attempt=1,
            command=["uv", "run", "gflow"],
            project_id="project-123",
            media_id="media-old",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            result_json={"status": "ok"},
            untouched_path=str(old_candidate),
            checksum_sha256="a" * 64,
        )
    ]
    rejected.status = "rejected"
    (output / "flow-shot-plan.json").write_text(
        json.dumps(
            [shot.model_dump(mode="json") for shot in shots],
            indent=2,
        ),
        encoding="utf-8",
    )
    now = datetime.now(UTC)
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
            flow_project_id="project-123",
            created_at=now,
            updated_at=now,
        )
    )

    class FakeAdapter:
        def __init__(self) -> None:
            self.generated: list[str] = []
            self.reconciled: list[str] = []

        def reconcile_media(self, **kwargs):
            self.reconciled.append(kwargs["media_id"])
            return {
                "media_id": kwargs["media_id"],
                "project_id": kwargs["project_id"],
                "local_path": str(old_candidate),
            }

        def generate(
            self,
            *,
            project_id: str,
            shot: FlowShotSpec,
            output_dir: Path,
        ):
            self.generated.append(shot.id)
            candidate = output_dir / f"{shot.id}-retry.mp4"
            candidate.parent.mkdir(parents=True, exist_ok=True)
            candidate.write_bytes(b"retry")
            return (
                ["uv", "run", "gflow", "video", "i2v"],
                {
                    "status": "ok",
                    "media_id": "media-retry",
                    "local_path": str(candidate),
                    "project_id": project_id,
                },
            )

    adapter = FakeAdapter()
    generate_flow_candidates(
        output_dir=output,
        approve_paid_ops=2,
        adapter=adapter,
        candidate_preparer=lambda **_kwargs: None,
    )

    persisted = [
        FlowShotSpec.model_validate(item)
        for item in json.loads(
            (output / "flow-shot-plan.json").read_text(encoding="utf-8")
        )
    ][0]
    assert adapter.generated == [rejected.id]
    assert adapter.reconciled == []
    assert len(persisted.attempts) == 2
    assert persisted.attempts[-1].media_id == "media-retry"
    assert ProductionStore(output).load().consumed_paid_operations == 2


def test_paid_attempt_is_persisted_before_candidate_preparation(
    tmp_path: Path,
) -> None:
    output = tmp_path / "production"
    output.mkdir()
    shots = build_0806_flow_shots(output)
    (output / "flow-shot-plan.json").write_text(
        json.dumps(
            [shot.model_dump(mode="json") for shot in shots],
            indent=2,
        ),
        encoding="utf-8",
    )
    now = datetime.now(UTC)
    ProductionStore(output).create(
        ProductionJobRecord(
            id="production-0806",
            source_path="D:/Downloads/0806.mp4",
            output_dir=str(output),
            state="awaiting-generation-approval",
            primary_reference=10,
            secondary_reference=4,
            flow_operation_budget=3,
            flow_project_id="project-123",
            created_at=now,
            updated_at=now,
        )
    )

    class FakeAdapter:
        def generate(
            self,
            *,
            project_id: str,
            shot: FlowShotSpec,
            output_dir: Path,
        ):
            candidate = output_dir / f"{shot.id}.mp4"
            candidate.parent.mkdir(parents=True, exist_ok=True)
            candidate.write_bytes(b"candidate")
            return (
                ["uv", "run", "gflow", "video", "i2v"],
                {
                    "status": "ok",
                    "media_id": "media-persisted",
                    "local_path": str(candidate),
                    "project_id": project_id,
                },
            )

    def fail_preparation(**_kwargs) -> None:
        raise RuntimeError("review proxy failed")

    with pytest.raises(RuntimeError, match="review proxy failed"):
        generate_flow_candidates(
            output_dir=output,
            approve_paid_ops=1,
            adapter=FakeAdapter(),
            candidate_preparer=fail_preparation,
        )

    persisted = FlowShotSpec.model_validate(
        json.loads(
            (output / "flow-shot-plan.json").read_text(encoding="utf-8")
        )[0]
    )
    record = ProductionStore(output).load()
    assert persisted.attempts[0].media_id == "media-persisted"
    assert persisted.status == "recovery-needed"
    assert record.consumed_paid_operations == 1
    assert record.state == "awaiting-candidate-review"


def test_failed_candidate_preparation_resumes_from_catalog_without_new_paid_op(
    tmp_path: Path,
) -> None:
    output = tmp_path / "production"
    output.mkdir()
    shots = build_0806_flow_shots(output)
    (output / "flow-shot-plan.json").write_text(
        json.dumps(
            [shot.model_dump(mode="json") for shot in shots],
            indent=2,
        ),
        encoding="utf-8",
    )
    now = datetime.now(UTC)
    ProductionStore(output).create(
        ProductionJobRecord(
            id="production-0806",
            source_path="D:/Downloads/0806.mp4",
            output_dir=str(output),
            state="awaiting-generation-approval",
            primary_reference=10,
            secondary_reference=4,
            flow_operation_budget=3,
            flow_project_id="project-123",
            created_at=now,
            updated_at=now,
        )
    )

    class FakeAdapter:
        def __init__(self) -> None:
            self.generate_calls = 0
            self.reconcile_calls = 0
            self.candidate = output / "flow-candidates" / "raw" / "candidate.mp4"

        def generate(
            self,
            *,
            project_id: str,
            shot: FlowShotSpec,
            output_dir: Path,
        ):
            self.generate_calls += 1
            self.candidate.parent.mkdir(parents=True, exist_ok=True)
            self.candidate.write_bytes(b"candidate")
            return (
                ["uv", "run", "gflow", "video", "i2v"],
                {
                    "status": "ok",
                    "media_id": "media-persisted",
                    "local_path": str(self.candidate),
                    "project_id": project_id,
                },
            )

        def reconcile_media(self, **kwargs):
            self.reconcile_calls += 1
            return {
                "media_id": kwargs["media_id"],
                "project_id": kwargs["project_id"],
                "local_path": str(self.candidate),
            }

    adapter = FakeAdapter()

    def fail_preparation(**_kwargs) -> None:
        raise RuntimeError("review proxy failed")

    with pytest.raises(RuntimeError, match="review proxy failed"):
        generate_flow_candidates(
            output_dir=output,
            approve_paid_ops=1,
            adapter=adapter,
            candidate_preparer=fail_preparation,
        )

    stranded = FlowShotSpec.model_validate(
        json.loads(
            (output / "flow-shot-plan.json").read_text(encoding="utf-8")
        )[0]
    )
    assert stranded.status == "recovery-needed"

    def recover_preparation(**kwargs) -> None:
        attempt = kwargs["attempt"]
        result_json = dict(attempt.result_json or {})
        result_json["candidate_review"] = {
            "proxy_path": "flow-candidates/proxies/recovered.mp4",
            "contact_sheet_path": "flow-candidates/contact-sheets/recovered.jpg",
            "automated_report_path": (
                "flow-candidates/reviews/recovered-automated.json"
            ),
            "hard_gate_passed": True,
        }
        attempt.result_json = result_json

    resumed = generate_flow_candidates(
        output_dir=output,
        approve_paid_ops=1,
        adapter=adapter,
        candidate_preparer=recover_preparation,
    )

    recovered = FlowShotSpec.model_validate(
        json.loads(
            (output / "flow-shot-plan.json").read_text(encoding="utf-8")
        )[0]
    )
    assert adapter.generate_calls == 1
    assert adapter.reconcile_calls == 1
    assert recovered.status == "awaiting-review"
    assert recovered.attempts[0].reconciliation_state == "catalog-confirmed"
    assert resumed["consumed_paid_operations"] == 1
    assert resumed["state"] == "awaiting-candidate-review"


def test_unpersisted_paid_result_reconciles_by_prompt_without_new_paid_op(
    tmp_path: Path,
) -> None:
    output = tmp_path / "production"
    output.mkdir()
    shots = build_0806_flow_shots(output)
    (output / "flow-shot-plan.json").write_text(
        json.dumps(
            [shot.model_dump(mode="json") for shot in shots],
            indent=2,
        ),
        encoding="utf-8",
    )
    candidate = output / "flow-candidates" / "raw" / "recovered.mp4"
    candidate.parent.mkdir(parents=True)
    candidate.write_bytes(b"recovered")
    now = datetime.now(UTC)
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
            flow_project_id="project-123",
            created_at=now,
            updated_at=now,
        )
    )

    class FakeAdapter:
        def __init__(self) -> None:
            self.generated = 0
            self.reconciled_prompts: list[str] = []

        def reconcile_shot(self, *, project_id: str, prompt: str):
            self.reconciled_prompts.append(prompt)
            if prompt != shots[0].prompt:
                return None
            return {
                "media_id": "media-recovered",
                "project_id": project_id,
                "prompt": prompt,
                "local_path": str(candidate),
            }

        def generate(self, **_kwargs):
            self.generated += 1
            raise AssertionError("A reconciled paid result must not regenerate")

    def prepare(**kwargs) -> None:
        attempt = kwargs["attempt"]
        result_json = dict(attempt.result_json or {})
        result_json["candidate_review"] = {
            "proxy_path": "flow-candidates/proxies/recovered.mp4",
            "contact_sheet_path": "flow-candidates/contact-sheets/recovered.jpg",
            "automated_report_path": (
                "flow-candidates/reviews/recovered-automated.json"
            ),
            "hard_gate_passed": True,
        }
        attempt.result_json = result_json

    adapter = FakeAdapter()
    resumed = generate_flow_candidates(
        output_dir=output,
        approve_paid_ops=1,
        adapter=adapter,
        candidate_preparer=prepare,
    )

    persisted = FlowShotSpec.model_validate(
        json.loads(
            (output / "flow-shot-plan.json").read_text(encoding="utf-8")
        )[0]
    )
    assert adapter.generated == 0
    assert adapter.reconciled_prompts[0] == shots[0].prompt
    assert persisted.status == "awaiting-review"
    assert persisted.attempts[0].media_id == "media-recovered"
    assert persisted.attempts[0].reconciliation_state == "catalog-confirmed"
    assert resumed["consumed_paid_operations"] == 1


def test_catalog_reconciliation_failure_returns_job_to_review_state(
    tmp_path: Path,
) -> None:
    output = tmp_path / "production"
    output.mkdir()
    shots = build_0806_flow_shots(output)
    candidate = output / "flow-candidates" / "raw" / "candidate.mp4"
    candidate.parent.mkdir(parents=True)
    candidate.write_bytes(b"candidate")
    shots[0].attempts = [
        FlowGenerationAttempt(
            attempt=1,
            command=["uv", "run", "gflow"],
            project_id="project-123",
            media_id="media-known",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            result_json={"status": "ok"},
            untouched_path=str(candidate),
            checksum_sha256="a" * 64,
            reconciliation_state="pending",
        )
    ]
    shots[0].status = "recovery-needed"
    (output / "flow-shot-plan.json").write_text(
        json.dumps(
            [shot.model_dump(mode="json") for shot in shots],
            indent=2,
        ),
        encoding="utf-8",
    )
    now = datetime.now(UTC)
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
            flow_project_id="project-123",
            created_at=now,
            updated_at=now,
        )
    )

    class MissingCatalogAdapter:
        def reconcile_media(self, **_kwargs):
            return None

    with pytest.raises(RuntimeError, match="catalog entry is unavailable"):
        generate_flow_candidates(
            output_dir=output,
            approve_paid_ops=1,
            adapter=MissingCatalogAdapter(),
            candidate_preparer=lambda **_kwargs: None,
        )

    record = ProductionStore(output).load()
    assert record.state == "awaiting-candidate-review"
    assert record.consumed_paid_operations == 1


def test_missing_local_candidate_keeps_media_id_for_reconciliation(
    tmp_path: Path,
) -> None:
    output = tmp_path / "production"
    output.mkdir()
    shots = build_0806_flow_shots(output)
    (output / "flow-shot-plan.json").write_text(
        json.dumps(
            [shot.model_dump(mode="json") for shot in shots],
            indent=2,
        ),
        encoding="utf-8",
    )
    now = datetime.now(UTC)
    ProductionStore(output).create(
        ProductionJobRecord(
            id="production-0806",
            source_path="D:/Downloads/0806.mp4",
            output_dir=str(output),
            state="awaiting-generation-approval",
            primary_reference=10,
            secondary_reference=4,
            flow_operation_budget=3,
            flow_project_id="project-123",
            created_at=now,
            updated_at=now,
        )
    )

    class FakeAdapter:
        def generate(self, *, project_id: str, **_kwargs):
            return (
                ["uv", "run", "gflow", "video", "i2v"],
                {
                    "status": "ok",
                    "media_id": "media-without-download",
                    "local_path": str(output / "missing.mp4"),
                    "project_id": project_id,
                },
            )

    with pytest.raises(RuntimeError, match="missing candidate file"):
        generate_flow_candidates(
            output_dir=output,
            approve_paid_ops=1,
            adapter=FakeAdapter(),
            candidate_preparer=lambda **_kwargs: None,
        )

    persisted = FlowShotSpec.model_validate(
        json.loads(
            (output / "flow-shot-plan.json").read_text(encoding="utf-8")
        )[0]
    )
    record = ProductionStore(output).load()
    assert persisted.attempts[0].media_id == "media-without-download"
    assert persisted.attempts[0].reconciliation_state == "pending"
    assert record.consumed_paid_operations == 1
    assert record.state == "awaiting-candidate-review"
