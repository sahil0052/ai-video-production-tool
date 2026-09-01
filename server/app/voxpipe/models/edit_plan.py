from __future__ import annotations

from typing import Literal, List, Optional
from pydantic import BaseModel, Field, model_validator


LayoutMode = Literal["SPLIT_50_50", "FULL_EXPLAINER", "FULL_CHARACTER"]
StyleMode = Literal["vox", "varun", "iman"]


class CaptionWord(BaseModel):
    word: str
    start: float
    end: float
    is_accent: bool = False


class CaptionBurst(BaseModel):
    start: float
    end: float
    words: List[CaptionWord]
    accent_word: Optional[str] = None


class SFXEvent(BaseModel):
    timestamp: float
    name: str
    category: str
    volume: float = 0.85


class SceneBeat(BaseModel):
    id: int
    start: float
    end: float
    duration: float
    layout: LayoutMode
    topic: str
    concept_summary: str
    prompt_shot: Optional[str] = None
    prompt_full: Optional[str] = None
    asset_path: Optional[str] = None
    asset_engine: Optional[Literal["flow_i2v", "vox_diorama", "presenter"]] = None


class VoxEditPlan(BaseModel):
    job_id: str
    source_video: str
    duration: float
    fps: float = 30.0
    style: StyleMode = "vox"
    beats: List[SceneBeat]
    captions: List[CaptionBurst] = Field(default_factory=list)
    sfx_tracks: List[SFXEvent] = Field(default_factory=list)
    created_at: Optional[str] = None

    @model_validator(mode="after")
    def validate_plan_integrity(self) -> VoxEditPlan:
        if not self.beats:
            raise ValueError("Edit plan must have at least one scene beat.")

        # 1. Zero Timeline Gaps / Black Holes
        curr = 0.0
        for b in self.beats:
            if abs(b.start - curr) > 0.08:
                raise ValueError(
                    f"Timeline gap detected between {curr:.2f}s and {b.start:.2f}s at beat {b.id}!"
                )
            if b.end <= b.start:
                raise ValueError(f"Beat {b.id} has invalid duration: {b.start} to {b.end}")
            curr = b.end

        # 2. 0-Second Hook Rule: Frame 0 MUST start in SPLIT_50_50
        if self.beats[0].layout != "SPLIT_50_50":
            raise ValueError("Frame 0 must start in SPLIT_50_50 hook mode.")

        # 3. Layout Distribution Check
        total_d = self.duration
        split_d = sum(b.duration for b in self.beats if b.layout == "SPLIT_50_50")
        explainer_d = sum(b.duration for b in self.beats if b.layout == "FULL_EXPLAINER")
        char_d = sum(b.duration for b in self.beats if b.layout == "FULL_CHARACTER")

        split_pct = (split_d / total_d) * 100
        explainer_pct = (explainer_d / total_d) * 100
        char_pct = (char_d / total_d) * 100

        # Target: Split >= 30%
        if split_pct < 30.0:
            raise ValueError(f"Split layout percentage too low: {split_pct:.1f}% (target >= 40%)")

        return self
