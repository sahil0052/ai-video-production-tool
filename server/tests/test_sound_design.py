from pathlib import Path
import wave

import numpy as np

from app.editor import sound_design
from app.editor.sound_design import generate_sound_design
from app.models import TranscriptSegment, TranscriptWord


def test_generate_sound_design_creates_original_music_and_sparse_sfx(
    tmp_path: Path,
) -> None:
    assets, audio = generate_sound_design(
        tmp_path,
        duration_ms=8000,
        emphasis_times_ms=[0, 2400, 5100],
    )

    music = next(asset for asset in assets if asset.id == audio.music_asset_id)
    assert music.provenance == "generated-original"
    assert music.license == "Original procedural audio"
    assert Path(music.path).is_file()
    assert len(audio.sfx_cues) == 3
    assert all(cue.start_ms < 8000 for cue in audio.sfx_cues)
    assert len(audio.sfx_cues) <= 6

    with wave.open(music.path, "rb") as stream:
        assert stream.getframerate() == 48000
        assert stream.getnchannels() == 2
        assert stream.getnframes() > 48000


def test_full_production_soundtrack_is_evolving_and_motivated(
    tmp_path: Path,
) -> None:
    cue_times = [
        0,
        90,
        2820,
        4320,
        7200,
        9560,
        11_880,
        14_480,
        17_920,
        21_820,
        24_000,
        26_700,
        33_180,
    ]
    assets, audio = generate_sound_design(
        tmp_path,
        duration_ms=41_401,
        emphasis_times_ms=cue_times,
    )

    assert 9 <= len(audio.sfx_cues) <= 13
    assert all(getattr(cue, "reason", "") for cue in audio.sfx_cues)
    assert len({cue.asset_id for cue in audio.sfx_cues}) >= 6
    label_snap = next(
        cue
        for cue in audio.sfx_cues
        if cue.asset_id == "generated-label-snap"
    )
    assert label_snap.volume >= 0.22

    music = next(asset for asset in assets if asset.id == audio.music_asset_id)
    with wave.open(music.path, "rb") as stream:
        assert stream.getframerate() == 48_000
        assert stream.getnchannels() == 2
        assert abs(stream.getnframes() - round(41.401 * 48_000)) <= 1
        samples = np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2")

    stereo = samples.reshape(-1, 2)
    eight_seconds = 8 * 48_000
    assert not np.array_equal(
        stereo[:eight_seconds],
        stereo[eight_seconds : eight_seconds * 2],
    )


def test_build_audio_automation_protects_word_onsets_and_ducks_music() -> None:
    builder = getattr(sound_design, "build_audio_automation", None)
    assert builder is not None
    segments = [
        TranscriptSegment(
            start=0.2,
            end=1.2,
            text="Do you know",
            words=[
                TranscriptWord(start=0.2, end=0.38, text="Do"),
                TranscriptWord(start=0.48, end=0.67, text="you"),
                TranscriptWord(start=0.82, end=1.12, text="know"),
            ],
        )
    ]

    gain, protected = builder(segments, duck_db=6)

    assert gain == [
        {
            "start_ms": 200,
            "end_ms": 1120,
            "gain_db": -6.0,
            "reason": "dialogue duck",
        }
    ]
    assert protected[0]["start_ms"] == 100
    assert protected[0]["end_ms"] == 320
    assert protected[0]["word"] == "Do"


def test_generated_sfx_never_overlap_protected_word_onsets(
    tmp_path: Path,
) -> None:
    segments = [
        TranscriptSegment(
            start=0,
            end=1.2,
            text="Do you know",
            words=[
                TranscriptWord(start=0.0, end=0.3, text="Do"),
                TranscriptWord(start=0.5, end=0.8, text="you"),
                TranscriptWord(start=0.9, end=1.2, text="know"),
            ],
        )
    ]
    _assets, audio = generate_sound_design(
        tmp_path,
        duration_ms=3000,
        emphasis_times_ms=[0, 500, 2000],
        speech_segments=segments,
    )

    assert audio.music_gain_automation
    assert audio.speech_protection_windows
    for cue in audio.sfx_cues:
        cue_end = cue.start_ms + cue.duration_ms
        assert all(
            cue_end <= window.start_ms or cue.start_ms >= window.end_ms
            for window in audio.speech_protection_windows
        )
