from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class TrainingReferenceProfile:
    story_id: str
    primary_reference: int
    secondary_reference: int
    caption_mode: str
    hard_cut_count: tuple[int, int]
    median_shot_ms: tuple[int, int]
    presenter_ratio: tuple[float, float]
    dark_ratio: tuple[float, float]
    luminance: tuple[float, float]
    luminance_p10: tuple[float, float]
    luminance_p90: tuple[float, float]
    saturation: tuple[float, float]
    caption_coverage: tuple[float, float]
    cut_audio_alignment_min: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


PROFILES = {
    "ppi": TrainingReferenceProfile(
        story_id="ppi",
        primary_reference=13,
        secondary_reference=10,
        caption_mode="news-evidence",
        hard_cut_count=(31, 36),
        median_shot_ms=(1_000, 1_500),
        presenter_ratio=(0.14, 0.20),
        dark_ratio=(0.24, 0.36),
        luminance=(78, 96),
        luminance_p10=(15, 35),
        luminance_p90=(210, 240),
        saturation=(58, 78),
        caption_coverage=(0.68, 0.75),
        cut_audio_alignment_min=0.85,
    ),
    "backtest": TrainingReferenceProfile(
        story_id="backtest",
        primary_reference=10,
        secondary_reference=4,
        caption_mode="technical-reference",
        hard_cut_count=(19, 22),
        median_shot_ms=(1_700, 2_300),
        presenter_ratio=(0.14, 0.20),
        dark_ratio=(0.38, 0.55),
        luminance=(68, 95),
        luminance_p10=(5, 18),
        luminance_p90=(215, 245),
        saturation=(45, 75),
        caption_coverage=(0.68, 0.75),
        cut_audio_alignment_min=0.88,
    ),
    "lot-size": TrainingReferenceProfile(
        story_id="lot-size",
        primary_reference=10,
        secondary_reference=5,
        caption_mode="technical-product",
        hard_cut_count=(20, 25),
        median_shot_ms=(1_500, 2_100),
        presenter_ratio=(0.14, 0.20),
        dark_ratio=(0.30, 0.45),
        luminance=(75, 100),
        luminance_p10=(8, 22),
        luminance_p90=(210, 242),
        saturation=(55, 90),
        caption_coverage=(0.68, 0.75),
        cut_audio_alignment_min=0.88,
    ),
}

_ALIASES = {
    "ppi-training-v8": "ppi",
    "backtest-training-v8": "backtest",
    "lot-size-training-v8": "lot-size",
}


def profile_for_story(story_id: str) -> TrainingReferenceProfile:
    normalized = _ALIASES.get(story_id.casefold(), story_id.casefold())
    try:
        return PROFILES[normalized]
    except KeyError as error:
        raise ValueError(
            f"Unknown V8 story profile: {story_id}"
        ) from error
