from datetime import datetime, timezone
import json
import os
from pathlib import Path
from threading import RLock
from uuid import UUID, uuid4

from app.models import JobRecord, JobState, PipelineResult


class JobStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def create(self, original_filename: str) -> JobRecord:
        now = datetime.now(timezone.utc)
        record = JobRecord(
            id=str(uuid4()),
            original_filename=Path(original_filename).name,
            state="queued",
            progress=0,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self.job_dir(record.id).mkdir(parents=False, exist_ok=False)
            self._write(record)
        return record

    def get(self, job_id: str) -> JobRecord:
        record_path = self._record_path(job_id)
        with self._lock:
            if not record_path.is_file():
                raise KeyError(job_id)
            return JobRecord.model_validate_json(
                record_path.read_text(encoding="utf-8")
            )

    def update(
        self,
        job_id: str,
        *,
        state: JobState,
        progress: int,
        error: str | None = None,
        result: PipelineResult | None = None,
    ) -> JobRecord:
        with self._lock:
            current = self.get(job_id)
            updated = current.model_copy(
                update={
                    "state": state,
                    "progress": min(100, max(0, progress)),
                    "error": error,
                    "result": result if result is not None else current.result,
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            self._write(updated)
            return updated

    def job_dir(self, job_id: str) -> Path:
        normalized = _validate_job_id(job_id)
        return self.root / normalized

    def source_path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "source.mp4"

    def output_path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "edited.mp4"

    def _record_path(self, job_id: str) -> Path:
        return self.job_dir(job_id) / "job.json"

    def _write(self, record: JobRecord) -> None:
        destination = self._record_path(record.id)
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(record.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary, destination)


def _validate_job_id(job_id: str) -> str:
    try:
        parsed = UUID(job_id)
    except (ValueError, AttributeError) as error:
        raise KeyError(job_id) from error
    normalized = str(parsed)
    if normalized != job_id:
        raise KeyError(job_id)
    return normalized
