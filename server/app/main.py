from collections.abc import Callable
import json
import logging
from pathlib import Path
import shutil
from threading import Lock
from uuid import UUID, uuid4

from fastapi import (
    BackgroundTasks,
    FastAPI,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import Settings
from app.editor.analysis import probe_video, validate_source
from app.editor.pipeline import run_pipeline
from app.jobs import JobStore
from app.models import JobRecord, JobState, PipelineResult
from app.production_models import (
    FinalApprovalRequest,
    FlowCandidateDecisionRequest,
    FlowGenerationApprovalRequest,
    ProductionJobRecord,
)

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings,
    *,
    pipeline_runner: Callable[..., object] | None = None,
    production_planner: Callable[..., dict[str, object]] | None = None,
    production_generator: Callable[..., dict[str, object]] | None = None,
    production_candidate_reviewer: (
        Callable[..., dict[str, object]] | None
    ) = None,
    production_assembler: Callable[..., dict[str, object]] | None = None,
    production_approver: Callable[..., dict[str, object]] | None = None,
) -> FastAPI:
    app = FastAPI(title="Cutline Video Editor", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    store = JobStore(settings.storage_root)
    render = pipeline_runner or run_pipeline
    processing_lock = Lock()
    production_root = (
        settings.production_root
        or settings.storage_root.parent / "production-jobs"
    ).resolve()
    production_root.mkdir(parents=True, exist_ok=True)
    from app.editor.production_v4 import (
        ProductionStore,
        approve_production_edit,
        assemble_production_edit,
        generate_flow_candidates,
        plan_production_edit,
        review_flow_candidate,
    )

    plan_production = production_planner or plan_production_edit
    generate_production = (
        production_generator or generate_flow_candidates
    )
    review_candidate = (
        production_candidate_reviewer or review_flow_candidate
    )
    assemble_production = (
        production_assembler or assemble_production_edit
    )
    approve_production = (
        production_approver or approve_production_edit
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/api/jobs",
        response_model=JobRecord,
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def create_job(
        background_tasks: BackgroundTasks,
        file: UploadFile,
    ) -> JobRecord:
        filename = Path(file.filename or "").name
        if Path(filename).suffix.lower() != ".mp4":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only MP4 video uploads are supported.",
            )

        record = store.create(filename)
        source_path = store.source_path(record.id)
        total = 0
        try:
            with source_path.open("wb") as destination:
                while chunk := await file.read(1024 * 1024):
                    total += len(chunk)
                    if total > settings.max_upload_bytes:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail="Upload exceeds the configured size limit.",
                        )
                    destination.write(chunk)
            metadata = probe_video(source_path)
            validate_source(metadata)
        except HTTPException:
            shutil.rmtree(store.job_dir(record.id), ignore_errors=True)
            raise
        except ValueError as error:
            shutil.rmtree(store.job_dir(record.id), ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            ) from error
        finally:
            await file.close()

        store.update(record.id, state="queued", progress=2)
        background_tasks.add_task(
            _process_job,
            store,
            record.id,
            render,
            processing_lock,
        )
        return store.get(record.id)

    @app.get("/api/jobs/{job_id}", response_model=JobRecord)
    def get_job(job_id: str) -> JobRecord:
        try:
            return store.get(job_id)
        except KeyError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found.",
            ) from error

    @app.get("/api/jobs/{job_id}/video")
    def get_video(job_id: str) -> FileResponse:
        try:
            record = store.get(job_id)
        except KeyError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found.",
            ) from error
        output = store.output_path(job_id)
        if record.state != "completed" or not output.is_file():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Edited video is not ready.",
            )
        return FileResponse(
            output,
            media_type="video/mp4",
            filename=f"edited-{record.original_filename}",
        )

    @app.get("/api/jobs/{job_id}/report")
    def get_report(job_id: str) -> dict[str, object]:
        try:
            record = store.get(job_id)
        except KeyError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found.",
            ) from error
        if record.state != "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Editing report is not ready.",
            )
        job_dir = store.job_dir(job_id)
        plan_path = job_dir / "edit-plan.json"
        qc_path = job_dir / "qc-report.json"
        if not plan_path.is_file() or not qc_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Editing report artifacts are missing.",
            )
        return {
            "edit_plan": json.loads(plan_path.read_text(encoding="utf-8")),
            "qc_report": json.loads(qc_path.read_text(encoding="utf-8")),
        }

    @app.post(
        "/api/production/jobs",
        response_model=ProductionJobRecord,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_production_job(
        file: UploadFile,
        primary_reference: int = Form(default=10, ge=1, le=14),
        secondary_reference: int = Form(default=4, ge=1, le=14),
        flow_operation_budget: int = Form(default=3, ge=0, le=5),
        asset_policy: str = Form(default="free-licensed"),
        quality_target: str = Form(default="reference-max"),
        capture_profile: str = Form(default="local-metatrader"),
        voice_policy: str = Form(default="preserve-verbatim"),
    ) -> ProductionJobRecord:
        filename = Path(file.filename or "").name
        if Path(filename).suffix.lower() != ".mp4":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only MP4 video uploads are supported.",
            )
        job_id = str(uuid4())
        output_dir = production_root / job_id
        output_dir.mkdir(parents=False, exist_ok=False)
        source_path = output_dir / filename
        total = 0
        try:
            with source_path.open("wb") as destination:
                while chunk := await file.read(1024 * 1024):
                    total += len(chunk)
                    if total > settings.max_upload_bytes:
                        raise HTTPException(
                            status_code=(
                                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                            ),
                            detail="Upload exceeds the configured size limit.",
                        )
                    destination.write(chunk)
            metadata = probe_video(source_path)
            validate_source(metadata)
            plan_production(
                source=source_path,
                output_dir=output_dir,
                primary_reference=primary_reference,
                secondary_reference=secondary_reference,
                asset_policy=asset_policy,
                quality_target=quality_target,
                capture_profile=capture_profile,
                voice_policy=voice_policy,
                flow_operation_budget=flow_operation_budget,
                flow_repository=None,
                flow_profile="sahilsharmabybit2",
                job_id=job_id,
            )
            return ProductionStore(output_dir).load()
        except HTTPException:
            shutil.rmtree(output_dir, ignore_errors=True)
            raise
        except (ValueError, FileNotFoundError) as error:
            shutil.rmtree(output_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            ) from error
        finally:
            await file.close()

    @app.get(
        "/api/production/jobs/{job_id}",
        response_model=ProductionJobRecord,
    )
    def get_production_job(job_id: str) -> ProductionJobRecord:
        output_dir = _production_job_dir(production_root, job_id)
        try:
            return ProductionStore(output_dir).load()
        except FileNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Production job not found.",
            ) from error

    @app.get("/api/production/jobs/{job_id}/flow-candidates")
    def get_flow_candidates(job_id: str) -> dict[str, object]:
        output_dir = _production_job_dir(production_root, job_id)
        record_path = output_dir / "production-job.json"
        flow_path = output_dir / "flow-shot-plan.json"
        if not record_path.is_file() or not flow_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Production job not found.",
            )
        shots = json.loads(flow_path.read_text(encoding="utf-8"))
        for shot in shots:
            for attempt in shot.get("attempts", []):
                result = attempt.get("result_json") or {}
                review = result.get("candidate_review") or {}
                for key in (
                    "proxy_path",
                    "contact_sheet_path",
                    "automated_report_path",
                ):
                    if review.get(key):
                        review[key] = _relative_production_artifact(
                            output_dir,
                            review[key],
                        )
                if attempt.get("untouched_path"):
                    attempt["untouched_path"] = (
                        _relative_production_artifact(
                            output_dir,
                            attempt["untouched_path"],
                        )
                    )
        accepted_clips = []
        for item in ProductionStore(output_dir).load().accepted_clips:
            payload = item.model_dump(mode="json")
            payload["untouched_path"] = _relative_production_artifact(
                output_dir,
                payload["untouched_path"],
            )
            payload["proxy_path"] = _relative_production_artifact(
                output_dir,
                payload["proxy_path"],
            )
            accepted_clips.append(payload)
        return {"shots": shots, "accepted_clips": accepted_clips}

    @app.post(
        "/api/production/jobs/{job_id}/generation-approval",
        status_code=status.HTTP_202_ACCEPTED,
    )
    def approve_flow_generation(
        job_id: str,
        request: FlowGenerationApprovalRequest,
        background_tasks: BackgroundTasks,
    ) -> ProductionJobRecord:
        output_dir = _production_job_dir(production_root, job_id)
        try:
            record = ProductionStore(output_dir).load()
        except FileNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Production job not found.",
            ) from error
        if record.state not in {
            "awaiting-generation-approval",
            "awaiting-candidate-review",
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Paid generation is not available in this state.",
            )
        background_tasks.add_task(
            _run_production_action,
            output_dir,
            generate_production,
            {
                "output_dir": output_dir,
                "approve_paid_ops": request.approve_paid_ops,
            },
        )
        return record

    @app.post("/api/production/jobs/{job_id}/candidate-decisions")
    def decide_flow_candidate(
        job_id: str,
        request: FlowCandidateDecisionRequest,
    ) -> dict[str, object]:
        output_dir = _production_job_dir(production_root, job_id)
        try:
            return review_candidate(
                output_dir=output_dir,
                shot_id=request.shot_id,
                attempt=request.attempt,
                accepted=request.accepted,
                scores=request.scores.model_dump(),
                accepted_start_ms=request.accepted_start_ms,
                accepted_end_ms=request.accepted_end_ms,
                reviewer=request.reviewer,
                rejection_reasons=request.rejection_reasons,
                speed=request.speed,
                crop=request.crop.model_dump(),
                color_correction=request.color_correction.model_dump(),
            )
        except FileNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Production job not found.",
            ) from error
        except (ValueError, KeyError) as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

    @app.post(
        "/api/production/jobs/{job_id}/assemble",
        status_code=status.HTTP_202_ACCEPTED,
    )
    def assemble_production_job(
        job_id: str,
        background_tasks: BackgroundTasks,
    ) -> ProductionJobRecord:
        output_dir = _production_job_dir(production_root, job_id)
        try:
            record = ProductionStore(output_dir).load()
        except FileNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Production job not found.",
            ) from error
        background_tasks.add_task(
            _run_production_action,
            output_dir,
            assemble_production,
            {"output_dir": output_dir},
        )
        return record

    @app.post(
        "/api/production/jobs/{job_id}/final-approval",
        response_model=ProductionJobRecord,
    )
    def approve_final_production(
        job_id: str,
        request: FinalApprovalRequest,
    ) -> ProductionJobRecord:
        output_dir = _production_job_dir(production_root, job_id)
        try:
            approve_production(
                output_dir=output_dir,
                reviewer=request.reviewer,
            )
            return ProductionStore(output_dir).load()
        except FileNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Production job not found.",
            ) from error
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

    @app.get("/api/production/jobs/{job_id}/video")
    def get_production_video(job_id: str) -> FileResponse:
        output_dir = _production_job_dir(production_root, job_id)
        try:
            record = ProductionStore(output_dir).load()
        except FileNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Production job not found.",
            ) from error
        video = output_dir / "edited.mp4"
        if record.state != "completed" or not video.is_file():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Production video has not passed final approval.",
            )
        return FileResponse(
            video,
            media_type="video/mp4",
            filename=f"production-{Path(record.source_path).name}",
        )

    @app.get("/api/production/jobs/{job_id}/artifacts/{artifact_path:path}")
    def get_production_artifact(
        job_id: str,
        artifact_path: str,
    ) -> FileResponse:
        output_dir = _production_job_dir(production_root, job_id)
        candidate = (output_dir / artifact_path).resolve()
        if (
            output_dir not in candidate.parents
            or not candidate.is_file()
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Production artifact not found.",
            )
        return FileResponse(candidate)

    return app


def _process_job(
    store: JobStore,
    job_id: str,
    pipeline_runner: Callable[..., object],
    processing_lock,
) -> None:
    stage_states: dict[str, JobState] = {
        "analyzing": "analyzing",
        "transcribing": "transcribing",
        "cleaning": "cleaning",
        "planning": "planning",
        "sourcing": "sourcing",
        "rendering": "rendering",
        "mastering": "mastering",
        "quality_control": "quality_control",
        "verifying": "verifying",
        "completed": "completed",
    }

    def progress(stage: str, percent: int) -> None:
        state = stage_states.get(stage, "rendering")
        store.update(job_id, state=state, progress=percent)

    try:
        with processing_lock:
            result = pipeline_runner(
                source=store.source_path(job_id),
                output=store.output_path(job_id),
                work_dir=store.job_dir(job_id),
                progress=progress,
            )
            if not isinstance(result, PipelineResult):
                raise TypeError("Pipeline returned an invalid result")
            store.update(
                job_id,
                state="completed",
                progress=100,
                result=result,
            )
    except Exception as error:
        logger.error(
            "Video job %s failed (%s)",
            job_id,
            type(error).__name__,
        )
        store.update(
            job_id,
            state="failed",
            progress=100,
            error="Video processing failed. Check the server logs.",
        )


def _production_job_dir(root: Path, job_id: str) -> Path:
    try:
        parsed = UUID(job_id)
    except (ValueError, AttributeError) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Production job not found.",
        ) from error
    if str(parsed) != job_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Production job not found.",
        )
    return root / job_id


def _relative_production_artifact(
    output_dir: Path,
    value: str,
) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        return path.as_posix()
    resolved = path.resolve()
    if output_dir not in resolved.parents:
        return resolved.name
    return resolved.relative_to(output_dir).as_posix()


def _run_production_action(
    output_dir: Path,
    action: Callable[..., object],
    kwargs: dict[str, object],
) -> None:
    try:
        action(**kwargs)
    except Exception as error:
        logger.error(
            "Production job %s failed (%s)",
            output_dir.name,
            type(error).__name__,
        )
        try:
            from app.editor.production_v4 import ProductionStore

            store = ProductionStore(output_dir)
            record = store.load()
            updated = record.model_copy(
                update={
                    "error": (
                        "Production action failed. Check the server logs."
                    )
                }
            )
            store.save(
                ProductionJobRecord.model_validate(
                    updated.model_dump(mode="json")
                )
            )
        except Exception:
            logger.exception(
                "Unable to persist production failure state for %s",
                output_dir.name,
            )


_workspace_root = Path(__file__).resolve().parents[2]
app = create_app(
    Settings(
        storage_root=_workspace_root / "storage" / "jobs",
        production_root=_workspace_root / "storage" / "production-jobs",
    )
)
