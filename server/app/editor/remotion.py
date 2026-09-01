from collections.abc import Callable
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess

from app.models import EditPlanV1
from app.production_models import EditPlanV2


@dataclass(frozen=True)
class PreparedRendererInputs:
    source_path: Path
    plan_path: Path


@dataclass(frozen=True)
class PreparedProductionRendererInputs:
    plan_path: Path


SourcePreparer = Callable[[Path, Path], None]


def build_renderer_source_proxy_command(
    *,
    executable: Path,
    source: Path,
    output: Path,
    fps: int,
) -> list[str]:
    return [
        str(executable),
        "-y",
        "-i",
        str(source),
        "-map",
        "0:v:0",
        "-an",
        "-r",
        str(fps),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "14",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]


def prepare_renderer_source_proxy(
    *,
    executable: Path,
    source: Path,
    output: Path,
    fps: int,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        build_renderer_source_proxy_command(
            executable=executable,
            source=source,
            output=output,
            fps=fps,
        ),
        capture_output=True,
        text=True,
        errors="replace",
        timeout=1800,
        check=False,
        shell=False,
    )
    if completed.returncode != 0:
        error = completed.stderr[-6000:].strip()
        raise RuntimeError(f"Renderer source proxy failed: {error}")
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("Renderer source proxy was not created")


def prepare_renderer_inputs(
    *,
    source: Path,
    plan: EditPlanV1,
    public_dir: Path,
    source_preparer: SourcePreparer | None = None,
) -> PreparedRendererInputs:
    public_dir.mkdir(parents=True, exist_ok=True)
    source_path = public_dir / "source.mp4"
    plan_path = public_dir / "edit-plan.json"
    if source_preparer is None:
        shutil.copy2(source, source_path)
    else:
        source_preparer(source, source_path)
    payload = plan.model_dump(mode="json")
    payload["source_url"] = source_path.name
    assets_dir = public_dir / "assets"
    for asset in payload["assets"]:
        asset_source = Path(asset["path"])
        if not asset_source.is_file():
            continue
        assets_dir.mkdir(parents=True, exist_ok=True)
        safe_id = "".join(
            character
            for character in str(asset["id"])
            if character.isalnum() or character in {"-", "_"}
        )
        destination = assets_dir / f"{safe_id}{asset_source.suffix.lower()}"
        shutil.copy2(asset_source, destination)
        asset["path"] = destination.relative_to(public_dir).as_posix()
    plan_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return PreparedRendererInputs(
        source_path=source_path,
        plan_path=plan_path,
    )


def prepare_production_renderer_inputs(
    *,
    plan: EditPlanV2,
    public_dir: Path,
) -> PreparedProductionRendererInputs:
    public_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = public_dir / "assets"
    payload = plan.model_dump(mode="json")
    for asset in payload["assets"]:
        source = Path(asset["path"]).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        assets_dir.mkdir(parents=True, exist_ok=True)
        safe_id = "".join(
            character
            for character in str(asset["id"])
            if character.isalnum() or character in {"-", "_"}
        )
        destination = assets_dir / f"{safe_id}{source.suffix.lower()}"
        if (
            not destination.is_file()
            or destination.stat().st_size != source.stat().st_size
        ):
            shutil.copy2(source, destination)
        asset["path"] = destination.relative_to(public_dir).as_posix()
    plan_path = public_dir / "edit-plan.json"
    plan_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return PreparedProductionRendererInputs(plan_path=plan_path)


def build_remotion_render_command(
    *,
    node_executable: Path,
    render_script: Path,
    plan_path: Path,
    public_dir: Path,
    output: Path,
) -> list[str]:
    return [
        str(node_executable),
        str(render_script),
        "--plan",
        str(plan_path),
        "--public-dir",
        str(public_dir),
        "--output",
        str(output),
    ]


def run_remotion_command(
    command: list[str],
    *,
    cwd: Path,
    timeout_seconds: int = 7200,
) -> None:
    environment = os.environ.copy()
    configured_temp = environment.get("CUTLINE_REMOTION_TEMP_DIR")
    if configured_temp:
        temp_dir = Path(configured_temp).expanduser().resolve()
        temp_dir.mkdir(parents=True, exist_ok=True)
        environment["TEMP"] = str(temp_dir)
        environment["TMP"] = str(temp_dir)
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout_seconds,
            check=False,
            shell=False,
            env=environment,
        )
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        stderr = error.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        diagnostics = "\n".join(
            value for value in (stdout[-3000:], stderr[-3000:]) if value
        ).strip()
        raise RuntimeError(
            "Remotion render timed out after "
            f"{timeout_seconds} seconds. Last diagnostics: {diagnostics}"
        ) from error
    if completed.returncode != 0:
        error = completed.stderr[-6000:].strip()
        raise RuntimeError(f"Remotion render failed: {error}")
