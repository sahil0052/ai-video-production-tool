from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
import subprocess
from typing import Any

from app.production_models import FlowShotSpec


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


class FlowGenerationError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        command: list[str],
        payload: dict[str, Any] | None,
    ) -> None:
        super().__init__(message)
        self.command = command
        self.payload = payload


def parse_json_document(output: str) -> dict[str, Any]:
    stripped = output.strip()
    if not stripped:
        raise ValueError("Flow CLI did not return JSON")
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Flow CLI returned invalid JSON") from None
        try:
            payload = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError as error:
            raise ValueError("Flow CLI returned invalid JSON") from error
    if not isinstance(payload, dict):
        raise ValueError("Flow CLI JSON result must be an object")
    return payload


def parse_json_lines(output: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError("Flow catalog JSONL rows must be objects")
        rows.append(payload)
    return rows


def build_flow_video_command(
    *,
    repository: Path,
    profile: str,
    project_id: str,
    shot: FlowShotSpec,
    output_dir: Path,
) -> list[str]:
    del repository
    command = ["uv", "run", "gflow", "video", shot.mode]
    if shot.mode == "i2v":
        command.extend(["--initial-frame", shot.input_plates[0]])
        if len(shot.input_plates) == 2:
            command.extend(["--end-frame", shot.input_plates[1]])
        command.append(shot.prompt)
    elif shot.mode == "r2v":
        command.append(shot.prompt)
        for plate in shot.input_plates:
            command.extend(["--ref", plate])
    else:
        command.append(shot.prompt)
    command.extend(
        [
            "--aspect",
            "9:16",
            "--model",
            shot.model,
            "--count",
            "1",
            "--profile",
            profile,
            "--project",
            project_id,
            "--out-dir",
            str(output_dir),
            "--json",
        ]
    )
    return command


class FlowCliAdapter:
    def __init__(
        self,
        *,
        repository: Path,
        profile: str,
        runner: CommandRunner = subprocess.run,
    ) -> None:
        self.repository = repository.resolve()
        self.profile = profile
        self.runner = runner

    def _run(
        self,
        command: list[str],
        *,
        timeout_seconds: int = 1800,
    ) -> subprocess.CompletedProcess[str]:
        completed = self.runner(
            command,
            cwd=self.repository,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
        return completed

    def create_project(self, *, title: str) -> dict[str, Any]:
        command = [
            "uv",
            "run",
            "gflow",
            "project",
            "create",
            "--name",
            title,
            "--profile",
            self.profile,
            "--json",
        ]
        completed = self._run(command, timeout_seconds=300)
        if completed.returncode != 0:
            detail = (
                completed.stderr.strip()
                or completed.stdout.strip()
                or f"exit code {completed.returncode}"
            )
            raise RuntimeError(f"Flow project creation failed: {detail}")
        payload = parse_json_document(completed.stdout)
        if payload.get("status") != "ok":
            detail = completed.stderr.strip() or str(payload)
            raise RuntimeError(f"Flow project creation failed: {detail}")
        return payload

    def apply_instructions(
        self,
        *,
        project_id: str,
        instructions_file: Path,
    ) -> None:
        command = [
            "uv",
            "run",
            "gflow",
            "instructions",
            "apply",
            str(instructions_file),
            "--project",
            project_id,
            "--profile",
            self.profile,
        ]
        completed = self._run(command, timeout_seconds=300)
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(f"Flow instruction sync failed: {detail}")

    def generate(
        self,
        *,
        project_id: str,
        shot: FlowShotSpec,
        output_dir: Path,
    ) -> tuple[list[str], dict[str, Any]]:
        output_dir.mkdir(parents=True, exist_ok=True)
        command = build_flow_video_command(
            repository=self.repository,
            profile=self.profile,
            project_id=project_id,
            shot=shot,
            output_dir=output_dir,
        )
        completed = self._run(command)
        try:
            payload = parse_json_document(completed.stdout)
        except ValueError as error:
            raise FlowGenerationError(
                "Flow generation returned no usable JSON result",
                command=command,
                payload=None,
            ) from error
        if (
            completed.returncode != 0
            or payload.get("status") != "ok"
            or not payload.get("media_id")
        ):
            detail = completed.stderr.strip() or str(payload)
            raise FlowGenerationError(
                f"Flow generation failed: {detail}",
                command=command,
                payload=payload,
            )
        return command, payload

    def reconcile_media(
        self,
        *,
        project_id: str,
        media_id: str,
    ) -> dict[str, Any] | None:
        command = [
            "uv",
            "run",
            "gflow",
            "data",
            "list",
            "videos",
            "--profile",
            self.profile,
            "--limit",
            "1000",
            "--json",
        ]
        completed = self._run(command, timeout_seconds=120)
        if completed.returncode != 0:
            return None
        try:
            rows = parse_json_lines(completed.stdout)
        except (ValueError, json.JSONDecodeError):
            payload = parse_json_document(completed.stdout)
            rows = [payload]
        return next(
            (
                row
                for row in rows
                if row.get("media_id") == media_id
                and row.get("project_id") == project_id
            ),
            None,
        )

    def reconcile_shot(
        self,
        *,
        project_id: str,
        prompt: str,
    ) -> dict[str, Any] | None:
        command = [
            "uv",
            "run",
            "gflow",
            "data",
            "list",
            "videos",
            "--profile",
            self.profile,
            "--limit",
            "1000",
            "--json",
        ]
        completed = self._run(command, timeout_seconds=120)
        if completed.returncode != 0:
            return None
        rows = parse_json_lines(completed.stdout)
        return next(
            (
                row
                for row in rows
                if row.get("project_id") == project_id
                and row.get("prompt") == prompt
                and row.get("media_id")
            ),
            None,
        )
