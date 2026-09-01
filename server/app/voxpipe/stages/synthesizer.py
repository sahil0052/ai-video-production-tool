from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import List, Dict
from imageio_ffmpeg import get_ffmpeg_exe

from app.voxpipe.models.edit_plan import VoxEditPlan
from app.voxpipe.core.encode_standards import (
    get_canonical_output_path,
    get_job_deliverable_dir,
    get_broadcast_video_args,
    get_broadcast_audio_args,
    WORKSPACE_ROOT,
)
from app.voxpipe.core.captions_renderer import generate_emphasis_punchline_captions

logger = logging.getLogger("voxpipe.synthesizer")
FFMPEG = get_ffmpeg_exe()
ASSETS_SFX_DIR = WORKSPACE_ROOT / "storage" / "assets" / "viral_sfx_library"
PROCEDURAL_SFX_DIR = WORKSPACE_ROOT / "storage" / "deliverables" / "0824-certified-master" / "assets" / "sfx"


def synthesize_master_video(plan: VoxEditPlan) -> Path:
    """Renders the master 1080x1920 video with consistent vocal leveling, full-screen top visuals, and punchline captions."""
    job_dir = get_job_deliverable_dir(plan.job_id)
    output_mp4 = get_canonical_output_path(plan.job_id)
    source_video = Path(plan.source_video)

    top_segments_dir = job_dir / "top_segments"
    top_segments_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Synthesizing {len(plan.beats)} Macro Pillars for job {plan.job_id} into {output_mp4}...")

    # 1. Build Top Track Segments (1080x960 Edge-to-Edge Full Screen)
    top_seg_files: List[Path] = []
    full_explainers: List[dict] = []

    for idx, b in enumerate(plan.beats):
        p = top_segments_dir / f"top_seg_{idx:02d}.mp4"
        top_seg_files.append(p)
        dur = b.duration

        if b.layout == "FULL_EXPLAINER" and b.asset_path:
            full_explainers.append({
                "beat_id": b.id,
                "start": b.start,
                "end": b.end,
                "asset_path": Path(b.asset_path),
            })

        if b.asset_path:
            asset_p = Path(b.asset_path)
            if asset_p.suffix.lower() == ".mp4":
                fc = "[0:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,fps=30,setpts=PTS-STARTPTS[out]"
                cmd = [FFMPEG, "-y", "-stream_loop", "-1", "-t", str(dur), "-i", str(asset_p), "-filter_complex", fc, "-map", "[out]", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p", str(p)]
            else:
                fc = f"loop=loop=-1:size=1:start=0,scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,fps=30,trim=duration={dur},setpts=PTS-STARTPTS[out]"
                cmd = [FFMPEG, "-y", "-i", str(asset_p), "-filter_complex", fc, "-map", "[out]", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p", str(p)]
        else:
            fc = f"color=c=black:s=1080x960:d={dur}:r=30[out]"
            cmd = [FFMPEG, "-y", "-filter_complex", fc, "-map", "[out]", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p", str(p)]

        subprocess.run(cmd, check=True, capture_output=True)

    # Concat Top Track
    concat_txt = top_segments_dir / "concat_top.txt"
    concat_txt.write_text("\n".join([f"file '{s.name}'" for s in top_seg_files]) + "\n", encoding="ascii")
    top_track_video = job_dir / "top_flow_track.mp4"
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", str(top_track_video)], check=True)

    # 2. Build High-Impact Emphasis Captions (ASS) - Main punchlines only
    ass_subtitles_path = job_dir / "kinetic_captions.ass"
    generate_emphasis_punchline_captions(plan, ass_subtitles_path)

    # 3. Build Audio Mix with TRUE ZERO-ATTENUATION AUDIO MIXING & LEVELING
    sfx_args: List[str] = ["-i", str(source_video)]
    sfx_inputs_count = 1

    resolved_sfx_inputs: List[Path] = []
    for sfx in plan.sfx_tracks:
        sfx_path = ASSETS_SFX_DIR / sfx.category / sfx.name
        if not sfx_path.exists():
            sfx_path = PROCEDURAL_SFX_DIR / sfx.name
        if not sfx_path.exists():
            sfx_path = ASSETS_SFX_DIR / "paper_and_cards" / "card-slide-1.mp3"
        resolved_sfx_inputs.append(sfx_path)

    unique_sfx = list(dict.fromkeys(resolved_sfx_inputs))
    sfx_to_idx: Dict[str, int] = {}
    for s_file in unique_sfx:
        sfx_args.extend(["-i", str(s_file)])
        sfx_to_idx[str(s_file)] = sfx_inputs_count
        sfx_inputs_count += 1

    # Dialogue compression to eliminate soft starts
    audio_filter_lines = [
        "[0:a]acompressor=threshold=-20dB:ratio=3.5:attack=15:release=150,volume=1.0[a_dialogue];"
    ]

    sfx_submix_labels = []
    for idx, (sfx, s_file) in enumerate(zip(plan.sfx_tracks, resolved_sfx_inputs)):
        in_idx = sfx_to_idx[str(s_file)]
        delay_ms = int(sfx.timestamp * 1000)
        a_label = f"a_sfx_{idx}"
        audio_filter_lines.append(f"[{in_idx}:a]adelay={delay_ms}|{delay_ms},volume={sfx.volume}[{a_label}];")
        sfx_submix_labels.append(f"[{a_label}]")

    if sfx_submix_labels:
        audio_filter_lines.append(f"{''.join(sfx_submix_labels)}amix=inputs={len(sfx_submix_labels)}:normalize=0:dropout_transition=0[sfx_bed];")
        # Overlay dialogue + sfx bed without dividing dialogue volume
        audio_filter_lines.append("[a_dialogue][sfx_bed]amix=inputs=2:normalize=0:duration=first[a_combined];")
        audio_filter_lines.append("[a_combined]loudnorm=I=-14.0:TP=-1.5:LRA=7.0[a_final]")
    else:
        audio_filter_lines.append("[a_dialogue]loudnorm=I=-14.0:TP=-1.5:LRA=7.0[a_final]")

    master_audio_track = job_dir / "master_audio_track.wav"
    mix_cmd = [
        FFMPEG, "-y",
        *sfx_args,
        "-filter_complex", "".join(audio_filter_lines),
        "-map", "[a_final]",
        "-c:a", "pcm_s16le",
        "-ar", "48000",
        "-t", f"{plan.duration:.2f}",
        str(master_audio_track)
    ]
    subprocess.run(mix_cmd, check=True)
    logger.info(f"Master Audio Track Mixed & Leveled: {master_audio_track}")

    # 4. Assemble Final Video (Snug Presenter Framing y=320, Full Edge-to-Edge Top)
    input_args: List[str] = [
        "-i", str(source_video),        # 0: Continuous Presenter (0ms Lip Sync Anchor)
        "-i", str(top_track_video),     # 1: Top Track
        "-i", str(master_audio_track),  # 2: Master Audio Track
    ]
    input_count = 3

    exp_stream_map: Dict[str, int] = {}
    for exp in full_explainers:
        exp_path_str = str(exp["asset_path"])
        if exp_path_str not in exp_stream_map:
            if Path(exp_path_str).suffix.lower() == ".mp4":
                input_args.extend(["-stream_loop", "-1", "-i", exp_path_str])
            else:
                input_args.extend(["-i", exp_path_str])
            exp_stream_map[exp_path_str] = input_count
            input_count += 1

    crop_y = 160 if ("0831 (1)" in plan.source_video or "0831_1" in plan.job_id.lower() or "nishahomes" in plan.job_id.lower()) else 320
    filter_lines = [
        f"[0:v]scale=1080:1920,crop=1080:960:0:{crop_y},fps=30[char_bot];",
    ]
    has_full_char = any(b.layout == "FULL_CHARACTER" for b in plan.beats)
    if has_full_char:
        filter_lines.append("[0:v]scale=1200:2133,crop=1080:1920:60:120,fps=30[char_full];")

    filter_lines.extend([
        "[1:v]scale=1080:960,fps=30[top_track];",
        "[top_track][char_bot]vstack=inputs=2[raw_split];",
        "[raw_split]drawbox=x=0:y=958:w=1080:h=4:color=#1A1A1A@0.85:t=fill[base_split];",
    ])

    curr_stream = "base_split"
    step_num = 1

    for b in plan.beats:
        if b.layout == "FULL_CHARACTER":
            next_stream = f"s{step_num}"
            filter_lines.append(f"[{curr_stream}][char_full]overlay=0:0:enable='between(t,{b.start:.2f},{b.end:.2f})'[{next_stream}];")
            curr_stream = next_stream
            step_num += 1
        elif b.layout == "FULL_EXPLAINER" and b.asset_path:
            exp_input_idx = exp_stream_map[str(b.asset_path)]
            scaled_exp = f"exp_{step_num}"
            filter_lines.append(f"[{exp_input_idx}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setpts=PTS-STARTPTS[{scaled_exp}];")
            next_stream = f"s{step_num}"
            filter_lines.append(f"[{curr_stream}][{scaled_exp}]overlay=0:0:enable='between(t,{b.start:.2f},{b.end:.2f})'[{next_stream}];")
            curr_stream = next_stream
            step_num += 1

    # Studio Color Grading
    graded_stream = "v_graded"
    filter_lines.append(f"[{curr_stream}]eq=contrast=1.06:brightness=0.01:saturation=1.10[{graded_stream}];")

    # Emphasis Punchline Captions Overlay
    if ass_subtitles_path.exists():
        ass_escaped = str(ass_subtitles_path).replace("\\", "/").replace(":", "\\:")
        filter_lines.append(f"[{graded_stream}]ass='{ass_escaped}'[v_out];")
    else:
        filter_lines.append(f"[{graded_stream}]null[v_out];")

    full_fc = "".join(filter_lines)

    final_cmd = [
        FFMPEG, "-y",
        *input_args,
        "-filter_complex", full_fc,
        "-map", "[v_out]",
        "-map", "2:a",
        *get_broadcast_video_args(),
        *get_broadcast_audio_args(),
        "-t", f"{plan.duration:.2f}",
        str(output_mp4),
    ]

    subprocess.run(final_cmd, check=True)
    logger.info(f"Synthesized Master Deliverable: {output_mp4} ({output_mp4.stat().st_size / (1024*1024):.2f} MB)")
    return output_mp4
