from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import re
from typing import Any, Iterable

from app.editor.training_reference_profiles import (
    TrainingReferenceProfile,
    profile_for_story,
)


SERVER_DIR = Path(__file__).resolve().parent
WORKSPACE = SERVER_DIR.parent
OUTPUT_ROOT = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0813-all-three-v8-training-reference"
)

_REFERENCE_ROLE = re.compile(
    r"^reference-(4|5|10|13)-[a-z0-9][a-z0-9-]*$"
)
_SOURCE_ROLES = {
    "presenter",
    "real-product",
    "direct-evidence",
    "deterministic-graphic",
    "licensed-context",
}
_CAPTION_FAMILIES = {
    "technical-mono",
    "documentary-clean",
    "compact-pill",
    "outlined-demo",
    "display-emphasis",
}


@dataclass(frozen=True)
class V8Shot:
    id: str
    start_ms: int
    end_ms: int
    narration_phrase: str
    source_role: str
    reference_role: str
    primary_subject: str
    action: str
    treatment: str
    treatment_class: str
    asset_id: str
    caption_family: str
    source_start_ms: int = 0
    crop_x: float = 0.5
    crop_y: float = 0.5
    zoom: float = 1.0
    illustrative: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("id is required")
        if self.end_ms <= self.start_ms:
            raise ValueError("shot requires a positive time range")
        if self.source_role not in _SOURCE_ROLES:
            raise ValueError(f"unknown source_role: {self.source_role}")
        if (
            self.reference_role != "profit-bricks-brand"
            and not _REFERENCE_ROLE.fullmatch(self.reference_role)
        ):
            raise ValueError(
                f"invalid reference_role: {self.reference_role}"
            )
        if not self.primary_subject.strip():
            raise ValueError("primary_subject is required")
        if not self.action.strip():
            raise ValueError("action is required")
        if not self.treatment_class.strip():
            raise ValueError("treatment_class is required")
        if self.caption_family not in _CAPTION_FAMILIES:
            raise ValueError(
                f"unknown caption_family: {self.caption_family}"
            )
        if self.treatment in {"vertical-split", "persistent-pip"}:
            raise ValueError("V8 prohibits vertical split and persistent PIP")
        if not 0 <= self.crop_x <= 1 or not 0 <= self.crop_y <= 1:
            raise ValueError("crop anchors must be normalized")
        if not 0.75 <= self.zoom <= 2.5:
            raise ValueError("zoom is outside the safe production range")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StoryBlueprint:
    story_id: str
    title: str
    source: Path
    transcript_path: Path
    output_dir: Path
    duration_ms: int
    primary_reference: int
    secondary_reference: int
    music_bpm: int
    shots: tuple[V8Shot, ...]
    profile: TrainingReferenceProfile

    def __post_init__(self) -> None:
        if self.profile.story_id != self.story_id:
            raise ValueError("profile and story identifiers do not match")
        if not self.shots:
            raise ValueError("storyboard requires shots")
        if self.shots[0].start_ms != 0:
            raise ValueError("storyboard must start at zero")
        if self.shots[-1].end_ms != self.duration_ms:
            raise ValueError("storyboard must cover the final frame")
        for left, right in zip(self.shots, self.shots[1:]):
            if left.end_ms != right.start_ms:
                raise ValueError("storyboard shots must be contiguous")
        for first, second, third in zip(
            self.shots,
            self.shots[1:],
            self.shots[2:],
        ):
            if (
                first.treatment_class
                == second.treatment_class
                == third.treatment_class
            ):
                raise ValueError(
                    "one treatment class cannot run for three shots"
                )
        distinct = {shot.treatment_class for shot in self.shots}
        if len(distinct) < 6:
            raise ValueError("storyboard needs six treatment classes")
        presenter_ms = sum(
            shot.end_ms - shot.start_ms
            for shot in self.shots
            if shot.source_role == "presenter"
        )
        presenter_ratio = presenter_ms / self.duration_ms
        low, high = self.profile.presenter_ratio
        if not low <= presenter_ratio <= high:
            raise ValueError(
                "presenter coverage is outside the reference profile"
            )
        minimum, maximum = self.profile.hard_cut_count
        if not minimum <= len(self.shots) <= maximum:
            raise ValueError(
                "shot count is outside the reference profile"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "story_id": self.story_id,
            "title": self.title,
            "source": str(self.source),
            "transcript_path": str(self.transcript_path),
            "output_dir": str(self.output_dir),
            "duration_ms": self.duration_ms,
            "primary_reference": self.primary_reference,
            "secondary_reference": self.secondary_reference,
            "music_bpm": self.music_bpm,
            "profile": self.profile.to_dict(),
            "shots": [shot.to_dict() for shot in self.shots],
        }


def make_blueprint(
    *,
    story_id: str,
    title: str,
    source: Path,
    transcript_path: Path,
    duration_ms: int,
    music_bpm: int,
    shots: Iterable[V8Shot],
) -> StoryBlueprint:
    profile = profile_for_story(story_id)
    return StoryBlueprint(
        story_id=story_id,
        title=title,
        source=source,
        transcript_path=transcript_path,
        output_dir=OUTPUT_ROOT / story_id,
        duration_ms=duration_ms,
        primary_reference=profile.primary_reference,
        secondary_reference=profile.secondary_reference,
        music_bpm=music_bpm,
        shots=tuple(shots),
        profile=profile,
    )


def shot(
    index: int,
    start_ms: int,
    end_ms: int,
    *,
    phrase: str,
    source_role: str,
    reference_role: str,
    subject: str,
    action: str,
    treatment: str,
    treatment_class: str,
    asset_id: str,
    caption_family: str,
    source_start_ms: int = 0,
    crop_x: float = 0.5,
    crop_y: float = 0.5,
    zoom: float = 1.0,
    illustrative: bool = False,
    **metadata: Any,
) -> V8Shot:
    return V8Shot(
        id=f"shot-{index:02d}",
        start_ms=start_ms,
        end_ms=end_ms,
        narration_phrase=phrase,
        source_role=source_role,
        reference_role=reference_role,
        primary_subject=subject,
        action=action,
        treatment=treatment,
        treatment_class=treatment_class,
        asset_id=asset_id,
        caption_family=caption_family,
        source_start_ms=source_start_ms,
        crop_x=crop_x,
        crop_y=crop_y,
        zoom=zoom,
        illustrative=illustrative,
        metadata=metadata,
    )
