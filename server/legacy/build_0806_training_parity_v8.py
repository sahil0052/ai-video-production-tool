from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

import cv2
from imageio_ffmpeg import get_ffmpeg_exe
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


SERVER_DIR = Path(__file__).resolve().parent
WORKSPACE = SERVER_DIR.parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

import build_0806_training_reference_v7 as base  # noqa: E402
from app.editor.analysis import probe_video  # noqa: E402
from app.editor.production_v4 import ProductionStore  # noqa: E402
from app.editor.training_parity_0806 import (  # noqa: E402
    DURATION_MS,
    V8_CAPTURE_OVERRIDES,
    V8_MUSIC_CANDIDATE,
    build_v8_caption_pages,
    build_v8_music_filter,
    build_v8_shot_schedule,
    caption_coverage_ratio,
    caption_token_window_violations,
    create_v8_blueprint,
    estimate_role_coverage,
    prepare_v8_evidence_frames,
    prepare_v8_risk_reversal_graphic,
    prepare_v8_solid_dark_backdrop,
    technical_mono_caption_share,
)
from app.models import AssetRef  # noqa: E402
from app.production_models import (  # noqa: E402
    ProductionJobRecord,
    ProductionStateEvent,
)


SOURCE = Path(r"D:\Downloads\0806.mp4")
OUTPUT_DIR = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0806-production-v8-training-parity"
)
V7_DIR = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0806-production-v7-training-reference"
)
V4_DIR = WORKSPACE / "storage" / "deliverables" / "0806-production-v4"
MUSIC_LIBRARY = (
    WORKSPACE
    / "storage"
    / "assets"
    / "audio"
    / "technical-reference"
    / "candidates"
)
LICENSED_ROOT = WORKSPACE / "storage" / "assets" / "licensed" / "mixkit"
CAPTURE_ROOT = (
    WORKSPACE
    / "storage"
    / "assets"
    / "product"
    / "0806-v8-captures"
)


def write_json(path: Path, payload: Any) -> None:
    base.write_json(path, payload)


def relative(path: Path) -> str:
    return path.relative_to(OUTPUT_DIR).as_posix()


def copy_reference_targets(
    *,
    source_dir: Path,
    output_dir: Path,
) -> list[Path]:
    source = source_dir / "review" / "reference-targets"
    if not source.is_dir():
        raise FileNotFoundError(source)
    destination = output_dir / "review" / "reference-targets"
    destination.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for candidate in sorted(source.iterdir()):
        if not candidate.is_file() or candidate.suffix.lower() not in {
            ".jpg",
            ".jpeg",
            ".png",
        }:
            continue
        target = destination / candidate.name
        shutil.copy2(candidate, target)
        copied.append(target)
    if not copied:
        raise FileNotFoundError(
            f"No reference review targets found in {source}"
        )
    return copied


def build_training_pattern_report() -> str:
    return """# Training Reference #10 Production Grammar

Reference #10 is the dominant grammar for this edit. Reference #4 is limited
to the qualitative risk-reversal beat. These rules describe rendered behavior,
not treatment names or plan metadata.

## Visual selection

- Open on the product, evidence, physical subject, or story action; presenter
  footage is a connective reset rather than the default background.
- Give each shot one named primary subject and one meaningful action.
- Match each spoken noun and action at the moment it is said.
- Prefer direct source pixels, readable real software macros, and licensed
  tactile footage over generic robots, decorative HUDs, floating icons, or
  generated cinematic plates.
- Reuse one source for no more than two consecutive shots.
- Keep presenter visibility near 12–16% for this strict parity edit.

## Composition

- Alternate dark technical frames, bright source pages, and warm tactile or
  presenter footage to reproduce the reference's wide tonal range.
- Use solid dark negative space around code and diagrams; textured backdrops
  must remain subordinate and low-detail.
- Product UI must be cropped to the active control, code line, or Navigator
  item so it remains legible on a phone.
- Evidence uses overview under 800 ms, then a readable source-pixel excerpt,
  then a verified fact macro.
- Full-frame media is the default. Floating cards are used only when negative
  space is part of the reference composition.
- Keep local edge density in the 0.060–0.090 range and avoid dense full-desktop
  captures.

## Motion and pacing

- Hard cuts dominate; the target is 19–21 detected cuts with a 1.7–2.3 second
  median shot.
- Still evidence alternates intentional holds with one restrained push or
  tracked underline.
- Moving product shots need measurable cursor/action motion and a deliberate
  crop push; nominal video that is effectively static is rejected.
- Near-static frame pairs should remain between 25% and 50%, while moving
  beats must be strong enough to keep structural motion in range.
- Do not add constant drift, global grain, motion washes, random shakes,
  glitches, or particles to inflate motion scores.

## Typography

- Use one serif hook treatment in the opening two seconds.
- Body captions use Share Tech Mono, uppercase white, in a fitted near-black
  rectangle at approximately 31–34 px on a 1080×1920 frame.
- Captions contain one to three words normally, four only when grammar
  requires it, and replace cleanly at phrase boundaries.
- Every page holds 350–1,300 ms, remains inside one sentence, and keeps every
  token inside its visible window.
- Anchor technical captions near 73–74% frame height, then move only to avoid
  a face, active UI, or evidence line.
- Do not use karaoke scaling, active-word colors, oversized yellow social
  captions, or continuous entrance animation.

## Evidence

- Show exact claims, numbers, documents, and results only when an attached
  primary or official source supports them.
- Preserve genuine source pixels; never redraw a fake article or software
  result.
- Crop on line and word boundaries, keep attribution outside the source crop,
  and verify required terms with OCR at phone size.
- The $110,000 claim must remain attached to the MQL5 Article 525 excerpt and
  must not be described as an unsupported final balance.
- Generated diagrams are qualitative, story-specific, and labelled
  ILLUSTRATIVE when they are not evidence.

## Sound

- Use one uninterrupted, vocal-free documentary/technical bed whose rendered
  residual pulse measures 84–100 BPM.
- Keep music psychologically behind narration with real gain automation;
  do not use bright EDM leads or double-time percussion.
- Use semantic effects only: hook settle, UI clicks, evidence movement, proof
  hit, reversal boom, attachment click, and CTA lift.
- Protect every spoken-word onset from SFX and verify the encoded mix against
  the untouched 48 kHz dialogue master.
- Master near −14.2 LUFS, no higher than −1 dBTP, with 2.3–3.5 LU LRA.

## Release gates

- Flow coverage is exactly 0%; copied training footage or audio is forbidden.
- Real product plus direct evidence must supply at least 52% of visible pixels.
- Caption coverage must stay between 70% and 74%, with at least 96% of visible
  caption time using technical mono.
- Dark frames, bright frames, luminance percentiles, saturation, local edge
  density, intentional holds, and dark negative space are measured from the
  final encoded pixels.
- Every narration word must remain audible and ordered; no protected term,
  sentence opening, number, or CTA word may be lost.
- Automation may only advance to awaiting-final-approval. Human side-by-side
  approval is required for hook, code, evidence, risk, product demo, and ending.
"""


def build_v7_gap_audit_report() -> str:
    return """# V7 Perceptual Gap Audit

V7 was blocked because its source-role labels looked correct while the final
pixels still diverged from reference #10.

## Measured failures

- Local edge density was 0.1173 versus the 0.060–0.090 target and the 0.0733
  reference measurement.
- Near-static pair ratio was 0.0000 versus reference #10 at 0.4102.
- Bright uniform blank P90 was 0.4935 versus the 0.43 maximum.
- Dark uniform negative-space mean was 0.1597 versus the 0.28 minimum and the
  0.3609 reference measurement.
- Only 64.36% of visible caption time used technical mono.
- Ten caption tokens extended outside their visible caption pages.
- The rendered mixed pulse measured 113.5 BPM versus the approximately 90 BPM
  reference pulse.

## Root causes

- Authentic desktop captures were treated as inherently production-ready even
  when their active control was too small or the footage was effectively
  static.
- Several nominally different treatments used the same dense desktop view,
  so scene changes did not create reference-like composition changes.
- Textured backdrops and full-page evidence increased local detail while
  reducing clean dark negative space.
- Caption family selection and token containment were checked in metadata but
  not enforced against the final visible page sequence.
- Music was selected from nominal metadata instead of the rendered residual
  bed, allowing bright double-time energy to dominate the finished mix.

## Required correction

V8 must use credential-free demo source files, readable action crops, measured
cursor movement, source-pixel evidence macros, technical-mono captions, a
rendered 84–100 BPM bed, and pixel-level composition gates before human review.
"""


def prepare_music() -> Path:
    source = MUSIC_LIBRARY / str(V8_MUSIC_CANDIDATE["file"])
    if not source.is_file():
        raise FileNotFoundError(source)
    output = (
        OUTPUT_DIR
        / "assets"
        / "audio"
        / "music-technical-documentary.wav"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        get_ffmpeg_exe(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        str(V8_MUSIC_CANDIDATE["selection_start_seconds"]),
        "-i",
        str(source),
        "-t",
        "42.5",
        "-af",
        build_v8_music_filter(),
        "-ar",
        "48000",
        "-ac",
        "2",
        "-c:a",
        "pcm_s16le",
        str(output),
    ]
    subprocess.run(
        command,
        check=True,
        timeout=300,
        shell=False,
    )
    return output


def prepare_soft_backdrop(
    *,
    video: Path,
    output: Path,
    frame_ratio: float,
) -> Path:
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise RuntimeError(f"Unable to read licensed context: {video}")
    frame_count = max(1, int(capture.get(cv2.CAP_PROP_FRAME_COUNT)))
    capture.set(
        cv2.CAP_PROP_POS_FRAMES,
        max(0, min(frame_count - 1, round(frame_count * frame_ratio))),
    )
    ok, frame = capture.read()
    capture.release()
    if not ok:
        raise RuntimeError(f"Unable to extract licensed context: {video}")
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(frame_rgb)
    image = ImageOps.fit(
        image,
        (1080, 1920),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )
    image = image.filter(ImageFilter.GaussianBlur(radius=26))
    image = ImageEnhance.Color(image).enhance(0.40)
    image = ImageEnhance.Brightness(image).enhance(0.42)
    image = ImageEnhance.Contrast(image).enhance(1.05)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return output


def prepare_assets(
    *,
    graphics: dict[str, Path],
    evidence_paths: dict[str, Path],
    music_path: Path,
) -> list[AssetRef]:
    assets = base.prepare_assets(graphics, evidence_paths, music_path)
    updated: list[AssetRef] = []
    for asset in assets:
        if asset.id in V8_CAPTURE_OVERRIDES:
            source = CAPTURE_ROOT / V8_CAPTURE_OVERRIDES[asset.id]
            if not source.is_file():
                raise FileNotFoundError(source)
            destination = base.copy_file(
                source,
                (
                    OUTPUT_DIR
                    / "assets"
                    / "product"
                    / f"{asset.id}.mp4"
                ),
            )
            updated.append(
                asset.model_copy(
                    update={
                        "path": relative(destination),
                        "keywords": [
                            "privacy-safe local MetaTrader demo",
                            "visible cursor action",
                            "real product capture",
                        ],
                        "provenance": "local-safe-demo-capture",
                        "license": "user-owned local capture",
                        "provider": "local-metatrader",
                        "remote_id": None,
                        "creator": "production capture",
                        "source_url": None,
                        "license_url": None,
                        "search_query": None,
                    }
                )
            )
        elif asset.id == "music-technical-documentary":
            updated.append(
                asset.model_copy(
                    update={
                        "keywords": [
                            "technical documentary",
                            "87-92 bpm",
                            "instrumental",
                        ],
                        "remote_id": str(V8_MUSIC_CANDIDATE["id"]),
                        "creator": "Mixkit contributor",
                        "search_query": (
                            "restrained documentary technology ambient"
                        ),
                    }
                )
            )
        else:
            updated.append(asset)

    code_backdrop = prepare_soft_backdrop(
        video=LICENSED_ROOT / "code-screen-9757.mp4",
        output=(
            OUTPUT_DIR
            / "assets"
            / "licensed"
            / "code-soft-backdrop.png"
        ),
        frame_ratio=0.42,
    )
    keyboard_backdrop = prepare_soft_backdrop(
        video=LICENSED_ROOT / "typing-242.mp4",
        output=(
            OUTPUT_DIR
            / "assets"
            / "licensed"
            / "keyboard-soft-backdrop.png"
        ),
        frame_ratio=0.54,
    )
    updated.extend(
        [
            AssetRef(
                id="licensed-code-soft-backdrop",
                kind="image",
                path=relative(code_backdrop),
                keywords=["blurred code screen", "technical context"],
                provenance="internet:licensed-stock-video-derived-still",
                license="Mixkit Free License",
                provider="Mixkit",
                remote_id="9757",
                creator="Mixkit contributor",
                source_url=(
                    "https://mixkit.co/free-stock-video/"
                    "computer-code-in-the-screen-9757/"
                ),
                license_url="https://mixkit.co/license/",
                search_query="computer code screen",
            ),
            AssetRef(
                id="licensed-keyboard-soft-backdrop",
                kind="image",
                path=relative(keyboard_backdrop),
                keywords=["blurred keyboard", "tactile context"],
                provenance="internet:licensed-stock-video-derived-still",
                license="Mixkit Free License",
                provider="Mixkit",
                remote_id="242",
                creator="Mixkit contributor",
                source_url=(
                    "https://mixkit.co/free-stock-video/"
                    "typing-on-a-laptop-242/"
                ),
                license_url="https://mixkit.co/license/",
                search_query="typing on laptop",
            ),
        ]
    )
    return updated


def write_reports(
    *,
    assets: list[AssetRef],
    blueprint: Any,
    evidence_paths: dict[str, Path],
) -> dict[str, str]:
    artifacts = {
        "training_pattern_report": "training-pattern-report.md",
        "v7_gap_audit": "v7-gap-audit.md",
        "reference_profile": "reference-profile.json",
        "storyboard": "storyboard.json",
        "caption_plan": "caption-plan.json",
        "sound_cue_sheet": "sound-cue-sheet.json",
        "music_candidate_report": "music-candidate-report.json",
        "asset_manifest": "asset-manifest.json",
        "capture_manifest": "capture-manifest.json",
        "dialogue_edl": "dialogue-edl.json",
        "motion_events": "motion-events.json",
        "flow_shot_plan": "flow-shot-plan.json",
        "blueprint": "blueprint.json",
        "transcript_aligned": "transcript-aligned.json",
        "transcript_deepgram": "transcript-deepgram-en-in.json",
        "production_settings": "production-settings.json",
        "evidence": "evidence.json",
    }
    (OUTPUT_DIR / artifacts["training_pattern_report"]).write_text(
        build_training_pattern_report(),
        encoding="utf-8",
    )
    (OUTPUT_DIR / artifacts["v7_gap_audit"]).write_text(
        build_v7_gap_audit_report(),
        encoding="utf-8",
    )
    layers_by_shot: dict[str, list[str]] = {}
    for layer in blueprint.layers:
        layers_by_shot.setdefault(layer.shot_id, []).append(layer.id)
    storyboard = []
    for shot in build_v8_shot_schedule():
        storyboard.append(
            {
                **shot,
                "layer_ids": layers_by_shot.get(str(shot["id"]), []),
            }
        )
    write_json(OUTPUT_DIR / artifacts["storyboard"], storyboard)
    caption_pages = blueprint.caption_pages
    write_json(
        OUTPUT_DIR / artifacts["caption_plan"],
        {
            "primary_reference": 10,
            "family": "technical-mono",
            "coverage_ratio": caption_coverage_ratio(
                caption_pages,
                DURATION_MS,
            ),
            "technical_mono_share": technical_mono_caption_share(
                caption_pages
            ),
            "token_window_violations": caption_token_window_violations(
                caption_pages
            ),
            "pages": [
                page.model_dump(mode="json")
                for page in caption_pages
            ],
        },
    )
    write_json(
        OUTPUT_DIR / artifacts["sound_cue_sheet"],
        blueprint.audio.model_dump(mode="json"),
    )
    write_json(
        OUTPUT_DIR / artifacts["music_candidate_report"],
        {
            "policy": "licensed, vocal-free, no loop",
            "reference_mixed_pulse_bpm": 90,
            "selected": {
                **V8_MUSIC_CANDIDATE,
                "processing": build_v8_music_filter(),
            },
            "rejected_v7_selection": {
                "name": "Cyberpunk City",
                "rendered_mixed_pulse_bpm": 113.5,
                "reason": "Finished mix remained too rhythmically urgent.",
            },
        },
    )
    manifest_assets = []
    for asset in assets:
        path = OUTPUT_DIR / asset.path
        manifest_assets.append(
            {
                **asset.model_dump(mode="json"),
                "checksum_sha256": base.sha256(path),
            }
        )
    write_json(
        OUTPUT_DIR / artifacts["asset_manifest"],
        {
            "policy": "evidence-first free-licensed",
            "assets": manifest_assets,
        },
    )
    write_json(
        OUTPUT_DIR / artifacts["capture_manifest"],
        {
            "profile": "local-metatrader",
            "privacy_reviewed": True,
            "captures": [
                {
                    "asset_id": asset.id,
                    "path": asset.path,
                    "checksum_sha256": base.sha256(
                        OUTPUT_DIR / asset.path
                    ),
                }
                for asset in assets
                if asset.provenance == "local-safe-demo-capture"
            ],
        },
    )
    write_json(
        OUTPUT_DIR / artifacts["reference_profile"],
        {
            "name": "technical-reference-parity",
            "primary_reference": 10,
            "secondary_reference": 4,
            "duration_ms": DURATION_MS,
            "presenter_ratio": [0.12, 0.16],
            "flow_ratio_max": 0,
            "caption_coverage_ratio": [0.70, 0.74],
            "technical_mono_share_min": 0.96,
            "composition": {
                "edge_density": [0.060, 0.090],
                "near_static_pair_ratio": [0.25, 0.50],
                "bright_uniform_blank_p90_max": 0.43,
                "dark_uniform_blank_mean_min": 0.28,
            },
            "audio": {
                "mixed_pulse_bpm": [84, 100],
                "integrated_lufs": [-14.5, -13.9],
                "true_peak_max": -1,
                "lra": [2.3, 3.5],
            },
            "planned_role_coverage": estimate_role_coverage(
                blueprint.layers
            ),
        },
    )
    write_json(
        OUTPUT_DIR / artifacts["dialogue_edl"],
        [
            segment.model_dump(mode="json")
            for segment in blueprint.dialogue_edl
        ],
    )
    write_json(
        OUTPUT_DIR / artifacts["motion_events"],
        [
            event.model_dump(mode="json")
            for event in blueprint.motion_events
        ],
    )
    write_json(OUTPUT_DIR / artifacts["flow_shot_plan"], [])
    write_json(
        OUTPUT_DIR / artifacts["evidence"],
        [
            item.model_dump(mode="json")
            for item in blueprint.evidence
        ],
    )
    write_json(
        OUTPUT_DIR / artifacts["production_settings"],
        {
            "primary_reference": 10,
            "secondary_reference": 4,
            "reference_profile": "technical-reference",
            "story_profile": "automation-future-parity",
            "voice_policy": "preserve-verbatim",
            "flow_operation_budget": 0,
            "asset_policy": "free-licensed",
            "music_profile": "documentary-technical-95",
            "human_final_approval_required": True,
        },
    )
    return artifacts


def main() -> int:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    if not V7_DIR.is_dir():
        raise FileNotFoundError(V7_DIR)
    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"V8 output already exists and will not be overwritten: {OUTPUT_DIR}"
        )
    OUTPUT_DIR.mkdir(parents=True)
    copy_reference_targets(
        source_dir=V7_DIR,
        output_dir=OUTPUT_DIR,
    )

    base.OUTPUT_DIR = OUTPUT_DIR
    transcript = json.loads(
        (V7_DIR / "transcript-aligned.json").read_text(encoding="utf-8")
    )
    write_json(OUTPUT_DIR / "transcript-aligned.json", transcript)
    deepgram_source = (
        V7_DIR
        / "review"
        / "deep-audit"
        / "deepgram-nova2-en-in-transcript.json"
    )
    if not deepgram_source.is_file():
        raise FileNotFoundError(deepgram_source)
    shutil.copy2(
        deepgram_source,
        OUTPUT_DIR / "transcript-deepgram-en-in.json",
    )

    graphics = base.prepare_graphics()
    graphics["graphic-dark-backdrop"] = (
        prepare_v8_solid_dark_backdrop(
            graphics["graphic-dark-backdrop"]
        )
    )
    graphics["graphic-risk-reversal"] = (
        prepare_v8_risk_reversal_graphic(
            graphics["graphic-risk-reversal"]
        )
    )
    source_evidence_dir = V7_DIR / "assets" / "evidence"
    evidence_dir = OUTPUT_DIR / "assets" / "evidence"
    original_history = base.copy_file(
        source_evidence_dir / "metatrader5-atc-history.png",
        evidence_dir / "metatrader5-atc-history.png",
    )
    original_risk = base.copy_file(
        source_evidence_dir / "mql5-atc-2008-risk-readable.png",
        evidence_dir / "mql5-atc-2008-risk-readable.png",
    )
    evidence_paths = prepare_v8_evidence_frames(
        history_source=original_history,
        risk_source=original_risk,
        output_dir=evidence_dir,
    )
    music_path = prepare_music()
    assets = prepare_assets(
        graphics=graphics,
        evidence_paths=evidence_paths,
        music_path=music_path,
    )
    evidence = base.prepare_evidence_records(evidence_paths)
    metadata = probe_video(SOURCE)
    blueprint = create_v8_blueprint(
        source_filename=SOURCE.name,
        source_metadata=metadata,
        assets=assets,
        evidence=evidence,
        transcript=transcript,
    )
    write_json(
        OUTPUT_DIR / "blueprint.json",
        blueprint.model_dump(mode="json"),
    )
    artifacts = write_reports(
        assets=assets,
        blueprint=blueprint,
        evidence_paths=evidence_paths,
    )
    now = datetime.now(UTC)
    ProductionStore(OUTPUT_DIR).create(
        ProductionJobRecord(
            id="production-0806-v8-training-parity",
            source_path=str(SOURCE),
            output_dir=str(OUTPUT_DIR),
            state="blueprint-ready",
            primary_reference=10,
            secondary_reference=4,
            flow_operation_budget=0,
            approved_paid_operations=0,
            consumed_paid_operations=0,
            artifacts=artifacts,
            automated_pass=False,
            human_approved=False,
            state_history=[
                ProductionStateEvent(
                    state="analyzing",
                    at=now,
                    detail=(
                        "V7 was role-matched against reference #10 for "
                        "composition, caption, motion and mixed-audio parity."
                    ),
                ),
                ProductionStateEvent(
                    state="blueprint-ready",
                    at=now,
                    detail=(
                        "V8 parity blueprint persisted with zero Flow "
                        "operations and V7 preserved unchanged."
                    ),
                ),
            ],
            created_at=now,
            updated_at=now,
        )
    )
    print(
        json.dumps(
            {
                "output_dir": str(OUTPUT_DIR),
                "state": "blueprint-ready",
                "layers": len(blueprint.layers),
                "caption_pages": len(blueprint.caption_pages),
                "role_coverage": estimate_role_coverage(blueprint.layers),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
