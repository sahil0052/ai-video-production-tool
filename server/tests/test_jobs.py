from pathlib import Path

import pytest

from app.jobs import JobStore


def test_job_store_persists_and_updates_records(tmp_path: Path) -> None:
    store = JobStore(tmp_path)

    created = store.create("0806.mp4")
    updated = store.update(
        created.id,
        state="rendering",
        progress=64,
    )

    loaded = store.get(created.id)
    assert loaded.id == created.id
    assert loaded.original_filename == "0806.mp4"
    assert loaded.state == "rendering"
    assert loaded.progress == 64
    assert updated.updated_at >= created.created_at


def test_job_store_rejects_path_traversal_ids(tmp_path: Path) -> None:
    store = JobStore(tmp_path)

    with pytest.raises(KeyError):
        store.get("../../outside")

