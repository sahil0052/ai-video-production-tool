from collections.abc import Callable
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from faster_whisper import WhisperModel
from imageio_ffmpeg import get_ffmpeg_exe

from app.editor.analysis import (
    detect_hard_cuts,
    detect_reframe_keyframes,
    probe_video,
    validate_source,
)
from app.editor.assets import (
    RemoteAssetRequest,
    discover_internet_assets,
    discover_local_assets,
)
from app.editor.ffmpeg import (
    LoudnessMeasurement,
    build_master_command,
    measure_loudness_for_master,
    verify_render,
)
from app.editor.planning import build_edit_plan
from app.editor.qc import (
    calculate_meaningful_visual_coverage,
    evaluate_qc,
    measure_qc,
)
from app.editor.remotion import (
    build_remotion_render_command,
    prepare_renderer_inputs,
    prepare_renderer_source_proxy,
    run_remotion_command,
)
from app.editor.sound_design import generate_sound_design
from app.editor.transcript import clean_transcript
from app.models import (
    EditPlanV1,
    GraphicCue,
    PipelineResult,
    QCMeasurements,
    QCReport,
    ScenePlan,
    TranscriptSegment,
    TranscriptWord,
)

ProgressCallback = Callable[[str, int], None]
Transcriber = Callable[[Path], list[TranscriptSegment]]
CommandRunner = Callable[[list[str], Path], None]
RendererRunner = Callable[..., None]
QCMeasurementProvider = Callable[..., QCMeasurements]
LoudnessMeasurementProvider = Callable[[Path], LoudnessMeasurement]


def run_pipeline(
    *,
    source: Path,
    output: Path,
    work_dir: Path,
    transcriber: Transcriber | None = None,
    renderer_runner: RendererRunner | None = None,
    command_runner: CommandRunner | None = None,
    qc_measurement_provider: QCMeasurementProvider | None = None,
    loudness_measurement_provider: LoudnessMeasurementProvider | None = None,
    progress: ProgressCallback | None = None,
) -> PipelineResult:
    work_dir.mkdir(parents=True, exist_ok=True)
    report = progress or (lambda _stage, _percent: None)
    transcribe = transcriber or transcribe_video
    render = renderer_runner or render_edit_plan
    execute = command_runner or run_ffmpeg_command
    measure = qc_measurement_provider or measure_qc
    measure_master_loudness = (
        loudness_measurement_provider
        or (measure_loudness_for_master if command_runner is None else None)
    )

    report("analyzing", 6)
    source_metadata = probe_video(source)
    validate_source(source_metadata)
    source_cuts = detect_hard_cuts(source)
    reframing = detect_reframe_keyframes(source)

    report("transcribing", 18)
    segments = transcribe(source)

    report("cleaning", 32)
    plan = build_edit_plan(
        source_filename="source.mp4",
        metadata=source_metadata,
        transcript=segments,
    )
    plan = plan.model_copy(
        update={"reframing": _retime_reframing(reframing, plan)}
    )

    report("planning", 43)
    report("sourcing", 50)
    transcript_text = " ".join(
        segment.text.strip() for segment in segments if segment.text.strip()
    )
    plan = _attach_local_assets(plan, transcript_text)
    plan = _attach_internet_assets(plan, work_dir / "internet-assets")
    plan = _attach_generated_sound_design(plan, work_dir)
    plan = _validate_plan(plan)
    _write_plan_artifacts(work_dir, plan)
    rendered_path = work_dir / "rendered.mp4"

    qc_report = None
    for repair_attempt in range(3):
        report("rendering", 56 + repair_attempt * 2)
        render(
            source=source,
            output=rendered_path,
            work_dir=work_dir,
            plan=plan,
        )

        report("mastering", 82 + repair_attempt * 2)
        loudness_measurement = (
            measure_master_loudness(rendered_path)
            if measure_master_loudness is not None
            else None
        )
        master_command = build_master_command(
            executable=Path(get_ffmpeg_exe()),
            rendered=rendered_path,
            output=output,
            loudness_measurement=loudness_measurement,
        )
        execute(master_command, work_dir)

        report("quality_control", min(95, 91 + repair_attempt * 2))
        measurements = measure(
            output=output,
            plan=plan,
        )
        qc_report = evaluate_qc(
            plan,
            measurements,
            repair_attempts=repair_attempt,
        )
        if qc_report.passed:
            break
        if repair_attempt < 2:
            plan = _repair_plan_for_qc(plan, qc_report)
            _write_plan_artifacts(work_dir, plan)
    assert qc_report is not None
    (work_dir / "qc-report.json").write_text(
        qc_report.model_dump_json(indent=2),
        encoding="utf-8",
    )

    report("verifying", 96)
    strict_output_validation = (
        renderer_runner is None and command_runner is None
    )
    output_metadata = verify_render(
        output,
        expected_width=plan.output.width if strict_output_validation else None,
        expected_height=plan.output.height if strict_output_validation else None,
        expected_fps=plan.output.fps if strict_output_validation else None,
        require_h264_aac=strict_output_validation,
        require_yuv420p=strict_output_validation,
    )
    result = PipelineResult(
        output_metadata=output_metadata,
        caption_count=len(plan.caption_pages),
        cut_timestamps=source_cuts,
        transcript_text=transcript_text,
        broll_coverage=_calculate_visual_coverage(plan),
        style_score=qc_report.style_score,
        qc_passed=qc_report.passed,
    )
    manifest = {
        "source": source_metadata.model_dump(mode="json"),
        "output": output_metadata.model_dump(mode="json"),
        "source_cut_timestamps": source_cuts,
        "caption_count": len(plan.caption_pages),
        "transcript": [segment.model_dump(mode="json") for segment in segments],
        "edit_plan": "edit-plan.json",
        "captions": "captions.json",
        "qc_report": "qc-report.json",
        "result": result.model_dump(mode="json"),
    }
    (work_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    rendered_path.unlink(missing_ok=True)
    shutil.rmtree(work_dir / "renderer-public", ignore_errors=True)
    report("completed", 100)
    return result


def render_edit_plan(
    *,
    source: Path,
    output: Path,
    work_dir: Path,
    plan: EditPlanV1,
) -> None:
    project_root = Path(__file__).resolve().parents[3]
    renderer_root = project_root / "renderer"
    render_script = renderer_root / "render.mjs"
    if not render_script.is_file():
        raise RuntimeError(
            "Remotion renderer is not installed. Expected renderer/render.mjs."
        )
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is required for Remotion rendering")

    prepared = prepare_renderer_inputs(
        source=source,
        plan=plan,
        public_dir=work_dir / "renderer-public",
        source_preparer=lambda input_path, output_path: (
            prepare_renderer_source_proxy(
                executable=Path(get_ffmpeg_exe()),
                source=input_path,
                output=output_path,
                fps=plan.output.fps,
            )
        ),
    )
    command = build_remotion_render_command(
        node_executable=Path(node),
        render_script=render_script,
        plan_path=prepared.plan_path,
        public_dir=prepared.plan_path.parent,
        output=output,
    )
    run_remotion_command(command, cwd=renderer_root)


def _write_plan_artifacts(work_dir: Path, plan: EditPlanV1) -> None:
    (work_dir / "edit-plan.json").write_text(
        plan.model_dump_json(indent=2),
        encoding="utf-8",
    )
    captions = [
        token.model_dump(mode="json")
        for page in plan.caption_pages
        for token in page.tokens
    ]
    (work_dir / "captions.json").write_text(
        json.dumps(captions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _retime_reframing(reframing, plan: EditPlanV1):
    retimed = []
    for keyframe in reframing:
        for segment in plan.timeline:
            if (
                segment.source_start_ms
                <= keyframe.time_ms
                <= segment.source_end_ms
            ):
                output_time = (
                    segment.output_start_ms
                    + keyframe.time_ms
                    - segment.source_start_ms
                )
                retimed.append(
                    keyframe.model_copy(
                        update={
                            "time_ms": min(output_time, plan.duration_ms - 1)
                        }
                    )
                )
                break
    if not retimed:
        return [
            reframing[0].model_copy(update={"time_ms": 0})
        ] if reframing else []
    if retimed[0].time_ms != 0:
        retimed.insert(0, retimed[0].model_copy(update={"time_ms": 0}))
    return retimed


def _attach_local_assets(
    plan: EditPlanV1,
    transcript_text: str,
) -> EditPlanV1:
    project_root = Path(__file__).resolve().parents[3]
    configured = os.getenv("VIDEO_EDITOR_ASSET_LIBRARY")
    library_root = (
        Path(configured).expanduser().resolve()
        if configured
        else project_root / "assets" / "library"
    )
    body_scenes = [
        scene
        for scene in plan.scenes[1:]
        if scene.end_ms - scene.start_ms >= 700
    ]
    if not body_scenes:
        return plan
    candidates = discover_local_assets(
        library_root,
        text=transcript_text,
        start_ms=body_scenes[0].start_ms,
        end_ms=body_scenes[-1].end_ms,
        limit=min(4, len(body_scenes)),
    )
    scheduled = [
        asset.model_copy(
            update={
                "start_ms": scene.start_ms,
                "end_ms": min(scene.end_ms, scene.start_ms + 2400),
            }
        )
        for asset, scene in zip(candidates, body_scenes)
    ]
    return plan.model_copy(update={"assets": scheduled})


def _attach_internet_assets(
    plan: EditPlanV1,
    destination_dir: Path,
    *,
    discoverer=discover_internet_assets,
) -> EditPlanV1:
    requests = _build_internet_asset_requests(plan)
    if not requests:
        return plan
    downloaded = discoverer(requests, destination_dir)
    if not downloaded:
        return plan

    scheduled_by_start = {
        asset.start_ms: asset
        for asset in downloaded
        if asset.start_ms is not None and asset.end_ms is not None
    }
    scenes = []
    for scene in plan.scenes:
        asset = scheduled_by_start.get(scene.start_ms)
        if asset is None or asset.end_ms != scene.end_ms:
            scenes.append(scene)
            continue
        scenes.append(
            scene.model_copy(
                update={
                    "layout": (
                        "asset-full"
                        if asset.kind == "video"
                        else "presenter-pip"
                    )
                }
            )
        )
    return plan.model_copy(
        update={
            "assets": [*downloaded, *plan.assets],
            "scenes": scenes,
        }
    )


def _build_internet_asset_requests(
    plan: EditPlanV1,
    *,
    limit: int = 4,
) -> list[RemoteAssetRequest]:
    requests: list[RemoteAssetRequest] = []
    existing_intervals = {
        (asset.start_ms, asset.end_ms)
        for asset in plan.assets
        if asset.kind in {"image", "video"}
        and asset.start_ms is not None
        and asset.end_ms is not None
    }
    eligible = [
        scene
        for scene in plan.scenes[1:-1]
        if scene.end_ms - scene.start_ms >= 800
        and scene.role != "cta"
        and (scene.start_ms, scene.end_ms) not in existing_intervals
    ]
    if not eligible:
        return requests

    topic_text = " ".join(
        token.text
        for page in plan.caption_pages
        for token in page.tokens
    )
    selected: list[ScenePlan] = []
    for scene in eligible:
        if not selected or scene.start_ms - selected[-1].start_ms >= 2800:
            selected.append(scene)
        if len(selected) >= limit:
            break

    for scene in selected:
        text = " ".join(
            token.text
            for page in plan.caption_pages
            if page.start_ms < scene.end_ms and page.end_ms > scene.start_ms
            for token in page.tokens
            if token.start_ms < scene.end_ms
            and token.end_ms > scene.start_ms
        )
        query, keywords = _internet_query_for_scene(
            text,
            style_variant=plan.style_variant,
            topic_text=topic_text,
        )
        if not query:
            continue
        requests.append(
            RemoteAssetRequest(
                query=query,
                keywords=keywords,
                start_ms=scene.start_ms,
                end_ms=scene.end_ms,
            )
        )
    return requests


def _internet_query_for_scene(
    text: str,
    *,
    style_variant: str,
    topic_text: str = "",
) -> tuple[str, list[str]]:
    normalized = re.sub(r"[^a-z0-9%$]+", " ", text.lower())
    normalized_topic = re.sub(
        r"[^a-z0-9%$]+",
        " ",
        topic_text.lower(),
    )
    tokens = [
        token
        for token in normalized.split()
        if len(token) > 1
        and token
        not in {
            "and",
            "are",
            "but",
            "for",
            "hai",
            "hain",
            "if",
            "in",
            "into",
            "is",
            "it",
            "kar",
            "karta",
            "mein",
            "nahi",
            "on",
            "par",
            "professionally",
            "set",
            "short",
            "that",
            "the",
            "then",
            "this",
            "was",
            "with",
            "you",
        }
    ]
    token_set = set(tokens)
    topic_tokens = set(normalized_topic.split())
    if {"forex", "trading"}.intersection(topic_tokens):
        anchor = ["forex", "trading"]
    elif {"robot", "humanoid", "hardware"}.intersection(
        topic_tokens | token_set
    ):
        anchor = ["technology", "robot"]
    elif {"app", "phone", "software"}.intersection(
        topic_tokens | token_set
    ):
        anchor = ["technology", "software"]
    elif style_variant == "technical-explanation":
        anchor = ["technology", "engineering"]
    elif style_variant == "hardware-launch":
        anchor = ["technology", "hardware"]
    else:
        anchor = ["technology"]
    keywords = list(dict.fromkeys([*anchor, *tokens]))[:8]
    return " ".join(keywords[:6]), keywords


def _attach_generated_sound_design(
    plan: EditPlanV1,
    work_dir: Path,
) -> EditPlanV1:
    emphasis_times = [0]
    emphasis_times.extend(cue.start_ms for cue in plan.graphics[1:])
    emphasis_times.extend(scene.start_ms for scene in plan.scenes[1::2])
    audio_assets, audio_plan = generate_sound_design(
        work_dir,
        duration_ms=plan.duration_ms,
        emphasis_times_ms=emphasis_times,
    )
    return plan.model_copy(
        update={
            "assets": [*plan.assets, *audio_assets],
            "audio": audio_plan,
        }
    )


def _calculate_visual_coverage(plan: EditPlanV1) -> float:
    return calculate_meaningful_visual_coverage(plan)


def _validate_plan(plan: EditPlanV1) -> EditPlanV1:
    return EditPlanV1.model_validate(plan.model_dump(mode="json"))


def _repair_plan_for_qc(
    plan: EditPlanV1,
    report: QCReport,
) -> EditPlanV1:
    failed = {check.name for check in report.checks if not check.passed}
    repaired = plan
    if {"pacing", "shot_length"}.intersection(failed):
        scenes, graphics = _repair_visual_pacing(repaired)
        repaired = repaired.model_copy(
            update={"scenes": scenes, "graphics": graphics}
        )
    return _validate_plan(repaired)


def _repair_visual_pacing(
    plan: EditPlanV1,
) -> tuple[list[ScenePlan], list[GraphicCue]]:
    target_cuts_per_minute = (
        55 if plan.style_variant == "hyper-montage" else 40
    )
    target_events = max(
        1,
        round(plan.duration_ms / 60_000 * target_cuts_per_minute),
    )
    fixed_timeline_events = {
        segment.output_start_ms for segment in plan.timeline[1:]
    }
    scene_event_budget = max(0, target_events - len(fixed_timeline_events))
    scene_count = scene_event_budget + 1
    boundaries = [
        round(index * plan.duration_ms / scene_count)
        for index in range(scene_count + 1)
    ]
    zooms = [1.0, 1.12, 1.24]
    scenes: list[ScenePlan] = []
    for index, (start_ms, end_ms) in enumerate(
        zip(boundaries, boundaries[1:])
    ):
        midpoint = start_ms + (end_ms - start_ms) // 2
        source_scene = next(
            (
                scene
                for scene in plan.scenes
                if scene.start_ms <= midpoint < scene.end_ms
            ),
            plan.scenes[-1],
        )
        scenes.append(
            ScenePlan(
                id=f"scene-repair-{index + 1}",
                start_ms=start_ms,
                end_ms=end_ms,
                role=source_scene.role,
                layout="presenter" if index % 2 == 0 else "graphic",
                zoom=zooms[index % len(zooms)],
            )
        )
    hook_graphics = [
        graphic for graphic in plan.graphics if graphic.start_ms == 0
    ]
    return scenes, hook_graphics


@lru_cache(maxsize=2)
def _load_whisper_model(model_name: str) -> WhisperModel:
    return WhisperModel(model_name, device="cpu", compute_type="int8")


def transcribe_video(path: Path) -> list[TranscriptSegment]:
    model_name = os.getenv("VIDEO_EDITOR_WHISPER_MODEL", "small")
    model = _load_whisper_model(model_name)
    language_setting = os.getenv("VIDEO_EDITOR_LANGUAGE", "auto").strip().lower()
    language = None if language_setting == "auto" else language_setting
    segments = _transcribe_with_language(model, path, language=language)
    if (
        language is None
        and _needs_english_transcription_retry(segments)
    ):
        english_segments = _transcribe_with_language(
            model,
            path,
            language="en",
        )
        if english_segments:
            segments = english_segments
    return _clean_transcript_if_configured(segments)


def transcribe_video_fixed_language(
    path: Path,
    *,
    language: str,
) -> list[TranscriptSegment]:
    normalized_language = language.strip().lower()
    if not normalized_language:
        raise ValueError("language must not be empty")
    model_name = os.getenv("VIDEO_EDITOR_WHISPER_MODEL", "small")
    model = _load_whisper_model(model_name)
    return _transcribe_with_language(
        model,
        path,
        language=normalized_language,
    )


def _transcribe_with_language(
    model: WhisperModel,
    path: Path,
    *,
    language: str | None,
) -> list[TranscriptSegment]:
    raw_segments, _info = model.transcribe(
        str(path),
        language=language,
        task="transcribe",
        beam_size=5,
        vad_filter=True,
        word_timestamps=True,
        condition_on_previous_text=False,
        initial_prompt=(
            "English and Hindi/Hinglish talking-head social video. Preserve "
            "names, acronyms, numbers, domain terminology and calls to action."
        ),
    )
    segments: list[TranscriptSegment] = []
    for raw_segment in raw_segments:
        words = [
            TranscriptWord(
                start=float(word.start),
                end=float(word.end),
                text=word.word.strip(),
                confidence=getattr(word, "probability", None),
            )
            for word in (raw_segment.words or [])
            if word.word.strip()
        ]
        text = raw_segment.text.strip()
        if text:
            segments.append(
                TranscriptSegment(
                    start=float(raw_segment.start),
                    end=float(raw_segment.end),
                    text=text,
                    words=words,
                )
            )
    return segments


def _needs_english_transcription_retry(
    segments: list[TranscriptSegment],
) -> bool:
    text = " ".join(segment.text for segment in segments)
    if not text:
        return False
    if "\ufffd" in text:
        return True
    alphabetic = [character for character in text if character.isalpha()]
    if not alphabetic:
        return False
    latin = [
        character
        for character in alphabetic
        if character.isascii()
    ]
    return len(latin) / len(alphabetic) < 0.55


def _clean_transcript_if_configured(
    segments: list[TranscriptSegment],
) -> list[TranscriptSegment]:
    if os.getenv("VIDEO_EDITOR_TRANSCRIPT_CLEANUP", "auto").lower() == "off":
        return segments
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment = os.getenv("AZURE_GPT56_SOL_DEPLOYMENT")
    if not endpoint or not api_key or not deployment:
        return segments

    def requester(prompt: str) -> str:
        from openai import OpenAI

        client = OpenAI(
            base_url=endpoint.rstrip("/") + "/",
            api_key=api_key,
            timeout=120,
            max_retries=0,
        )
        response = client.responses.create(
            model=deployment,
            input=prompt,
            store=False,
        )
        return response.output_text

    try:
        return clean_transcript(segments, requester=requester)
    except Exception:
        return segments


def run_ffmpeg_command(command: list[str], cwd: Path) -> None:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=1800,
        check=False,
        shell=False,
    )
    if completed.returncode != 0:
        error = completed.stderr[-6000:].strip()
        raise RuntimeError(f"FFmpeg render failed: {error}")
