import json
from pathlib import Path
import subprocess

import pytest

from app.editor import pipeline as pipeline_module
from app.editor import remotion as remotion_module
from app.editor.planning import build_edit_plan
from app.editor.remotion import (
    PreparedRendererInputs,
    build_remotion_render_command,
    prepare_production_renderer_inputs,
    prepare_renderer_inputs,
)
from app.models import (
    AssetRef,
    AudioPlan,
    OutputSpec,
    TranscriptSegment,
    TranscriptWord,
    VideoMetadata,
)
from app.production_models import EditPlanV2, VisualLayerSpec


def make_plan():
    words = [
        TranscriptWord(
            start=0,
            end=0.4,
            text="AI",
            confidence=0.99,
        ),
        TranscriptWord(
            start=0.4,
            end=0.8,
            text="works",
            confidence=0.99,
        ),
    ]
    return build_edit_plan(
        source_filename="source.mp4",
        metadata=VideoMetadata(
            width=720,
            height=1280,
            fps=30,
            frame_count=30,
            duration_seconds=1,
        ),
        transcript=[
            TranscriptSegment(
                start=0,
                end=0.8,
                text="AI works",
                words=words,
            )
        ],
    )


def test_prepare_renderer_inputs_copies_source_and_writes_plan(
    tmp_path: Path,
) -> None:
    source = tmp_path / "raw source.mp4"
    source.write_bytes(b"video")
    public_dir = tmp_path / "public"

    prepared = prepare_renderer_inputs(
        source=source,
        plan=make_plan(),
        public_dir=public_dir,
    )

    assert prepared.source_path.read_bytes() == b"video"
    payload = json.loads(prepared.plan_path.read_text(encoding="utf-8"))
    assert payload["version"] == "1.0"
    assert payload["source_filename"] == "source.mp4"
    assert payload["source_url"] == "source.mp4"


def test_prepare_renderer_inputs_copies_scheduled_assets(tmp_path: Path) -> None:
    source = tmp_path / "raw.mp4"
    source.write_bytes(b"video")
    image = tmp_path / "ai chip.png"
    image.write_bytes(b"image")
    plan = make_plan().model_copy(
        update={
            "assets": [
                AssetRef(
                    id="asset-1",
                    kind="image",
                    path=str(image),
                    keywords=["ai", "chip"],
                    provenance="local-library",
                    license="Internal",
                    start_ms=200,
                    end_ms=800,
                )
            ]
        }
    )

    prepared = prepare_renderer_inputs(
        source=source,
        plan=plan,
        public_dir=tmp_path / "public",
    )

    payload = json.loads(prepared.plan_path.read_text(encoding="utf-8"))
    copied = prepared.plan_path.parent / payload["assets"][0]["path"]
    assert copied.read_bytes() == b"image"
    assert payload["assets"][0]["provenance"] == "local-library"


def test_prepare_renderer_inputs_preserves_remote_asset_provenance(
    tmp_path: Path,
) -> None:
    source = tmp_path / "raw.mp4"
    source.write_bytes(b"video")
    image = tmp_path / "remote.jpg"
    image.write_bytes(b"image")
    plan = make_plan().model_copy(
        update={
            "assets": [
                AssetRef(
                    id="internet-asset-1",
                    kind="image",
                    path=str(image),
                    keywords=["forex"],
                    provenance="internet:wikimedia-commons",
                    license="CC BY-SA 4.0",
                    provider="wikimedia-commons",
                    remote_id="10",
                    creator="Creator",
                    source_url=(
                        "https://commons.wikimedia.org/wiki/File:Forex.jpg"
                    ),
                    license_url=(
                        "https://creativecommons.org/licenses/by-sa/4.0/"
                    ),
                    search_query="forex market",
                    start_ms=200,
                    end_ms=800,
                )
            ]
        }
    )

    prepared = prepare_renderer_inputs(
        source=source,
        plan=plan,
        public_dir=tmp_path / "public",
    )
    payload = json.loads(prepared.plan_path.read_text(encoding="utf-8"))

    assert payload["assets"][0]["provider"] == "wikimedia-commons"
    assert payload["assets"][0]["creator"] == "Creator"
    assert payload["assets"][0]["search_query"] == "forex market"


def test_build_remotion_render_command_is_argument_safe(tmp_path: Path) -> None:
    command = build_remotion_render_command(
        node_executable=Path("node"),
        render_script=tmp_path / "render.mjs",
        plan_path=tmp_path / "edit plan.json",
        public_dir=tmp_path / "public assets",
        output=tmp_path / "rendered video.mp4",
    )

    assert command[0] == "node"
    assert str(tmp_path / "edit plan.json") in command
    assert str(tmp_path / "public assets") in command
    assert str(tmp_path / "rendered video.mp4") in command
    assert "--plan" in command
    assert "--public-dir" in command
    assert "--output" in command


def test_build_renderer_source_proxy_command_targets_browser_h264(
    tmp_path: Path,
) -> None:
    assert hasattr(remotion_module, "build_renderer_source_proxy_command")

    command = remotion_module.build_renderer_source_proxy_command(
        executable=Path("ffmpeg"),
        source=tmp_path / "raw source.mp4",
        output=tmp_path / "source.mp4",
        fps=30,
    )

    assert command[0] == "ffmpeg"
    assert str(tmp_path / "raw source.mp4") in command
    assert str(tmp_path / "source.mp4") in command
    assert command[command.index("-c:v") + 1] == "libx264"
    assert command[command.index("-pix_fmt") + 1] == "yuv420p"
    assert command[command.index("-r") + 1] == "30"
    assert command[command.index("-crf") + 1] == "14"
    assert "-an" in command
    assert "+faststart" in command


def test_prepare_renderer_inputs_accepts_a_source_preparer(
    tmp_path: Path,
) -> None:
    source = tmp_path / "raw source.mp4"
    source.write_bytes(b"hevc")
    calls: list[tuple[Path, Path]] = []

    def source_preparer(input_path: Path, output_path: Path) -> None:
        calls.append((input_path, output_path))
        output_path.write_bytes(b"h264")

    prepared = prepare_renderer_inputs(
        source=source,
        plan=make_plan(),
        public_dir=tmp_path / "public",
        source_preparer=source_preparer,
    )

    assert calls == [(source, prepared.source_path)]
    assert prepared.source_path.read_bytes() == b"h264"


def test_prepare_production_renderer_inputs_stages_explicit_layer_assets(
    tmp_path: Path,
) -> None:
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"clip")
    plan = EditPlanV2(
        source_filename="0806.mp4",
        source_metadata=VideoMetadata(
            width=1080,
            height=1920,
            fps=30,
            frame_count=30,
            duration_seconds=1,
        ),
        output=OutputSpec(),
        duration_ms=1000,
        assets=[
            AssetRef(
                id="clip",
                kind="video",
                path=str(clip),
                provenance="user-provided",
            )
        ],
        visual_layers=[
            VisualLayerSpec(
                id="layer",
                shot_id="shot",
                start_ms=0,
                end_ms=1000,
                source_role="presenter",
                asset_id="clip",
                source_start_ms=0,
                source_end_ms=1000,
            )
        ],
        audio=AudioPlan(),
    )

    prepared = prepare_production_renderer_inputs(
        plan=plan,
        public_dir=tmp_path / "public-v2",
    )

    payload = json.loads(prepared.plan_path.read_text(encoding="utf-8"))
    assert payload["version"] == "2.0"
    assert payload["assets"][0]["path"] == "assets/clip.mp4"
    assert (prepared.plan_path.parent / "assets" / "clip.mp4").is_file()


def test_render_edit_plan_uses_browser_source_proxy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "raw.mp4"
    source.write_bytes(b"hevc")
    captured: dict[str, object] = {}

    def fake_prepare_renderer_inputs(**kwargs) -> PreparedRendererInputs:
        captured.update(kwargs)
        public_dir = kwargs["public_dir"]
        public_dir.mkdir(parents=True, exist_ok=True)
        source_path = public_dir / "source.mp4"
        source_preparer = kwargs.get("source_preparer")
        if source_preparer is not None:
            source_preparer(source, source_path)
        plan_path = public_dir / "edit-plan.json"
        plan_path.write_text("{}", encoding="utf-8")
        return PreparedRendererInputs(
            source_path=source_path,
            plan_path=plan_path,
        )

    def fake_proxy(**kwargs) -> None:
        captured["proxy"] = kwargs
        kwargs["output"].write_bytes(b"h264")

    monkeypatch.setattr(
        pipeline_module,
        "prepare_renderer_inputs",
        fake_prepare_renderer_inputs,
    )
    monkeypatch.setattr(
        pipeline_module,
        "prepare_renderer_source_proxy",
        fake_proxy,
        raising=False,
    )
    monkeypatch.setattr(
        pipeline_module,
        "build_remotion_render_command",
        lambda **_kwargs: ["node", "render.mjs"],
    )
    monkeypatch.setattr(
        pipeline_module,
        "run_remotion_command",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        pipeline_module.shutil,
        "which",
        lambda _name: "node",
    )

    pipeline_module.render_edit_plan(
        source=source,
        output=tmp_path / "rendered.mp4",
        work_dir=tmp_path,
        plan=make_plan(),
    )

    assert callable(captured.get("source_preparer"))
    proxy = captured.get("proxy")
    assert isinstance(proxy, dict)
    assert proxy["source"] == source
    assert proxy["fps"] == 30


def test_run_remotion_command_uses_production_timeout_and_temp_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    render_temp = tmp_path / "remotion temp"
    monkeypatch.setenv("CUTLINE_REMOTION_TEMP_DIR", str(render_temp))

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured.update(kwargs)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(remotion_module.subprocess, "run", fake_run)

    remotion_module.run_remotion_command(
        ["node", "render.mjs"],
        cwd=tmp_path,
    )

    assert captured["timeout"] == 7200
    environment = captured["env"]
    assert environment["TEMP"] == str(render_temp)
    assert environment["TMP"] == str(render_temp)
    assert render_temp.is_dir()


def test_run_remotion_command_reports_timeout_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(command, **_kwargs):
        raise subprocess.TimeoutExpired(
            command,
            timeout=7200,
            output='{"stage":"rendering","progress":0.89}\n',
            stderr="decoder warning",
        )

    monkeypatch.setattr(remotion_module.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="progress.*0.89"):
        remotion_module.run_remotion_command(
            ["node", "render.mjs"],
            cwd=tmp_path,
        )
