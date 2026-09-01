import json
from pathlib import Path

import pytest

from app.editor.flow_adapter import (
    FlowCliAdapter,
    build_flow_video_command,
    parse_json_document,
    parse_json_lines,
)
from app.production_models import FlowShotSpec


def _shot(tmp_path: Path) -> FlowShotSpec:
    start = tmp_path / "start.png"
    end = tmp_path / "end.png"
    start.write_bytes(b"start")
    end.write_bytes(b"end")
    return FlowShotSpec(
        id="wrong-rule",
        start_ms=10700,
        end_ms=14160,
        editorial_role="wrong-rule-branch",
        prompt=(
            "A clean physical branching mechanism takes the wrong path. "
            "One continuous shot. No text, no UI, no code, no charts, "
            "no numbers, no documents."
        ),
        mode="i2v",
        model="veo-lite",
        input_plates=[str(start), str(end)],
        requested_content=["physical-metaphor"],
        constraints=["No readable text", "One continuous shot"],
    )


def test_flow_video_command_is_sequential_portrait_json_and_has_no_duration(
    tmp_path: Path,
) -> None:
    command = build_flow_video_command(
        repository=Path("C:/gflow"),
        profile="sahilsharmabybit2",
        project_id="project-123",
        shot=_shot(tmp_path),
        output_dir=tmp_path / "raw",
    )

    assert command[:4] == ["uv", "run", "gflow", "video"]
    assert command[4] == "i2v"
    assert command.count("--count") == 1
    assert command[command.index("--count") + 1] == "1"
    assert command[command.index("--aspect") + 1] == "9:16"
    assert command[command.index("--model") + 1] == "veo-lite"
    assert command[command.index("--profile") + 1] == "sahilsharmabybit2"
    assert command[command.index("--project") + 1] == "project-123"
    assert "--json" in command
    assert "--duration" not in command


def test_flow_json_parsers_accept_stable_document_and_catalog_jsonl() -> None:
    document = parse_json_document(
        json.dumps(
            {
                "status": "ok",
                "media_id": "media-123",
                "local_path": "C:/out/clip.mp4",
            }
        )
    )
    assert document["media_id"] == "media-123"

    rows = parse_json_lines(
        "\n".join(
            [
                json.dumps({"media_id": "one", "project_id": "project"}),
                json.dumps({"media_id": "two", "project_id": "project"}),
            ]
        )
    )
    assert [row["media_id"] for row in rows] == ["one", "two"]

    with pytest.raises(ValueError, match="JSON"):
        parse_json_document("not json")


def test_adapter_reconciles_known_media_before_any_resubmission(
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    def runner(command, **_kwargs):
        calls.append(command)
        return type(
            "Completed",
            (),
            {
                "returncode": 0,
                "stdout": json.dumps(
                    {
                        "media_id": "known-media",
                        "project_id": "project-123",
                        "local_path": str(tmp_path / "known.mp4"),
                    }
                ),
                "stderr": "",
            },
        )()

    adapter = FlowCliAdapter(
        repository=tmp_path,
        profile="sahilsharmabybit2",
        runner=runner,
    )
    found = adapter.reconcile_media(
        project_id="project-123",
        media_id="known-media",
    )

    assert found is not None
    assert found["media_id"] == "known-media"
    assert calls[0][3:7] == ["data", "list", "videos", "--profile"]


def test_project_creation_reports_plain_text_cli_failures(tmp_path: Path) -> None:
    def runner(_command, **_kwargs):
        return type(
            "Completed",
            (),
            {
                "returncode": 2,
                "stdout": (
                    "No session for profile 'sahilsharmabybit2'. "
                    "Run gflow auth login first."
                ),
                "stderr": "",
            },
        )()

    adapter = FlowCliAdapter(
        repository=tmp_path,
        profile="sahilsharmabybit2",
        runner=runner,
    )

    with pytest.raises(RuntimeError, match="No session for profile"):
        adapter.create_project(title="Cutline 0810")
