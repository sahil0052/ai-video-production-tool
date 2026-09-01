from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from threading import Lock
import time

import cv2
from fastapi.testclient import TestClient
import numpy as np

from app.config import Settings
from app.jobs import JobStore
from app.main import _process_job, create_app
from app.models import PipelineResult, VideoMetadata
from app.editor.production_v4 import ProductionStore
from app.production_models import ProductionJobRecord, ProductionStateEvent
from datetime import UTC, datetime


def write_video(path: Path) -> None:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        10,
        (180, 320),
    )
    assert writer.isOpened()
    for index in range(20):
        frame = np.full((320, 180, 3), 30 + index, dtype=np.uint8)
        writer.write(frame)
    writer.release()


def test_health_endpoint(tmp_path: Path) -> None:
    app = create_app(Settings(storage_root=tmp_path))

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_rejects_unsupported_extension(tmp_path: Path) -> None:
    app = create_app(Settings(storage_root=tmp_path))

    with TestClient(app) as client:
        response = client.post(
            "/api/jobs",
            files={"file": ("notes.txt", b"not video", "text/plain")},
        )

    assert response.status_code == 400
    assert "MP4" in response.json()["detail"]


def test_upload_rejects_files_over_limit(tmp_path: Path) -> None:
    app = create_app(Settings(storage_root=tmp_path, max_upload_bytes=8))

    with TestClient(app) as client:
        response = client.post(
            "/api/jobs",
            files={"file": ("raw.mp4", b"123456789", "video/mp4")},
        )

    assert response.status_code == 413


def test_upload_processes_video_and_exposes_download(tmp_path: Path) -> None:
    source_fixture = tmp_path / "fixture.mp4"
    write_video(source_fixture)

    def fake_pipeline(**kwargs) -> PipelineResult:
        kwargs["progress"]("rendering", 65)
        kwargs["output"].write_bytes(kwargs["source"].read_bytes())
        (kwargs["work_dir"] / "edit-plan.json").write_text(
            json.dumps({"version": "1.0", "profile": "tech-story-v1"}),
            encoding="utf-8",
        )
        (kwargs["work_dir"] / "qc-report.json").write_text(
            json.dumps({"passed": True, "style_score": 90, "checks": []}),
            encoding="utf-8",
        )
        kwargs["progress"]("completed", 100)
        return PipelineResult(
            output_metadata=VideoMetadata(
                width=180,
                height=320,
                fps=10,
                frame_count=20,
                duration_seconds=2,
            ),
            caption_count=1,
            cut_timestamps=[],
            transcript_text="Expert Advisor",
            broll_coverage=0.6,
            style_score=90,
            qc_passed=True,
        )

    app = create_app(
        Settings(storage_root=tmp_path / "jobs"),
        pipeline_runner=fake_pipeline,
    )

    with TestClient(app) as client:
        with source_fixture.open("rb") as source:
            response = client.post(
                "/api/jobs",
                files={"file": ("0806.mp4", source, "video/mp4")},
            )
        assert response.status_code == 202
        job_id = response.json()["id"]

        deadline = time.time() + 2
        job = None
        while time.time() < deadline:
            status = client.get(f"/api/jobs/{job_id}")
            assert status.status_code == 200
            job = status.json()
            if job["state"] == "completed":
                break
            time.sleep(0.02)

        assert job is not None
        assert job["state"] == "completed"
        assert job["progress"] == 100

        download = client.get(f"/api/jobs/{job_id}/video")
        assert download.status_code == 200
        assert download.headers["content-type"].startswith("video/mp4")

        report = client.get(f"/api/jobs/{job_id}/report")
        assert report.status_code == 200
        assert report.json()["edit_plan"]["version"] == "1.0"
        assert report.json()["qc_report"]["passed"] is True


def test_process_job_serializes_pipeline_runs(tmp_path: Path) -> None:
    store = JobStore(tmp_path)
    first = store.create("first.mp4")
    second = store.create("second.mp4")
    processing_lock = Lock()
    state_lock = Lock()
    active = 0
    maximum_active = 0

    def fake_pipeline(**_kwargs) -> PipelineResult:
        nonlocal active, maximum_active
        with state_lock:
            active += 1
            maximum_active = max(maximum_active, active)
        time.sleep(0.05)
        with state_lock:
            active -= 1
        return PipelineResult(
            output_metadata=VideoMetadata(
                width=1080,
                height=1920,
                fps=30,
                frame_count=30,
                duration_seconds=1,
            ),
            caption_count=0,
            cut_timestamps=[],
            transcript_text="",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                _process_job,
                store,
                record.id,
                fake_pipeline,
                processing_lock,
            )
            for record in (first, second)
        ]
        for future in futures:
            future.result()

    assert maximum_active == 1
    assert store.get(first.id).state == "completed"
    assert store.get(second.id).state == "completed"


def test_process_job_hides_internal_error_details(tmp_path: Path) -> None:
    store = JobStore(tmp_path)
    record = store.create("raw.mp4")

    def failing_pipeline(**_kwargs):
        raise RuntimeError("secret path C:\\private\\input.mp4")

    _process_job(store, record.id, failing_pipeline, Lock())

    failed = store.get(record.id)
    assert failed.state == "failed"
    assert failed.error == "Video processing failed. Check the server logs."
    assert "private" not in failed.error


def test_staged_production_api_enforces_generation_and_final_approval(
    tmp_path: Path,
) -> None:
    source_fixture = tmp_path / "fixture.mp4"
    write_video(source_fixture)
    production_root = tmp_path / "production"

    def fake_planner(**kwargs):
        now = datetime.now(UTC)
        store = ProductionStore(kwargs["output_dir"])
        record = ProductionJobRecord(
            id=kwargs["job_id"],
            source_path=str(kwargs["source"]),
            output_dir=str(kwargs["output_dir"]),
            state="awaiting-generation-approval",
            primary_reference=kwargs["primary_reference"],
            secondary_reference=kwargs["secondary_reference"],
            flow_operation_budget=kwargs["flow_operation_budget"],
            state_history=[
                ProductionStateEvent(
                    state="awaiting-generation-approval",
                    at=now,
                    detail="Test blueprint ready.",
                )
            ],
            artifacts={"blueprint": "blueprint.json"},
            created_at=now,
            updated_at=now,
        )
        store.create(record)
        (kwargs["output_dir"] / "blueprint.json").write_text(
            json.dumps({"version": "4.0"}),
            encoding="utf-8",
        )
        (kwargs["output_dir"] / "flow-shot-plan.json").write_text(
            "[]",
            encoding="utf-8",
        )
        return record.model_dump(mode="json")

    def fake_generator(**kwargs):
        store = ProductionStore(kwargs["output_dir"])
        record = store.load().model_copy(
            update={
                "state": "awaiting-candidate-review",
                "approved_paid_operations": kwargs["approve_paid_ops"],
                "consumed_paid_operations": kwargs["approve_paid_ops"],
                "updated_at": datetime.now(UTC),
            }
        )
        store.save(
            ProductionJobRecord.model_validate(
                record.model_dump(mode="json")
            )
        )
        return record.model_dump(mode="json")

    def fake_assembler(**kwargs):
        store = ProductionStore(kwargs["output_dir"])
        record = store.load().model_copy(
            update={
                "state": "awaiting-final-approval",
                "automated_pass": True,
                "updated_at": datetime.now(UTC),
            }
        )
        store.save(
            ProductionJobRecord.model_validate(
                record.model_dump(mode="json")
            )
        )
        (kwargs["output_dir"] / "edited.mp4").write_bytes(
            source_fixture.read_bytes()
        )
        return record.model_dump(mode="json")

    def fake_approver(**kwargs):
        store = ProductionStore(kwargs["output_dir"])
        record = store.load().model_copy(
            update={
                "state": "completed",
                "human_approved": True,
                "final_reviewer": kwargs["reviewer"],
                "updated_at": datetime.now(UTC),
            }
        )
        store.save(
            ProductionJobRecord.model_validate(
                record.model_dump(mode="json")
            )
        )
        return record.model_dump(mode="json")

    app = create_app(
        Settings(
            storage_root=tmp_path / "jobs",
            production_root=production_root,
        ),
        production_planner=fake_planner,
        production_generator=fake_generator,
        production_assembler=fake_assembler,
        production_approver=fake_approver,
    )

    with TestClient(app) as client:
        with source_fixture.open("rb") as source:
            created = client.post(
                "/api/production/jobs",
                files={"file": ("0806.mp4", source, "video/mp4")},
                data={"flow_operation_budget": "3"},
            )
        assert created.status_code == 201
        job_id = created.json()["id"]
        assert created.json()["state"] == "awaiting-generation-approval"

        blocked_video = client.get(
            f"/api/production/jobs/{job_id}/video"
        )
        assert blocked_video.status_code == 409

        artifact = client.get(
            f"/api/production/jobs/{job_id}/artifacts/blueprint.json"
        )
        assert artifact.status_code == 200

        approved = client.post(
            f"/api/production/jobs/{job_id}/generation-approval",
            json={"approve_paid_ops": 2},
        )
        assert approved.status_code == 202
        status_after_generation = client.get(
            f"/api/production/jobs/{job_id}"
        )
        assert status_after_generation.json()["state"] == (
            "awaiting-candidate-review"
        )

        assembled = client.post(
            f"/api/production/jobs/{job_id}/assemble"
        )
        assert assembled.status_code == 202
        ready = client.get(f"/api/production/jobs/{job_id}")
        assert ready.json()["state"] == "awaiting-final-approval"
        assert ready.json()["human_approved"] is False

        final = client.post(
            f"/api/production/jobs/{job_id}/final-approval",
            json={"reviewer": "user"},
        )
        assert final.status_code == 200
        assert final.json()["state"] == "completed"
        assert final.json()["human_approved"] is True

        released = client.get(
            f"/api/production/jobs/{job_id}/video"
        )
        assert released.status_code == 200
