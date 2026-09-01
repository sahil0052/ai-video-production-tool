from pathlib import Path
import wave

import numpy as np

from app.models import (
    AssetRef,
    AudioPlan,
    GainAutomation,
    SfxCue,
    SpeechProtectionWindow,
    TranscriptSegment,
)

_SAMPLE_RATE = 48_000

_CUE_TEMPLATES = [
    (
        "generated-hook-impact",
        "impact",
        0.38,
        "Layered hook impact on the opening product/presenter reveal.",
    ),
    (
        "generated-air-whoosh",
        "whoosh",
        0.22,
        "Short air sweep supporting the hook headline reveal.",
    ),
    (
        "generated-ui-click",
        "click",
        0.20,
        "Dry interface click on the MetaEditor boot action.",
    ),
    (
        "generated-code-tick",
        "click",
        0.15,
        "Quiet code tick on a meaningful rule-line highlight.",
    ),
    (
        "generated-label-snap",
        "notification",
        0.22,
        "Short label snap when Expert Advisor is identified.",
    ),
    (
        "generated-ui-click",
        "click",
        0.17,
        "Restrained click on the brief EA presenter reset.",
    ),
    (
        "generated-reverse-riser",
        "riser",
        0.20,
        "Reverse suction into the wrong-rules question.",
    ),
    (
        "generated-paper-scroll",
        "whoosh",
        0.14,
        "Quiet paper/trackpad texture tied to the visible source-page scroll.",
    ),
    (
        "generated-number-impact",
        "impact",
        0.25,
        "Controlled mid impact when the verified 110,000 excerpt lands.",
    ),
    (
        "generated-tonal-drop",
        "impact",
        0.21,
        "Short tonal fall on the story's risk turn.",
    ),
    (
        "generated-tension-riser",
        "riser",
        0.17,
        "Low-level tension layer while the risk control increases.",
    ),
    (
        "generated-reversal-drop",
        "whoosh",
        0.22,
        "Descending reversal synchronized to the upside-down turn.",
    ),
    (
        "generated-product-click",
        "click",
        0.18,
        "Motivated product click when the demonstration CTA begins.",
    ),
]


def build_audio_automation(
    segments: list[TranscriptSegment],
    *,
    duck_db: float,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    words = [
        word
        for segment in segments
        for word in segment.words
        if word.end > word.start
    ]
    if not words:
        return [], []

    speech_ranges: list[tuple[int, int]] = []
    for segment in segments:
        valid_words = [
            word for word in segment.words if word.end > word.start
        ]
        if not valid_words:
            continue
        start_ms = round(valid_words[0].start * 1000)
        end_ms = round(valid_words[-1].end * 1000)
        if speech_ranges and start_ms - speech_ranges[-1][1] <= 120:
            speech_ranges[-1] = (
                speech_ranges[-1][0],
                max(speech_ranges[-1][1], end_ms),
            )
        else:
            speech_ranges.append((start_ms, end_ms))

    gain = [
        GainAutomation(
            start_ms=start_ms,
            end_ms=end_ms,
            gain_db=-abs(float(duck_db)),
            reason="dialogue duck",
        ).model_dump(mode="json")
        for start_ms, end_ms in speech_ranges
    ]
    protected = [
        SpeechProtectionWindow(
            start_ms=max(0, round(word.start * 1000) - 100),
            end_ms=round(word.start * 1000) + 120,
            word=word.text,
        ).model_dump(mode="json")
        for word in words
    ]
    return gain, protected


def generate_sound_design(
    work_dir: Path,
    *,
    duration_ms: int,
    emphasis_times_ms: list[int],
    speech_segments: list[TranscriptSegment] | None = None,
) -> tuple[list[AssetRef], AudioPlan]:
    sound_dir = work_dir / "sound-library"
    sound_dir.mkdir(parents=True, exist_ok=True)

    music_path = sound_dir / "reference-10-micro-score.wav"
    effect_specs = [
        (
            "generated-hook-impact",
            sound_dir / "hook-impact.wav",
            _impact(low_start_hz=94, duration=0.34, seed=11),
            ["impact", "hook", "layered"],
        ),
        (
            "generated-air-whoosh",
            sound_dir / "air-whoosh.wav",
            _whoosh(duration=0.20, reverse=False, seed=12),
            ["whoosh", "air", "headline"],
        ),
        (
            "generated-ui-click",
            sound_dir / "ui-click.wav",
            _click(frequency_hz=1580, duration=0.070),
            ["click", "ui", "dry"],
        ),
        (
            "generated-code-tick",
            sound_dir / "code-tick.wav",
            _click(frequency_hz=2320, duration=0.045),
            ["click", "code", "tick"],
        ),
        (
            "generated-label-snap",
            sound_dir / "label-snap.wav",
            _label_snap(),
            ["notification", "label", "snap"],
        ),
        (
            "generated-reverse-riser",
            sound_dir / "reverse-riser.wav",
            _whoosh(duration=0.72, reverse=True, seed=13),
            ["riser", "reverse", "transition"],
        ),
        (
            "generated-paper-scroll",
            sound_dir / "paper-scroll.wav",
            _paper_scroll(),
            ["paper", "scroll", "evidence"],
        ),
        (
            "generated-number-impact",
            sound_dir / "number-impact.wav",
            _impact(low_start_hz=132, duration=0.22, seed=14),
            ["impact", "number", "evidence"],
        ),
        (
            "generated-tonal-drop",
            sound_dir / "tonal-drop.wav",
            _tonal_drop(duration=0.48, start_hz=410, end_hz=118),
            ["impact", "tonal", "risk"],
        ),
        (
            "generated-tension-riser",
            sound_dir / "tension-riser.wav",
            _tension_riser(),
            ["riser", "tension", "risk"],
        ),
        (
            "generated-reversal-drop",
            sound_dir / "reversal-drop.wav",
            _reversal_drop(),
            ["whoosh", "reversal", "descending"],
        ),
        (
            "generated-product-click",
            sound_dir / "product-click.wav",
            _click(frequency_hz=1180, duration=0.085),
            ["click", "product", "demo"],
        ),
    ]

    _write_wav(
        music_path,
        _music_score(max(duration_ms, 1) / 1000),
    )
    for _asset_id, path, samples, _keywords in effect_specs:
        _write_wav(path, samples)

    assets = [
        _audio_asset(
            "generated-music",
            music_path,
            ["tech", "music", "120bpm", "evolving", "reference-10"],
        ),
        *[
            _audio_asset(asset_id, path, keywords)
            for asset_id, path, _samples, keywords in effect_specs
        ],
    ]

    gain_payload, protection_payload = build_audio_automation(
        speech_segments or [],
        duck_db=6,
    )
    protection_windows = [
        SpeechProtectionWindow.model_validate(item)
        for item in protection_payload
    ]
    effect_durations = {
        asset_id: max(
            1,
            round(samples.shape[0] / _SAMPLE_RATE * 1000),
        )
        for asset_id, _path, samples, _keywords in effect_specs
    }
    cue_times = [
        time_ms
        for time_ms in sorted(set(emphasis_times_ms))
        if 0 <= time_ms < duration_ms
    ][: len(_CUE_TEMPLATES)]
    cues: list[SfxCue] = []
    for index, (time_ms, template) in enumerate(
        zip(cue_times, _CUE_TEMPLATES, strict=False)
    ):
        cue_duration_ms = effect_durations[template[0]]
        safe_time = _next_speech_safe_time(
            requested_ms=time_ms,
            duration_ms=cue_duration_ms,
            protection_windows=protection_windows,
            output_duration_ms=duration_ms,
        )
        if safe_time is None:
            continue
        cues.append(
            SfxCue(
                id=f"sfx-{index + 1:02d}",
                asset_id=template[0],
                start_ms=safe_time,
                duration_ms=cue_duration_ms,
                kind=template[1],
                volume=template[2],
                gain_db=-15,
                reason=template[3],
            )
        )
    sfx_asset_ids = list(dict.fromkeys(cue.asset_id for cue in cues))
    return assets, AudioPlan(
        music_asset_id="generated-music",
        music_gain_automation=[
            GainAutomation.model_validate(item)
            for item in gain_payload
        ],
        speech_protection_windows=protection_windows,
        sfx_asset_ids=sfx_asset_ids,
        sfx_cues=cues,
    )


def _next_speech_safe_time(
    *,
    requested_ms: int,
    duration_ms: int,
    protection_windows: list[SpeechProtectionWindow],
    output_duration_ms: int,
) -> int | None:
    candidate = max(0, requested_ms)
    for _attempt in range(len(protection_windows) + 1):
        collision = next(
            (
                window
                for window in protection_windows
                if candidate < window.end_ms
                and candidate + duration_ms > window.start_ms
            ),
            None,
        )
        if collision is None:
            return (
                candidate
                if candidate + duration_ms <= output_duration_ms
                else None
            )
        candidate = collision.end_ms
    return None


def music_sections(duration_ms: int) -> list[dict[str, object]]:
    sections = [
        (0, 4_000, "hook", "impact, filtered pulse, restrained sub"),
        (4_000, 12_000, "code-build", "pulse, ticks, upper arpeggio"),
        (12_000, 16_000, "question", "thinned pad and reverse texture"),
        (16_000, 24_000, "evidence", "controlled lift and brighter pulse"),
        (24_000, 32_000, "risk", "tension rise followed by tonal resolution"),
        (32_000, 40_000, "cta", "lighter percussion and resolved harmony"),
        (40_000, duration_ms, "tail", "short controlled musical release"),
    ]
    return [
        {
            "start_ms": start,
            "end_ms": min(end, duration_ms),
            "role": role,
            "change": change,
        }
        for start, end, role, change in sections
        if start < duration_ms and min(end, duration_ms) > start
    ]


def _audio_asset(asset_id: str, path: Path, keywords: list[str]) -> AssetRef:
    return AssetRef(
        id=asset_id,
        kind="audio",
        path=str(path.resolve()),
        keywords=keywords,
        provenance="generated-original",
        license="Original procedural audio",
        provider="Cutline local synthesis",
    )


def _music_score(duration_seconds: float) -> np.ndarray:
    frame_count = max(1, round(duration_seconds * _SAMPLE_RATE))
    time = np.arange(frame_count, dtype=np.float64) / _SAMPLE_RATE
    left = np.zeros(frame_count, dtype=np.float64)
    right = np.zeros(frame_count, dtype=np.float64)
    rng = np.random.default_rng(20260806)

    sections = [
        (0.0, 4.0, 110.0, 0.52, 0),
        (4.0, 12.0, 123.47, 0.68, 1),
        (12.0, 16.0, 98.0, 0.38, 2),
        (16.0, 24.0, 130.81, 0.62, 3),
        (24.0, 32.0, 103.83, 0.58, 4),
        (32.0, 40.0, 146.83, 0.54, 5),
        (40.0, duration_seconds, 130.81, 0.34, 6),
    ]
    for start, nominal_end, root, energy, variation in sections:
        end = min(duration_seconds, nominal_end)
        if end <= start:
            continue
        active = (time >= start) & (time < end)
        local = time[active] - start
        section_duration = end - start
        release_seconds = (
            0.012
            if abs(end - duration_seconds) < 1e-6
            else 0.22
        )
        edge = np.minimum(
            np.clip(local / 0.16, 0, 1),
            np.clip(
                (section_duration - local) / release_seconds,
                0,
                1,
            ),
        )
        chord_ratios = (
            (1.0, 1.25, 1.5)
            if variation not in {2, 4}
            else (1.0, 1.2, 1.498)
        )
        pad = sum(
            np.sin(
                2 * np.pi * root * ratio * local
                + variation * 0.19 * index
            )
            for index, ratio in enumerate(chord_ratios)
        ) / len(chord_ratios)
        shimmer = np.sin(
            2 * np.pi * root * (2.0 + 0.125 * (variation % 3)) * local
            + 0.35,
        )
        left[active] += edge * energy * (0.022 * pad + 0.006 * shimmer)
        right[active] += edge * energy * (
            0.021 * np.roll(pad, min(variation + 1, pad.size - 1))
            + 0.006 * shimmer
        )

    beat_interval = 0.5
    for beat_index, beat in enumerate(
        np.arange(0, duration_seconds, beat_interval)
    ):
        section_index = min(6, int(beat // 4))
        local = time - beat
        active = (local >= 0) & (local < 0.18)
        if np.any(active):
            envelope = np.exp(-local[active] * (21 + section_index))
            frequency = 112 + section_index * 5
            pulse = (
                0.052
                * np.sin(2 * np.pi * frequency * local[active])
                * envelope
            )
            left[active] += pulse
            right[active] += pulse * 0.96

        if beat_index % 2 == (section_index % 2):
            tick_start = beat + 0.25
            tick_local = time - tick_start
            tick_active = (tick_local >= 0) & (tick_local < 0.052)
            if np.any(tick_active):
                noise = rng.standard_normal(np.count_nonzero(tick_active))
                tick = (
                    noise
                    * np.exp(-tick_local[tick_active] * 74)
                    * (0.010 + section_index * 0.0007)
                )
                left[tick_active] += tick
                right[tick_active] -= tick * 0.72

        if section_index in {1, 3, 5} and beat_index % 4 == 2:
            note_start = beat + 0.08
            note_local = time - note_start
            note_active = (note_local >= 0) & (note_local < 0.22)
            if np.any(note_active):
                note_frequency = 660 + section_index * 42
                note = (
                    0.018
                    * np.sin(2 * np.pi * note_frequency * note_local[note_active])
                    * np.exp(-note_local[note_active] * 18)
                )
                left[note_active] += note * 0.82
                right[note_active] += note

    fade_in_frames = min(frame_count, round(_SAMPLE_RATE * 0.10))
    fade_out_frames = min(frame_count, round(_SAMPLE_RATE * 0.012))
    left[:fade_in_frames] *= np.linspace(0, 1, fade_in_frames)
    right[:fade_in_frames] *= np.linspace(0, 1, fade_in_frames)
    left[-fade_out_frames:] *= np.linspace(1, 0, fade_out_frames)
    right[-fade_out_frames:] *= np.linspace(1, 0, fade_out_frames)
    return _normalize(np.column_stack([left, right]), peak=0.54)


def _impact(
    *,
    low_start_hz: float,
    duration: float,
    seed: int,
) -> np.ndarray:
    time = np.arange(round(duration * _SAMPLE_RATE)) / _SAMPLE_RATE
    envelope = np.exp(-time * 13)
    phase = 2 * np.pi * (
        low_start_hz * time - (low_start_hz * 0.34) * time**2
    )
    body = np.sin(phase) * envelope
    mid = np.sin(2 * np.pi * 226 * time) * np.exp(-time * 24)
    noise = (
        np.random.default_rng(seed).standard_normal(time.size)
        * np.exp(-time * 38)
    )
    mono = 0.56 * body + 0.20 * mid + 0.075 * noise
    return _normalize(np.column_stack([mono, mono * 0.97]), peak=0.72)


def _whoosh(
    *,
    duration: float,
    reverse: bool,
    seed: int,
) -> np.ndarray:
    time = np.arange(round(duration * _SAMPLE_RATE)) / _SAMPLE_RATE
    progress = np.clip(time / duration, 0, 1)
    envelope = np.sin(np.pi * progress) ** 1.7
    if reverse:
        envelope *= progress**0.6
    noise = np.random.default_rng(seed).standard_normal(time.size)
    smooth = np.convolve(noise, np.ones(21) / 21, mode="same")
    high = noise - smooth
    sweep_phase = 2 * np.pi * (
        260 * time + (920 if reverse else 1480) * time**2
    )
    mono = (0.12 * high + 0.07 * np.sin(sweep_phase)) * envelope
    if reverse:
        mono = mono[::-1]
    return _normalize(
        np.column_stack([mono * 0.76, np.roll(mono, 23)]),
        peak=0.48,
    )


def _click(*, frequency_hz: float, duration: float) -> np.ndarray:
    time = np.arange(round(duration * _SAMPLE_RATE)) / _SAMPLE_RATE
    envelope = np.exp(-time * 82)
    mono = (
        0.70 * np.sin(2 * np.pi * frequency_hz * time)
        + 0.30 * np.sin(2 * np.pi * frequency_hz * 1.78 * time)
    ) * envelope
    return _normalize(np.column_stack([mono, mono]), peak=0.46)


def _label_snap() -> np.ndarray:
    time = np.arange(round(0.12 * _SAMPLE_RATE)) / _SAMPLE_RATE
    envelope = np.exp(-time * 44)
    mono = (
        np.sin(2 * np.pi * 980 * time)
        + 0.58 * np.sin(2 * np.pi * 1710 * time + 0.3)
    ) * envelope
    return _normalize(np.column_stack([mono * 0.92, mono]), peak=0.50)


def _paper_scroll() -> np.ndarray:
    duration = 0.44
    time = np.arange(round(duration * _SAMPLE_RATE)) / _SAMPLE_RATE
    rng = np.random.default_rng(22)
    noise = rng.standard_normal(time.size)
    smooth = np.convolve(noise, np.ones(51) / 51, mode="same")
    texture = noise - smooth
    envelope = np.sin(np.pi * time / duration) ** 1.3
    pulses = 0.6 + 0.4 * np.sin(2 * np.pi * 11 * time) ** 2
    mono = texture * envelope * pulses
    return _normalize(
        np.column_stack([mono * 0.84, np.roll(mono, 37)]),
        peak=0.30,
    )


def _tonal_drop(
    *,
    duration: float,
    start_hz: float,
    end_hz: float,
) -> np.ndarray:
    time = np.arange(round(duration * _SAMPLE_RATE)) / _SAMPLE_RATE
    progress = time / duration
    frequency = start_hz + (end_hz - start_hz) * progress
    phase = 2 * np.pi * np.cumsum(frequency) / _SAMPLE_RATE
    envelope = np.sin(np.pi * progress) ** 1.25
    mono = np.sin(phase) * envelope
    return _normalize(np.column_stack([mono, mono * 0.96]), peak=0.46)


def _tension_riser() -> np.ndarray:
    duration = 1.05
    time = np.arange(round(duration * _SAMPLE_RATE)) / _SAMPLE_RATE
    progress = time / duration
    rng = np.random.default_rng(25)
    noise = rng.standard_normal(time.size)
    smooth = np.convolve(noise, np.ones(61) / 61, mode="same")
    high = noise - smooth
    tone = np.sin(2 * np.pi * (180 * time + 510 * time**2))
    mono = (0.10 * high + 0.08 * tone) * progress**1.8
    return _normalize(
        np.column_stack([mono * 0.80, np.roll(mono, 31)]),
        peak=0.38,
    )


def _reversal_drop() -> np.ndarray:
    tonal = _tonal_drop(duration=0.64, start_hz=720, end_hz=92)
    air = _whoosh(duration=0.64, reverse=False, seed=31)
    return _normalize(tonal * 0.72 + air * 0.48, peak=0.48)


def _normalize(samples: np.ndarray, *, peak: float) -> np.ndarray:
    maximum = float(np.max(np.abs(samples)))
    if maximum == 0:
        return samples
    return samples / maximum * peak


def _write_wav(path: Path, samples: np.ndarray) -> None:
    pcm = np.clip(samples, -1, 1)
    pcm = (pcm * np.iinfo(np.int16).max).astype("<i2")
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(2)
        stream.setsampwidth(2)
        stream.setframerate(_SAMPLE_RATE)
        stream.writeframes(pcm.tobytes())
