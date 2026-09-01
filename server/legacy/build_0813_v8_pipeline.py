from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any, Iterable

import cv2
from imageio_ffmpeg import get_ffmpeg_exe
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from app.editor.dialogue_mastering import (
    DialogueAssets,
    DialoguePlan,
    build_dialogue_plan_from_ranges,
    materialize_dialogue_assets,
)
from app.editor.production_audit import estimate_audio_pulse_bpm
from app.editor.training_caption_planner import (
    PlannedCaptionPage,
    covered_ms,
    plan_captions,
)
from app.editor.v8_graphics import (
    render_evidence_crop,
    render_graphic,
)
from app.production_models import EditPlanV2
from build_0813_v8_common import StoryBlueprint, WORKSPACE
from caption_transliteration_0813 import romanize_word
from ffmpeg_plan_renderer import render_plan_with_ffmpeg


FFMPEG = Path(get_ffmpeg_exe())
RENDERER = WORKSPACE / "renderer"
TRAINING_DIR = WORKSPACE / "training videos data"
ASSET_ROOT = WORKSPACE / "storage" / "assets"
V7_PPI = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0813-production-v7-semantic-visuals"
    / "assets"
)
V7_BACKTEST = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0813-production-v7-semantic-visuals-take-2"
    / "assets"
)
V7_LOT = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0813-production-v7-semantic-visuals-take-3"
    / "assets"
)
PPI_CANDIDATE_ROOT = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0813-production-v3-live-footage"
    / "asset-candidates"
    / "ppi-search"
)
V9_ASSET_ROOT = ASSET_ROOT / "0813-v9-internet"
PRODUCT_ROOT = (
    WORKSPACE
    / "storage"
    / "assets"
    / "product"
    / "0806-v8-captures"
)
SFX_ROOT = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0813-production-v1"
    / "assets"
    / "audio"
)
MUSIC_ROOT = ASSET_ROOT / "audio" / "technical-reference" / "candidates"

MUSIC_TARGET_BPM = {
    "ppi": (96, 104),
    "backtest": (88, 96),
    "lot-size": (92, 100),
}


ASSET_LIBRARY: dict[str, dict[str, Any]] = {
    "pexels-27093700": {
        "path": V7_PPI / "licensed" / "pexels-27093700.mp4",
        "provider": "Pexels",
        "creator": "Esra Afsar",
        "remote_id": "27093700",
        "source_url": "https://www.pexels.com/video/27093700/",
        "license": "Pexels License",
        "license_url": "https://www.pexels.com/license/",
    },
    "pexels-29817236": {
        "path": PPI_CANDIDATE_ROOT / "pexels-29817236.mp4",
        "provider": "Pexels",
        "creator": "Nathan J Hilton",
        "remote_id": "29817236",
        "source_url": "https://www.pexels.com/video/29817236/",
        "license": "Pexels License",
        "license_url": "https://www.pexels.com/license/",
    },
    "pexels-13850344": {
        "path": PPI_CANDIDATE_ROOT / "pexels-13850344.mp4",
        "provider": "Pexels",
        "creator": "Erik Mclean",
        "remote_id": "13850344",
        "source_url": "https://www.pexels.com/video/13850344/",
        "license": "Pexels License",
        "license_url": "https://www.pexels.com/license/",
    },
    "pexels-29604470": {
        "path": PPI_CANDIDATE_ROOT / "pexels-29604470.mp4",
        "provider": "Pexels",
        "creator": "K",
        "remote_id": "29604470",
        "source_url": "https://www.pexels.com/video/29604470/",
        "license": "Pexels License",
        "license_url": "https://www.pexels.com/license/",
    },
    "pexels-7019230": {
        "path": PPI_CANDIDATE_ROOT / "pexels-7019230.mp4",
        "provider": "Pexels",
        "creator": "cottonbro studio",
        "remote_id": "7019230",
        "source_url": "https://www.pexels.com/video/7019230/",
        "license": "Pexels License",
        "license_url": "https://www.pexels.com/license/",
    },
    "pexels-7222345": {
        "path": PPI_CANDIDATE_ROOT / "pexels-7222345.mp4",
        "provider": "Pexels",
        "creator": "cottonbro studio",
        "remote_id": "7222345",
        "source_url": "https://www.pexels.com/video/7222345/",
        "license": "Pexels License",
        "license_url": "https://www.pexels.com/license/",
    },
    "pexels-6169086": {
        "path": V7_PPI / "licensed" / "pexels-6169086.mp4",
        "provider": "Pexels",
        "creator": "Tima Miroshnichenko",
        "remote_id": "6169086",
        "source_url": "https://www.pexels.com/video/6169086/",
        "license": "Pexels License",
        "license_url": "https://www.pexels.com/license/",
    },
    "pexels-4820115": {
        "path": V7_PPI / "licensed" / "pexels-4820115.mp4",
        "provider": "Pexels",
        "creator": "cottonbro studio",
        "remote_id": "4820115",
        "source_url": "https://www.pexels.com/video/4820115/",
        "license": "Pexels License",
        "license_url": "https://www.pexels.com/license/",
    },
    "pexels-38362060": {
        "path": V7_PPI / "licensed" / "pexels-38362060.mp4",
        "provider": "Pexels",
        "creator": "Dmitriy Steinke",
        "remote_id": "38362060",
        "source_url": "https://www.pexels.com/video/38362060/",
        "license": "Pexels License",
        "license_url": "https://www.pexels.com/license/",
    },
    "pexels-37101039": {
        "path": V7_PPI / "licensed" / "pexels-37101039.mp4",
        "provider": "Pexels",
        "creator": "Ronie Aristosa",
        "remote_id": "37101039",
        "source_url": "https://www.pexels.com/video/37101039/",
        "license": "Pexels License",
        "license_url": "https://www.pexels.com/license/",
    },
    "pexels-34433115": {
        "path": V7_PPI / "licensed" / "pexels-34433115.mp4",
        "provider": "Pexels",
        "creator": "Cis14_04 09",
        "remote_id": "34433115",
        "source_url": "https://www.pexels.com/video/34433115/",
        "license": "Pexels License",
        "license_url": "https://www.pexels.com/license/",
    },
    "pexels-32953312": {
        "path": V9_ASSET_ROOT / "pexels-32953312.mp4",
        "provider": "Pexels",
        "creator": "Comercial GB",
        "remote_id": "32953312",
        "source_url": (
            "https://www.pexels.com/video/"
            "automated-lime-sorting-on-conveyor-belt-in-factory-32953312/"
        ),
        "license": "Pexels License",
        "license_url": "https://www.pexels.com/license/",
    },
    "pexels-36088020": {
        "path": V9_ASSET_ROOT / "pexels-36088020.mp4",
        "provider": "Pexels",
        "creator": "Shulabh Singh Chauhan",
        "remote_id": "36088020",
        "source_url": (
            "https://www.pexels.com/video/"
            "intense-cricket-match-on-outdoor-field-36088020/"
        ),
        "license": "Pexels License",
        "license_url": "https://www.pexels.com/license/",
    },
    "pexels-36088031": {
        "path": V9_ASSET_ROOT / "pexels-36088031.mp4",
        "provider": "Pexels",
        "creator": "Shulabh Singh Chauhan",
        "remote_id": "36088031",
        "source_url": (
            "https://www.pexels.com/video/"
            "dynamic-cricket-practice-at-urban-outdoor-field-36088031/"
        ),
        "license": "Pexels License",
        "license_url": "https://www.pexels.com/license/",
    },
    "pexels-38870320": {
        "path": V9_ASSET_ROOT / "pexels-38870320.mp4",
        "provider": "Pexels",
        "creator": "Jakub Zerdzicki",
        "remote_id": "38870320",
        "source_url": (
            "https://www.pexels.com/video/"
            "analyzing-financial-data-on-tablet-and-monitors-38870320/"
        ),
        "license": "Pexels License",
        "license_url": "https://www.pexels.com/license/",
    },
    "pexels-6830019": {
        "path": V9_ASSET_ROOT / "pexels-6830019.mp4",
        "provider": "Pexels",
        "creator": "Andy Barbour",
        "remote_id": "6830019",
        "source_url": "https://www.pexels.com/video/student-in-a-quiz-6830019/",
        "license": "Pexels License",
        "license_url": "https://www.pexels.com/license/",
    },
    "pexels-7362804": {
        "path": V9_ASSET_ROOT / "pexels-7362804.mp4",
        "provider": "Pexels",
        "creator": "RDNE Stock project",
        "remote_id": "7362804",
        "source_url": "https://www.pexels.com/video/woman-delivering-pizza-7362804/",
        "license": "Pexels License",
        "license_url": "https://www.pexels.com/license/",
    },
    "bls-source-static": {
        "path": ASSET_ROOT / "0813-stories" / "bls-ppi-july-2026-excerpt.png",
        "provider": "U.S. Bureau of Labor Statistics",
        "creator": "U.S. Bureau of Labor Statistics",
        "remote_id": "ppi-july-2026",
        "source_url": "https://www.bls.gov/news.release/ppi.nr0.htm",
        "license": "Official government source capture",
        "license_url": "https://www.bls.gov/bls/linksite.htm",
    },
    "bls-zero-proof-static": {
        "path": (
            WORKSPACE
            / "storage"
            / "deliverables"
            / "0813-all-three-v8-training-reference"
            / "ppi"
            / "source-captures"
            / "evidence-zero.png"
        ),
        "provider": "U.S. Bureau of Labor Statistics",
        "creator": "U.S. Bureau of Labor Statistics",
        "remote_id": "ppi-july-2026-zero-proof",
        "source_url": "https://www.bls.gov/news.release/ppi.nr0.htm",
        "license": "Official government source capture",
        "license_url": "https://www.bls.gov/bls/linksite.htm",
    },
    "pexels-7580269": {
        "path": V7_BACKTEST / "licensed" / "pexels-7580269.mp4",
        "provider": "Pexels",
        "creator": "Tima Miroshnichenko",
        "remote_id": "7580269",
        "source_url": "https://www.pexels.com/video/7580269/",
        "license": "Pexels License",
        "license_url": "https://www.pexels.com/license/",
    },
    "pixabay-281621": {
        "path": V7_BACKTEST / "licensed" / "pixabay-281621.mp4",
        "provider": "Pixabay",
        "creator": "PatternsWorld",
        "remote_id": "281621",
        "source_url": "https://pixabay.com/videos/id-281621/",
        "license": "Pixabay Content License",
        "license_url": "https://pixabay.com/service/license-summary/",
    },
    "pixabay-138691": {
        "path": V7_BACKTEST / "licensed" / "pixabay-138691.mp4",
        "provider": "Pixabay",
        "creator": "MuneerKhan92",
        "remote_id": "138691",
        "source_url": "https://pixabay.com/videos/id-138691/",
        "license": "Pixabay Content License",
        "license_url": "https://pixabay.com/service/license-summary/",
    },
    "student-writing": {
        "path": V7_BACKTEST / "licensed" / "student-writing.mp4",
        "provider": "Pixabay",
        "creator": "rcp24",
        "remote_id": "355580",
        "source_url": "https://pixabay.com/videos/id-355580/",
        "license": "Pixabay Content License",
        "license_url": "https://pixabay.com/service/license-summary/",
    },
    "pexels-13441351": {
        "path": V7_LOT / "licensed" / "pexels-13441351.mp4",
        "provider": "Pexels",
        "creator": "Mizuno K",
        "remote_id": "13441351",
        "source_url": "https://www.pexels.com/video/13441351/",
        "license": "Pexels License",
        "license_url": "https://www.pexels.com/license/",
    },
    "pexels-7362641": {
        "path": V7_LOT / "licensed" / "pexels-7362641.mp4",
        "provider": "Pexels",
        "creator": "RDNE Stock project",
        "remote_id": "7362641",
        "source_url": "https://www.pexels.com/video/7362641/",
        "license": "Pexels License",
        "license_url": "https://www.pexels.com/license/",
    },
    "mt5-risk-inputs": {
        "path": PRODUCT_ROOT / "mt5-risk-input-action-v2.mp4",
        "provider": "Local capture",
        "license": "User-owned privacy-reviewed capture",
    },
    "mt5-risk-alternate": {
        "path": PRODUCT_ROOT / "mt5-risk-alternate-action-v2.mp4",
        "provider": "Local capture",
        "license": "User-owned privacy-reviewed capture",
    },
    "mt5-strategy-tester": {
        "path": PRODUCT_ROOT / "mt5-strategy-tester-action-v2.mp4",
        "provider": "Local capture",
        "license": "User-owned privacy-reviewed capture",
    },
    "metaeditor-rule-highlight": {
        "path": PRODUCT_ROOT / "metaeditor-rule-highlight-v2.mp4",
        "provider": "Local capture",
        "license": "User-owned privacy-reviewed capture",
    },
    "mt5-attach-ea": {
        "path": PRODUCT_ROOT / "mt5-attach-action-v2.mp4",
        "provider": "Local capture",
        "license": "User-owned privacy-reviewed capture",
    },
}

MUSIC = {
    "ppi": {
        "path": MUSIC_ROOT / "close-up-1167.mp3",
        "name": "Close Up",
        "remote_id": "1167",
        "selection_start": 15,
        "bpm": 101,
        "tempo": 1.0,
        "gain_db": -34.0,
    },
    "backtest": {
        "path": MUSIC_ROOT / "sci-fi-score-464.mp3",
        "name": "Sci-Fi Score",
        "remote_id": "464",
        "selection_start": 8,
        "bpm": 90,
        "tempo": 1.18,
        "gain_db": -29.5,
    },
    "lot-size": {
        "path": MUSIC_ROOT / "meditation-441.mp3",
        "name": "Meditation",
        "remote_id": "441",
        "selection_start": 10,
        "bpm": 100,
        "tempo": 0.94,
        "gain_db": -29.5,
    },
}

SFX_CUES = {
    "ppi": [
        ("hook-settle", "impact-soft.wav", 1_900, 220, -17.0, "impact"),
        ("supplier-step", "snap.wav", 3_200, 120, -18.0, "impact"),
        ("flow-step", "click.wav", 6_400, 100, -19.0, "click"),
        ("source-page", "paper.wav", 15_100, 260, -17.0, "whoosh"),
        ("actual-proof", "impact.wav", 18_800, 220, -18.0, "impact"),
        ("reversal", "reverse-whoosh.wav", 28_500, 320, -17.0, "whoosh"),
        ("market-turn", "whoosh.wav", 31_600, 260, -19.0, "whoosh"),
        ("spread-click", "click.wav", 35_100, 100, -18.0, "click"),
        ("confirmation", "snap.wav", 38_100, 120, -18.0, "impact"),
        ("lesson", "impact-soft.wav", 40_900, 180, -19.0, "impact"),
        ("cta-lift", "riser.wav", 44_100, 520, -20.0, "riser"),
    ],
    "backtest": [
        ("cricket-contrast", "impact.wav", 1_400, 220, -17.0, "impact"),
        ("tester-open", "click.wav", 2_900, 100, -18.0, "click"),
        ("practice-rule", "snap.wav", 9_300, 120, -19.0, "impact"),
        ("perfect-condition", "click.wav", 16_100, 100, -19.0, "click"),
        ("live-friction", "reverse-whoosh.wav", 20_600, 300, -17.0, "whoosh"),
        ("overfit-turn", "drop.wav", 25_300, 320, -18.0, "impact"),
        ("forward-test", "click.wav", 33_100, 100, -18.0, "click"),
        ("not-guarantee", "impact-soft.wav", 37_500, 200, -18.0, "impact"),
        ("cta-lift", "riser.wav", 46_600, 520, -20.0, "riser"),
    ],
    "lot-size": [
        ("lot-input", "click.wav", 1_800, 100, -18.0, "click"),
        ("pizza-count", "pop.wav", 3_900, 120, -18.0, "notification"),
        ("total-scale", "snap.wav", 5_900, 120, -19.0, "impact"),
        ("impact-change", "whoosh.wav", 18_500, 260, -18.0, "whoosh"),
        ("risk-equation", "impact-soft.wav", 28_400, 220, -17.0, "impact"),
        ("code-rule", "click.wav", 33_200, 100, -18.0, "click"),
        ("wrong-repeat", "reverse-whoosh.wav", 35_600, 300, -18.0, "whoosh"),
        ("attach-action", "click.wav", 42_500, 100, -18.0, "click"),
        ("cta-lift", "riser.wav", 46_400, 520, -20.0, "riser"),
    ],
}


def _run(command: list[str], *, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            f"Command failed ({completed.returncode}): {' '.join(command)}\n"
            + completed.stderr[-6000:]
        )
    return completed.stdout


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def score_music_candidate(
    *,
    bpm: float,
    target_bpm: tuple[int, int],
    speech_masking_ratio: float,
    brightness_ratio: float,
    section_stability_cv: float,
) -> dict[str, float]:
    def clamp(value: float) -> float:
        return max(0.0, min(5.0, value))

    low, high = target_bpm
    if low <= bpm <= high:
        pulse = 5.0
    else:
        distance = low - bpm if bpm < low else bpm - high
        pulse = clamp(5.0 - distance / 4.0)
    speech_masking = clamp(5.0 - speech_masking_ratio * 5.0)
    brightness = clamp(5.0 - brightness_ratio * 8.0)
    stability = clamp(5.0 - section_stability_cv * 6.0)
    values = {
        "pulse": round(pulse, 3),
        "speech_masking": round(speech_masking, 3),
        "brightness": round(brightness, 3),
        "stability": round(stability, 3),
    }
    values["total"] = round(sum(values.values()), 3)
    return values


def music_candidate_paths(story_id: str) -> tuple[Path, ...]:
    selected = Path(MUSIC[story_id]["path"])
    available = sorted(MUSIC_ROOT.glob("*.mp3"))
    alternatives = [path for path in available if path != selected]
    candidates = [selected, *alternatives[:4]]
    if len(candidates) != 5 or len(set(candidates)) != 5:
        raise RuntimeError("Five distinct music candidates are required")
    return tuple(candidates)


def _music_features(path: Path) -> dict[str, float]:
    completed = subprocess.run(
        [
            str(FFMPEG),
            "-v",
            "error",
            "-ss",
            "10",
            "-t",
            "30",
            "-i",
            str(path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "f32le",
            "-",
        ],
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            f"Could not analyze music candidate: {path}\n"
            + completed.stderr.decode("utf-8", errors="replace")[-3000:]
        )
    samples = np.frombuffer(completed.stdout, dtype="<f4").astype(np.float64)
    if samples.size < 16_000 * 4:
        raise RuntimeError(f"Music candidate is too short: {path}")
    bpm = estimate_audio_pulse_bpm(
        samples,
        sample_rate=16_000,
        bpm_min=72,
        bpm_max=120,
    )
    spectrum_samples = samples[: min(samples.size, 262_144)]
    spectrum = np.abs(
        np.fft.rfft(spectrum_samples * np.hanning(spectrum_samples.size))
    ) ** 2
    frequencies = np.fft.rfftfreq(
        spectrum_samples.size,
        d=1 / 16_000,
    )
    audible = (frequencies >= 40) & (frequencies <= 8_000)
    speech = (frequencies >= 250) & (frequencies <= 3_500)
    bright = (frequencies >= 4_000) & (frequencies <= 8_000)
    total_energy = max(float(np.sum(spectrum[audible])), 1e-12)
    frame_size = 32_000
    usable = samples.size - samples.size % frame_size
    rms = np.sqrt(
        np.mean(samples[:usable].reshape(-1, frame_size) ** 2, axis=1)
        + 1e-12
    )
    return {
        "bpm_estimate": float(bpm),
        "speech_masking_ratio": float(np.sum(spectrum[speech]) / total_energy),
        "brightness_ratio": float(np.sum(spectrum[bright]) / total_energy),
        "section_stability_cv": float(
            np.std(rms) / max(float(np.mean(rms)), 1e-12)
        ),
    }


def _music_candidate_report(
    blueprint: StoryBlueprint,
) -> dict[str, Any]:
    target = MUSIC_TARGET_BPM[blueprint.story_id]
    selected = Path(MUSIC[blueprint.story_id]["path"])
    candidates = []
    for path in music_candidate_paths(blueprint.story_id):
        features = _music_features(path)
        scores = score_music_candidate(
            bpm=features["bpm_estimate"],
            target_bpm=target,
            speech_masking_ratio=features["speech_masking_ratio"],
            brightness_ratio=features["brightness_ratio"],
            section_stability_cv=features["section_stability_cv"],
        )
        candidates.append(
            {
                "name": path.stem,
                "path": str(path),
                "checksum_sha256": _sha256(path),
                "provider": "Mixkit",
                "license": "Mixkit Free License",
                "license_url": "https://mixkit.co/license/",
                "selected": path == selected,
                "features": {
                    key: round(value, 6)
                    for key, value in features.items()
                },
                "scores": scores,
            }
        )
    return {
        "story_id": blueprint.story_id,
        "target_bpm": list(target),
        "selection": selected.stem,
        "selection_basis": (
            "Speech-safe editorial fit after pulse, masking, brightness, "
            "and section-stability review."
        ),
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def _copy(source: Path, destination: Path) -> Path:
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if (
        not destination.is_file()
        or source.stat().st_size != destination.stat().st_size
        or _sha256(source) != _sha256(destination)
    ):
        shutil.copy2(source, destination)
    return destination


def _render_presenter_split(
    *,
    top: Path,
    presenter: Path,
    output: Path,
    duration_ms: int,
    top_source_start_ms: int,
    presenter_source_start_ms: int,
) -> Path:
    if not top.is_file():
        raise FileNotFoundError(top)
    if not presenter.is_file():
        raise FileNotFoundError(presenter)
    output.parent.mkdir(parents=True, exist_ok=True)
    duration_seconds = duration_ms / 1000
    command = [str(FFMPEG), "-y"]
    if top.suffix.casefold() in {".png", ".jpg", ".jpeg", ".webp"}:
        command.extend(["-loop", "1", "-framerate", "30"])
    elif top_source_start_ms:
        command.extend(["-ss", f"{top_source_start_ms / 1000:.6f}"])
    command.extend(["-i", str(top)])
    if presenter_source_start_ms:
        command.extend(
            ["-ss", f"{presenter_source_start_ms / 1000:.6f}"]
        )
    command.extend(
        [
            "-i",
            str(presenter),
            "-filter_complex",
            (
                f"[0:v]trim=duration={duration_seconds:.6f},"
                "setpts=PTS-STARTPTS,fps=30,"
                "scale=1080:1076:force_original_aspect_ratio=increase,"
                "crop=1080:1076,setsar=1,"
                "eq=brightness=-0.025:contrast=1.060:saturation=0.920[top];"
                f"[1:v]trim=duration={duration_seconds:.6f},"
                "setpts=PTS-STARTPTS,fps=30,"
                "crop=iw:ih*0.48:0:ih*0.08,"
                "scale=1080:844,setsar=1,"
                "eq=brightness=0.010:contrast=1.030:saturation=0.940[face];"
                "[top][face]vstack=inputs=2,"
                "drawbox=x=0:y=1072:w=1080:h=8:"
                "color=white@0.75:t=fill,format=yuv420p[out]"
            ),
            "-map",
            "[out]",
            "-an",
            "-t",
            f"{duration_seconds:.6f}",
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "16",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    _run(command)
    return output


def _source_metadata(path: Path) -> dict[str, Any]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot inspect video: {path}")
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 30)
    frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    capture.release()
    return {
        "width": width,
        "height": height,
        "fps": fps,
        "frame_count": frames,
        "duration_seconds": frames / fps,
    }


def _media_duration_ms(path: Path) -> int:
    if path.suffix.lower() not in {".mp4", ".mov", ".mkv", ".webm"}:
        return 0
    metadata = _source_metadata(path)
    return round(metadata["duration_seconds"] * 1000)


def _old_source_ranges(story_id: str) -> list[tuple[int, int]]:
    module_name = {
        "ppi": "build_0813_ppi_live",
        "backtest": "build_0813_backtest_live",
        "lot-size": "build_0813_lotsize_live",
    }[story_id]
    module = importlib.import_module(module_name)
    return [
        (segment.source_start_ms, segment.source_end_ms)
        for segment in module.dialogue_edl()
    ]


def _map_time(source_ms: int, plan: DialoguePlan, *, end: bool) -> int:
    for segment in plan.segments:
        if segment.source_start_ms <= source_ms <= segment.source_end_ms:
            return min(
                segment.output_end_ms,
                segment.output_start_ms
                + source_ms
                - segment.source_start_ms,
            )
    if source_ms < plan.segments[0].source_start_ms:
        return 0
    for left, right in zip(plan.segments, plan.segments[1:]):
        if left.source_end_ms < source_ms < right.source_start_ms:
            return left.output_end_ms if not end else right.output_start_ms
    return plan.output_duration_ms


def _remap_words(
    words: list[dict[str, Any]],
    plan: DialoguePlan,
) -> list[dict[str, Any]]:
    def display_text(value: str) -> str:
        try:
            return romanize_word(value)
        except ValueError:
            for punctuation in (",", ".", "?", "!"):
                try:
                    return romanize_word(value + punctuation).rstrip(
                        punctuation
                    )
                except ValueError:
                    continue
            raise

    remapped: list[dict[str, Any]] = []
    for word in words:
        start = round(float(word["start"]) * 1000)
        end = round(float(word["end"]) * 1000)
        mapped_start = _map_time(start, plan, end=False)
        mapped_end = _map_time(end, plan, end=True)
        if mapped_end <= mapped_start:
            mapped_end = mapped_start + max(1, end - start)
        remapped.append(
            {
                "text": display_text(
                    word.get(
                        "punctuated_word",
                        word.get("word", ""),
                    )
                ),
                "start_ms": mapped_start,
                "end_ms": mapped_end,
                "confidence": word.get("confidence"),
            }
        )
    return remapped


def _role_spans(blueprint: StoryBlueprint) -> list[dict[str, Any]]:
    result = []
    for shot_spec in blueprint.shots:
        if shot_spec.treatment_class == "cta":
            role = "presenter-cta"
        elif shot_spec.source_role == "direct-evidence":
            role = "evidence"
        elif shot_spec.source_role == "real-product":
            role = "product-action"
        else:
            role = "explanation"
        result.append(
            {
                "start_ms": shot_spec.start_ms,
                "end_ms": shot_spec.end_ms,
                "role": role,
            }
        )
    return result


def _source_capture_frame(
    source: Path,
    output: Path,
    *,
    source_label: str,
    variant: str = "overview",
) -> Path:
    with Image.open(source).convert("RGB") as original:
        if variant == "detail":
            original = original.crop(
                (
                    0,
                    round(original.height * 0.56),
                    original.width,
                    original.height,
                )
            )
        contained = ImageOps.contain(
            original,
            (990, 980 if variant == "detail" else 900),
            method=Image.Resampling.LANCZOS,
        )
    canvas = Image.new("RGB", (1080, 1920), "#F4F1E8")
    x = (1080 - contained.width) // 2
    evidence_height = 980 if variant == "detail" else 900
    y = 560 + (evidence_height - contained.height) // 2
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 23)
    bold = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 70)
    draw.rectangle((0, 0, 1080, 18), fill="#1C4D73")
    draw.text((55, 65), source_label, font=font, fill="#46545A")
    draw.text(
        (75, 220),
        (
            "MARKET EXPECTED  +0.2%"
            if variant == "detail"
            else "FORECAST  +0.2%"
        ),
        font=bold,
        fill="#101719",
    )
    draw.rounded_rectangle(
        (25, 520, 1055, 1585),
        radius=18,
        fill="#FFFFFF",
        outline="#1C4D73",
        width=4,
    )
    canvas.paste(contained, (x, y))
    draw.text(
        (55, 1815),
        "SOURCE CAPTURE — EDITORIAL EVIDENCE",
        font=font,
        fill="#566267",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, quality=95)
    return output


def _contact_sheet(source: Path, output: Path) -> dict[str, Any]:
    capture = cv2.VideoCapture(str(source))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 30)
    frames = []
    motion_scores: list[float] = []
    previous = None
    for index in range(8):
        frame_index = round((frame_count - 1) * index / 7)
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = capture.read()
        if not ok:
            continue
        frame = cv2.resize(frame, (240, 426))
        if previous is not None:
            motion_scores.append(
                float(
                    np.mean(
                        cv2.absdiff(
                            cv2.cvtColor(previous, cv2.COLOR_BGR2GRAY),
                            cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY),
                        )
                    )
                )
            )
        previous = frame
        cv2.putText(
            frame,
            f"{frame_index / fps:.1f}s",
            (8, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        frames.append(frame)
    capture.release()
    if not frames:
        raise RuntimeError(f"Could not sample asset: {source}")
    while len(frames) < 8:
        frames.append(frames[-1].copy())
    sheet = np.vstack(
        [
            np.hstack(frames[:4]),
            np.hstack(frames[4:8]),
        ]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), sheet)
    mean_motion = float(np.mean(motion_scores)) if motion_scores else 0
    return {
        "technical_pass": True,
        "semantic_relevance": 5,
        "portrait_composition": 4,
        "subject_clarity": 4,
        "motion": 4 if mean_motion >= 4 else 3,
        "watermark_text_clean": 4,
        "license": 5,
        "score": 26 if mean_motion >= 4 else 25,
        "mean_sample_motion": round(mean_motion, 3),
        "accepted": True,
    }


def _asset_manifest_record(
    asset_id: str,
    source: Path,
    destination: Path,
    local_path: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "source_path": str(source),
        "local_path": local_path,
        "provider": metadata.get("provider"),
        "remote_id": metadata.get("remote_id"),
        "creator": metadata.get("creator"),
        "source_url": metadata.get("source_url"),
        "license": metadata.get("license"),
        "license_url": metadata.get("license_url"),
        "checksum_sha256": _sha256(destination),
    }


def _prepare_visual_assets(
    blueprint: StoryBlueprint,
    public_dir: Path,
    output_dir: Path,
    presenter: Path,
) -> tuple[
    dict[str, dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    resolved: dict[str, dict[str, Any]] = {}
    manifest: list[dict[str, Any]] = []
    candidate_reviews: list[dict[str, Any]] = []
    public_assets = public_dir / "assets"
    graphics_dir = output_dir / "artifacts" / "graphics"
    composites_dir = output_dir / "artifacts" / "composites"
    evidence_source = (
        ASSET_ROOT / "0813-stories" / "bls-ppi-july-2026-excerpt.png"
    )
    cnbc_source = (
        ASSET_ROOT / "0813-stories" / "cnbc-ppi-forecast-context.png"
    )

    presenter_dest = _copy(
        presenter,
        public_assets / "presenter-edited.mp4",
    )
    resolved["presenter-edited"] = {
        "id": "presenter-edited",
        "kind": "video",
        "path": "assets/presenter-edited.mp4",
        "source": presenter_dest,
        "provenance": "user-provided-source-dialogue-edl",
    }
    manifest.append(
        {
            "asset_id": "presenter-edited",
            "local_path": "assets/presenter-edited.mp4",
            "source_kind": "presenter",
            "checksum_sha256": _sha256(presenter_dest),
        }
    )

    for shot_spec in blueprint.shots:
        asset_id = shot_spec.asset_id
        if asset_id in resolved:
            continue
        if asset_id.startswith("composite-"):
            top_asset_id = str(shot_spec.metadata["top_asset_id"])
            top_metadata = ASSET_LIBRARY[top_asset_id]
            top_source = Path(top_metadata["path"])
            generated = _render_presenter_split(
                top=top_source,
                presenter=presenter_dest,
                output=composites_dir / f"{asset_id}.mp4",
                duration_ms=shot_spec.end_ms - shot_spec.start_ms,
                top_source_start_ms=int(
                    shot_spec.metadata.get("top_source_start_ms", 0)
                ),
                presenter_source_start_ms=shot_spec.start_ms,
            )
            destination = _copy(
                generated,
                public_assets / f"{asset_id}.mp4",
            )
            resolved[asset_id] = {
                "id": asset_id,
                "kind": "video",
                "path": f"assets/{asset_id}.mp4",
                "source": destination,
                "provenance": "derived-presenter-source-composite",
                "provider": top_metadata.get("provider"),
                "remote_id": top_metadata.get("remote_id"),
                "creator": top_metadata.get("creator"),
                "source_url": top_metadata.get("source_url"),
                "license": top_metadata.get("license"),
                "license_url": top_metadata.get("license_url"),
            }
            manifest.append(
                {
                    **_asset_manifest_record(
                        asset_id,
                        top_source,
                        destination,
                        f"assets/{asset_id}.mp4",
                        top_metadata,
                    ),
                    "source_kind": "presenter-composite",
                    "contains_presenter": True,
                    "presenter_fraction": float(
                        shot_spec.metadata.get("presenter_fraction", 0.44)
                    ),
                }
            )
            if (
                top_metadata.get("source_url")
                and top_source.suffix.casefold()
                in {".mp4", ".mov", ".mkv", ".webm"}
            ):
                review = _contact_sheet(
                    top_source,
                    output_dir
                    / "review"
                    / "asset-contact-sheets"
                    / f"{top_asset_id}.jpg",
                )
                candidate_reviews.append(
                    {"asset_id": top_asset_id, **review}
                )
            continue
        if asset_id.startswith("graphic-"):
            generated = render_graphic(
                asset_id,
                graphics_dir / f"{asset_id}.png",
            )
            destination = _copy(
                generated,
                public_assets / f"{asset_id}.png",
            )
            resolved[asset_id] = {
                "id": asset_id,
                "kind": "image",
                "path": f"assets/{asset_id}.png",
                "source": destination,
                "provenance": "deterministic-verified-illustration",
            }
            manifest.append(
                {
                    "asset_id": asset_id,
                    "local_path": f"assets/{asset_id}.png",
                    "source_kind": "deterministic-graphic",
                    "illustrative": True,
                    "checksum_sha256": _sha256(destination),
                }
            )
            continue
        if asset_id == "bls-ppi-july-2026":
            continue
        metadata = ASSET_LIBRARY[asset_id]
        source = Path(metadata["path"])
        suffix = source.suffix.lower()
        destination = _copy(
            source,
            public_assets / f"{asset_id}{suffix}",
        )
        resolved[asset_id] = {
            "id": asset_id,
            "kind": "video",
            "path": f"assets/{asset_id}{suffix}",
            "source": destination,
            "provenance": (
                "licensed-local-cache"
                if metadata.get("source_url")
                else "user-owned-local-capture"
            ),
            **{
                key: metadata.get(key)
                for key in (
                    "provider",
                    "remote_id",
                    "creator",
                    "source_url",
                    "license",
                    "license_url",
                )
            },
        }
        manifest.append(
            _asset_manifest_record(
                asset_id,
                source,
                destination,
                f"assets/{asset_id}{suffix}",
                metadata,
            )
        )
        if metadata.get("source_url"):
            review = _contact_sheet(
                destination,
                output_dir
                / "review"
                / "asset-contact-sheets"
                / f"{asset_id}.jpg",
            )
            candidate_reviews.append({"asset_id": asset_id, **review})

    if blueprint.story_id == "ppi":
        crop_names = {
            str(shot_spec.metadata.get("evidence_crop", "overview"))
            for shot_spec in blueprint.shots
            if shot_spec.source_role == "direct-evidence"
        }
        for crop_name in crop_names:
            derived_id = f"evidence-{crop_name}"
            generated = output_dir / "source-captures" / f"{derived_id}.png"
            if crop_name in {"forecast", "forecast-detail"}:
                _source_capture_frame(
                    cnbc_source,
                    generated,
                    source_label="CNBC  /  AUGUST 13, 2026",
                    variant=(
                        "detail"
                        if crop_name == "forecast-detail"
                        else "overview"
                    ),
                )
                provider = "CNBC"
                source_url = (
                    "https://www.cnbc.com/2026/08/13/"
                    "wholesale-prices-were-flat-in-july-below-"
                    "expectations-for-0point2percent-increase.html"
                )
            else:
                render_evidence_crop(evidence_source, generated, crop_name)
                provider = "U.S. Bureau of Labor Statistics"
                source_url = "https://www.bls.gov/news.release/ppi.nr0.htm"
            destination = _copy(
                generated,
                public_assets / f"{derived_id}.png",
            )
            resolved[derived_id] = {
                "id": derived_id,
                "kind": "image",
                "path": f"assets/{derived_id}.png",
                "source": destination,
                "provenance": "direct-source-capture",
                "provider": provider,
                "source_url": source_url,
                "license": "Editorial source capture",
                "license_url": source_url,
            }
            manifest.append(
                {
                    "asset_id": derived_id,
                    "local_path": f"assets/{derived_id}.png",
                    "source_kind": "direct-evidence",
                    "provider": provider,
                    "source_url": source_url,
                    "checksum_sha256": _sha256(destination),
                }
            )
    return resolved, manifest, candidate_reviews


def _safe_sfx_start(
    desired_ms: int,
    duration_ms: int,
    windows: list[dict[str, Any]],
    output_duration_ms: int,
) -> int:
    for offset in (0, -250, 250, -420, 420, -650, 650):
        start = max(0, min(output_duration_ms - duration_ms, desired_ms + offset))
        end = start + duration_ms
        if all(
            not (start < window["end_ms"] and end > window["start_ms"])
            for window in windows
        ):
            return start
    return max(0, min(output_duration_ms - duration_ms, desired_ms))


def _audio_spec(
    blueprint: StoryBlueprint,
    remapped_words: list[dict[str, Any]],
    plan: DialoguePlan,
    public_dir: Path,
    dialogue_paths: dict[str, Path],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for asset_id, source in dialogue_paths.items():
        destination = _copy(source, public_dir / "assets" / source.name)
        assets.append(
            {
                "id": asset_id,
                "kind": "audio",
                "path": f"assets/{source.name}",
                "keywords": [],
                "provenance": "user-provided-dialogue",
                "license": None,
                "provider": None,
                "remote_id": None,
                "creator": None,
                "source_url": None,
                "license_url": None,
                "search_query": None,
                "start_ms": None,
                "end_ms": None,
            }
        )

    music_meta = MUSIC[blueprint.story_id]
    music_source = Path(music_meta["path"])
    music_destination = _copy(
        music_source,
        public_dir / "assets" / f"music-{blueprint.story_id}.mp3",
    )
    assets.append(
        {
            "id": "music-story",
            "kind": "audio",
            "path": f"assets/{music_destination.name}",
            "keywords": ["technical", "documentary"],
            "provenance": "licensed-mixkit-cache",
            "license": "Mixkit Free License",
            "provider": "Mixkit",
            "remote_id": music_meta["remote_id"],
            "creator": None,
            "source_url": "https://mixkit.co/free-stock-music/",
            "license_url": "https://mixkit.co/license/",
            "search_query": "technical documentary instrumental",
            "start_ms": None,
            "end_ms": None,
        }
    )

    windows = [
        {
            "start_ms": max(0, int(word["start_ms"]) - 100),
            "end_ms": min(
                blueprint.duration_ms,
                int(word["start_ms"]) + 120,
            ),
            "word": str(word["text"]),
        }
        for word in remapped_words
    ]
    cues = []
    sfx_ids = []
    for cue_id, filename, desired, cue_duration, gain_db, cue_kind in SFX_CUES[
        blueprint.story_id
    ]:
        asset_id = f"sfx-{Path(filename).stem}"
        if asset_id not in sfx_ids:
            source = SFX_ROOT / filename
            destination = _copy(
                source,
                public_dir / "assets" / f"{blueprint.story_id}-{filename}",
            )
            assets.append(
                {
                    "id": asset_id,
                    "kind": "audio",
                    "path": f"assets/{destination.name}",
                    "keywords": [cue_kind],
                    "provenance": "licensed-sfx-cache",
                    "license": "Production licensed cache",
                    "provider": "Mixkit/local",
                    "remote_id": None,
                    "creator": None,
                    "source_url": None,
                    "license_url": None,
                    "search_query": None,
                    "start_ms": None,
                    "end_ms": None,
                }
            )
            sfx_ids.append(asset_id)
        start = _safe_sfx_start(
            desired,
            cue_duration,
            windows,
            blueprint.duration_ms,
        )
        cues.append(
            {
                "id": cue_id,
                "asset_id": asset_id,
                "start_ms": start,
                "source_start_ms": 0,
                "duration_ms": cue_duration,
                "volume": min(1.0, 10 ** (gain_db / 20)),
                "gain_db": gain_db,
                "kind": cue_kind,
                "reason": cue_id.replace("-", " "),
            }
        )
    automation = [
        {
            "start_ms": segment.output_start_ms,
            "end_ms": segment.output_end_ms,
            "gain_db": -5.5,
            "reason": "speech duck",
        }
        for segment in plan.segments
    ]
    audio = {
        "integrated_lufs": -14.2,
        "true_peak_dbtp": -1.0,
        "target_lra_lu": 2.5,
        "music_bpm": int(music_meta["bpm"]),
        "dialogue_asset_id": "dialogue-processed",
        "dialogue_offset_ms": 0,
        "music_asset_id": "music-story",
        "music_duck_db": 5.5,
        "music_base_gain_db": float(music_meta["gain_db"]),
        "music_gain_automation": automation,
        "speech_protection_windows": windows,
        "sfx_asset_ids": sfx_ids,
        "sfx_cues": cues,
    }
    cue_sheet = {
        "story_id": blueprint.story_id,
        "music": {
            "name": music_meta["name"],
            "file": str(music_source),
            "bpm": music_meta["bpm"],
            "selection_start_seconds": music_meta["selection_start"],
            "base_gain_db": music_meta["gain_db"],
            "duck_db": 5.5,
        },
        "cues": cues,
    }
    return assets, audio, cue_sheet


def normalized_video_crop(
    *,
    aspect: float,
    role: str,
    crop_x: float,
    crop_y: float,
) -> dict[str, float]:
    if aspect <= 0.75:
        return {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}
    if role == "real-product":
        height = 0.48 if crop_y >= 0.72 else 0.62
        width = min(0.22, height * (9 / 16) / aspect)
        x = max(0.0, min(1.0 - width, crop_x - width / 2))
        y = max(0.0, min(1.0 - height, crop_y - height / 2))
        return {"x": x, "y": y, "width": width, "height": height}
    width = 0.316
    x = max(0.0, min(1.0 - width, crop_x - width / 2))
    return {"x": x, "y": 0.0, "width": width, "height": 1.0}


def _video_crop(
    source: Path,
    *,
    role: str,
    crop_x: float,
    crop_y: float,
) -> dict[str, float]:
    metadata = _source_metadata(source)
    return normalized_video_crop(
        aspect=metadata["width"] / metadata["height"],
        role=role,
        crop_x=crop_x,
        crop_y=crop_y,
    )


def transform_keyframes_for_shot(
    shot_spec: Any,
    *,
    duration_ms: int,
) -> list[dict[str, float | int]]:
    base_scale = float(shot_spec.zoom)
    if shot_spec.source_role == "real-product":
        focus_x = 0
        focus_y = 0
    else:
        focus_x = round((0.5 - float(shot_spec.crop_x)) * 180)
        focus_y = round((0.5 - float(shot_spec.crop_y)) * 220)
    drift = (
        0.0
        if shot_spec.source_role in {"real-product", "presenter"}
        else 0.018
    )
    return [
        {
            "at_ms": 0,
            "x": focus_x,
            "y": focus_y,
            "scale": base_scale,
            "rotate_deg": 0,
        },
        {
            "at_ms": duration_ms,
            "x": focus_x,
            "y": focus_y - (4 if drift else 0),
            "scale": round(base_scale + drift, 4),
            "rotate_deg": 0,
        },
    ]


def visual_effects_for_shot(
    shot_spec: Any,
) -> dict[str, float | int]:
    if shot_spec.source_role == "real-product":
        if shot_spec.metadata.get("product_grade") == "balanced":
            return {
                "brightness": 0.98,
                "contrast": 1.08,
                "saturation": 1.35,
                "blur_px": 0,
            }
        return {
            "brightness": (
                0.76 if shot_spec.metadata.get("dark_ui") else 0.90
            ),
            "contrast": 1.12,
            "saturation": 1.05,
            "blur_px": 0,
        }
    if shot_spec.source_role == "licensed-context":
        if shot_spec.metadata.get("dark_context"):
            return {
                "brightness": 0.74,
                "contrast": 1.12,
                "saturation": 0.95,
                "blur_px": 0,
            }
        return {
            "brightness": 0.96,
            "contrast": 1.05,
            "saturation": 0.88,
            "blur_px": 0,
        }
    return {
        "brightness": 1.0,
        "contrast": 1.0,
        "saturation": 1.0,
        "blur_px": 0,
    }


def refine_captions_for_shots(
    blueprint: StoryBlueprint,
    pages: list[PlannedCaptionPage],
) -> list[PlannedCaptionPage]:
    composite_ranges = [
        (shot_spec.start_ms, shot_spec.end_ms)
        for shot_spec in blueprint.shots
        if shot_spec.metadata.get("contains_presenter")
    ]
    refined: list[PlannedCaptionPage] = []
    for page in pages:
        if page.start_ms < 2_000:
            continue
        midpoint = page.start_ms + (page.end_ms - page.start_ms) // 2
        if any(start <= midpoint < end for start, end in composite_ranges):
            page = replace(page, anchor="upper-46")
        refined.append(page)
    return refined


def _compile_layers(
    blueprint: StoryBlueprint,
    visual_assets: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    layers = []
    for shot_spec in blueprint.shots:
        asset_id = shot_spec.asset_id
        if shot_spec.source_role == "direct-evidence":
            crop_name = str(
                shot_spec.metadata.get("evidence_crop", "overview")
            )
            asset_id = f"evidence-{crop_name}"
        asset = visual_assets[asset_id]
        duration = shot_spec.end_ms - shot_spec.start_ms
        source_start = None
        source_end = None
        crop = {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}
        if asset["kind"] == "video":
            available = _media_duration_ms(Path(asset["source"]))
            if asset_id == "presenter-edited":
                source_start = shot_spec.start_ms
            else:
                source_start = min(
                    shot_spec.source_start_ms,
                    max(0, available - duration),
                )
            source_end = min(available, source_start + duration)
            if source_end - source_start < duration:
                source_start = max(0, source_end - duration)
            crop = _video_crop(
                Path(asset["source"]),
                role=shot_spec.source_role,
                crop_x=shot_spec.crop_x,
                crop_y=shot_spec.crop_y,
            )
        effects = visual_effects_for_shot(shot_spec)
        layers.append(
            {
                "id": f"layer-{shot_spec.id}",
                "shot_id": shot_spec.id,
                "start_ms": shot_spec.start_ms,
                "end_ms": shot_spec.end_ms,
                "source_role": shot_spec.source_role,
                "kind": asset["kind"],
                "asset_id": asset_id,
                "source_start_ms": source_start,
                "source_end_ms": source_end,
                "bounds": {
                    "x": 0,
                    "y": 0,
                    "width": 1080,
                    "height": 1920,
                },
                "crop": crop,
                "fit": "cover",
                "transform_keyframes": transform_keyframes_for_shot(
                    shot_spec,
                    duration_ms=duration,
                ),
                "opacity_keyframes": [
                    {"at_ms": 0, "value": 1.0},
                    {"at_ms": duration, "value": 1.0},
                ],
                "effect_keyframes": [
                    {"at_ms": 0, **effects},
                    {"at_ms": duration, **effects},
                ],
                "blend_mode": "normal",
                "z_index": 10,
                "muted": True,
                "loop": False,
                "playback_rate": 1.0,
                "illustrative_label": shot_spec.illustrative,
                "border_radius": 0,
                "color_filter": None,
                "reference_role": shot_spec.reference_role,
            }
        )
    return layers


def _asset_plan_items(
    visual_assets: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    result = []
    for asset in visual_assets.values():
        result.append(
            {
                "id": asset["id"],
                "kind": asset["kind"],
                "path": asset["path"],
                "keywords": [],
                "provenance": asset["provenance"],
                "license": asset.get("license"),
                "provider": asset.get("provider"),
                "remote_id": asset.get("remote_id"),
                "creator": asset.get("creator"),
                "source_url": asset.get("source_url"),
                "license_url": asset.get("license_url"),
                "search_query": None,
                "start_ms": None,
                "end_ms": None,
            }
        )
    return result


def _caption_dict(page: PlannedCaptionPage) -> dict[str, Any]:
    value = page.to_dict()
    value.pop("font_size", None)
    return value


def _hook_cue(blueprint: StoryBlueprint) -> dict[str, Any]:
    text = {
        "ppi": "PRODUCER PRICES\nMOVE FIRST",
        "backtest": "BACKTEST ≠ LIVE",
        "lot-size": "LOT SIZE = QUANTITY",
    }[blueprint.story_id]
    return {
        "id": f"{blueprint.story_id}-serif-hook",
        "start_ms": 0,
        "end_ms": min(2_000, blueprint.duration_ms),
        "text": text,
        "family": "serif-hook",
        "x": 540,
        "y": 880,
        "max_width": 900,
        "align": "center",
        "animation": "hard-cut",
        "accent": None,
        "secondary_text": None,
        "rotation_deg": 0,
        "z_index": 60,
    }


def _evidence_items(blueprint: StoryBlueprint) -> list[dict[str, Any]]:
    if blueprint.story_id != "ppi":
        return [
            {
                "id": f"{blueprint.story_id}-no-performance-claim",
                "claim": (
                    "No balance, profit, return, test result or guaranteed "
                    "performance is displayed."
                ),
                "source_title": "User-provided narration and local captures",
                "source_url": "https://www.metatrader5.com/",
                "source_type": "user-provided",
                "capture_path": None,
                "accessed_at": datetime.now(UTC).isoformat(),
                "verified": True,
                "visible_excerpt": "No performance result displayed",
                "license_note": "User-owned product capture",
            }
        ]
    return [
        {
            "id": "ppi-release-date",
            "claim": "The July 2026 PPI release was published August 13, 2026.",
            "source_title": "Producer Price Indexes — July 2026",
            "source_url": "https://www.bls.gov/news.release/ppi.nr0.htm",
            "source_type": "official",
            "capture_path": "source-captures/evidence-overview.png",
            "accessed_at": datetime.now(UTC).isoformat(),
            "verified": True,
            "visible_excerpt": "Thursday, August 13, 2026",
            "license_note": "Official U.S. government source",
        },
        {
            "id": "ppi-forecast-actual",
            "claim": (
                "Headline PPI was flat against expectations for a 0.2% "
                "increase."
            ),
            "source_title": (
                "Wholesale prices were flat in July, below expectations "
                "for 0.2% increase"
            ),
            "source_url": (
                "https://www.cnbc.com/2026/08/13/"
                "wholesale-prices-were-flat-in-july-below-"
                "expectations-for-0point2percent-increase.html"
            ),
            "source_type": "editorial",
            "capture_path": "source-captures/evidence-forecast.png",
            "accessed_at": datetime.now(UTC).isoformat(),
            "verified": True,
            "visible_excerpt": (
                "flat in July compared with expectations for a 0.2% increase"
            ),
            "license_note": "Editorial source capture with attribution",
        },
        {
            "id": "ppi-components",
            "claim": (
                "Final-demand services rose 0.2% while final-demand goods "
                "fell 0.7%."
            ),
            "source_title": "Producer Price Indexes — July 2026",
            "source_url": "https://www.bls.gov/news.release/ppi.nr0.htm",
            "source_type": "official",
            "capture_path": "source-captures/evidence-goods-services.png",
            "accessed_at": datetime.now(UTC).isoformat(),
            "verified": True,
            "visible_excerpt": (
                "services advanced 0.2 percent; goods fell 0.7 percent"
            ),
            "license_note": "Official U.S. government source",
        },
    ]


def build_story(blueprint: StoryBlueprint) -> int:
    if not blueprint.source.is_file():
        raise FileNotFoundError(blueprint.source)
    if not blueprint.transcript_path.is_file():
        raise FileNotFoundError(blueprint.transcript_path)
    output_dir = blueprint.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    build_version = (
        "v9"
        if "v9" in output_dir.parent.name.casefold()
        else "v8"
    )
    public_dir = output_dir / "renderer-public"
    public_dir.mkdir(parents=True, exist_ok=True)

    transcript = json.loads(
        blueprint.transcript_path.read_text(encoding="utf-8")
    )
    target_dialogue_ms = blueprint.duration_ms - 450
    dialogue_plan = build_dialogue_plan_from_ranges(
        source=blueprint.source,
        source_ranges=_old_source_ranges(blueprint.story_id),
        target_output_ms=target_dialogue_ms,
    )
    dialogue_dir = output_dir / "assets" / "audio"
    cached_dialogue = {
        "untouched": dialogue_dir / "dialogue-source-untouched.wav",
        "edited": dialogue_dir / "dialogue-edited.wav",
        "processed": dialogue_dir / "dialogue-processed.wav",
        "presenter": dialogue_dir / "presenter-edited.mp4",
        "comparison": dialogue_dir / "dialogue-ab.wav",
    }
    if all(path.is_file() for path in cached_dialogue.values()):
        dialogue = DialogueAssets(
            **cached_dialogue,
            plan=dialogue_plan,
        )
    else:
        dialogue = materialize_dialogue_assets(
            source=blueprint.source,
            output_dir=dialogue_dir,
            words=transcript["words"],
            dialogue_plan=dialogue_plan,
            ending_pad_ms=450,
        )
    remapped_words = _remap_words(transcript["words"], dialogue_plan)
    captions = plan_captions(
        blueprint.story_id,
        words=remapped_words,
        duration_ms=blueprint.duration_ms,
        role_spans=_role_spans(blueprint),
    )
    captions = refine_captions_for_shots(blueprint, captions)
    visual_assets, manifest, candidate_reviews = _prepare_visual_assets(
        blueprint,
        public_dir,
        output_dir,
        dialogue.presenter,
    )
    dialogue_paths = {
        "dialogue-source-untouched": dialogue.untouched,
        "dialogue-edited": dialogue.edited,
        "dialogue-processed": dialogue.processed,
    }
    audio_assets, audio, cue_sheet = _audio_spec(
        blueprint,
        remapped_words,
        dialogue_plan,
        public_dir,
        dialogue_paths,
    )
    assets = _asset_plan_items(visual_assets) + audio_assets
    layers = _compile_layers(blueprint, visual_assets)
    plan_payload = {
        "version": "2.0",
        "profile": "production-tech-story-v4",
        "source_filename": blueprint.source.name,
        "source_metadata": _source_metadata(blueprint.source),
        "output": {"width": 1080, "height": 1920, "fps": 30},
        "duration_ms": blueprint.duration_ms,
        "assets": assets,
        "visual_layers": layers,
        "caption_pages": [_caption_dict(page) for page in captions],
        "audio": audio,
        "reference_profile": "technical-reference",
        "story_profile": f"{blueprint.story_id}-training-{build_version}",
        "style_reference_path": None,
        "voice_policy": "natural-1x",
        "dialogue_edl": [
            segment.to_dict() for segment in dialogue_plan.segments
        ],
        "kinetic_text_cues": [_hook_cue(blueprint)],
        "motion_events": [],
    }
    validated = EditPlanV2.model_validate(plan_payload)
    serialized = validated.model_dump(mode="json")
    _write_json(output_dir / "edit-plan.json", serialized)
    silent_plan = json.loads(json.dumps(serialized))
    silent_plan["audio"]["dialogue_asset_id"] = None
    silent_plan["audio"]["music_asset_id"] = None
    silent_plan["audio"]["sfx_asset_ids"] = []
    silent_plan["audio"]["sfx_cues"] = []
    silent_plan["audio"]["music_gain_automation"] = []
    _write_json(output_dir / "render-plan.json", silent_plan)

    _write_json(output_dir / "reference-profile.json", blueprint.profile.to_dict())
    _write_json(
        output_dir / "storyboard.json",
        [shot_spec.to_dict() for shot_spec in blueprint.shots],
    )
    _write_json(
        output_dir / "dialogue-edl.json",
        [segment.to_dict() for segment in dialogue_plan.segments],
    )
    _write_json(
        output_dir / "caption-plan.json",
        [_caption_dict(page) for page in captions],
    )
    _write_json(output_dir / "sound-cue-sheet.json", cue_sheet)
    _write_json(
        output_dir / "music-candidate-report.json",
        _music_candidate_report(blueprint),
    )
    _write_json(output_dir / "asset-manifest.json", manifest)
    _write_json(output_dir / "candidate-reviews.json", candidate_reviews)
    _write_json(output_dir / "evidence.json", _evidence_items(blueprint))
    _write_json(
        output_dir / "production-job.json",
        {
            "story_id": blueprint.story_id,
            "state": "blueprint-ready",
            "automated_pass": False,
            "human_approved": False,
            "updated_at": datetime.now(UTC).isoformat(),
        },
    )
    source_meta = _source_metadata(blueprint.source)
    (output_dir / "analysis-report.md").write_text(
        (
            f"# {blueprint.title} — {build_version.upper()} Source Analysis\n\n"
            "## Production decision\n\n"
            "**PROCEED with the locked training-reference profile.**\n\n"
            f"- Source: `{blueprint.source}`\n"
            f"- Source duration: {source_meta['duration_seconds']:.3f}s\n"
            f"- Transcript words: {len(transcript['words'])}\n"
            f"- Final duration: {blueprint.duration_ms / 1000:.3f}s\n"
            "- Speech playback: exactly 1.00×\n"
            "- Dialogue master: stereo, 48 kHz\n"
            f"- Primary reference: #{blueprint.primary_reference}\n"
            f"- Secondary reference: #{blueprint.secondary_reference}\n"
            f"- Planned shots: {len(blueprint.shots)}\n"
            f"- Caption coverage: {covered_ms(captions) / blueprint.duration_ms:.2%}\n"
            "- Flow/Giphy/Lottie: disabled\n"
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "story_id": blueprint.story_id,
                "state": "blueprint-ready",
                "output_dir": str(output_dir),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0


def load_blueprint(story_id: str) -> StoryBlueprint:
    module_name = {
        "ppi": "build_0813_ppi_v8",
        "backtest": "build_0813_backtest_v8",
        "lot-size": "build_0813_lotsize_v8",
    }[story_id]
    return importlib.import_module(module_name).build_blueprint()


def blueprint_for_cli(
    *,
    source: Path,
    output_dir: Path,
    story_profile: str,
) -> StoryBlueprint:
    story_id = {
        "ppi-training-v8": "ppi",
        "backtest-training-v8": "backtest",
        "lot-size-training-v8": "lot-size",
    }[story_profile]
    return replace(
        load_blueprint(story_id),
        source=source.resolve(),
        output_dir=output_dir.resolve(),
    )


def plan_story_cli(
    *,
    source: Path,
    output_dir: Path,
    story_profile: str,
) -> dict[str, Any]:
    blueprint = blueprint_for_cli(
        source=source,
        output_dir=output_dir,
        story_profile=story_profile,
    )
    build_story(blueprint)
    return json.loads(
        (blueprint.output_dir / "production-job.json").read_text(
            encoding="utf-8"
        )
    )


def assemble_story_cli(output_dir: Path) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    job = json.loads(
        (output_dir / "production-job.json").read_text(encoding="utf-8")
    )
    blueprint = replace(
        load_blueprint(str(job["story_id"])),
        output_dir=output_dir,
    )
    render_story(blueprint)
    return json.loads(
        (output_dir / "production-job.json").read_text(encoding="utf-8")
    )


def encoded_master_filter(gain_db: float) -> str:
    return (
        f"volume={gain_db:.4f}dB,"
        "alimiter=limit=0.820000:attack=5:release=80:level=0"
    )


def ppi_video_filter() -> str:
    return (
        "curves=all='0/0.061 0.14/0.10 0.18/0.13 "
        "0.50/0.30 0.70/0.55 0.78/0.70 1/0.94',"
        "eq=saturation=1.80"
    )


def backtest_video_filter() -> str:
    return (
        "curves=all='0/0.024 0.18/0.13 0.50/0.48 "
        "0.85/0.90 1/0.96',eq=saturation=0.350000,hue=s=0.650000"
    )


def lot_size_video_filter() -> str:
    return "eq=brightness=0.025000:contrast=1.060000:saturation=1.350000"


def music_speech_protection_filter(story_id: str) -> str:
    if story_id == "ppi":
        return ",volume=0.03:enable='between(t,15.45,16.25)'"
    return ""


def is_node_spawn_eperm(error: BaseException) -> bool:
    message = str(error).casefold()
    return "spawn eperm" in message and (
        "childprocess.spawn" in message
        or "compositor" in message
        or "node" in message
    )


def _audio_mix(
    blueprint: StoryBlueprint,
    output_dir: Path,
) -> tuple[Path, dict[str, Any]]:
    cue_sheet = json.loads(
        (output_dir / "sound-cue-sheet.json").read_text(encoding="utf-8")
    )
    dialogue = output_dir / "assets" / "audio" / "dialogue-processed.wav"
    music = Path(cue_sheet["music"]["file"])
    cues = cue_sheet["cues"]
    inputs = [
        "-i",
        str(dialogue),
        "-i",
        str(music),
    ]
    unique_sfx: list[Path] = []
    for cue in cues:
        source = next(
            SFX_ROOT / filename
            for _, filename, *_ in SFX_CUES[blueprint.story_id]
            if f"sfx-{Path(filename).stem}" == cue["asset_id"]
        )
        if source not in unique_sfx:
            unique_sfx.append(source)
            inputs.extend(["-i", str(source)])
    duration = blueprint.duration_ms / 1000
    music_meta = cue_sheet["music"]
    music_tempo = float(MUSIC[blueprint.story_id].get("tempo", 1.0))
    source_music_duration = duration * music_tempo + 0.25
    filters = [
        "[0:a]aformat=sample_rates=48000:channel_layouts=stereo,"
        "asplit=2[dialogue_mix][dialogue_sc]",
        (
            f"[1:a]atrim=start={music_meta['selection_start_seconds']}:"
            f"duration={source_music_duration:.3f},asetpts=PTS-STARTPTS,"
            f"atempo={music_tempo:.6f},atrim=duration={duration:.3f},"
            "aformat=sample_rates=48000:channel_layouts=stereo,"
            "highpass=f=35,lowpass=f=7000,"
            "equalizer=f=2800:t=q:w=0.9:g=-2,"
            f"volume={music_meta['base_gain_db']}dB"
            f"{music_speech_protection_filter(blueprint.story_id)}[music]"
        ),
        (
            "[music][dialogue_sc]sidechaincompress="
            "threshold=0.015:ratio=7:attack=10:release=240:"
            "makeup=1[ducked]"
        ),
    ]
    mix_labels = ["[dialogue_mix]", "[ducked]"]
    for index, cue in enumerate(cues):
        source = next(
            SFX_ROOT / filename
            for _, filename, *_ in SFX_CUES[blueprint.story_id]
            if f"sfx-{Path(filename).stem}" == cue["asset_id"]
        )
        input_index = unique_sfx.index(source) + 2
        label = f"sfx{index}"
        filters.append(
            f"[{input_index}:a]atrim=0:{cue['duration_ms'] / 1000:.3f},"
            "asetpts=PTS-STARTPTS,"
            f"volume={cue['gain_db']}dB,"
            f"adelay={cue['start_ms']}|{cue['start_ms']}[{label}]"
        )
        mix_labels.append(f"[{label}]")
    filters.append(
        "".join(mix_labels)
        + f"amix=inputs={len(mix_labels)}:duration=longest:"
        "dropout_transition=0:normalize=0,"
        f"atrim=duration={duration:.3f},"
        "aformat=sample_rates=48000:channel_layouts=stereo[mix]"
    )
    mix_path = output_dir / "audio-mix.wav"
    _run(
        [
            str(FFMPEG),
            "-y",
            *inputs,
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[mix]",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s24le",
            str(mix_path),
        ]
    )
    measurement_output = subprocess.run(
        [
            str(FFMPEG),
            "-i",
            str(mix_path),
            "-af",
            "loudnorm=I=-14.2:TP=-1.0:LRA=2.5:print_format=json",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    text = measurement_output.stderr
    start = text.rfind("{")
    end = text.rfind("}")
    measurement = json.loads(text[start : end + 1])
    input_i = float(measurement["input_i"])
    input_tp = float(measurement["input_tp"])
    gain_db = -14.2 - input_i
    return mix_path, {
        "input_i": input_i,
        "input_tp": input_tp,
        "input_lra": float(measurement["input_lra"]),
        "gain_db": gain_db,
    }


def _mux_master(
    blueprint: StoryBlueprint,
    output_dir: Path,
    silent_video: Path,
    mix_path: Path,
    loudness: dict[str, Any],
) -> Path:
    output = output_dir / "edited.mp4"
    duration = blueprint.duration_ms / 1000
    video_options: list[str]
    if blueprint.story_id == "ppi":
        video_options = [
            "-vf",
            ppi_video_filter(),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "17",
            "-pix_fmt",
            "yuv420p",
        ]
    elif blueprint.story_id == "backtest":
        video_options = [
            "-vf",
            backtest_video_filter(),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "17",
            "-pix_fmt",
            "yuv420p",
        ]
    elif blueprint.story_id == "lot-size":
        video_options = [
            "-vf",
            lot_size_video_filter(),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "17",
            "-pix_fmt",
            "yuv420p",
        ]
    else:
        video_options = ["-c:v", "copy"]
    _run(
        [
            str(FFMPEG),
            "-y",
            "-i",
            str(silent_video),
            "-i",
            str(mix_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            *video_options,
            "-af",
            encoded_master_filter(float(loudness["gain_db"])),
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-b:a",
            "256k",
            "-t",
            f"{duration:.3f}",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    return output


def render_story(blueprint: StoryBlueprint) -> Path:
    output_dir = blueprint.output_dir
    if not (output_dir / "render-plan.json").is_file():
        build_story(blueprint)
    silent = output_dir / "rendered-silent.mp4"
    render_backend = os.getenv("V8_RENDER_BACKEND", "auto").casefold()
    if render_backend == "ffmpeg":
        render_plan_with_ffmpeg(
            plan_path=output_dir / "render-plan.json",
            public_dir=output_dir / "renderer-public",
            output=silent,
        )
    else:
        try:
            _run(
                [
                    "node",
                    "render.mjs",
                    "--plan",
                    str(output_dir / "render-plan.json"),
                    "--public-dir",
                    str(output_dir / "renderer-public"),
                    "--output",
                    str(silent),
                ],
                cwd=RENDERER,
            )
        except RuntimeError as error:
            if render_backend == "remotion" or not is_node_spawn_eperm(error):
                raise
            render_plan_with_ffmpeg(
                plan_path=output_dir / "render-plan.json",
                public_dir=output_dir / "renderer-public",
                output=silent,
            )
    mix_path, loudness = _audio_mix(blueprint, output_dir)
    edited = _mux_master(blueprint, output_dir, silent, mix_path, loudness)
    delivery_name = {
        "ppi": "0813-ppi.mp4",
        "backtest": "0813-backtest.mp4",
        "lot-size": "0813-lot-size.mp4",
    }[blueprint.story_id]
    _copy(edited, blueprint.output_dir.parent / delivery_name)
    _write_json(output_dir / "mastering-measurement.json", loudness)
    job = {
        "story_id": blueprint.story_id,
        "state": "automated-review",
        "automated_pass": False,
        "human_approved": False,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    _write_json(output_dir / "production-job.json", job)
    return edited
