from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field, model_validator

from app.models import (
    AssetRef,
    AudioPlan,
    CaptionPage,
    EvidenceItem,
    OutputSpec,
    VideoMetadata,
)


SourceRole = Literal[
    "presenter",
    "real-product",
    "direct-evidence",
    "deterministic-graphic",
    "licensed-context",
    "flow-illustrative",
]

ReferenceProfile = Literal[
    "technical-reference",
    "social-kinetic",
]
StoryProfile = Literal[
    "automation-future",
    "automation-future-parity",
    "rofx-case",
    "cpi-inflation",
    "cpi-inflation-training",
    "ppi-training-v8",
    "backtest-training-v8",
    "lot-size-training-v8",
    "ppi-training-v9",
    "backtest-training-v9",
    "lot-size-training-v9",
]
VoicePolicy = Literal[
    "retime-safe",
    "preserve-verbatim",
    "reference-compressed",
    "natural-1x",
]
ProductionReferenceRole = str
_LEGACY_PRODUCTION_REFERENCE_ROLES = {
    "primary-10",
    "primary-13",
    "secondary-4",
    "primary-human",
    "secondary-10",
    "supporting",
}
_PRODUCTION_REFERENCE_ROLE_PATTERN = re.compile(
    r"^reference-(4|5|10|13)-[a-z0-9][a-z0-9-]*$"
)


def _validate_production_reference_role(value: str) -> str:
    if (
        value in _LEGACY_PRODUCTION_REFERENCE_ROLES
        or value == "profit-bricks-brand"
        or _PRODUCTION_REFERENCE_ROLE_PATTERN.fullmatch(value)
    ):
        return value
    raise ValueError(
        "reference_role must name a locked reference and editorial role"
    )
KineticTextFamily = Literal[
    "serif-hook",
    "hero-condensed",
    "outlined-stack",
    "cyan-secondary",
    "gradient-number",
    "correction-symbol",
    "cta-quote",
    "micro-source",
]
KineticTextAnimation = Literal[
    "hard-cut",
    "slam",
    "stack",
    "rise",
    "glow",
    "draw",
    "quote-pop",
]
MotionEventKind = Literal[
    "punch-crop",
    "text-reveal",
    "pip-pop",
    "logo-build",
    "directional-jump",
    "highlight-sweep",
    "impact-flash",
    "question-pulse",
    "proof-punch",
]
MotionDirection = Literal[
    "none",
    "left",
    "right",
    "up",
    "down",
]

LayerKind = Literal["video", "image"]
LayerFit = Literal["cover", "contain", "fill"]
BlendMode = Literal[
    "normal",
    "multiply",
    "screen",
    "overlay",
    "soft-light",
]

FlowMode = Literal["t2v", "i2v", "r2v"]
FlowModel = Literal["veo-lite"]
FlowShotStatus = Literal[
    "planned",
    "blocked",
    "generating",
    "recovery-needed",
    "awaiting-review",
    "accepted",
    "rejected",
    "exhausted",
]
FlowRequestedContent = Literal[
    "process-illustration",
    "abstract-motion",
    "physical-metaphor",
    "evidence",
    "exact-text",
    "product-ui",
    "code",
    "number",
    "currency",
    "chart",
    "source-document",
    "caption",
]

ProductionState = Literal[
    "analyzing",
    "blueprint-ready",
    "awaiting-generation-approval",
    "generating",
    "awaiting-candidate-review",
    "assembling",
    "automated-review",
    "awaiting-final-approval",
    "completed",
]

_FLOW_FORBIDDEN_CONTENT = {
    "evidence",
    "exact-text",
    "product-ui",
    "code",
    "number",
    "currency",
    "chart",
    "source-document",
    "caption",
}

_PRODUCTION_TRANSITIONS: dict[str, set[str]] = {
    "analyzing": {"blueprint-ready"},
    "blueprint-ready": {"awaiting-generation-approval", "assembling"},
    "awaiting-generation-approval": {"generating"},
    "generating": {
        "awaiting-generation-approval",
        "awaiting-candidate-review",
    },
    "awaiting-candidate-review": {"generating", "assembling"},
    "assembling": {
        "blueprint-ready",
        "awaiting-candidate-review",
        "automated-review",
    },
    "automated-review": {
        "blueprint-ready",
        "awaiting-candidate-review",
        "awaiting-final-approval",
        "assembling",
    },
    "awaiting-final-approval": {"completed", "assembling"},
    "completed": set(),
}


def validate_production_transition(
    current: ProductionState,
    target: ProductionState,
) -> ProductionState:
    if target not in _PRODUCTION_TRANSITIONS[current]:
        raise ValueError(
            f"Invalid production transition: {current} -> {target}"
        )
    return target


class CropSpec(BaseModel):
    x: float = Field(default=0, ge=0, le=1)
    y: float = Field(default=0, ge=0, le=1)
    width: float = Field(default=1, gt=0, le=1)
    height: float = Field(default=1, gt=0, le=1)

    @model_validator(mode="after")
    def validate_bounds(self) -> "CropSpec":
        if self.x + self.width > 1.000001:
            raise ValueError("Crop exceeds the source width")
        if self.y + self.height > 1.000001:
            raise ValueError("Crop exceeds the source height")
        return self


class LayerBounds(BaseModel):
    x: int = 0
    y: int = 0
    width: int = Field(default=1080, gt=0)
    height: int = Field(default=1920, gt=0)


class TransformKeyframe(BaseModel):
    at_ms: int = Field(ge=0)
    x: float = 0
    y: float = 0
    scale: float = Field(default=1, gt=0, le=4)
    rotate_deg: float = Field(default=0, ge=-360, le=360)


class OpacityKeyframe(BaseModel):
    at_ms: int = Field(ge=0)
    value: float = Field(ge=0, le=1)


class EffectKeyframe(BaseModel):
    at_ms: int = Field(ge=0)
    brightness: float = Field(default=1, ge=0.25, le=2)
    contrast: float = Field(default=1, ge=0.25, le=2)
    saturation: float = Field(default=1, ge=0, le=2)
    blur_px: float = Field(default=0, ge=0, le=80)


class DialogueEditSegment(BaseModel):
    id: str = Field(min_length=1)
    source_start_ms: int = Field(ge=0)
    source_end_ms: int = Field(gt=0)
    output_start_ms: int = Field(ge=0)
    output_end_ms: int = Field(gt=0)
    playback_rate: float = Field(default=1, ge=0.5, le=1.06)
    preserve_pitch: bool = True

    @model_validator(mode="after")
    def validate_ranges(self) -> "DialogueEditSegment":
        if self.source_end_ms <= self.source_start_ms:
            raise ValueError("Dialogue source range must have positive duration")
        if self.output_end_ms <= self.output_start_ms:
            raise ValueError("Dialogue output range must have positive duration")
        expected = (
            self.source_end_ms - self.source_start_ms
        ) / self.playback_rate
        actual = self.output_end_ms - self.output_start_ms
        if abs(actual - expected) > 4:
            raise ValueError(
                "Dialogue output duration must match its playback rate"
            )
        if not self.preserve_pitch:
            raise ValueError("Dialogue speed changes must preserve pitch")
        return self


class KineticTextCue(BaseModel):
    id: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    text: str = Field(min_length=1)
    family: KineticTextFamily
    x: int = Field(default=540, ge=-1080, le=2160)
    y: int = Field(default=1320, ge=-1920, le=3840)
    max_width: int = Field(default=940, ge=160, le=1080)
    align: Literal["left", "center", "right"] = "center"
    animation: KineticTextAnimation = "hard-cut"
    accent: str | None = None
    secondary_text: str | None = None
    rotation_deg: float = Field(default=0, ge=-30, le=30)
    z_index: int = Field(default=60, ge=0, le=1000)

    @model_validator(mode="after")
    def validate_range(self) -> "KineticTextCue":
        if self.end_ms <= self.start_ms:
            raise ValueError("Kinetic text cue must have positive duration")
        return self


class MotionEventSpec(BaseModel):
    id: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    kind: MotionEventKind
    target_id: str = Field(min_length=1)
    intensity: float = Field(default=0.5, ge=0, le=1)
    direction: MotionDirection = "none"

    @model_validator(mode="after")
    def validate_range(self) -> "MotionEventSpec":
        if self.end_ms <= self.start_ms:
            raise ValueError("Motion event must have positive duration")
        return self


class VisualLayerSpec(BaseModel):
    id: str = Field(min_length=1)
    shot_id: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    source_role: SourceRole
    kind: LayerKind = "video"
    asset_id: str = Field(min_length=1)
    source_start_ms: int | None = Field(default=None, ge=0)
    source_end_ms: int | None = Field(default=None, gt=0)
    bounds: LayerBounds = Field(default_factory=LayerBounds)
    crop: CropSpec = Field(default_factory=CropSpec)
    fit: LayerFit = "cover"
    transform_keyframes: list[TransformKeyframe] = Field(
        default_factory=lambda: [TransformKeyframe(at_ms=0)]
    )
    opacity_keyframes: list[OpacityKeyframe] = Field(
        default_factory=lambda: [OpacityKeyframe(at_ms=0, value=1)]
    )
    effect_keyframes: list[EffectKeyframe] = Field(
        default_factory=lambda: [EffectKeyframe(at_ms=0)]
    )
    blend_mode: BlendMode = "normal"
    z_index: int = Field(default=10, ge=0, le=1000)
    muted: bool = True
    loop: bool = False
    playback_rate: float = Field(default=1, ge=0.25, le=4)
    illustrative_label: bool = False
    border_radius: int = Field(default=0, ge=0, le=240)
    color_filter: str | None = None
    reference_role: ProductionReferenceRole = "primary-10"

    @model_validator(mode="after")
    def validate_layer(self) -> "VisualLayerSpec":
        self.reference_role = _validate_production_reference_role(
            self.reference_role
        )
        if self.end_ms <= self.start_ms:
            raise ValueError("Visual layer must have positive duration")
        if (self.source_start_ms is None) != (self.source_end_ms is None):
            raise ValueError("Media source trim requires start and end")
        if (
            self.source_start_ms is not None
            and self.source_end_ms is not None
            and self.source_end_ms <= self.source_start_ms
        ):
            raise ValueError("Media source trim must have positive duration")
        duration_ms = self.end_ms - self.start_ms
        if any(
            keyframe.at_ms > duration_ms
            for keyframe in self.transform_keyframes
        ):
            raise ValueError("Transform keyframe exceeds layer duration")
        if any(
            keyframe.at_ms > duration_ms
            for keyframe in self.opacity_keyframes
        ):
            raise ValueError("Opacity keyframe exceeds layer duration")
        if any(
            keyframe.at_ms > duration_ms
            for keyframe in self.effect_keyframes
        ):
            raise ValueError("Effect keyframe exceeds layer duration")
        if self.source_role == "flow-illustrative":
            if not self.muted:
                raise ValueError("Flow layers must always be muted")
            if not self.illustrative_label:
                raise ValueError(
                    "Flow layers must display the ILLUSTRATIVE label"
                )
            if self.loop:
                raise ValueError("Flow layers must not loop")
        return self


class FlowGenerationAttempt(BaseModel):
    attempt: int = Field(ge=1, le=2)
    command: list[str] = Field(min_length=1)
    project_id: str = Field(min_length=1)
    media_id: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    result_json: dict[str, Any] | None = None
    untouched_path: str | None = None
    checksum_sha256: str | None = Field(
        default=None,
        pattern=r"^[a-fA-F0-9]{64}$",
    )
    reconciliation_state: Literal[
        "not-needed",
        "pending",
        "catalog-confirmed",
        "missing",
    ] = "not-needed"


class FlowShotSpec(BaseModel):
    id: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    editorial_role: str = Field(min_length=1)
    prompt: str = Field(min_length=20)
    mode: FlowMode
    model: FlowModel = "veo-lite"
    input_plates: list[str] = Field(default_factory=list, max_length=3)
    requested_content: list[FlowRequestedContent] = Field(min_length=1)
    constraints: list[str] = Field(min_length=1)
    attempts: list[FlowGenerationAttempt] = Field(
        default_factory=list,
        max_length=2,
    )
    status: FlowShotStatus = "planned"

    @model_validator(mode="after")
    def validate_flow_policy(self) -> "FlowShotSpec":
        if self.end_ms <= self.start_ms:
            raise ValueError("Flow shot must have positive duration")
        forbidden = _FLOW_FORBIDDEN_CONTENT.intersection(
            self.requested_content
        )
        if forbidden:
            labels = ", ".join(sorted(forbidden))
            raise ValueError(
                f"Flow cannot generate factual or exact content: {labels}"
            )
        if self.mode == "i2v" and len(self.input_plates) not in {1, 2}:
            raise ValueError("Flow I2V requires one or two input plates")
        if self.mode == "t2v" and self.input_plates:
            raise ValueError("Flow T2V cannot receive input plates")
        if len(self.attempts) > 2:
            raise ValueError("Flow shots allow at most two attempts")
        attempt_numbers = [attempt.attempt for attempt in self.attempts]
        if len(attempt_numbers) != len(set(attempt_numbers)):
            raise ValueError("Flow attempt numbers must be unique")
        return self


class FlowTechnicalGates(BaseModel):
    decoded: bool
    duration_ok: bool
    no_black_sequence: bool
    no_frozen_sequence: bool
    single_continuous_shot: bool
    safe_framing: bool
    no_generated_text: bool


class FlowReviewScores(BaseModel):
    prompt_fidelity: int = Field(ge=1, le=5)
    motion_quality: int = Field(ge=1, le=5)
    continuity: int = Field(ge=1, le=5)
    composition: int = Field(ge=1, le=5)
    artifact_integrity: int = Field(ge=1, le=5)
    editorial_usefulness: int = Field(ge=1, le=5)

    def values(self) -> list[int]:
        return [
            self.prompt_fidelity,
            self.motion_quality,
            self.continuity,
            self.composition,
            self.artifact_integrity,
            self.editorial_usefulness,
        ]


class FlowCandidateReview(BaseModel):
    shot_id: str = Field(min_length=1)
    attempt: int = Field(ge=1, le=2)
    technical_gates: FlowTechnicalGates
    scores: FlowReviewScores
    rejection_reasons: list[str] = Field(default_factory=list)
    human_accepted: bool = False
    accepted_start_ms: int | None = Field(default=None, ge=0)
    accepted_end_ms: int | None = Field(default=None, gt=0)
    contact_sheet_path: str | None = None
    reviewed_at: datetime | None = None
    reviewer: str | None = None

    @computed_field
    @property
    def total_score(self) -> int:
        return sum(self.scores.values())

    @computed_field
    @property
    def accepted(self) -> bool:
        return (
            self.human_accepted
            and all(self.technical_gates.model_dump().values())
            and self.total_score >= 24
            and min(self.scores.values()) >= 3
            and not self.rejection_reasons
        )

    @model_validator(mode="after")
    def validate_human_acceptance(self) -> "FlowCandidateReview":
        if not self.human_accepted:
            return self
        if not all(self.technical_gates.model_dump().values()):
            raise ValueError(
                "Human acceptance is blocked by a technical hard gate"
            )
        if min(self.scores.values()) < 3:
            raise ValueError("Human acceptance requires every score >= 3")
        if self.total_score < 24:
            raise ValueError("Human acceptance requires at least 24/30")
        if (
            self.accepted_start_ms is None
            or self.accepted_end_ms is None
        ):
            raise ValueError("Human acceptance requires a selected window")
        duration_ms = self.accepted_end_ms - self.accepted_start_ms
        if duration_ms < 700 or duration_ms > 2200:
            raise ValueError(
                "Accepted Flow window must be between 700 and 2200 ms"
            )
        if self.rejection_reasons:
            raise ValueError(
                "Accepted Flow candidate cannot have rejection reasons"
            )
        return self


class FlowColorCorrection(BaseModel):
    brightness: float = Field(default=1, ge=0.5, le=1.5)
    contrast: float = Field(default=1, ge=0.5, le=1.5)
    saturation: float = Field(default=1, ge=0, le=2)


class FlowAcceptedClip(BaseModel):
    shot_id: str = Field(min_length=1)
    attempt: int = Field(ge=1, le=2)
    untouched_path: str = Field(min_length=1)
    proxy_path: str = Field(min_length=1)
    trim_start_ms: int = Field(ge=0)
    trim_end_ms: int = Field(gt=0)
    crop: CropSpec = Field(default_factory=CropSpec)
    speed: float = Field(default=1, ge=0.5, le=2)
    color_correction: FlowColorCorrection = Field(
        default_factory=FlowColorCorrection
    )
    provenance: str = "google-flow-veo-illustrative"
    illustrative_label_required: bool = True
    checksum_sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")

    @model_validator(mode="after")
    def validate_clip(self) -> "FlowAcceptedClip":
        duration_ms = self.trim_end_ms - self.trim_start_ms
        if duration_ms < 700 or duration_ms > 2200:
            raise ValueError(
                "Accepted Flow clip must be between 700 and 2200 ms"
            )
        if not self.illustrative_label_required:
            raise ValueError("Accepted Flow clips require an illustrative label")
        return self


class BlueprintLayerSpec(BaseModel):
    id: str = Field(min_length=1)
    shot_id: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    source_role: SourceRole
    kind: LayerKind = "video"
    asset_id: str | None = None
    flow_shot_id: str | None = None
    source_start_ms: int | None = Field(default=None, ge=0)
    source_end_ms: int | None = Field(default=None, gt=0)
    bounds: LayerBounds = Field(default_factory=LayerBounds)
    crop: CropSpec = Field(default_factory=CropSpec)
    fit: LayerFit = "cover"
    transform_keyframes: list[TransformKeyframe] = Field(
        default_factory=lambda: [TransformKeyframe(at_ms=0)]
    )
    opacity_keyframes: list[OpacityKeyframe] = Field(
        default_factory=lambda: [OpacityKeyframe(at_ms=0, value=1)]
    )
    effect_keyframes: list[EffectKeyframe] = Field(
        default_factory=lambda: [EffectKeyframe(at_ms=0)]
    )
    blend_mode: BlendMode = "normal"
    z_index: int = Field(default=10, ge=0, le=1000)
    muted: bool = True
    playback_rate: float = Field(default=1, ge=0.25, le=4)
    illustrative_label: bool = False
    border_radius: int = Field(default=0, ge=0, le=240)
    color_filter: str | None = None
    reference_role: ProductionReferenceRole = "primary-10"

    @model_validator(mode="after")
    def validate_source(self) -> "BlueprintLayerSpec":
        self.reference_role = _validate_production_reference_role(
            self.reference_role
        )
        if self.end_ms <= self.start_ms:
            raise ValueError("Blueprint layer must have positive duration")
        if (self.asset_id is None) == (self.flow_shot_id is None):
            raise ValueError(
                "Blueprint layer requires exactly one asset or Flow shot"
            )
        if self.flow_shot_id is not None:
            if self.source_role != "flow-illustrative":
                raise ValueError("Flow slots require the flow source role")
            if not self.muted or not self.illustrative_label:
                raise ValueError(
                    "Flow slots must be muted and marked illustrative"
                )
        return self


class ProductionBlueprint(BaseModel):
    version: Literal["4.0"] = "4.0"
    profile: Literal["flow-assisted-reference-v4"] = (
        "flow-assisted-reference-v4"
    )
    source_filename: str = Field(min_length=1)
    source_metadata: VideoMetadata
    output: OutputSpec = Field(default_factory=OutputSpec)
    duration_ms: int = Field(gt=0)
    assets: list[AssetRef] = Field(default_factory=list)
    layers: list[BlueprintLayerSpec] = Field(min_length=1)
    caption_pages: list[CaptionPage] = Field(default_factory=list)
    audio: AudioPlan = Field(default_factory=AudioPlan)
    flow_shots: list[FlowShotSpec] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    reference_profile: ReferenceProfile | None = None
    story_profile: StoryProfile | None = None
    style_reference_path: str | None = None
    voice_policy: VoicePolicy | None = None
    dialogue_edl: list[DialogueEditSegment] = Field(default_factory=list)
    kinetic_text_cues: list[KineticTextCue] = Field(default_factory=list)
    motion_events: list[MotionEventSpec] = Field(default_factory=list)


class EditPlanV2(BaseModel):
    version: Literal["2.0"] = "2.0"
    profile: Literal["production-tech-story-v4"] = (
        "production-tech-story-v4"
    )
    source_filename: str = Field(min_length=1)
    source_metadata: VideoMetadata
    output: OutputSpec = Field(default_factory=OutputSpec)
    duration_ms: int = Field(gt=0)
    assets: list[AssetRef] = Field(default_factory=list)
    visual_layers: list[VisualLayerSpec] = Field(min_length=1)
    caption_pages: list[CaptionPage] = Field(default_factory=list)
    audio: AudioPlan = Field(default_factory=AudioPlan)
    reference_profile: ReferenceProfile | None = None
    story_profile: StoryProfile | None = None
    style_reference_path: str | None = None
    voice_policy: VoicePolicy | None = None
    dialogue_edl: list[DialogueEditSegment] = Field(default_factory=list)
    kinetic_text_cues: list[KineticTextCue] = Field(default_factory=list)
    motion_events: list[MotionEventSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_plan(self) -> "EditPlanV2":
        asset_ids = [asset.id for asset in self.assets]
        if len(asset_ids) != len(set(asset_ids)):
            raise ValueError("Production asset identifiers must be unique")
        for asset in self.assets:
            if (
                "training videos data" in asset.path.casefold()
                or "training-video" in asset.provenance.casefold()
            ):
                raise ValueError(
                    "Training-video media cannot be used as an output asset"
                )
        layer_ids = [layer.id for layer in self.visual_layers]
        if len(layer_ids) != len(set(layer_ids)):
            raise ValueError("Visual layer identifiers must be unique")
        known_assets = set(asset_ids)
        for layer in self.visual_layers:
            if layer.end_ms > self.duration_ms:
                raise ValueError("Visual layer exceeds output duration")
            if layer.asset_id not in known_assets:
                raise ValueError(
                    f"Visual layer references unknown asset: {layer.asset_id}"
                )
        cue_ids = [cue.id for cue in self.kinetic_text_cues]
        if len(cue_ids) != len(set(cue_ids)):
            raise ValueError("Kinetic text identifiers must be unique")
        for cue in self.kinetic_text_cues:
            if cue.end_ms > self.duration_ms:
                raise ValueError("Kinetic text cue exceeds output duration")
        event_ids = [event.id for event in self.motion_events]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("Motion event identifiers must be unique")
        known_motion_targets = {
            *layer_ids,
            *cue_ids,
            "composition",
        }
        for event in self.motion_events:
            if event.end_ms > self.duration_ms:
                raise ValueError("Motion event exceeds output duration")
            if event.target_id not in known_motion_targets:
                raise ValueError(
                    f"Motion event references unknown target: {event.target_id}"
                )
        previous_output_end = 0
        for index, segment in enumerate(self.dialogue_edl):
            if segment.output_start_ms != previous_output_end:
                raise ValueError(
                    "Dialogue EDL output ranges must be contiguous"
                )
            if index and (
                segment.source_start_ms
                < self.dialogue_edl[index - 1].source_end_ms
            ):
                raise ValueError(
                    "Dialogue EDL source ranges must be ordered"
                )
            if segment.source_end_ms > round(
                self.source_metadata.duration_seconds * 1000
            ) + 1:
                raise ValueError("Dialogue EDL exceeds source duration")
            if segment.output_end_ms > self.duration_ms:
                raise ValueError("Dialogue EDL exceeds output duration")
            previous_output_end = segment.output_end_ms
        previous_caption_end = -1
        for page in self.caption_pages:
            duration_ms = page.end_ms - page.start_ms
            if page.end_ms > self.duration_ms:
                raise ValueError("Caption page exceeds output duration")
            if duration_ms < 350 or duration_ms > 1300:
                raise ValueError(
                    "Caption pages must remain visible for 350-1300 ms"
                )
            if page.start_ms < previous_caption_end:
                raise ValueError("Caption pages must not overlap")
            previous_caption_end = page.end_ms
            for token in page.tokens:
                if token.end_ms <= token.start_ms:
                    raise ValueError(
                        "Caption token must have positive duration"
                    )
                if (
                    token.end_ms <= page.start_ms
                    or token.start_ms >= page.end_ms
                ):
                    raise ValueError(
                        "Caption token must overlap its visible page"
                    )
        audio_ids = {
            asset.id for asset in self.assets if asset.kind == "audio"
        }
        for asset_id in (
            self.audio.dialogue_asset_id,
            self.audio.music_asset_id,
        ):
            if asset_id is not None and asset_id not in audio_ids:
                raise ValueError("Audio plan references an unknown audio asset")
        sfx_ids = {
            *self.audio.sfx_asset_ids,
            *(cue.asset_id for cue in self.audio.sfx_cues),
        }
        if not sfx_ids.issubset(audio_ids):
            raise ValueError("Sound effects must reference audio assets")
        return self


class ProductionStateEvent(BaseModel):
    state: ProductionState
    at: datetime
    detail: str = ""


class ProductionJobRecord(BaseModel):
    id: str = Field(min_length=1)
    source_path: str = Field(min_length=1)
    output_dir: str = Field(min_length=1)
    state: ProductionState = "analyzing"
    primary_reference: int = Field(ge=1, le=14)
    secondary_reference: int = Field(ge=1, le=14)
    flow_operation_budget: int = Field(default=3, ge=0, le=8)
    approved_paid_operations: int = Field(default=0, ge=0, le=8)
    consumed_paid_operations: int = Field(default=0, ge=0, le=8)
    flow_profile: str = "sahilsharmabybit2"
    flow_project_id: str | None = None
    flow_repository: str | None = None
    artifacts: dict[str, str] = Field(default_factory=dict)
    accepted_clips: list[FlowAcceptedClip] = Field(default_factory=list)
    automated_pass: bool = False
    human_approved: bool = False
    final_reviewer: str | None = None
    state_history: list[ProductionStateEvent] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_budget(self) -> "ProductionJobRecord":
        if self.approved_paid_operations > self.flow_operation_budget:
            raise ValueError(
                "Approved paid operations exceed the configured budget"
            )
        if self.consumed_paid_operations > self.approved_paid_operations:
            raise ValueError(
                "Consumed paid operations exceed explicit approval"
            )
        if self.human_approved and not self.automated_pass:
            raise ValueError(
                "Final human approval requires an automated pass"
            )
        if self.state == "completed" and not self.human_approved:
            raise ValueError(
                "Completed production jobs require human approval"
            )
        return self


class FlowGenerationApprovalRequest(BaseModel):
    approve_paid_ops: int = Field(ge=1, le=8)


class FlowCandidateDecisionRequest(BaseModel):
    shot_id: str = Field(min_length=1)
    attempt: int = Field(ge=1, le=2)
    accepted: bool
    scores: FlowReviewScores
    accepted_start_ms: int | None = Field(default=None, ge=0)
    accepted_end_ms: int | None = Field(default=None, gt=0)
    reviewer: str = Field(min_length=1)
    rejection_reasons: list[str] = Field(default_factory=list)
    speed: float = Field(default=1, ge=0.5, le=2)
    crop: CropSpec = Field(default_factory=CropSpec)
    color_correction: FlowColorCorrection = Field(
        default_factory=FlowColorCorrection
    )


class FinalApprovalRequest(BaseModel):
    reviewer: str = Field(min_length=1)
