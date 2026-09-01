from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class VideoMetadata(BaseModel):
    width: int
    height: int
    fps: float
    frame_count: int
    duration_seconds: float


class TranscriptWord(BaseModel):
    start: float
    end: float
    text: str
    confidence: float | None = Field(default=None, ge=0, le=1)


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str
    words: list[TranscriptWord]


class CaptionCue(BaseModel):
    start: float
    end: float
    text: str


StyleVariant = Literal[
    "tech-news",
    "cinematic-concept",
    "technical-explanation",
    "product-demo",
    "hardware-launch",
    "hyper-montage",
]

CaptionFamily = Literal[
    "technical-mono",
    "documentary-clean",
    "compact-pill",
    "outlined-demo",
    "display-emphasis",
]

CaptionAnchor = Literal[
    "center-69",
    "center-71",
    "center-74",
    "center-76",
    "center-78",
    "lower-82",
    "upper-46",
    "upper-56",
    "upper-62",
]

CaptionTransition = Literal[
    "hard-cut",
    "fade-up",
    "scale-in",
]

SceneRole = Literal[
    "hook",
    "claim",
    "evidence",
    "explanation",
    "demonstration",
    "contrast",
    "payoff",
    "cta",
]

SceneMotion = Literal[
    "live-footage",
    "animated",
    "document-pan",
    "static",
]

SourceKind = Literal[
    "presenter",
    "screen-recording",
    "direct-source",
    "licensed-footage",
    "procedural",
]

ReferenceRole = Literal[
    "primary-10",
    "secondary-4",
    "supporting",
]

VisualCategory = Literal[
    "presenter",
    "hook-composite",
    "cinematic-broll",
    "designed-explanation",
    "edited-evidence",
    "product-macro",
    "literal-desktop-ui",
]

EditorialVisualKind = Literal[
    "trading-chart",
    "rule-flow",
    "code-terminal",
    "evidence-card",
    "metric-reveal",
    "risk-meter",
    "comparison",
    "chat-cta",
]


class OutputSpec(BaseModel):
    width: int = 1080
    height: int = 1920
    fps: Literal[30, 60] = 30


class TimelineMapSegment(BaseModel):
    source_start_ms: int = Field(ge=0)
    source_end_ms: int = Field(gt=0)
    output_start_ms: int = Field(ge=0)
    output_end_ms: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_ranges(self) -> "TimelineMapSegment":
        if self.source_end_ms <= self.source_start_ms:
            raise ValueError("Source range must have positive duration")
        if self.output_end_ms <= self.output_start_ms:
            raise ValueError("Output range must have positive duration")
        if (
            self.source_end_ms - self.source_start_ms
            != self.output_end_ms - self.output_start_ms
        ):
            raise ValueError("Timeline map segments must preserve playback speed")
        return self


class CaptionToken(BaseModel):
    text: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    highlighted: bool = False
    confidence: float | None = Field(default=None, ge=0, le=1)


class CaptionPage(BaseModel):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    tokens: list[CaptionToken] = Field(min_length=1, max_length=5)
    family: CaptionFamily = "compact-pill"
    anchor: CaptionAnchor = "center-76"
    transition: CaptionTransition = "fade-up"
    max_width: int = Field(default=920, ge=320, le=980)

    @model_validator(mode="after")
    def validate_range(self) -> "CaptionPage":
        if self.end_ms <= self.start_ms:
            raise ValueError("Caption page must have positive duration")
        return self


class ScenePlan(BaseModel):
    id: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    role: SceneRole
    layout: Literal[
        "presenter",
        "split-screen",
        "graphic",
        "asset-full",
        "presenter-pip",
    ] = "presenter"
    zoom: Literal[1.0, 1.12, 1.24] = 1.0
    visual_id: str | None = None
    treatment: str | None = None
    asset_id: str | None = None
    motion: SceneMotion = "live-footage"

    @model_validator(mode="after")
    def validate_range(self) -> "ScenePlan":
        if self.end_ms <= self.start_ms:
            raise ValueError("Scene must have positive duration")
        return self


class EditorialVisual(BaseModel):
    id: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    kind: EditorialVisualKind
    title: str = Field(min_length=1)
    subtitle: str = ""
    accent: str = "#00E5FF"
    value: str | None = None
    items: list[str] = Field(default_factory=list, max_length=5)
    direction: Literal["up", "down", "neutral"] = "neutral"

    @model_validator(mode="after")
    def validate_range(self) -> "EditorialVisual":
        if self.end_ms <= self.start_ms:
            raise ValueError("Editorial visual must have positive duration")
        return self


class ReframeKeyframe(BaseModel):
    time_ms: int = Field(ge=0)
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    scale: float = Field(ge=1, le=1.5)


class AssetRef(BaseModel):
    id: str = Field(min_length=1)
    kind: Literal["image", "video", "audio", "font"]
    path: str = Field(min_length=1)
    keywords: list[str] = Field(default_factory=list)
    provenance: str = Field(min_length=1)
    license: str | None = None
    provider: str | None = None
    remote_id: str | None = None
    creator: str | None = None
    source_url: str | None = None
    license_url: str | None = None
    search_query: str | None = None
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_schedule(self) -> "AssetRef":
        if (self.start_ms is None) != (self.end_ms is None):
            raise ValueError("Asset schedule requires both start_ms and end_ms")
        if (
            self.start_ms is not None
            and self.end_ms is not None
            and self.end_ms <= self.start_ms
        ):
            raise ValueError("Asset schedule must have positive duration")
        if self.provenance.lower().startswith("internet:"):
            required = {
                "provider": self.provider,
                "source_url": self.source_url,
                "license": self.license,
                "license_url": self.license_url,
            }
            missing = [
                name for name, value in required.items() if not value
            ]
            if missing:
                raise ValueError(
                    "Internet assets require provider, source and license "
                    "metadata"
                )
        for url in (self.source_url, self.license_url):
            if url is not None and not url.startswith("https://"):
                raise ValueError("Asset metadata URLs must use HTTPS")
        return self


class GraphicCue(BaseModel):
    id: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    kind: Literal[
        "headline",
        "callout",
        "label",
        "counter",
        "progress",
        "browser",
        "phone",
        "chat",
    ]
    text: str
    accent: str = "#D7FF64"

    @model_validator(mode="after")
    def validate_range(self) -> "GraphicCue":
        if self.end_ms <= self.start_ms:
            raise ValueError("Graphic cue must have positive duration")
        return self


class SfxCue(BaseModel):
    id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    source_start_ms: int = Field(default=0, ge=0)
    duration_ms: int = Field(default=100, gt=0)
    volume: float = Field(default=0.45, ge=0, le=1)
    gain_db: float = Field(default=-15.0, ge=-30, le=0)
    kind: Literal["whoosh", "click", "impact", "riser", "notification"]
    reason: str = ""


class GainAutomation(BaseModel):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    gain_db: float = Field(ge=-12, le=0)
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_range(self) -> "GainAutomation":
        if self.end_ms <= self.start_ms:
            raise ValueError("Gain automation must have positive duration")
        return self


class SpeechProtectionWindow(BaseModel):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    word: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_range(self) -> "SpeechProtectionWindow":
        if self.end_ms <= self.start_ms:
            raise ValueError("Speech protection must have positive duration")
        return self


class AudioPlan(BaseModel):
    integrated_lufs: float = -14.2
    true_peak_dbtp: float = -1.0
    target_lra_lu: float = Field(default=5.0, ge=1.0, le=10.0)
    music_bpm: int = Field(default=120, ge=80, le=145)
    dialogue_asset_id: str | None = None
    dialogue_offset_ms: int = Field(default=0, ge=-500, le=500)
    music_asset_id: str | None = None
    music_duck_db: float = Field(default=6.0, ge=4, le=12)
    music_base_gain_db: float = Field(default=-18.0, ge=-40, le=0)
    music_gain_automation: list[GainAutomation] = Field(
        default_factory=list
    )
    speech_protection_windows: list[SpeechProtectionWindow] = Field(
        default_factory=list
    )
    sfx_asset_ids: list[str] = Field(default_factory=list)
    sfx_cues: list[SfxCue] = Field(default_factory=list)


class QCTargets(BaseModel):
    integrated_lufs: float = -14.2
    loudness_tolerance: float = 0.5
    true_peak_dbtp: float = -1.0
    max_silence_ms: int = 120
    max_black_frame_ratio: float = 0.001
    max_freeze_frame_ratio: float = 0.14
    min_cuts_per_minute: float = 30
    max_cuts_per_minute: float = 75
    min_median_shot_ms: int = 800
    max_median_shot_ms: int = 1800
    min_cut_onset_percent: float = 70
    min_meaningful_visual_coverage: float = Field(
        default=0.55,
        ge=0,
        le=1,
    )
    min_style_score: float = 80


EvidenceSourceType = Literal[
    "primary",
    "official",
    "editorial",
    "licensed-media",
    "user-provided",
]

EvidenceStatus = Literal["verified", "rejected", "pending"]


class EvidenceItem(BaseModel):
    id: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    source_type: EvidenceSourceType
    capture_path: str = Field(min_length=1)
    accessed_at: datetime
    status: EvidenceStatus
    published_at: datetime | None = None
    visible_excerpt: str | None = None
    license: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_source(self) -> "EvidenceItem":
        if not self.source_url.startswith("https://"):
            raise ValueError("Evidence source URLs must use HTTPS")
        normalized_capture = self.capture_path.replace("\\", "/")
        if normalized_capture.startswith("/") or ".." in normalized_capture.split("/"):
            raise ValueError("Evidence capture paths must be relative")
        if self.status == "verified" and not self.capture_path:
            raise ValueError("Verified evidence requires a source capture")
        return self


class ShotSpec(BaseModel):
    id: str = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    role: SceneRole
    layout: Literal[
        "presenter",
        "split-screen",
        "graphic",
        "asset-full",
        "presenter-pip",
    ]
    treatment: str = Field(min_length=1)
    caption_family: CaptionFamily
    evidence_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    asset_id: str | None = None
    motion: SceneMotion = "live-footage"
    source_kind: SourceKind = "procedural"
    reference_role: ReferenceRole = "primary-10"
    visual_category: VisualCategory | None = None
    primary_subject: str = ""
    source_family: str = ""
    simultaneous_actions: int = Field(default=0, ge=0, le=3)
    notes: str = ""

    @model_validator(mode="after")
    def validate_range(self) -> "ShotSpec":
        if self.end_ms <= self.start_ms:
            raise ValueError("Shot must have positive duration")
        return self


class ArtifactSpec(BaseModel):
    id: str = Field(min_length=1)
    kind: Literal[
        "source-capture",
        "diagram",
        "chart",
        "code",
        "title-card",
        "image",
        "video",
        "audio",
        "font-fixture",
    ]
    path: str = Field(min_length=1)
    provenance: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    illustrative: bool = False
    label: str | None = None

    @model_validator(mode="after")
    def validate_provenance(self) -> "ArtifactSpec":
        normalized_path = self.path.replace("\\", "/")
        if normalized_path.startswith("/") or ".." in normalized_path.split("/"):
            raise ValueError("Artifact paths must be relative")
        if (
            not self.illustrative
            and self.provenance == "generated-from-verified-facts"
            and not self.evidence_ids
        ):
            raise ValueError(
                "Fact-based generated artifacts require evidence identifiers"
            )
        return self


class CaptureManifestEntry(BaseModel):
    id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    source_kind: Literal["screen-recording"]
    application: str = Field(min_length=1)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fps: float = Field(gt=0)
    codec: str = Field(min_length=1)
    checksum_sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    captured_at: datetime
    privacy_reviewed: bool
    privacy_notes: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_capture(self) -> "CaptureManifestEntry":
        normalized = self.path.replace("\\", "/")
        if normalized.startswith("/") or ".." in normalized.split("/"):
            raise ValueError("Capture paths must be relative")
        if not self.privacy_reviewed:
            raise ValueError("Capture must pass privacy review")
        return self


class CaptureManifest(BaseModel):
    profile: Literal["local-metatrader"]
    recorder: str = Field(min_length=1)
    entries: list[CaptureManifestEntry] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_entries(self) -> "CaptureManifest":
        identifiers = [entry.id for entry in self.entries]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Capture identifiers must be unique")
        return self


class VisualReviewCheck(BaseModel):
    name: str = Field(min_length=1)
    passed: bool
    detail: str = ""
    evidence: list[str] = Field(default_factory=list)


class VisualReview(BaseModel):
    passed: bool
    automated_pass: bool | None = None
    human_approved: bool | None = None
    checks: list[VisualReviewCheck]
    caption_family_stills: list[str] = Field(default_factory=list)
    sourced_evidence_beats: int = Field(ge=0)
    unique_visual_treatments: int = Field(ge=0)
    unsupported_visible_facts: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_release_gate(self) -> "VisualReview":
        checks_pass = all(check.passed for check in self.checks)
        expected_automated = (
            checks_pass and not self.unsupported_visible_facts
        )
        automated_pass = (
            self.passed
            if self.automated_pass is None
            else self.automated_pass
        )
        human_approved = (
            self.passed
            if self.human_approved is None
            else self.human_approved
        )
        if automated_pass != expected_automated:
            raise ValueError(
                "Automated review state must match its checks and fact gate"
            )
        expected_release = expected_automated and human_approved
        if self.passed != expected_release:
            raise ValueError(
                "Release pass requires automated and human approval"
            )
        self.automated_pass = automated_pass
        self.human_approved = human_approved
        return self


class EditPlanV1(BaseModel):
    version: Literal["1.0"] = "1.0"
    profile: Literal["tech-story-v1"] = "tech-story-v1"
    source_filename: str
    source_metadata: VideoMetadata
    output: OutputSpec
    duration_ms: int = Field(gt=0)
    style_variant: StyleVariant
    timeline: list[TimelineMapSegment] = Field(min_length=1)
    caption_pages: list[CaptionPage] = Field(default_factory=list)
    scenes: list[ScenePlan] = Field(min_length=1)
    reframing: list[ReframeKeyframe] = Field(default_factory=list)
    graphics: list[GraphicCue] = Field(default_factory=list)
    editorial_visuals: list[EditorialVisual] = Field(default_factory=list)
    assets: list[AssetRef] = Field(default_factory=list)
    audio: AudioPlan = Field(default_factory=AudioPlan)
    qc_targets: QCTargets = Field(default_factory=QCTargets)

    @model_validator(mode="after")
    def validate_contract(self) -> "EditPlanV1":
        source_duration_ms = round(self.source_metadata.duration_seconds * 1000)
        previous_output_end = 0
        previous_source_end = -1
        for index, segment in enumerate(self.timeline):
            if segment.output_start_ms != previous_output_end:
                raise ValueError("Output timeline must be ordered and contiguous")
            if index and segment.source_start_ms < previous_source_end:
                raise ValueError("Source timeline must be ordered and non-overlapping")
            if segment.source_end_ms > source_duration_ms + 1:
                raise ValueError("Timeline exceeds source duration")
            previous_output_end = segment.output_end_ms
            previous_source_end = segment.source_end_ms
        if previous_output_end != self.duration_ms:
            raise ValueError("Timeline must end at the output duration")

        self._validate_timed_layers()
        self._validate_assets()
        return self

    def _validate_timed_layers(self) -> None:
        if self.scenes[0].start_ms != 0:
            raise ValueError("Scenes must start at zero")
        previous_scene_end = 0
        for scene in self.scenes:
            if scene.start_ms != previous_scene_end:
                raise ValueError("Scenes must be ordered and contiguous")
            if scene.end_ms > self.duration_ms:
                raise ValueError("Scene exceeds output duration")
            previous_scene_end = scene.end_ms
        if previous_scene_end != self.duration_ms:
            raise ValueError("Scenes must end at the output duration")

        for page in self.caption_pages:
            if page.end_ms > self.duration_ms:
                raise ValueError("Caption page exceeds output duration")
            previous_token_start = -1
            for token in page.tokens:
                if token.end_ms <= token.start_ms:
                    raise ValueError(
                        "Caption token must have positive source duration"
                    )
                if token.start_ms < previous_token_start:
                    raise ValueError("Caption tokens must be ordered")
                previous_token_start = token.start_ms

        for graphic in self.graphics:
            if graphic.end_ms > self.duration_ms:
                raise ValueError("Graphic cue exceeds output duration")
        visual_ids: set[str] = set()
        for visual in self.editorial_visuals:
            if visual.id in visual_ids:
                raise ValueError("Editorial visual identifiers must be unique")
            visual_ids.add(visual.id)
            if visual.end_ms > self.duration_ms:
                raise ValueError("Editorial visual exceeds output duration")
        for scene in self.scenes:
            if scene.visual_id is None:
                continue
            if scene.visual_id not in visual_ids:
                raise ValueError("Scene must reference an editorial visual")
            visual = next(
                item
                for item in self.editorial_visuals
                if item.id == scene.visual_id
            )
            if (
                visual.start_ms != scene.start_ms
                or visual.end_ms != scene.end_ms
            ):
                raise ValueError(
                    "Editorial visual timing must match its scene"
                )
        for keyframe in self.reframing:
            if keyframe.time_ms >= self.duration_ms:
                raise ValueError("Reframe keyframe exceeds output duration")
        for cue in self.audio.sfx_cues:
            if cue.start_ms >= self.duration_ms:
                raise ValueError("Sound-effect cue exceeds output duration")

    def _validate_assets(self) -> None:
        asset_ids: set[str] = set()
        audio_asset_ids: set[str] = set()
        for asset in self.assets:
            if asset.id in asset_ids:
                raise ValueError("Asset identifiers must be unique")
            asset_ids.add(asset.id)
            if asset.kind == "audio":
                audio_asset_ids.add(asset.id)
            normalized_path = asset.path.replace("\\", "/").lower()
            normalized_provenance = asset.provenance.lower()
            if (
                "training-video" in normalized_provenance
                or "training videos data" in normalized_path
            ):
                raise ValueError("Training-video media cannot be used as an asset")
            if asset.end_ms is not None and asset.end_ms > self.duration_ms:
                raise ValueError("Asset schedule exceeds output duration")

        if (
            self.audio.music_asset_id is not None
            and self.audio.music_asset_id not in audio_asset_ids
        ):
            raise ValueError("Music asset must reference an audio asset")
        if (
            self.audio.dialogue_asset_id is not None
            and self.audio.dialogue_asset_id not in audio_asset_ids
        ):
            raise ValueError("Dialogue asset must reference an audio asset")
        referenced_sfx = {
            *self.audio.sfx_asset_ids,
            *(cue.asset_id for cue in self.audio.sfx_cues),
        }
        if not referenced_sfx.issubset(audio_asset_ids):
            raise ValueError("Sound effects must reference audio assets")


class QCCheck(BaseModel):
    name: str
    passed: bool
    measured: float | int | str | None = None
    target: float | int | str | None = None
    detail: str | None = None


class QCMeasurements(BaseModel):
    integrated_lufs: float
    true_peak_dbtp: float
    longest_silence_ms: int = Field(ge=0)
    black_frame_ratio: float = Field(ge=0, le=1)
    freeze_frame_ratio: float = Field(ge=0, le=1)
    cuts_per_minute: float = Field(ge=0)
    median_shot_ms: int = Field(ge=0)
    cut_onset_percent: float = Field(ge=0, le=100)
    caption_overflow_count: int = Field(ge=0)
    meaningful_visual_coverage: float = Field(ge=0, le=1)


class QCReport(BaseModel):
    passed: bool
    style_score: float = Field(ge=0, le=100)
    checks: list[QCCheck]
    repair_attempts: int = Field(default=0, ge=0, le=2)


class PipelineResult(BaseModel):
    output_metadata: VideoMetadata
    caption_count: int
    cut_timestamps: list[float]
    transcript_text: str
    broll_coverage: float = Field(default=0, ge=0, le=1)
    style_score: float = Field(default=0, ge=0, le=100)
    qc_passed: bool = False


JobState = Literal[
    "queued",
    "uploading",
    "analyzing",
    "transcribing",
    "cleaning",
    "planning",
    "sourcing",
    "rendering",
    "mastering",
    "quality_control",
    "verifying",
    "completed",
    "failed",
]


class JobRecord(BaseModel):
    id: str
    original_filename: str
    state: JobState
    progress: int
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    result: PipelineResult | None = None
