from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
from threading import Lock, RLock
from typing import Any

from app.editor.flow_adapter import FlowCliAdapter, FlowGenerationError
from app.production_models import (
    CropSpec,
    FlowAcceptedClip,
    FlowCandidateReview,
    FlowGenerationAttempt,
    FlowReviewScores,
    FlowShotSpec,
    FlowTechnicalGates,
    ProductionJobRecord,
    ProductionState,
    ProductionStateEvent,
    validate_production_transition,
)


_DEFAULT_FLOW_REPOSITORY = Path(
    r"C:\Users\HPUSER\Documents\ChatGPT\New project"
)
_JOB_FILENAME = "production-job.json"
_FLOW_PLAN_FILENAME = "flow-shot-plan.json"
_FLOW_INSTRUCTIONS_FILENAME = "flow-instructions.json"
_STORE_LOCKS_GUARD = Lock()
_STORE_LOCKS: dict[Path, RLock] = {}


def _store_lock(record_path: Path) -> RLock:
    with _STORE_LOCKS_GUARD:
        return _STORE_LOCKS.setdefault(record_path, RLock())


class ProductionStore:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir.expanduser().resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.record_path = self.output_dir / _JOB_FILENAME
        self._lock = _store_lock(self.record_path)

    def create(self, record: ProductionJobRecord) -> ProductionJobRecord:
        with self._lock:
            if self.record_path.exists():
                raise FileExistsError(self.record_path)
            self._write(record)
        return record

    def load(self) -> ProductionJobRecord:
        with self._lock:
            if not self.record_path.is_file():
                raise FileNotFoundError(self.record_path)
            return ProductionJobRecord.model_validate_json(
                self.record_path.read_text(encoding="utf-8")
            )

    def save(self, record: ProductionJobRecord) -> ProductionJobRecord:
        with self._lock:
            self._write(record)
        return record

    def transition(
        self,
        target: ProductionState,
        *,
        detail: str = "",
        updates: dict[str, Any] | None = None,
    ) -> ProductionJobRecord:
        with self._lock:
            current = self.load()
            validate_production_transition(current.state, target)
            now = datetime.now(UTC)
            payload: dict[str, Any] = {
                "state": target,
                "updated_at": now,
                "state_history": [
                    *current.state_history,
                    ProductionStateEvent(
                        state=target,
                        at=now,
                        detail=detail,
                    ),
                ],
            }
            if updates:
                payload.update(updates)
            updated = current.model_copy(update=payload)
            updated = ProductionJobRecord.model_validate(
                updated.model_dump(mode="json")
            )
            self._write(updated)
            return updated

    def _write(self, record: ProductionJobRecord) -> None:
        temporary = self.record_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                record.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        os.replace(temporary, self.record_path)


def build_0806_shot_schedule() -> list[dict[str, Any]]:
    boundaries = [
        0,
        650,
        2340,
        3800,
        5250,
        6820,
        7920,
        9560,
        10700,
        12050,
        14160,
        14880,
        17000,
        19220,
        21140,
        23140,
        24650,
        26080,
        27780,
        29900,
        32200,
        33180,
        35200,
        37160,
        41400,
    ]
    roles = [
        ("hook-action", "hook", "real-product"),
        ("hook-split", "hook", "real-product"),
        ("metaeditor-open", "explanation", "real-product"),
        ("code-macro", "explanation", "real-product"),
        ("rule-highlight", "explanation", "real-product"),
        ("navigator-open", "demonstration", "real-product"),
        ("ea-identification", "demonstration", "real-product"),
        ("presenter-reset", "claim", "presenter"),
        ("risk-code-detail", "explanation", "real-product"),
        ("wrong-rule-branch", "contrast", "flow-illustrative"),
        ("evidence-overview", "evidence", "direct-evidence"),
        ("evidence-championship", "evidence", "direct-evidence"),
        ("evidence-risk-excerpt", "evidence", "direct-evidence"),
        ("evidence-number", "evidence", "direct-evidence"),
        ("risk-input", "contrast", "real-product"),
        ("risk-input-detail", "demonstration", "real-product"),
        ("risk-alternate", "demonstration", "real-product"),
        ("risk-reversal", "contrast", "flow-illustrative"),
        ("lesson-code", "payoff", "real-product"),
        ("lesson-parameters", "payoff", "real-product"),
        ("presenter-reset-2", "payoff", "presenter"),
        ("attach-ea", "demonstration", "real-product"),
        ("strategy-tester", "demonstration", "real-product"),
        ("presenter-cta", "cta", "presenter"),
    ]
    return [
        {
            "id": f"shot-{index:02d}",
            "start_ms": boundaries[index - 1],
            "end_ms": boundaries[index],
            "editorial_role": editorial_role,
            "narrative_role": narrative_role,
            "source_role": source_role,
            "reference_role": (
                "secondary-4"
                if editorial_role in {"risk-input", "risk-reversal"}
                else "primary-10"
            ),
        }
        for index, (editorial_role, narrative_role, source_role) in enumerate(
            roles,
            start=1,
        )
    ]


def build_0806_flow_shots(output_dir: Path) -> list[FlowShotSpec]:
    plates = output_dir.expanduser().resolve() / "flow-plates"
    common_constraints = [
        "One continuous shot with no internal edit",
        "No readable text, letters, numbers, symbols or watermarks",
        "No software interface, code, chart, document or evidence",
        "Keep the main action inside the portrait center-safe region",
        "Natural physically plausible motion with restrained camera movement",
        "No crushed blacks; preserve well-exposed shape separation",
    ]
    return [
        FlowShotSpec(
            id="flow-wrong-rule-branch",
            start_ms=12050,
            end_ms=14160,
            editorial_role="wrong-rule-branch",
            prompt=(
                "Portrait cinematic macro view of a precise mechanical "
                "decision mechanism following one branch, then physically "
                "committing to the visibly wrong branch through motion only. "
                "Well-exposed deep graphite and navy materials, a crisp cyan "
                "correct branch and one restrained warm amber wrong branch, "
                "clean lighting, one continuous camera move. No readable "
                "text, no software UI, no code, no charts, no numbers, no "
                "documents, no logos."
            ),
            mode="i2v",
            model="veo-lite",
            input_plates=[
                str(plates / "wrong-rule-start.png"),
                str(plates / "wrong-rule-end.png"),
            ],
            requested_content=["physical-metaphor"],
            constraints=common_constraints,
        ),
        FlowShotSpec(
            id="flow-physical-risk",
            start_ms=21820,
            end_ms=23140,
            editorial_role="physical-risk-metaphor",
            prompt=(
                "Portrait macro shot of a balanced precision mechanism "
                "gradually becoming unstable as one physical load increases, "
                "communicating risk only through motion and weight. Restrained "
                "well-exposed documentary lighting, cool cyan balance "
                "hardware and one restrained risk-red load in one continuous "
                "shot. No readable text, no software UI, no code, no charts, "
                "no numbers, no currency, no documents, no logos."
            ),
            mode="i2v",
            model="veo-lite",
            input_plates=[
                str(plates / "physical-risk-start.png"),
                str(plates / "physical-risk-end.png"),
            ],
            requested_content=["physical-metaphor"],
            constraints=common_constraints,
        ),
        FlowShotSpec(
            id="flow-reversal-texture",
            start_ms=24650,
            end_ms=27780,
            editorial_role="risk-reversal-texture",
            prompt=(
                "Abstract but physically plausible portrait motion plate: "
                "layered directional material moves upward with controlled "
                "momentum, stalls, then reverses downward in one continuous "
                "shot. Well-exposed deep graphite with luminous teal upward "
                "layers and a restrained warm red downward reversal, no "
                "camera cut. No readable text, no software UI, no code, no "
                "charts, no numbers, no documents, no logos."
            ),
            mode="i2v",
            model="veo-lite",
            input_plates=[
                str(plates / "reversal-start.png"),
                str(plates / "reversal-end.png"),
            ],
            requested_content=["abstract-motion"],
            constraints=common_constraints,
        ),
    ]


SOCIAL_KINETIC_STORY_PROFILES = {
    "auto",
    "automation-future",
    "rofx-case",
    "cpi-inflation",
}


def resolve_social_kinetic_story_profile(
    *,
    source_name: str,
    requested: str,
) -> str:
    if requested not in SOCIAL_KINETIC_STORY_PROFILES:
        raise ValueError(f"Unknown social-kinetic story profile: {requested}")
    if requested != "auto":
        return requested
    stem = Path(source_name).stem.casefold()
    if stem == "0810":
        return "automation-future"
    if stem == "0811":
        return "rofx-case"
    if stem == "0813":
        return "cpi-inflation"
    raise ValueError(
        "Social-kinetic edits require --story-profile for an unknown story"
    )


def plan_production_edit(
    *,
    source: Path,
    output_dir: Path,
    primary_reference: int = 10,
    secondary_reference: int = 4,
    asset_policy: str = "free-licensed",
    quality_target: str = "reference-max",
    capture_profile: str = "local-metatrader",
    voice_policy: str = "preserve-verbatim",
    flow_operation_budget: int = 3,
    flow_repository: Path | None = None,
    flow_profile: str = "sahilsharmabybit2",
    style_reference: Path | None = None,
    reference_profile: str = "technical-reference",
    story_profile: str = "auto",
    seed_dir: Path | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    del asset_policy, quality_target, capture_profile, voice_policy
    source = source.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if flow_operation_budget < 0 or flow_operation_budget > 8:
        raise ValueError("Flow operation budget must be between zero and eight")

    store = ProductionStore(output_dir)
    if store.record_path.is_file():
        return store.load().model_dump(mode="json")

    now = datetime.now(UTC)
    record = ProductionJobRecord(
        id=job_id or f"production-{source.stem.casefold()}",
        source_path=str(source),
        output_dir=str(output_dir),
        state="analyzing",
        primary_reference=primary_reference,
        secondary_reference=secondary_reference,
        flow_operation_budget=flow_operation_budget,
        flow_profile=flow_profile,
        flow_repository=str(
            (flow_repository or _DEFAULT_FLOW_REPOSITORY)
            .expanduser()
            .resolve()
        ),
        state_history=[
            ProductionStateEvent(
                state="analyzing",
                at=now,
                detail="Production planning started.",
            )
        ],
        created_at=now,
        updated_at=now,
    )
    store.create(record)

    if reference_profile == "social-kinetic":
        resolved_story_profile = resolve_social_kinetic_story_profile(
            source_name=source.name,
            requested=story_profile,
        )
        if resolved_story_profile == "automation-future":
            from app.editor.human_reference_0810 import (
                build_human_reference_blueprint,
            )

            artifacts = build_human_reference_blueprint(
                source=source,
                output_dir=output_dir,
                style_reference=style_reference,
                flow_operation_budget=flow_operation_budget,
            )
        elif resolved_story_profile == "rofx-case":
            from app.editor.profit_bricks_rofx import (
                build_rofx_blueprint,
            )

            artifacts = build_rofx_blueprint(
                source=source,
                output_dir=output_dir,
                style_reference=style_reference,
                flow_operation_budget=flow_operation_budget,
            )
        else:
            from app.editor.profit_bricks_cpi import (
                build_cpi_blueprint,
            )

            artifacts = build_cpi_blueprint(
                source=source,
                output_dir=output_dir,
                style_reference=style_reference,
                flow_operation_budget=flow_operation_budget,
            )
    else:
        from app.editor.production_blueprint import (
            build_production_blueprint,
        )

        artifacts = build_production_blueprint(
            source=source,
            output_dir=output_dir,
            primary_reference=primary_reference,
            secondary_reference=secondary_reference,
            seed_dir=seed_dir,
        )
    store.transition(
        "blueprint-ready",
        detail="Explicit-layer production blueprint persisted.",
        updates={"artifacts": artifacts},
    )
    blueprint = json.loads(
        (output_dir / artifacts["blueprint"]).read_text(encoding="utf-8")
    )
    if blueprint.get("flow_shots"):
        record = store.transition(
            "awaiting-generation-approval",
            detail=(
                "Flow shots are planned; no paid operation has been submitted."
            ),
        )
    else:
        record = store.load()
    return record.model_dump(mode="json")


CandidatePreparer = Callable[..., object]
SelectionPreparer = Callable[..., dict[str, Any]]


def _candidate_review_is_ready(attempt: FlowGenerationAttempt) -> bool:
    result_json = attempt.result_json or {}
    candidate_review = result_json.get("candidate_review")
    return (
        isinstance(candidate_review, dict)
        and bool(candidate_review.get("automated_report_path"))
    )


def _return_generation_to_review(
    store: ProductionStore,
    *,
    detail: str,
) -> None:
    if store.load().state == "generating":
        store.transition(
            "awaiting-candidate-review",
            detail=detail,
        )


def generate_flow_candidates(
    *,
    output_dir: Path,
    approve_paid_ops: int,
    adapter: Any | None = None,
    candidate_preparer: CandidatePreparer | None = None,
) -> dict[str, Any]:
    if approve_paid_ops <= 0:
        raise ValueError(
            "Flow generation requires explicit paid-operation approval"
        )
    output_dir = output_dir.expanduser().resolve()
    store = ProductionStore(output_dir)
    record = store.load()
    if approve_paid_ops > record.flow_operation_budget:
        raise ValueError(
            "Paid-operation approval exceeds the configured Flow budget"
        )
    if approve_paid_ops > 8:
        raise ValueError("Paid-operation approval cannot exceed eight")
    if record.state not in {
        "awaiting-generation-approval",
        "awaiting-candidate-review",
    }:
        raise ValueError(
            f"Flow generation is not allowed from state {record.state}"
        )

    flow_plan_path = output_dir / _FLOW_PLAN_FILENAME
    shots = [
        FlowShotSpec.model_validate(item)
        for item in json.loads(flow_plan_path.read_text(encoding="utf-8"))
    ]
    remaining_approval = approve_paid_ops - record.consumed_paid_operations
    if remaining_approval < 0:
        raise ValueError(
            "Paid-operation approval cannot be below already consumed operations"
        )

    if record.state == "awaiting-generation-approval":
        record = store.transition(
            "generating",
            detail=f"Approved up to {approve_paid_ops} paid operations.",
            updates={
                "approved_paid_operations": approve_paid_ops,
                "error": None,
            },
        )
    else:
        record = store.transition(
            "generating",
            detail=f"Approved up to {approve_paid_ops} paid operations.",
            updates={
                "approved_paid_operations": approve_paid_ops,
                "error": None,
            },
        )

    if adapter is None:
        repository = Path(record.flow_repository or _DEFAULT_FLOW_REPOSITORY)
        adapter = FlowCliAdapter(
            repository=repository,
            profile=record.flow_profile,
        )
    project_id = record.flow_project_id
    if project_id is None:
        try:
            project = adapter.create_project(
                title=f"Cutline {Path(record.source_path).stem} production V4"
            )
            project_id = str(project["project_id"])
            instructions_path = _ensure_flow_instructions(output_dir)
            adapter.apply_instructions(
                project_id=project_id,
                instructions_file=instructions_path,
            )
        except Exception:
            store.transition(
                "awaiting-generation-approval",
                detail=(
                    "Flow setup failed before any paid operation. "
                    "Generation approval can be retried safely."
                ),
            )
            raise
        current = store.load()
        current = current.model_copy(
            update={
                "flow_project_id": project_id,
                "updated_at": datetime.now(UTC),
            }
        )
        record = store.save(
            ProductionJobRecord.model_validate(
                current.model_dump(mode="json")
            )
        )

    if candidate_preparer is None:
        from app.editor.flow_candidate import prepare_flow_candidate

        candidate_preparer = prepare_flow_candidate

    raw_dir = output_dir / "flow-candidates" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    submitted_count = 0
    recovered_count = 0
    for shot in shots:
        if shot.status in {
            "accepted",
            "blocked",
            "exhausted",
        }:
            continue
        known_attempt = next(
            (
                attempt
                for attempt in reversed(shot.attempts)
                if attempt.media_id is not None
            ),
            None,
        )
        if (
            known_attempt is not None
            and shot.status != "rejected"
            and _candidate_review_is_ready(known_attempt)
        ):
            shot.status = "awaiting-review"
            _write_flow_shots(flow_plan_path, shots)
            continue
        if known_attempt is not None and shot.status != "rejected":
            try:
                reconciled = adapter.reconcile_media(
                    project_id=project_id,
                    media_id=known_attempt.media_id,
                )
            except Exception:
                _return_generation_to_review(
                    store,
                    detail=(
                        "Flow catalog reconciliation failed before any "
                        "duplicate submission."
                    ),
                )
                raise
            known_attempt.reconciliation_state = (
                "catalog-confirmed" if reconciled else "missing"
            )
            if reconciled is None:
                _write_flow_shots(flow_plan_path, shots)
                _return_generation_to_review(
                    store,
                    detail=(
                        "The known Flow media ID is not currently available "
                        "in the catalog; retry reconciliation later."
                    ),
                )
                raise RuntimeError(
                    "A Flow media ID is known but its catalog entry is "
                    "unavailable; refusing to submit a duplicate operation"
                )
            local_path = reconciled.get("local_path")
            if local_path:
                candidate_path = Path(str(local_path)).expanduser().resolve()
                if not candidate_path.is_file():
                    shot.status = "recovery-needed"
                    _write_flow_shots(flow_plan_path, shots)
                    store.transition(
                        "awaiting-candidate-review",
                        detail=(
                            "Flow catalog reconciliation found the media ID, "
                            "but its local candidate file is unavailable."
                        ),
                    )
                    raise RuntimeError(
                        "Flow catalog candidate file is unavailable"
                    )
                known_attempt.untouched_path = str(candidate_path)
                known_attempt.checksum_sha256 = _sha256(candidate_path)
            else:
                shot.status = "recovery-needed"
                _write_flow_shots(flow_plan_path, shots)
                store.transition(
                    "awaiting-candidate-review",
                    detail=(
                        "Flow catalog reconciliation found the media ID "
                        "without a local candidate; manual recovery is "
                        "required before retry."
                    ),
                )
                raise RuntimeError(
                    "Flow catalog entry has no local candidate file"
                )
            shot.status = "recovery-needed"
            _write_flow_shots(flow_plan_path, shots)
            try:
                candidate_preparer(
                    output_dir=output_dir,
                    shot=shot,
                    attempt=known_attempt,
                    candidate_path=candidate_path,
                )
            except Exception:
                shot.status = "recovery-needed"
                _write_flow_shots(flow_plan_path, shots)
                store.transition(
                    "awaiting-candidate-review",
                    detail=(
                        "The paid Flow result was preserved, but candidate "
                        "review preparation failed."
                    ),
                )
                raise
            shot.status = "awaiting-review"
            _write_flow_shots(flow_plan_path, shots)
            recovered_count += 1
            continue

        if shot.status == "awaiting-review":
            continue
        if len(shot.attempts) >= 2:
            shot.status = "exhausted"
            continue

        reconcile_shot = getattr(adapter, "reconcile_shot", None)
        catalog_match = None
        if callable(reconcile_shot) and not shot.attempts:
            try:
                catalog_match = reconcile_shot(
                    project_id=project_id,
                    prompt=shot.prompt,
                )
            except Exception:
                _return_generation_to_review(
                    store,
                    detail=(
                        "Flow prompt reconciliation failed before any new "
                        "paid submission."
                    ),
                )
                raise
        if catalog_match is not None:
            local_path = Path(str(catalog_match["local_path"])).resolve()
            if not local_path.is_file():
                _return_generation_to_review(
                    store,
                    detail=(
                        "A reconciled Flow catalog result has no available "
                        "local candidate file."
                    ),
                )
                raise RuntimeError(
                    "Flow catalog matched a prior paid operation but its "
                    "local candidate is unavailable; refusing a duplicate"
                )
            recovered = FlowGenerationAttempt(
                attempt=len(shot.attempts) + 1,
                command=[
                    "reconciled-from-flow-catalog",
                    str(catalog_match["media_id"]),
                ],
                project_id=project_id,
                media_id=str(catalog_match["media_id"]),
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                result_json=catalog_match,
                untouched_path=str(local_path),
                checksum_sha256=_sha256(local_path),
                reconciliation_state="catalog-confirmed",
            )
            shot.attempts.append(recovered)
            shot.status = "recovery-needed"
            current = store.load()
            persisted_attempt_count = sum(
                len(item.attempts) for item in shots
            ) - 1
            operation_was_already_counted = (
                current.consumed_paid_operations > persisted_attempt_count
            )
            if not operation_was_already_counted:
                if current.consumed_paid_operations >= approve_paid_ops:
                    _return_generation_to_review(
                        store,
                        detail=(
                            "The Flow catalog contains an untracked result "
                            "outside the approved paid-operation count."
                        ),
                    )
                    raise RuntimeError(
                        "Flow catalog contains an untracked paid operation "
                        "outside the approved operation count"
                    )
                current = current.model_copy(
                    update={
                        "consumed_paid_operations": (
                            current.consumed_paid_operations + 1
                        ),
                        "updated_at": datetime.now(UTC),
                    }
                )
            store.save(
                ProductionJobRecord.model_validate(
                    current.model_dump(mode="json")
                )
            )
            _write_flow_shots(flow_plan_path, shots)
            try:
                candidate_preparer(
                    output_dir=output_dir,
                    shot=shot,
                    attempt=recovered,
                    candidate_path=local_path,
                )
            except Exception:
                shot.status = "recovery-needed"
                _write_flow_shots(flow_plan_path, shots)
                store.transition(
                    "awaiting-candidate-review",
                    detail=(
                        "The reconciled paid Flow result was preserved, but "
                        "candidate review preparation failed."
                    ),
                )
                raise
            shot.status = "awaiting-review"
            _write_flow_shots(flow_plan_path, shots)
            recovered_count += 1
            continue

        if submitted_count >= remaining_approval:
            continue

        attempt_number = len(shot.attempts) + 1
        started_at = datetime.now(UTC)
        try:
            command, result = adapter.generate(
                project_id=project_id,
                shot=shot,
                output_dir=raw_dir,
            )
        except FlowGenerationError as error:
            payload = error.payload or {}
            media_id = payload.get("media_id")
            if media_id:
                failed_attempt = FlowGenerationAttempt(
                    attempt=attempt_number,
                    command=error.command,
                    project_id=project_id,
                    media_id=str(media_id),
                    started_at=started_at,
                    completed_at=datetime.now(UTC),
                    result_json=payload,
                    reconciliation_state="pending",
                )
                shot.attempts.append(failed_attempt)
                shot.status = "generating"
                submitted_count += 1
                current = store.load()
                current = current.model_copy(
                    update={
                        "consumed_paid_operations": (
                            current.consumed_paid_operations + 1
                        ),
                        "updated_at": datetime.now(UTC),
                    }
                )
                store.save(
                    ProductionJobRecord.model_validate(
                        current.model_dump(mode="json")
                    )
                )
                _write_flow_shots(flow_plan_path, shots)
            store.transition(
                "awaiting-candidate-review",
                detail=(
                    "Flow returned an incomplete generation result. "
                    "Catalog reconciliation is required before any retry."
                ),
            )
            raise
        except Exception:
            _return_generation_to_review(
                store,
                detail=(
                    "Flow generation failed without a confirmed paid media "
                    "result; the operation can be retried safely."
                ),
            )
            raise
        local_path = Path(str(result["local_path"])).expanduser().resolve()
        if not local_path.is_file():
            failed_attempt = FlowGenerationAttempt(
                attempt=attempt_number,
                command=command,
                project_id=project_id,
                media_id=str(result["media_id"]),
                started_at=started_at,
                completed_at=datetime.now(UTC),
                result_json=result,
                untouched_path=str(local_path),
                reconciliation_state="pending",
            )
            shot.attempts.append(failed_attempt)
            shot.status = "generating"
            submitted_count += 1
            current = store.load()
            current = current.model_copy(
                update={
                    "consumed_paid_operations": (
                        current.consumed_paid_operations + 1
                    ),
                    "updated_at": datetime.now(UTC),
                }
            )
            store.save(
                ProductionJobRecord.model_validate(
                    current.model_dump(mode="json")
                )
            )
            _write_flow_shots(flow_plan_path, shots)
            store.transition(
                "awaiting-candidate-review",
                detail=(
                    "Flow returned a media ID without a local candidate. "
                    "Catalog reconciliation is required before any retry."
                ),
            )
            raise RuntimeError(
                f"Flow reported a missing candidate file: {local_path}"
            )
        canonical = raw_dir / f"{shot.id}-attempt-{attempt_number}.mp4"
        if local_path != canonical:
            shutil.copy2(local_path, canonical)
        checksum = _sha256(canonical)
        attempt = FlowGenerationAttempt(
            attempt=attempt_number,
            command=command,
            project_id=project_id,
            media_id=str(result["media_id"]),
            started_at=started_at,
            completed_at=datetime.now(UTC),
            result_json=result,
            untouched_path=str(canonical),
            checksum_sha256=checksum,
            reconciliation_state="not-needed",
        )
        shot.attempts.append(attempt)
        shot.status = "recovery-needed"
        submitted_count += 1
        current = store.load()
        current = current.model_copy(
            update={
                "consumed_paid_operations": (
                    current.consumed_paid_operations + 1
                ),
                "updated_at": datetime.now(UTC),
            }
        )
        store.save(
            ProductionJobRecord.model_validate(
                current.model_dump(mode="json")
            )
        )
        _write_flow_shots(flow_plan_path, shots)
        try:
            candidate_preparer(
                output_dir=output_dir,
                shot=shot,
                attempt=attempt,
                candidate_path=canonical,
            )
        except Exception:
            shot.status = "recovery-needed"
            _write_flow_shots(flow_plan_path, shots)
            store.transition(
                "awaiting-candidate-review",
                detail=(
                    "The paid Flow result was preserved, but candidate "
                    "review preparation failed."
                ),
            )
            raise
        shot.status = "awaiting-review"
        _write_flow_shots(flow_plan_path, shots)

    _write_flow_shots(flow_plan_path, shots)
    if submitted_count == 0 and recovered_count == 0:
        store.transition(
            "awaiting-candidate-review",
            detail=(
                "No recoverable Flow result was found and no newly approved "
                "paid operation remains."
            ),
        )
        raise ValueError(
            "No newly approved or recoverable Flow operation remains"
        )
    record = store.transition(
        "awaiting-candidate-review",
        detail=(
            f"{submitted_count} new Flow operation(s) completed and "
            f"{recovered_count} known result(s) recovered; human review "
            "is required."
        ),
    )
    return record.model_dump(mode="json")


def review_flow_candidate(
    *,
    output_dir: Path,
    shot_id: str,
    attempt: int,
    accepted: bool,
    scores: dict[str, int],
    accepted_start_ms: int | None = None,
    accepted_end_ms: int | None = None,
    reviewer: str,
    rejection_reasons: list[str] | None = None,
    speed: float = 1,
    crop: dict[str, float] | None = None,
    color_correction: dict[str, float] | None = None,
    transcoder: Callable[..., object] | None = None,
    selection_preparer: SelectionPreparer | None = None,
) -> dict[str, Any]:
    output_dir = output_dir.expanduser().resolve()
    store = ProductionStore(output_dir)
    record = store.load()
    if record.state != "awaiting-candidate-review":
        raise ValueError(
            "Candidate decisions require awaiting-candidate-review state"
        )
    flow_plan_path = output_dir / _FLOW_PLAN_FILENAME
    shots = [
        FlowShotSpec.model_validate(item)
        for item in json.loads(flow_plan_path.read_text(encoding="utf-8"))
    ]
    shot = next((item for item in shots if item.id == shot_id), None)
    if shot is None:
        raise KeyError(shot_id)
    generation_attempt = next(
        (item for item in shot.attempts if item.attempt == attempt),
        None,
    )
    if generation_attempt is None:
        raise KeyError(f"{shot_id}:attempt-{attempt}")
    candidate_review = (
        generation_attempt.result_json or {}
    ).get("candidate_review")
    if not isinstance(candidate_review, dict):
        raise ValueError("Candidate automated review is missing")
    automated_report_path = candidate_review.get("automated_report_path")
    if not automated_report_path:
        raise ValueError("Candidate automated review path is missing")
    automated_report = json.loads(
        Path(str(automated_report_path)).read_text(encoding="utf-8")
    )
    technical_gates = FlowTechnicalGates.model_validate(
        automated_report["technical_gates"]
    )
    review_contact_sheet_path = automated_report.get("contact_sheet_path")
    selected_crop = CropSpec.model_validate(crop or {})
    if accepted:
        metrics = automated_report.get("metrics")
        candidate_duration_ms = (
            metrics.get("duration_ms")
            if isinstance(metrics, dict)
            else None
        )
        if not isinstance(candidate_duration_ms, (int, float)):
            raise ValueError(
                "Candidate duration is missing from automated review"
            )
        if (
            accepted_end_ms is not None
            and accepted_end_ms > candidate_duration_ms
        ):
            raise ValueError(
                "Accepted window exceeds the candidate duration"
            )
        if accepted_start_ms is None or accepted_end_ms is None:
            raise ValueError("Human acceptance requires a selected window")
        if selection_preparer is None:
            from app.editor.flow_candidate import (
                prepare_flow_candidate_selection,
            )

            selection_preparer = prepare_flow_candidate_selection
        selection_report = selection_preparer(
            output_dir=output_dir,
            shot=shot,
            attempt=generation_attempt,
            proxy_path=Path(str(automated_report["proxy_path"])),
            start_ms=accepted_start_ms,
            end_ms=accepted_end_ms,
            crop=selected_crop.model_dump(mode="json"),
            speed=speed,
        )
        technical_gates = FlowTechnicalGates.model_validate(
            selection_report["technical_gates"]
        )
        review_contact_sheet_path = selection_report.get(
            "contact_sheet_path"
        )
        result_json = dict(generation_attempt.result_json or {})
        persisted_candidate_review = dict(
            result_json.get("candidate_review") or {}
        )
        persisted_candidate_review.update(
            {
                "selection_proxy_path": selection_report.get("proxy_path"),
                "selection_contact_sheet_path": (
                    selection_report.get("contact_sheet_path")
                ),
                "selection_report_path": selection_report.get("report_path"),
                "selection_hard_gate_passed": selection_report.get(
                    "hard_gate_passed"
                ),
            }
        )
        result_json["candidate_review"] = persisted_candidate_review
        generation_attempt.result_json = result_json
        _write_flow_shots(flow_plan_path, shots)
    review = FlowCandidateReview(
        shot_id=shot_id,
        attempt=attempt,
        technical_gates=technical_gates,
        scores=FlowReviewScores.model_validate(scores),
        rejection_reasons=rejection_reasons or [],
        human_accepted=accepted,
        accepted_start_ms=accepted_start_ms,
        accepted_end_ms=accepted_end_ms,
        contact_sheet_path=review_contact_sheet_path,
        reviewed_at=datetime.now(UTC),
        reviewer=reviewer,
    )
    human_review_path = (
        output_dir
        / "flow-candidates"
        / "reviews"
        / f"{shot_id}-attempt-{attempt}-human.json"
    )
    _write_json(human_review_path, review.model_dump(mode="json"))

    if not accepted:
        shot.status = "rejected"
        _write_flow_shots(flow_plan_path, shots)
        return {
            "accepted": False,
            "shot_id": shot_id,
            "attempt": attempt,
            "review_path": str(human_review_path),
            "regeneration_available": len(shot.attempts) < 2,
        }

    if not review.accepted:
        raise ValueError("Candidate did not satisfy the human release gate")
    proxy_path = Path(str(automated_report["proxy_path"]))
    untouched_path = Path(
        generation_attempt.untouched_path
        or str(automated_report["untouched_path"])
    )
    accepted_path = (
        output_dir
        / "flow-candidates"
        / "accepted"
        / f"{shot_id}-attempt-{attempt}.mp4"
    )
    if transcoder is None:
        from app.editor.flow_candidate import transcode_accepted_window

        transcoder = transcode_accepted_window
    transcoder(
        source=proxy_path,
        output=accepted_path,
        start_ms=review.accepted_start_ms,
        end_ms=review.accepted_end_ms,
        speed=speed,
    )
    if not accepted_path.is_file() or accepted_path.stat().st_size == 0:
        raise RuntimeError("Accepted Flow proxy was not created")
    accepted_clip = FlowAcceptedClip(
        shot_id=shot_id,
        attempt=attempt,
        untouched_path=str(untouched_path),
        proxy_path=str(accepted_path),
        trim_start_ms=review.accepted_start_ms,
        trim_end_ms=review.accepted_end_ms,
        crop=selected_crop,
        speed=speed,
        color_correction=color_correction or {},
        provenance="google-flow-veo-illustrative",
        illustrative_label_required=True,
        checksum_sha256=_sha256(accepted_path),
    )
    shot.status = "accepted"
    _write_flow_shots(flow_plan_path, shots)
    existing = [
        clip
        for clip in record.accepted_clips
        if clip.shot_id != shot_id
    ]
    updated = record.model_copy(
        update={
            "accepted_clips": [*existing, accepted_clip],
            "updated_at": datetime.now(UTC),
        }
    )
    store.save(
        ProductionJobRecord.model_validate(updated.model_dump(mode="json"))
    )
    return {
        "accepted": True,
        "shot_id": shot_id,
        "attempt": attempt,
        "accepted_clip": accepted_clip.model_dump(mode="json"),
        "review_path": str(human_review_path),
    }


def assemble_production_edit(*, output_dir: Path) -> dict[str, Any]:
    from app.editor.production_assembly import assemble_production

    return assemble_production(output_dir=output_dir)


def approve_production_edit(
    *,
    output_dir: Path,
    reviewer: str,
) -> dict[str, Any]:
    output_dir = output_dir.expanduser().resolve()
    store = ProductionStore(output_dir)
    record = store.load()
    if record.state != "awaiting-final-approval":
        raise ValueError(
            "Final approval is only allowed after automated review"
        )
    if not record.automated_pass:
        raise ValueError("Final approval requires an automated pass")
    record = store.transition(
        "completed",
        detail=f"Final production approved by {reviewer}.",
        updates={
            "human_approved": True,
            "final_reviewer": reviewer,
        },
    )
    return record.model_dump(mode="json")


def _ensure_flow_instructions(output_dir: Path) -> Path:
    path = output_dir / _FLOW_INSTRUCTIONS_FILENAME
    if path.is_file():
        return path
    _write_json(
        path,
        {
            "card": [
                {
                    "title": "Cutline production motion grammar",
                    "text": (
                        "Create portrait 9:16, single-shot, restrained "
                        "cinematic motion plates with physically plausible "
                        "movement, well-exposed graphite materials, controlled "
                        "cyan or teal with restrained amber or risk-red "
                        "accents, clean lighting and a center-safe subject. "
                        "Preserve shape separation without crushed blacks. "
                        "Never create readable text, letters, numbers, logos, "
                        "watermarks, software UI, code, charts, documents, "
                        "evidence or captions."
                    ),
                    "ref": [],
                    "enabled": True,
                }
            ]
        },
    )
    return path


def _write_flow_shots(path: Path, shots: list[FlowShotSpec]) -> None:
    _write_json(
        path,
        [shot.model_dump(mode="json") for shot in shots],
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
