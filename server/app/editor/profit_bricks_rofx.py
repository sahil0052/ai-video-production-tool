from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import shutil
from statistics import median
from typing import Any

from app.editor.human_reference_0810 import (
    _detect_silence_intervals,
    _prepare_dialogue_media,
    _remap_transcript,
    _safe_sfx_start,
    build_dialogue_edl_from_silences,
    measure_visible_interval_duration,
)
from app.editor.transcript import (
    _align_corrected_tokens,
    repair_nonpositive_word_durations,
)
from app.models import (
    AssetRef,
    AudioPlan,
    EvidenceItem,
    GainAutomation,
    OutputSpec,
    SfxCue,
    SpeechProtectionWindow,
    TranscriptSegment,
    TranscriptWord,
    VideoMetadata,
)
from app.production_models import (
    BlueprintLayerSpec,
    EffectKeyframe,
    FlowShotSpec,
    KineticTextCue,
    LayerBounds,
    MotionEventSpec,
    OpacityKeyframe,
    ProductionBlueprint,
    TransformKeyframe,
)
from PIL import (
    Image,
    ImageChops,
    ImageDraw,
    ImageEnhance,
    ImageFilter,
    ImageFont,
)


OUTPUT_DURATION_MS = 44_370
_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_STYLE_REFERENCE = Path(r"D:\Downloads\Profit Bricks_Reel 04.mp4")
_DEFAULT_ANALYSIS_DIR = _WORKSPACE_ROOT / "storage" / "analysis" / "0811"
_DEFAULT_SEED_DIR = (
    _WORKSPACE_ROOT
    / "storage"
    / "deliverables"
    / "0810-production-v2-human-reference"
)
_DEFAULT_BRAND_LOGO = (
    _WORKSPACE_ROOT
    / "storage"
    / "assets"
    / "brand"
    / "profit-bricks-forex-automation.png"
)
_DEFAULT_SOCIAL_SFX_DIR = (
    _WORKSPACE_ROOT
    / "storage"
    / "assets"
    / "audio"
    / "social-kinetic"
)
_DEFAULT_SOCIAL_SFX_LICENSE_DIR = (
    _WORKSPACE_ROOT
    / "storage"
    / "assets"
    / "licensed"
    / "mixkit"
    / "sfx"
)
_SANCTIONS_SOURCE_LINE = (
    "CFTC: OVER $225M COMBINED - COURT ORDER APRIL 22, 2024"
)
_DEFAULT_SILENCE_INTERVALS_MS = [
    (0, 144),
    (2_416, 2_719),
    (4_403, 4_585),
    (5_118, 5_411),
    (7_057, 7_216),
    (9_209, 9_573),
    (13_254, 13_814),
    (18_650, 18_946),
    (20_943, 21_450),
    (29_201, 29_513),
    (34_252, 34_464),
    (45_887, 46_152),
    (46_819, 47_033),
]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _copy_required(source: Path, destination: Path) -> Path:
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def _prepare_transparent_logo(source: Path, destination: Path) -> Path:
    if not source.is_file():
        raise FileNotFoundError(source)
    logo_rgb = Image.open(source).convert("RGB")
    white = Image.new("RGB", logo_rgb.size, (255, 255, 255))
    difference = ImageChops.difference(logo_rgb, white).convert("L")
    alpha = difference.point(
        lambda value: (
            0
            if value <= 3
            else min(255, round((value - 3) * 12))
        )
    )
    logo = logo_rgb.convert("RGBA")
    logo.putalpha(alpha)
    content_box = alpha.point(
        lambda value: 255 if value > 12 else 0
    ).getbbox()
    if content_box is not None:
        logo = logo.crop(content_box)
    padding = max(2, min(24, round(min(logo.size) * 0.02)))
    padded = Image.new(
        "RGBA",
        (logo.width + padding * 2, logo.height + padding * 2),
        (0, 0, 0, 0),
    )
    padded.alpha_composite(logo, (padding, padding))
    destination.parent.mkdir(parents=True, exist_ok=True)
    padded.save(destination, optimize=True)
    return destination


def _font(size: int, *, bold: bool = True) -> ImageFont.FreeTypeFont:
    candidates = [
        Path(r"C:\Windows\Fonts\arialbd.ttf")
        if bold
        else Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\calibrib.ttf")
        if bold
        else Path(r"C:\Windows\Fonts\calibri.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def build_rofx_schedule() -> list[dict[str, Any]]:
    specs = [
        (0, 3_600, "presenter", "zomato-hook"),
        (3_600, 4_880, "licensed-context", "empty-kitchen-context"),
        (4_880, 6_600, "presenter", "rofx-case-reveal"),
        (6_600, 7_760, "flow-illustrative", "rofx-robot-reveal"),
        (7_760, 11_630, "presenter", "forex-explanation"),
        (11_630, 14_560, "presenter", "rofx-identity"),
        (14_560, 16_200, "flow-illustrative", "claimed-trades"),
        (16_200, 18_160, "direct-evidence", "reserve-claim-proof"),
        (18_160, 21_460, "presenter", "customer-number"),
        (21_460, 24_640, "direct-evidence", "fund-scale-proof"),
        (24_640, 26_000, "direct-evidence", "court-overview"),
        (26_000, 28_520, "direct-evidence", "no-trading-proof"),
        (28_520, 31_230, "licensed-context", "fund-transfer-context"),
        (31_230, 33_120, "presenter", "april-order-reset"),
        (33_120, 36_190, "direct-evidence", "sanctions-proof"),
        (36_190, 40_290, "presenter", "transparency-lesson"),
        (40_290, OUTPUT_DURATION_MS, "presenter", "follow-cta"),
    ]
    shots = [
        {
            "id": f"shot-{index:02d}",
            "start_ms": start_ms,
            "end_ms": end_ms,
            "source_role": source_role,
            "editorial_role": editorial_role,
            "reference_role": "primary-human",
        }
        for index, (
            start_ms,
            end_ms,
            source_role,
            editorial_role,
        ) in enumerate(specs, start=1)
    ]
    durations = [shot["end_ms"] - shot["start_ms"] for shot in shots]
    if not 2_300 <= median(durations) <= 3_000:
        raise ValueError("ROFX schedule drifted from social-kinetic pacing")
    return shots


def build_rofx_text_cues() -> list[KineticTextCue]:
    return [
        KineticTextCue(
            id="text-zomato-order",
            start_ms=300,
            end_ms=1_200,
            text="ZOMATO ORDER",
            family="hero-condensed",
            x=540,
            y=1_270,
            max_width=940,
            animation="slam",
        ),
        KineticTextCue(
            id="text-no-food",
            start_ms=900,
            end_ms=2_400,
            text="NO FOOD?",
            family="outlined-stack",
            x=540,
            y=1_500,
            max_width=900,
            animation="stack",
        ),
        KineticTextCue(
            id="text-rofx",
            start_ms=5_000,
            end_ms=5_900,
            text="ROFX",
            family="cyan-secondary",
            x=540,
            y=1_420,
            max_width=760,
            animation="rise",
        ),
        KineticTextCue(
            id="text-forex-robot",
            start_ms=6_700,
            end_ms=7_600,
            text="FOREX ROBOT",
            family="outlined-stack",
            x=540,
            y=1_430,
            max_width=930,
            animation="stack",
        ),
        KineticTextCue(
            id="text-successful-trades",
            start_ms=14_800,
            end_ms=15_600,
            text="SUCCESSFUL TRADES?",
            family="correction-symbol",
            x=540,
            y=1_420,
            max_width=940,
            animation="draw",
        ),
        KineticTextCue(
            id="text-claim-source",
            start_ms=16_300,
            end_ms=17_100,
            text="SOURCE: CFTC COMPLAINT",
            family="micro-source",
            x=540,
            y=1_760,
            max_width=940,
            animation="hard-cut",
        ),
        KineticTextCue(
            id="text-customers",
            start_ms=18_500,
            end_ms=19_600,
            text="1100+ CUSTOMERS",
            family="gradient-number",
            x=540,
            y=1_080,
            max_width=980,
            animation="glow",
        ),
        KineticTextCue(
            id="text-customers-source",
            start_ms=18_650,
            end_ms=19_550,
            text="CFTC: OVER 1100 CUSTOMERS",
            family="micro-source",
            x=540,
            y=1_450,
            max_width=760,
            animation="hard-cut",
            z_index=61,
        ),
        KineticTextCue(
            id="text-funds",
            start_ms=22_000,
            end_ms=23_100,
            text="AT LEAST $58M",
            family="gradient-number",
            x=540,
            y=740,
            max_width=980,
            animation="glow",
        ),
        KineticTextCue(
            id="text-no-trading",
            start_ms=26_300,
            end_ms=27_700,
            text="NO FOREX TRADING",
            family="correction-symbol",
            x=540,
            y=1_430,
            max_width=970,
            animation="draw",
            secondary_text="NO ROFX ROBOT",
        ),
        KineticTextCue(
            id="text-april",
            start_ms=31_500,
            end_ms=32_300,
            text="APRIL 2024",
            family="cyan-secondary",
            x=540,
            y=1_420,
            max_width=820,
            animation="rise",
        ),
        KineticTextCue(
            id="text-order-total",
            start_ms=33_400,
            end_ms=34_900,
            text="OVER $225M ORDERED",
            family="gradient-number",
            x=540,
            y=350,
            max_width=1_000,
            animation="glow",
        ),
        KineticTextCue(
            id="text-follow",
            start_ms=41_500,
            end_ms=43_100,
            text="FOLLOW",
            family="cta-quote",
            x=540,
            y=1_500,
            max_width=860,
            animation="quote-pop",
        ),
    ]


def build_rofx_flow_shots(output_dir: Path) -> list[FlowShotSpec]:
    plates = output_dir.expanduser().resolve() / "flow-plates"
    constraints = [
        "Single continuous portrait shot with one clear subject",
        "No readable text, symbols, logos, captions or watermarks",
        "No software UI, code, charts, numbers, currencies or documents",
        "No internal cuts, flicker, warped hands or duplicate limbs",
        "Bright commercial exposure and safe center framing",
    ]
    return [
        FlowShotSpec(
            id="flow-rofx-robot",
            start_ms=6_600,
            end_ms=7_760,
            editorial_role="claimed-forex-robot",
            prompt=(
                "Premium bright portrait cinematography of one polished "
                "humanoid robot making deliberate physical control movements "
                "at an abstract financial operations desk. Moving cyan and "
                "amber reflections, realistic materials, controlled camera "
                "push-in, no readable screens or symbols."
            ),
            mode="i2v",
            model="veo-lite",
            input_plates=[
                str(plates / "rofx-robot-start.png"),
                str(plates / "rofx-robot-end.png"),
            ],
            requested_content=["process-illustration"],
            constraints=constraints,
        ),
        FlowShotSpec(
            id="flow-risk-control",
            start_ms=14_560,
            end_ms=16_200,
            editorial_role="claimed-risk-control",
            prompt=(
                "Bright cinematic portrait shot of one humanoid robot "
                "carefully balancing two physical control levers while a "
                "human supervisor observes from a safe distance. Premium "
                "commercial lighting, subtle parallax, realistic anatomy, "
                "one continuous move, no readable displays or symbols."
            ),
            mode="i2v",
            model="veo-lite",
            input_plates=[
                str(plates / "risk-control-start.png"),
                str(plates / "risk-control-end.png"),
            ],
            requested_content=["physical-metaphor"],
            constraints=constraints,
        ),
    ]


def build_rofx_evidence_items(output_dir: Path) -> list[EvidenceItem]:
    del output_dir
    accessed = datetime(2026, 8, 12, tzinfo=UTC)
    complaint_url = "https://www.cftc.gov/PressRoom/PressReleases/8486-22"
    order_url = (
        "https://www.cftc.gov/media/10671/"
        "enfnotusrofxorderofdefaultfinaljudgment042224/download"
    )
    release_url = "https://www.cftc.gov/PressRoom/PressReleases/8910-24"
    return [
        EvidenceItem(
            id="cftc-rofx-robot-claim",
            claim=(
                "ROFX claimed to trade forex using a highly successful "
                "automated trading robot."
            ),
            source_title="CFTC Charges ROFX Defendants with $58 Million Fraud",
            source_url=complaint_url,
            source_type="official",
            capture_path="source-captures/cftc-2022-robot-claim.png",
            accessed_at=accessed,
            published_at=datetime(2022, 1, 28, tzinfo=UTC),
            status="verified",
            visible_excerpt="highly successful automated trading robot",
            license="Official public record used as editorial evidence",
        ),
        EvidenceItem(
            id="cftc-rofx-customers",
            claim="More than 1,100 customers opened ROFX trading accounts.",
            source_title="CFTC Charges ROFX Defendants with $58 Million Fraud",
            source_url=complaint_url,
            source_type="official",
            capture_path="source-captures/cftc-2022-customers.png",
            accessed_at=accessed,
            published_at=datetime(2022, 1, 28, tzinfo=UTC),
            status="verified",
            visible_excerpt="over 1,100 customers opened trading accounts",
            license="Official public record used as editorial evidence",
        ),
        EvidenceItem(
            id="cftc-rofx-58m",
            claim="Defendants allegedly received at least $58 million.",
            source_title="CFTC Charges ROFX Defendants with $58 Million Fraud",
            source_url=complaint_url,
            source_type="official",
            capture_path="source-captures/cftc-2022-58m.png",
            accessed_at=accessed,
            published_at=datetime(2022, 1, 28, tzinfo=UTC),
            status="verified",
            visible_excerpt="received at least $58 million from customers",
            license="Official public record used as editorial evidence",
        ),
        EvidenceItem(
            id="court-no-trading",
            claim=(
                "The court found customer funds were not used for forex "
                "trading."
            ),
            source_title="Order of Default Final Judgment - NOTUS LLC d/b/a ROFX",
            source_url=order_url,
            source_type="primary",
            capture_path="source-captures/court-order-page-10.png",
            accessed_at=accessed,
            published_at=datetime(2024, 4, 22, tzinfo=UTC),
            status="verified",
            visible_excerpt="did not trade forex for customers",
            license="Federal court record used as editorial evidence",
        ),
        EvidenceItem(
            id="court-no-robot",
            claim="The court found there was no ROFX forex trading robot.",
            source_title="Order of Default Final Judgment - NOTUS LLC d/b/a ROFX",
            source_url=order_url,
            source_type="primary",
            capture_path="source-captures/court-order-page-11.png",
            accessed_at=accessed,
            published_at=datetime(2024, 4, 22, tzinfo=UTC),
            status="verified",
            visible_excerpt="there was no ROFX forex trading robot",
            license="Federal court record used as editorial evidence",
        ),
        EvidenceItem(
            id="court-transfers",
            claim=(
                "Customer funds were transferred to offshore entities and "
                "personal accounts."
            ),
            source_title="Order of Default Final Judgment - NOTUS LLC d/b/a ROFX",
            source_url=order_url,
            source_type="primary",
            capture_path="source-captures/court-order-page-11.png",
            accessed_at=accessed,
            published_at=datetime(2024, 4, 22, tzinfo=UTC),
            status="verified",
            visible_excerpt="transferring those same funds to various offshore entities",
            license="Federal court record used as editorial evidence",
        ),
        EvidenceItem(
            id="court-restitution",
            claim="The court ordered $56,362,279.21 in restitution.",
            source_title="Order of Default Final Judgment - NOTUS LLC d/b/a ROFX",
            source_url=order_url,
            source_type="primary",
            capture_path="source-captures/court-order-page-28.png",
            accessed_at=accessed,
            published_at=datetime(2024, 4, 22, tzinfo=UTC),
            status="verified",
            visible_excerpt="$56,362,279.21",
            license="Federal court record used as editorial evidence",
        ),
        EvidenceItem(
            id="court-penalty",
            claim="The court ordered a $169,086,837.63 civil monetary penalty.",
            source_title="Order of Default Final Judgment - NOTUS LLC d/b/a ROFX",
            source_url=order_url,
            source_type="primary",
            capture_path="source-captures/court-order-page-31.png",
            accessed_at=accessed,
            published_at=datetime(2024, 4, 22, tzinfo=UTC),
            status="verified",
            visible_excerpt="$169,086,837.63",
            license="Federal court record used as editorial evidence",
        ),
        EvidenceItem(
            id="cftc-over-225m",
            claim=(
                "The CFTC reported more than $225 million in combined "
                "restitution and civil monetary penalties."
            ),
            source_title="Miami Federal Court Orders Over $225 Million",
            source_url=release_url,
            source_type="official",
            capture_path="source-captures/cftc-2024-over-225m.png",
            accessed_at=accessed,
            published_at=datetime(2024, 5, 14, tzinfo=UTC),
            status="verified",
            visible_excerpt="pay over $225 million",
            license="Official public record used as editorial evidence",
        ),
    ]


def load_rofx_transcript(
    analysis_dir: Path = _DEFAULT_ANALYSIS_DIR,
) -> list[TranscriptSegment]:
    local_payload = json.loads(
        (analysis_dir / "transcript-whisper.json").read_text(
            encoding="utf-8"
        )
    )
    groq_payload = json.loads(
        (analysis_dir / "transcript-groq-raw.json").read_text(
            encoding="utf-8"
        )
    )
    corrected_texts = [
        str(item["text"]).strip()
        for item in local_payload
        if str(item.get("text", "")).strip()
    ]
    target_tokens = [
        token
        for text in corrected_texts
        for token in text.split()
    ]
    source_words = [
        TranscriptWord(
            start=float(item["start"]),
            end=float(item["end"]),
            text=str(item["word"]).strip(),
        )
        for item in groq_payload.get("words", [])
        if str(item.get("word", "")).strip()
    ]
    if not source_words:
        raise ValueError("Groq transcript does not contain word timestamps")
    duration = float(groq_payload.get("duration") or source_words[-1].end)
    aligned = _align_corrected_tokens(
        TranscriptSegment(
            start=0,
            end=duration,
            text=" ".join(word.text for word in source_words),
            words=source_words,
        ),
        target_tokens,
    )
    segments: list[TranscriptSegment] = []
    cursor = 0
    for text in corrected_texts:
        count = len(text.split())
        words = aligned[cursor : cursor + count]
        cursor += count
        segments.append(
            TranscriptSegment(
                start=words[0].start,
                end=words[-1].end,
                text=text,
                words=words,
            )
        )
    repaired = repair_nonpositive_word_durations(segments)
    if any(
        word.end <= word.start
        for segment in repaired
        for word in segment.words
    ):
        raise ValueError("ROFX transcript contains non-positive word timing")
    return repaired


def build_rofx_audio_plan(
    segments: list[TranscriptSegment],
) -> AudioPlan:
    windows = [
        SpeechProtectionWindow(
            start_ms=max(0, round(word.start * 1000) - 100),
            end_ms=min(
                OUTPUT_DURATION_MS,
                round(word.start * 1000) + 120,
            ),
            word=word.text,
        )
        for segment in segments
        for word in segment.words
        if round(word.start * 1000) < OUTPUT_DURATION_MS
    ]
    candidate_cues = [
        ("sfx-zomato", "sfx-impact", 300, 100, -16, "impact", "hook"),
        ("sfx-no-food", "sfx-snap", 950, 80, -17, "click", "hook stack"),
        ("sfx-empty", "sfx-whoosh", 3_600, 110, -15, "whoosh", "context"),
        (
            "sfx-empty-accent",
            "sfx-impact",
            3_620,
            110,
            -12,
            "impact",
            "context cut accent",
        ),
        ("sfx-rofx", "sfx-click", 4_950, 90, -18, "click", "case reveal"),
        ("sfx-robot", "sfx-impact", 6_600, 110, -13, "impact", "robot"),
        ("sfx-forex", "sfx-whoosh", 7_760, 110, -18, "whoosh", "forex"),
        ("sfx-identity", "sfx-click", 11_630, 90, -18, "click", "identity"),
        ("sfx-claim", "sfx-snap", 14_440, 60, -12, "click", "claim"),
        ("sfx-proof", "sfx-click", 16_200, 90, -18, "click", "proof"),
        ("sfx-customers", "sfx-snap", 18_500, 80, -16, "click", "number"),
        ("sfx-funds", "sfx-impact", 21_460, 110, -15, "impact", "$58M"),
        ("sfx-court", "sfx-impact", 24_640, 110, -12, "impact", "court"),
        ("sfx-highlight", "sfx-click", 26_300, 90, -18, "click", "finding"),
        (
            "sfx-funds-out",
            "sfx-click",
            23_700,
            90,
            -18,
            "click",
            "fund evidence reset",
        ),
        ("sfx-april", "sfx-riser", 31_230, 110, -18, "riser", "date"),
        ("sfx-order", "sfx-impact", 33_000, 110, -12, "impact", "order"),
        ("sfx-lesson", "sfx-snap", 36_820, 60, -13.5, "click", "lesson"),
        ("sfx-follow", "sfx-pop", 41_500, 90, -15, "notification", "CTA"),
    ]
    source_starts_ms = {
        "sfx-empty": 580,
        "sfx-empty-accent": 260,
        "sfx-robot": 260,
        "sfx-court": 300,
    }
    cues = [
        SfxCue(
            id=cue_id,
            asset_id=asset_id,
            start_ms=_safe_sfx_start(
                desired_ms=desired_ms,
                duration_ms=duration_ms,
                windows=windows,
            ),
            source_start_ms=source_starts_ms.get(cue_id, 0),
            duration_ms=duration_ms,
            volume=0.35,
            gain_db=gain_db,
            kind=kind,
            reason=reason,
        )
        for (
            cue_id,
            asset_id,
            desired_ms,
            duration_ms,
            gain_db,
            kind,
            reason,
        ) in candidate_cues
    ]
    automation = [
        GainAutomation(
            start_ms=max(0, round(segment.start * 1000) - 80),
            end_ms=min(
                OUTPUT_DURATION_MS,
                round(segment.end * 1000) + 120,
            ),
            gain_db=-10,
            reason="Duck music beneath narration",
        )
        for segment in segments
        if round(segment.start * 1000) < OUTPUT_DURATION_MS
    ]
    return AudioPlan(
        integrated_lufs=-13.5,
        true_peak_dbtp=-1.0,
        target_lra_lu=2.4,
        music_bpm=126,
        dialogue_asset_id="dialogue-original",
        dialogue_offset_ms=0,
        music_asset_id="music-social-kinetic",
        music_duck_db=10,
        music_base_gain_db=-27,
        music_gain_automation=automation,
        speech_protection_windows=windows,
        sfx_asset_ids=sorted({cue.asset_id for cue in cues}),
        sfx_cues=cues,
    )


def _gradient(
    top: tuple[int, int, int],
    bottom: tuple[int, int, int],
) -> Image.Image:
    image = Image.new("RGB", (1_080, 1_920), top)
    draw = ImageDraw.Draw(image)
    for y in range(1_920):
        progress = y / 1_919
        color = tuple(
            round(start + (end - start) * progress)
            for start, end in zip(top, bottom, strict=True)
        )
        draw.line((0, y, 1_080, y), fill=color)
    return image


def _build_flow_plate(
    destination: Path,
    *,
    palette: tuple[tuple[int, int, int], tuple[int, int, int]],
    subject: str,
    end_state: bool,
) -> None:
    image = _gradient(*palette).convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    center_x = 600 if end_state else 480
    center_y = 850
    for radius, alpha in ((420, 25), (280, 42), (160, 65)):
        draw.ellipse(
            (
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius,
            ),
            fill=(85, 225, 245, alpha),
        )
    if subject == "robot":
        draw.rounded_rectangle(
            (center_x - 165, 430, center_x + 165, 1_380),
            radius=100,
            fill=(215, 232, 238, 235),
            outline=(30, 90, 115, 230),
            width=10,
        )
        draw.ellipse(
            (center_x - 135, 300, center_x + 135, 570),
            fill=(228, 242, 246, 245),
            outline=(25, 85, 112, 230),
            width=10,
        )
        draw.ellipse(
            (center_x - 70, 385, center_x - 25, 430),
            fill=(45, 230, 255, 255),
        )
        draw.ellipse(
            (center_x + 25, 385, center_x + 70, 430),
            fill=(45, 230, 255, 255),
        )
        lever_y = 1_250 if end_state else 1_380
        draw.rounded_rectangle(
            (140, lever_y, 940, lever_y + 150),
            radius=36,
            fill=(10, 28, 43, 220),
        )
    else:
        draw.rounded_rectangle(
            (180, 520, 900, 1_350),
            radius=70,
            fill=(225, 237, 239, 235),
            outline=(28, 85, 105, 220),
            width=10,
        )
        offset = 70 if end_state else -70
        draw.line(
            (540, 700, 540 + offset, 1_150),
            fill=(242, 80, 70, 230),
            width=30,
        )
        draw.line(
            (540, 700, 540 - offset, 1_150),
            fill=(105, 224, 120, 230),
            width=30,
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(destination, quality=94)


def _build_rofx_flow_plates(output_dir: Path) -> None:
    plates = output_dir / "flow-plates"
    _build_flow_plate(
        plates / "rofx-robot-start.png",
        palette=((205, 235, 240), (15, 52, 72)),
        subject="robot",
        end_state=False,
    )
    _build_flow_plate(
        plates / "rofx-robot-end.png",
        palette=((225, 242, 245), (20, 67, 88)),
        subject="robot",
        end_state=True,
    )
    _build_flow_plate(
        plates / "risk-control-start.png",
        palette=((238, 239, 226), (38, 66, 78)),
        subject="risk",
        end_state=False,
    )
    _build_flow_plate(
        plates / "risk-control-end.png",
        palette=((246, 244, 221), (32, 77, 87)),
        subject="risk",
        end_state=True,
    )


def _crop_normalized(
    image: Image.Image,
    box: tuple[float, float, float, float],
) -> Image.Image:
    width, height = image.size
    left, top, right, bottom = box
    return image.crop(
        (
            round(left * width),
            round(top * height),
            round(right * width),
            round(bottom * height),
        )
    )


def _build_source_card(
    *,
    source: Path,
    destination: Path,
    crop: tuple[float, float, float, float],
    label: str,
    source_line: str,
    highlight: tuple[float, float, float, float] | None = None,
) -> None:
    canvas = Image.new("RGB", (1_080, 1_920), (246, 247, 244))
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rectangle((0, 0, 1_080, 205), fill=(11, 29, 63, 255))
    draw.rectangle((0, 0, 18, 205), fill=(236, 255, 58, 255))
    draw.text((55, 58), label, font=_font(52), fill=(255, 255, 255))
    raw = Image.open(source).convert("RGB")
    excerpt = _crop_normalized(raw, crop)
    scale = min(980 / excerpt.width, 1_485 / excerpt.height)
    resized = excerpt.resize(
        (
            max(1, round(excerpt.width * scale)),
            max(1, round(excerpt.height * scale)),
        ),
        Image.Resampling.LANCZOS,
    )
    x = (1_080 - resized.width) // 2
    y = 250 + (1_485 - resized.height) // 2
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow, "RGBA")
    shadow_draw.rounded_rectangle(
        (x - 16, y - 16, x + resized.width + 16, y + resized.height + 16),
        radius=24,
        fill=(0, 0, 0, 45),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(16))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), shadow)
    canvas.alpha_composite(resized.convert("RGBA"), (x, y))
    if highlight is not None:
        left, top, right, bottom = highlight
        marker = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        marker_draw = ImageDraw.Draw(marker, "RGBA")
        marker_draw.rounded_rectangle(
            (
                x + round(left * resized.width),
                y + round(top * resized.height),
                x + round(right * resized.width),
                y + round(bottom * resized.height),
            ),
            radius=10,
            fill=(232, 255, 55, 65),
            outline=(214, 52, 45, 235),
            width=6,
        )
        canvas = Image.alpha_composite(canvas, marker)
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.text(
        (55, 1_790),
        source_line,
        font=_font(25, bold=False),
        fill=(28, 38, 48, 255),
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(destination, quality=94)


def _build_evidence_pip(
    *,
    source: Path,
    destination: Path,
) -> None:
    raw = Image.open(source).convert("RGB")
    excerpt = _crop_normalized(raw, (0.18, 0.07, 0.88, 0.52))
    canvas = Image.new("RGB", (900, 520), (245, 246, 243))
    scale = min(850 / excerpt.width, 400 / excerpt.height)
    resized = excerpt.resize(
        (round(excerpt.width * scale), round(excerpt.height * scale)),
        Image.Resampling.LANCZOS,
    )
    canvas.paste(resized, ((900 - resized.width) // 2, 30))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 455, 900, 520), fill=(11, 29, 63))
    draw.text(
        (28, 470),
        "SOURCE: CFTC",
        font=_font(26),
        fill=(255, 255, 255),
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, quality=94)


def _build_excerpt_pip(
    *,
    source: Path,
    destination: Path,
    crop: tuple[float, float, float, float],
    source_line: str,
    highlight: tuple[float, float, float, float] | None = None,
) -> None:
    raw = Image.open(source).convert("RGB")
    excerpt = _crop_normalized(raw, crop)
    canvas = Image.new("RGBA", (900, 650), (246, 247, 244, 255))
    scale = min(850 / excerpt.width, 520 / excerpt.height)
    resized = excerpt.resize(
        (
            max(1, round(excerpt.width * scale)),
            max(1, round(excerpt.height * scale)),
        ),
        Image.Resampling.LANCZOS,
    )
    x = (900 - resized.width) // 2
    y = 20 + (520 - resized.height) // 2
    canvas.alpha_composite(resized.convert("RGBA"), (x, y))
    if highlight is not None:
        left, top, right, bottom = highlight
        marker = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        marker_draw = ImageDraw.Draw(marker, "RGBA")
        marker_draw.rounded_rectangle(
            (
                x + round(left * resized.width),
                y + round(top * resized.height),
                x + round(right * resized.width),
                y + round(bottom * resized.height),
            ),
            radius=8,
            fill=(232, 255, 55, 48),
            outline=(214, 52, 45, 235),
            width=5,
        )
        canvas = Image.alpha_composite(canvas, marker)
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rectangle((0, 560, 900, 650), fill=(11, 29, 63, 255))
    draw.text(
        (28, 582),
        source_line,
        font=_font(28),
        fill=(255, 255, 255, 255),
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(destination, quality=95)


def _build_sanctions_card(
    *,
    restitution_source: Path,
    penalty_source: Path,
    destination: Path,
) -> None:
    canvas = Image.new("RGB", (1_080, 1_920), (247, 247, 244))
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rectangle((0, 0, 1_080, 205), fill=(11, 29, 63, 255))
    draw.rectangle((0, 0, 18, 205), fill=(236, 255, 58, 255))
    draw.text(
        (55, 58),
        "APRIL 22, 2024 COURT ORDER",
        font=_font(48),
        fill=(255, 255, 255),
    )
    sources = [
        (
            Image.open(restitution_source).convert("RGB"),
            (0.08, 0.51, 0.94, 0.84),
            255,
        ),
        (
            Image.open(penalty_source).convert("RGB"),
            (0.08, 0.21, 0.94, 0.55),
            1_015,
        ),
    ]
    for image, crop, y in sources:
        excerpt = _crop_normalized(image, crop)
        scale = min(980 / excerpt.width, 640 / excerpt.height)
        excerpt = excerpt.resize(
            (
                round(excerpt.width * scale),
                round(excerpt.height * scale),
            ),
            Image.Resampling.LANCZOS,
        )
        x = (1_080 - excerpt.width) // 2
        canvas.paste(excerpt, (x, y))
        draw.rounded_rectangle(
            (x - 6, y - 6, x + excerpt.width + 6, y + excerpt.height + 6),
            radius=12,
            outline=(214, 52, 45, 230),
            width=6,
        )
    draw.text(
        (55, 1_810),
        _SANCTIONS_SOURCE_LINE,
        font=_font(24, bold=False),
        fill=(28, 38, 48, 255),
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, quality=94)


def _prepare_evidence_assets(
    *,
    analysis_dir: Path,
    output_dir: Path,
) -> dict[str, Path]:
    captures = output_dir / "source-captures"
    captures.mkdir(parents=True, exist_ok=True)
    mapping = {
        "cftc_2022": (
            analysis_dir / "cftc-rofx-2022-full.png",
            captures / "cftc-rofx-2022-full.png",
        ),
        "cftc_2024": (
            analysis_dir / "cftc-rofx-2024-full.png",
            captures / "cftc-rofx-2024-full.png",
        ),
        "court_10": (
            analysis_dir / "pdf-pages" / "findings-10.png",
            captures / "court-order-page-10.png",
        ),
        "court_11": (
            analysis_dir / "pdf-pages" / "findings-11.png",
            captures / "court-order-page-11.png",
        ),
        "court_28": (
            analysis_dir / "pdf-pages" / "sanctions-28.png",
            captures / "court-order-page-28.png",
        ),
        "court_31": (
            analysis_dir / "pdf-pages" / "sanctions-31.png",
            captures / "court-order-page-31.png",
        ),
    }
    copied = {
        key: _copy_required(source, destination)
        for key, (source, destination) in mapping.items()
    }
    graphics = output_dir / "assets" / "graphics"
    outputs = {
        "pip": graphics / "cftc-rofx-pip.jpg",
        "claim": graphics / "cftc-rofx-claim-card.jpg",
        "funds": graphics / "cftc-rofx-58m-card.jpg",
        "funds_pip": graphics / "cftc-rofx-funds-pip.jpg",
        "court_pip": graphics / "court-overview-pip.jpg",
        "no_trading": graphics / "court-no-trading-card.jpg",
        "sanctions": graphics / "court-sanctions-card.jpg",
        "final_release": graphics / "cftc-over-225m-card.jpg",
    }
    _build_evidence_pip(
        source=copied["cftc_2022"],
        destination=outputs["pip"],
    )
    _build_source_card(
        source=copied["cftc_2022"],
        destination=outputs["claim"],
        crop=(0.18, 0.10, 0.86, 0.58),
        label="DIRECT CFTC SOURCE",
        source_line="CFTC RELEASE 8486-22",
        highlight=(0.03, 0.55, 0.97, 0.83),
    )
    _build_source_card(
        source=copied["cftc_2022"],
        destination=outputs["funds"],
        crop=(0.18, 0.27, 0.86, 0.52),
        label="CUSTOMER FUNDS - CFTC",
        source_line="CFTC RELEASE 8486-22",
        highlight=(0.02, 0.50, 0.98, 0.89),
    )
    _build_excerpt_pip(
        source=copied["cftc_2022"],
        destination=outputs["funds_pip"],
        crop=(0.18, 0.27, 0.86, 0.52),
        source_line="CFTC RELEASE 8486-22",
        highlight=(0.02, 0.50, 0.98, 0.89),
    )
    _build_excerpt_pip(
        source=copied["court_10"],
        destination=outputs["court_pip"],
        crop=(0.04, 0, 0.96, 0.43),
        source_line="FEDERAL COURT RECORD - APRIL 22, 2024",
        highlight=(0.02, 0.06, 0.98, 0.28),
    )
    _build_source_card(
        source=copied["court_11"],
        destination=outputs["no_trading"],
        crop=(0.06, 0.04, 0.94, 0.67),
        label="FEDERAL COURT FINDING",
        source_line="CASE 1:22-CV-20291 - ORDER PAGE 11",
        highlight=(0.02, 0.02, 0.98, 0.53),
    )
    _build_sanctions_card(
        restitution_source=copied["court_28"],
        penalty_source=copied["court_31"],
        destination=outputs["sanctions"],
    )
    _build_source_card(
        source=copied["cftc_2024"],
        destination=outputs["final_release"],
        crop=(0.18, 0.08, 0.86, 0.47),
        label="CFTC FINAL JUDGMENT RELEASE",
        source_line="CFTC RELEASE 8910-24",
        highlight=(0.02, 0.02, 0.98, 0.32),
    )
    return {**copied, **outputs}


def _presenter_layer(
    *,
    layer_id: str,
    shot_id: str,
    start_ms: int,
    end_ms: int,
    start_scale: float,
    end_scale: float,
    brightness: float = 0.92,
    saturation: float = 1.18,
    z_index: int = 1,
) -> BlueprintLayerSpec:
    duration = end_ms - start_ms
    return BlueprintLayerSpec(
        id=layer_id,
        shot_id=shot_id,
        start_ms=start_ms,
        end_ms=end_ms,
        source_role="presenter",
        asset_id="presenter-edl",
        source_start_ms=start_ms,
        source_end_ms=end_ms,
        bounds=LayerBounds(),
        fit="cover",
        transform_keyframes=[
            TransformKeyframe(at_ms=0, scale=start_scale),
            TransformKeyframe(at_ms=duration, scale=end_scale),
        ],
        effect_keyframes=[
            EffectKeyframe(
                at_ms=0,
                brightness=brightness,
                contrast=1.08,
                saturation=saturation,
            )
        ],
        z_index=z_index,
        muted=True,
        reference_role="primary-human",
    )


def build_rofx_layers() -> list[BlueprintLayerSpec]:
    layers = [
        _presenter_layer(
            layer_id="layer-hook-presenter",
            shot_id="shot-01",
            start_ms=0,
            end_ms=3_600,
            start_scale=1.03,
            end_scale=1.10,
            saturation=0.78,
        ),
        BlueprintLayerSpec(
            id="layer-empty-restaurant",
            shot_id="shot-02",
            start_ms=3_600,
            end_ms=4_880,
            source_role="licensed-context",
            asset_id="licensed-empty-restaurant",
            source_start_ms=700,
            source_end_ms=1_980,
            bounds=LayerBounds(),
            fit="cover",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, x=-24, scale=1.08),
                TransformKeyframe(at_ms=1_280, x=28, scale=1.18),
            ],
            effect_keyframes=[
                EffectKeyframe(
                    at_ms=0,
                    brightness=1.18,
                    contrast=1.04,
                    saturation=0.88,
                )
            ],
            z_index=10,
            muted=True,
            reference_role="primary-human",
        ),
        _presenter_layer(
            layer_id="layer-rofx-presenter",
            shot_id="shot-03",
            start_ms=4_880,
            end_ms=6_600,
            start_scale=1.11,
            end_scale=1.16,
        ),
        BlueprintLayerSpec(
            id="layer-rofx-pip",
            shot_id="shot-03",
            start_ms=5_060,
            end_ms=6_560,
            source_role="direct-evidence",
            kind="image",
            asset_id="evidence-cftc-pip",
            bounds=LayerBounds(x=90, y=1_190, width=900, height=520),
            fit="contain",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, y=42, scale=0.9),
                TransformKeyframe(at_ms=260, y=0, scale=1),
                TransformKeyframe(at_ms=1_500, y=-10, scale=1.03),
            ],
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=180, value=1),
            ],
            z_index=25,
            muted=True,
            border_radius=28,
            reference_role="secondary-10",
        ),
        BlueprintLayerSpec(
            id="layer-flow-rofx-robot",
            shot_id="shot-04",
            start_ms=6_600,
            end_ms=7_760,
            source_role="flow-illustrative",
            flow_shot_id="flow-rofx-robot",
            source_start_ms=0,
            source_end_ms=1_160,
            bounds=LayerBounds(),
            fit="cover",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, scale=1.03),
                TransformKeyframe(at_ms=1_160, x=-18, scale=1.13),
            ],
            effect_keyframes=[
                EffectKeyframe(
                    at_ms=0,
                    brightness=1.12,
                    contrast=1.05,
                    saturation=1.8,
                )
            ],
            z_index=10,
            muted=True,
            illustrative_label=True,
            reference_role="primary-human",
        ),
        _presenter_layer(
            layer_id="layer-forex-presenter",
            shot_id="shot-05",
            start_ms=7_760,
            end_ms=11_630,
            start_scale=1.0,
            end_scale=1.06,
        ),
        BlueprintLayerSpec(
            id="layer-dollar-pip",
            shot_id="shot-05",
            start_ms=8_150,
            end_ms=11_450,
            source_role="licensed-context",
            asset_id="licensed-dollar-bills",
            source_start_ms=2_000,
            source_end_ms=5_300,
            bounds=LayerBounds(x=65, y=1_190, width=455, height=500),
            fit="cover",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, y=35, scale=0.94),
                TransformKeyframe(at_ms=260, y=0, scale=1),
                TransformKeyframe(at_ms=3_300, x=-12, scale=1.08),
            ],
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=180, value=1),
            ],
            z_index=20,
            muted=True,
            border_radius=34,
            reference_role="primary-human",
        ),
        BlueprintLayerSpec(
            id="layer-euro-pip",
            shot_id="shot-05",
            start_ms=8_420,
            end_ms=11_450,
            source_role="licensed-context",
            asset_id="licensed-euro-counting",
            source_start_ms=1_000,
            source_end_ms=4_030,
            bounds=LayerBounds(x=560, y=1_190, width=455, height=500),
            fit="cover",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, y=35, scale=0.94),
                TransformKeyframe(at_ms=260, y=0, scale=1),
                TransformKeyframe(at_ms=3_030, x=12, scale=1.08),
            ],
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=180, value=1),
            ],
            z_index=20,
            muted=True,
            border_radius=34,
            reference_role="primary-human",
        ),
        _presenter_layer(
            layer_id="layer-identity-presenter",
            shot_id="shot-06",
            start_ms=11_630,
            end_ms=14_560,
            start_scale=1.11,
            end_scale=1.16,
        ),
        BlueprintLayerSpec(
            id="layer-identity-pip",
            shot_id="shot-06",
            start_ms=11_850,
            end_ms=14_400,
            source_role="direct-evidence",
            kind="image",
            asset_id="evidence-cftc-pip",
            bounds=LayerBounds(x=105, y=1_185, width=870, height=500),
            fit="contain",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, y=35, scale=0.95),
                TransformKeyframe(at_ms=240, y=0, scale=1),
                TransformKeyframe(at_ms=2_550, y=-10, scale=1.04),
            ],
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=180, value=1),
            ],
            z_index=20,
            muted=True,
            border_radius=28,
            reference_role="secondary-10",
        ),
        BlueprintLayerSpec(
            id="layer-flow-risk-control",
            shot_id="shot-07",
            start_ms=14_560,
            end_ms=16_200,
            source_role="flow-illustrative",
            flow_shot_id="flow-risk-control",
            source_start_ms=0,
            source_end_ms=1_640,
            bounds=LayerBounds(),
            fit="cover",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, x=18, scale=1.03),
                TransformKeyframe(at_ms=1_640, x=-16, scale=1.12),
            ],
            effect_keyframes=[
                EffectKeyframe(
                    at_ms=0,
                    brightness=1.09,
                    contrast=1.04,
                    saturation=0.9,
                )
            ],
            z_index=10,
            muted=True,
            illustrative_label=True,
            reference_role="primary-human",
        ),
        BlueprintLayerSpec(
            id="layer-claim-proof",
            shot_id="shot-08",
            start_ms=16_200,
            end_ms=18_160,
            source_role="direct-evidence",
            kind="image",
            asset_id="evidence-cftc-2022-claim",
            bounds=LayerBounds(),
            fit="fill",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, y=18, scale=1.01),
                TransformKeyframe(at_ms=1_960, y=-26, scale=1.12),
            ],
            effect_keyframes=[
                EffectKeyframe(
                    at_ms=0,
                    brightness=0.9,
                    contrast=1.02,
                    saturation=1.0,
                )
            ],
            z_index=10,
            muted=True,
            reference_role="secondary-10",
        ),
        _presenter_layer(
            layer_id="layer-customers-presenter",
            shot_id="shot-09",
            start_ms=18_160,
            end_ms=21_460,
            start_scale=1.13,
            end_scale=1.19,
        ),
        _presenter_layer(
            layer_id="layer-funds-presenter",
            shot_id="shot-10",
            start_ms=21_460,
            end_ms=24_640,
            start_scale=1.05,
            end_scale=1.08,
        ),
        BlueprintLayerSpec(
            id="layer-funds-proof",
            shot_id="shot-10",
            start_ms=22_050,
            end_ms=24_640,
            source_role="direct-evidence",
            kind="image",
            asset_id="evidence-cftc-funds-pip",
            bounds=LayerBounds(
                x=60,
                y=920,
                width=960,
                height=690,
            ),
            fit="fill",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, y=38, scale=0.94),
                TransformKeyframe(at_ms=240, y=0, scale=1),
                TransformKeyframe(at_ms=2_590, y=-10, scale=1.05),
            ],
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=700, value=1),
            ],
            z_index=20,
            muted=True,
            border_radius=28,
            reference_role="secondary-10",
        ),
        _presenter_layer(
            layer_id="layer-court-overview-presenter",
            shot_id="shot-11",
            start_ms=24_640,
            end_ms=26_000,
            start_scale=1.1,
            end_scale=1.14,
        ),
        BlueprintLayerSpec(
            id="layer-court-overview",
            shot_id="shot-11",
            start_ms=24_640,
            end_ms=26_000,
            source_role="direct-evidence",
            kind="image",
            asset_id="evidence-court-overview-pip",
            bounds=LayerBounds(
                x=90,
                y=1_030,
                width=900,
                height=650,
            ),
            fit="fill",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, y=34, scale=0.94),
                TransformKeyframe(at_ms=240, y=0, scale=1),
                TransformKeyframe(at_ms=1_360, y=-8, scale=1.04),
            ],
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=180, value=1),
            ],
            z_index=20,
            muted=True,
            border_radius=28,
            reference_role="secondary-10",
        ),
        BlueprintLayerSpec(
            id="layer-court-no-trading",
            shot_id="shot-12",
            start_ms=26_000,
            end_ms=28_520,
            source_role="direct-evidence",
            kind="image",
            asset_id="evidence-court-no-trading",
            bounds=LayerBounds(),
            fit="fill",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, y=22, scale=1),
                TransformKeyframe(at_ms=2_520, y=-30, scale=1.14),
            ],
            effect_keyframes=[
                EffectKeyframe(
                    at_ms=0,
                    brightness=0.9,
                    contrast=1.02,
                    saturation=1.0,
                )
            ],
            z_index=10,
            muted=True,
            reference_role="secondary-10",
        ),
        BlueprintLayerSpec(
            id="layer-transfer-context",
            shot_id="shot-13",
            start_ms=28_520,
            end_ms=31_230,
            source_role="licensed-context",
            asset_id="licensed-online-payment",
            source_start_ms=1_000,
            source_end_ms=3_710,
            bounds=LayerBounds(),
            fit="cover",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, x=24, scale=1.07),
                TransformKeyframe(at_ms=2_710, x=-20, scale=1.16),
            ],
            effect_keyframes=[
                EffectKeyframe(
                    at_ms=0,
                    brightness=1.05,
                    contrast=1.06,
                    saturation=0.88,
                )
            ],
            z_index=10,
            muted=True,
            reference_role="primary-human",
        ),
        BlueprintLayerSpec(
            id="layer-transfer-proof-pip",
            shot_id="shot-13",
            start_ms=29_050,
            end_ms=31_080,
            source_role="direct-evidence",
            kind="image",
            asset_id="evidence-court-no-trading",
            bounds=LayerBounds(x=75, y=1_220, width=930, height=520),
            fit="cover",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, y=34, scale=0.96),
                TransformKeyframe(at_ms=220, y=0, scale=1),
            ],
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=160, value=1),
            ],
            z_index=20,
            muted=True,
            border_radius=28,
            reference_role="secondary-10",
        ),
        _presenter_layer(
            layer_id="layer-april-presenter",
            shot_id="shot-14",
            start_ms=31_230,
            end_ms=33_120,
            start_scale=1.12,
            end_scale=1.17,
        ),
        _presenter_layer(
            layer_id="layer-sanctions-presenter",
            shot_id="shot-15",
            start_ms=33_120,
            end_ms=36_190,
            start_scale=1.04,
            end_scale=1.12,
        ),
        BlueprintLayerSpec(
            id="layer-court-sanctions",
            shot_id="shot-15",
            start_ms=33_120,
            end_ms=35_920,
            source_role="direct-evidence",
            kind="image",
            asset_id="evidence-court-sanctions",
            bounds=LayerBounds(),
            fit="fill",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, y=20, scale=1),
                TransformKeyframe(at_ms=2_800, y=-22, scale=1.1),
            ],
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=1),
                OpacityKeyframe(at_ms=2_400, value=1),
                OpacityKeyframe(at_ms=2_800, value=0),
            ],
            effect_keyframes=[
                EffectKeyframe(
                    at_ms=0,
                    brightness=0.9,
                    contrast=1.02,
                    saturation=1.0,
                )
            ],
            z_index=10,
            muted=True,
            reference_role="secondary-10",
        ),
        _presenter_layer(
            layer_id="layer-lesson-presenter",
            shot_id="shot-16",
            start_ms=36_190,
            end_ms=40_290,
            start_scale=1.20,
            end_scale=1.28,
        ),
        _presenter_layer(
            layer_id="layer-cta-presenter",
            shot_id="shot-17",
            start_ms=40_290,
            end_ms=OUTPUT_DURATION_MS,
            start_scale=1.15,
            end_scale=1.23,
        ),
        BlueprintLayerSpec(
            id="layer-brand-logo",
            shot_id="shot-17",
            start_ms=40_900,
            end_ms=41_600,
            source_role="deterministic-graphic",
            kind="image",
            asset_id="brand-logo-original",
            bounds=LayerBounds(x=325, y=1_130, width=430, height=360),
            fit="contain",
            transform_keyframes=[
                TransformKeyframe(at_ms=0, y=30, scale=0.88),
                TransformKeyframe(at_ms=220, y=0, scale=1),
                TransformKeyframe(at_ms=700, y=-4, scale=1.02),
            ],
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=120, value=1),
                OpacityKeyframe(at_ms=450, value=1),
                OpacityKeyframe(at_ms=700, value=0),
            ],
            z_index=20,
            muted=True,
            reference_role="primary-human",
        ),
    ]
    return layers


def build_rofx_motion_events() -> list[MotionEventSpec]:
    events = [
        MotionEventSpec(
            id=f"motion-{cue.id}",
            start_ms=cue.start_ms,
            end_ms=min(cue.end_ms, cue.start_ms + 420),
            kind="text-reveal",
            target_id=cue.id,
            intensity=0.68,
        )
        for cue in build_rofx_text_cues()
    ]
    events.extend(
        [
            MotionEventSpec(
                id="motion-hook-punch",
                start_ms=0,
                end_ms=360,
                kind="punch-crop",
                target_id="layer-hook-presenter",
                intensity=0.55,
            ),
            MotionEventSpec(
                id="motion-empty-push",
                start_ms=3_600,
                end_ms=4_000,
                kind="directional-jump",
                target_id="layer-empty-restaurant",
                intensity=0.48,
                direction="right",
            ),
            MotionEventSpec(
                id="motion-rofx-pip",
                start_ms=5_060,
                end_ms=5_360,
                kind="pip-pop",
                target_id="layer-rofx-pip",
                intensity=0.7,
            ),
            MotionEventSpec(
                id="motion-robot-punch",
                start_ms=6_600,
                end_ms=6_960,
                kind="punch-crop",
                target_id="layer-flow-rofx-robot",
                intensity=0.56,
            ),
            MotionEventSpec(
                id="motion-dollar-pip",
                start_ms=8_150,
                end_ms=8_430,
                kind="pip-pop",
                target_id="layer-dollar-pip",
                intensity=0.55,
            ),
            MotionEventSpec(
                id="motion-euro-pip",
                start_ms=8_420,
                end_ms=8_700,
                kind="pip-pop",
                target_id="layer-euro-pip",
                intensity=0.55,
            ),
            MotionEventSpec(
                id="motion-identity-pip",
                start_ms=11_850,
                end_ms=12_180,
                kind="pip-pop",
                target_id="layer-identity-pip",
                intensity=0.62,
            ),
            MotionEventSpec(
                id="motion-risk-punch",
                start_ms=14_560,
                end_ms=14_800,
                kind="punch-crop",
                target_id="layer-flow-risk-control",
                intensity=0.55,
            ),
            MotionEventSpec(
                id="motion-claim-highlight",
                start_ms=16_450,
                end_ms=17_200,
                kind="highlight-sweep",
                target_id="layer-claim-proof",
                intensity=0.72,
            ),
            MotionEventSpec(
                id="motion-customer-punch",
                start_ms=18_160,
                end_ms=18_520,
                kind="punch-crop",
                target_id="layer-customers-presenter",
                intensity=0.58,
            ),
            MotionEventSpec(
                id="motion-funds-proof",
                start_ms=22_900,
                end_ms=23_450,
                kind="proof-punch",
                target_id="layer-funds-proof",
                intensity=0.78,
            ),
            MotionEventSpec(
                id="motion-court-overview",
                start_ms=24_640,
                end_ms=25_020,
                kind="impact-flash",
                target_id="layer-court-overview",
                intensity=0.48,
            ),
            MotionEventSpec(
                id="motion-no-trading-highlight",
                start_ms=26_250,
                end_ms=27_150,
                kind="highlight-sweep",
                target_id="layer-court-no-trading",
                intensity=0.85,
            ),
            MotionEventSpec(
                id="motion-transfer-punch",
                start_ms=28_520,
                end_ms=28_900,
                kind="punch-crop",
                target_id="layer-transfer-context",
                intensity=0.5,
            ),
            MotionEventSpec(
                id="motion-transfer-proof",
                start_ms=29_050,
                end_ms=29_380,
                kind="pip-pop",
                target_id="layer-transfer-proof-pip",
                intensity=0.58,
            ),
            MotionEventSpec(
                id="motion-sanctions-proof",
                start_ms=33_120,
                end_ms=33_820,
                kind="proof-punch",
                target_id="layer-court-sanctions",
                intensity=0.82,
            ),
            MotionEventSpec(
                id="motion-lesson-punch",
                start_ms=36_190,
                end_ms=36_550,
                kind="punch-crop",
                target_id="layer-lesson-presenter",
                intensity=0.5,
            ),
            MotionEventSpec(
                id="motion-logo-build",
                start_ms=40_900,
                end_ms=41_350,
                kind="logo-build",
                target_id="layer-brand-logo",
                intensity=0.64,
            ),
        ]
    )
    return events


_LICENSED_VIDEO_SPECS = [
    {
        "id": "licensed-empty-restaurant",
        "filename": "empty-restaurant-29050.mp4",
        "page_filename": "empty-restaurant-with-nice-lighting-29050.html",
        "remote_id": "29050",
        "creator": "Mixkit contributor",
        "source_url": (
            "https://mixkit.co/free-stock-video/"
            "empty-restaurant-with-nice-lighting-29050/"
        ),
        "query": "empty restaurant kitchen no food order",
        "keywords": ["empty restaurant", "food order", "licensed video"],
    },
    {
        "id": "licensed-dollar-bills",
        "filename": "dollar-bills-31102.mp4",
        "page_filename": "dollar-bills-close-up-rotating-31102.html",
        "remote_id": "31102",
        "creator": "Mixkit contributor",
        "source_url": (
            "https://mixkit.co/free-stock-video/"
            "dollar-bills-close-up-rotating-31102/"
        ),
        "query": "US dollar currency close up",
        "keywords": ["US dollars", "currency", "licensed video"],
    },
    {
        "id": "licensed-euro-counting",
        "filename": "euro-counting-14007.mp4",
        "page_filename": (
            "close-up-of-hands-counting-euro-currency-14007.html"
        ),
        "remote_id": "14007",
        "creator": "Mixkit contributor",
        "source_url": (
            "https://mixkit.co/free-stock-video/"
            "close-up-of-hands-counting-euro-currency-14007/"
        ),
        "query": "euro currency counting close up",
        "keywords": ["euros", "currency", "licensed video"],
    },
    {
        "id": "licensed-online-payment",
        "filename": "online-payment-47413.mp4",
        "page_filename": (
            "man-sitting-at-his-laptop-making-an-online-payment-47413.html"
        ),
        "remote_id": "47413",
        "creator": "Mixkit contributor",
        "source_url": (
            "https://mixkit.co/free-stock-video/"
            "man-sitting-at-his-laptop-making-an-online-payment-47413/"
        ),
        "query": "online payment transfer laptop",
        "keywords": ["online payment", "fund transfer", "licensed video"],
    },
]

_AUDIO_SPECS = [
    (
        "music-social-kinetic",
        "mixkit-minimal-techno-01-162.mp3",
        "162",
        "Alejandro Magaña (A. M.)",
        "https://mixkit.co/free-stock-music/tag/technology/",
        ["126 BPM", "electronic", "vocal-free"],
    ),
    (
        "sfx-snap",
        "sfx-snap-3124.mp3",
        "3124",
        "Mixkit contributor",
        "https://mixkit.co/free-sound-effects/click/",
        ["sound effect", "snap"],
    ),
    (
        "sfx-click",
        "sfx-click-1109.mp3",
        "1109",
        "Mixkit contributor",
        "https://mixkit.co/free-sound-effects/click/",
        ["sound effect", "click"],
    ),
    (
        "sfx-impact",
        "sfx-impact-1143.mp3",
        "1143",
        "Mixkit contributor",
        "https://mixkit.co/free-sound-effects/impact/",
        ["sound effect", "impact"],
    ),
    (
        "sfx-whoosh",
        "sfx-whoosh-1492.mp3",
        "1492",
        "Mixkit contributor",
        "https://mixkit.co/free-sound-effects/whoosh/",
        ["sound effect", "whoosh"],
    ),
    (
        "sfx-riser",
        "sfx-riser-1144.mp3",
        "1144",
        "Mixkit contributor",
        "https://mixkit.co/free-sound-effects/riser/",
        ["sound effect", "riser"],
    ),
    (
        "sfx-pop",
        "sfx-pop-2354.mp3",
        "2354",
        "Mixkit contributor",
        "https://mixkit.co/free-sound-effects/notification/",
        ["sound effect", "notification"],
    ),
]


def _prepare_supporting_assets(
    *,
    output_dir: Path,
    analysis_dir: Path,
    seed_dir: Path,
) -> list[AssetRef]:
    assets: list[AssetRef] = []
    licensed_dir = output_dir / "assets" / "licensed" / "mixkit"
    license_dir = output_dir / "assets" / "licenses"
    for spec in _LICENSED_VIDEO_SPECS:
        local = _copy_required(
            analysis_dir / "licensed-candidates" / spec["filename"],
            licensed_dir / spec["filename"],
        )
        _copy_required(
            analysis_dir / spec["page_filename"],
            license_dir / spec["page_filename"],
        )
        assets.append(
            AssetRef(
                id=spec["id"],
                kind="video",
                path=_relative(output_dir, local),
                keywords=spec["keywords"],
                provenance="internet:licensed-stock-video",
                license="Mixkit Free License",
                provider="Mixkit",
                remote_id=spec["remote_id"],
                creator=spec["creator"],
                source_url=spec["source_url"],
                license_url="https://mixkit.co/license/",
                search_query=spec["query"],
            )
        )
    _copy_required(
        seed_dir / "assets" / "licenses" / "mixkit-license.html",
        license_dir / "mixkit-license.html",
    )
    for filename in (
        "mixkit-sfx-click.html",
        "mixkit-sfx-impact.html",
        "mixkit-sfx-whoosh.html",
        "mixkit-sfx-riser.html",
        "mixkit-sfx-notification.html",
    ):
        _copy_required(
            _DEFAULT_SOCIAL_SFX_LICENSE_DIR / filename,
            license_dir / filename,
        )
    audio_dir = output_dir / "assets" / "audio"
    for (
        asset_id,
        filename,
        remote_id,
        creator,
        source_url,
        keywords,
    ) in _AUDIO_SPECS:
        source = (
            _DEFAULT_SOCIAL_SFX_DIR / f"{asset_id}.mp3"
            if asset_id.startswith("sfx-")
            else seed_dir / "assets" / "audio" / filename
        )
        local = _copy_required(source, audio_dir / filename)
        assets.append(
            AssetRef(
                id=asset_id,
                kind="audio",
                path=_relative(output_dir, local),
                keywords=keywords,
                provenance="internet:licensed-stock-audio",
                license="Mixkit Free License",
                provider="Mixkit",
                remote_id=remote_id,
                creator=creator,
                source_url=source_url,
                license_url="https://mixkit.co/license/",
                search_query=" ".join(keywords),
            )
        )
    brand = _prepare_transparent_logo(
        _DEFAULT_BRAND_LOGO,
        output_dir / "assets" / "brand" / "profit-bricks-logo.png",
    )
    assets.append(
        AssetRef(
            id="brand-logo-original",
            kind="image",
            path=_relative(output_dir, brand),
            keywords=["Profit Bricks", "brand logo"],
            provenance="user-provided-brand-asset",
            license="User-provided",
        )
    )
    return assets


def build_rofx_blueprint(
    *,
    source: Path,
    output_dir: Path,
    style_reference: Path | None = None,
    flow_operation_budget: int = 2,
    analysis_dir: Path = _DEFAULT_ANALYSIS_DIR,
    seed_dir: Path = _DEFAULT_SEED_DIR,
    prepare_media: bool = True,
    acquire_assets: bool = True,
) -> dict[str, str]:
    del acquire_assets
    from app.editor.analysis import probe_video

    source = source.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    analysis_dir = analysis_dir.expanduser().resolve()
    seed_dir = seed_dir.expanduser().resolve()
    style_reference = (
        style_reference.expanduser().resolve()
        if style_reference is not None
        else _DEFAULT_STYLE_REFERENCE
    )
    if not source.is_file():
        raise FileNotFoundError(source)
    if not style_reference.is_file():
        raise FileNotFoundError(style_reference)
    if not analysis_dir.is_dir():
        raise FileNotFoundError(analysis_dir)
    if not seed_dir.is_dir():
        raise FileNotFoundError(seed_dir)
    if not 0 <= flow_operation_budget <= 8:
        raise ValueError("Flow operation budget must be between zero and eight")
    output_dir.mkdir(parents=True, exist_ok=True)

    if prepare_media:
        metadata = probe_video(source)
        source_duration_ms = round(metadata.duration_seconds * 1000)
        silence_intervals = _detect_silence_intervals(source)
    else:
        metadata = VideoMetadata(
            width=1_080,
            height=1_920,
            fps=30,
            frame_count=1_411,
            duration_seconds=47.03333333333333,
        )
        source_duration_ms = 47_033
        silence_intervals = list(_DEFAULT_SILENCE_INTERVALS_MS)
    edl = build_dialogue_edl_from_silences(
        source_duration_ms=source_duration_ms,
        target_duration_ms=OUTPUT_DURATION_MS,
        silence_intervals_ms=silence_intervals,
        minimum_retained_silence_ms=70,
    )

    presenter = output_dir / "assets" / "presenter" / "presenter-edl.mp4"
    dialogue_original = (
        output_dir / "assets" / "audio" / "dialogue-original.wav"
    )
    dialogue_processed = (
        output_dir / "assets" / "audio" / "dialogue-processed.wav"
    )
    if prepare_media:
        _prepare_dialogue_media(
            source=source,
            edl=edl,
            presenter_output=presenter,
            original_audio_output=dialogue_original,
            processed_audio_output=dialogue_processed,
        )
    else:
        _copy_required(
            seed_dir / "assets" / "presenter" / "presenter-edl.mp4",
            presenter,
        )
        _copy_required(
            seed_dir / "assets" / "audio" / "dialogue-original.wav",
            dialogue_original,
        )
        _copy_required(
            seed_dir / "assets" / "audio" / "dialogue-processed.wav",
            dialogue_processed,
        )

    source_segments = load_rofx_transcript(analysis_dir)
    remapped_segments = _remap_transcript(source_segments, edl)
    _write_json(
        output_dir / "transcript-aligned.json",
        [segment.model_dump(mode="json") for segment in remapped_segments],
    )
    _copy_required(
        analysis_dir / "transcript-groq-raw.json",
        output_dir / "transcript-groq-raw.json",
    )
    _copy_required(
        analysis_dir / "transcript-whisper.json",
        output_dir / "transcript-whisper-source.json",
    )

    evidence_paths = _prepare_evidence_assets(
        analysis_dir=analysis_dir,
        output_dir=output_dir,
    )
    evidence = build_rofx_evidence_items(output_dir)
    _write_json(
        output_dir / "evidence.json",
        [item.model_dump(mode="json") for item in evidence],
    )
    _build_rofx_flow_plates(output_dir)

    assets: list[AssetRef] = [
        AssetRef(
            id="presenter-edl",
            kind="video",
            path=_relative(output_dir, presenter),
            keywords=["presenter", "dialogue EDL", "source footage"],
            provenance="user-provided-edl-preserved",
            license="User-provided source footage",
        ),
        AssetRef(
            id="dialogue-original",
            kind="audio",
            path=_relative(output_dir, dialogue_original),
            keywords=["EDL dialogue baseline", "48 kHz"],
            provenance="source-dialogue-edl-master",
            license="User-provided source audio",
        ),
        AssetRef(
            id="dialogue-processed",
            kind="audio",
            path=_relative(output_dir, dialogue_processed),
            keywords=["processed dialogue", "48 kHz"],
            provenance="source-dialogue-edl-processed",
            license="User-provided source audio",
        ),
        AssetRef(
            id="evidence-cftc-pip",
            kind="image",
            path=_relative(output_dir, evidence_paths["pip"]),
            keywords=["CFTC", "ROFX", "direct source PIP"],
            provenance="official-source-capture-derived-crop",
            license="Official public record used as editorial evidence",
        ),
        AssetRef(
            id="evidence-cftc-2022-claim",
            kind="image",
            path=_relative(output_dir, evidence_paths["claim"]),
            keywords=["CFTC", "ROFX robot claim"],
            provenance="official-source-capture-derived-card",
            license="Official public record used as editorial evidence",
        ),
        AssetRef(
            id="evidence-cftc-2022-funds",
            kind="image",
            path=_relative(output_dir, evidence_paths["funds"]),
            keywords=["CFTC", "at least $58 million"],
            provenance="official-source-capture-derived-card",
            license="Official public record used as editorial evidence",
        ),
        AssetRef(
            id="evidence-cftc-funds-pip",
            kind="image",
            path=_relative(output_dir, evidence_paths["funds_pip"]),
            keywords=["CFTC", "1,100 customers", "at least $58 million"],
            provenance="official-source-capture-derived-pip",
            license="Official public record used as editorial evidence",
        ),
        AssetRef(
            id="evidence-court-overview",
            kind="image",
            path=_relative(output_dir, evidence_paths["court_10"]),
            keywords=["federal court order", "ROFX"],
            provenance="direct-federal-court-page",
            license="Federal court record used as editorial evidence",
        ),
        AssetRef(
            id="evidence-court-overview-pip",
            kind="image",
            path=_relative(output_dir, evidence_paths["court_pip"]),
            keywords=["federal court order", "ROFX", "April 22 2024"],
            provenance="direct-federal-court-page-derived-pip",
            license="Federal court record used as editorial evidence",
        ),
        AssetRef(
            id="evidence-court-no-trading",
            kind="image",
            path=_relative(output_dir, evidence_paths["no_trading"]),
            keywords=["no forex trading", "no ROFX robot"],
            provenance="federal-court-source-derived-card",
            license="Federal court record used as editorial evidence",
        ),
        AssetRef(
            id="evidence-court-sanctions",
            kind="image",
            path=_relative(output_dir, evidence_paths["sanctions"]),
            keywords=["restitution", "civil monetary penalty"],
            provenance="federal-court-source-derived-card",
            license="Federal court record used as editorial evidence",
        ),
        AssetRef(
            id="evidence-cftc-over-225m",
            kind="image",
            path=_relative(output_dir, evidence_paths["final_release"]),
            keywords=["CFTC", "over $225 million"],
            provenance="official-source-capture-derived-card",
            license="Official public record used as editorial evidence",
        ),
    ]
    assets.extend(
        _prepare_supporting_assets(
            output_dir=output_dir,
            analysis_dir=analysis_dir,
            seed_dir=seed_dir,
        )
    )

    layers = build_rofx_layers()
    flow_shots = build_rofx_flow_shots(output_dir)
    kinetic_text = build_rofx_text_cues()
    motion_events = build_rofx_motion_events()
    audio = build_rofx_audio_plan(remapped_segments)
    blueprint = ProductionBlueprint(
        source_filename=source.name,
        source_metadata=metadata,
        output=OutputSpec(),
        duration_ms=OUTPUT_DURATION_MS,
        assets=assets,
        layers=layers,
        caption_pages=[],
        audio=audio,
        flow_shots=flow_shots,
        evidence=evidence,
        reference_profile="social-kinetic",
        story_profile="rofx-case",
        style_reference_path=str(style_reference),
        voice_policy="reference-compressed",
        dialogue_edl=edl,
        kinetic_text_cues=kinetic_text,
        motion_events=motion_events,
    )

    artifacts = {
        "blueprint": "blueprint.json",
        "storyboard": "storyboard.json",
        "evidence": "evidence.json",
        "reference_profile": "reference-profile.json",
        "dialogue_edl": "dialogue-edl.json",
        "kinetic_text_plan": "kinetic-text-plan.json",
        "motion_events": "motion-events.json",
        "sound_cue_sheet": "sound-cue-sheet.json",
        "flow_shot_plan": "flow-shot-plan.json",
        "flow_instructions": "flow-instructions.json",
        "asset_manifest": "asset-manifest.json",
        "capture_manifest": "capture-manifest.json",
        "caption_plan": "caption-plan.json",
        "production_settings": "production-settings.json",
        "transcript_aligned": "transcript-aligned.json",
    }
    _write_json(
        output_dir / artifacts["blueprint"],
        blueprint.model_dump(mode="json"),
    )
    _write_json(
        output_dir / artifacts["flow_shot_plan"],
        [shot.model_dump(mode="json") for shot in flow_shots],
    )
    _write_json(
        output_dir / artifacts["dialogue_edl"],
        {
            "source_duration_ms": source_duration_ms,
            "output_duration_ms": OUTPUT_DURATION_MS,
            "removed_ms": source_duration_ms - OUTPUT_DURATION_MS,
            "playback_rate_max": max(
                segment.playback_rate for segment in edl
            ),
            "segments": [
                segment.model_dump(mode="json") for segment in edl
            ],
        },
    )
    text_visible_ms = measure_visible_interval_duration(kinetic_text)
    _write_json(
        output_dir / artifacts["kinetic_text_plan"],
        {
            "profile": "social-kinetic",
            "continuous_captions": False,
            "semantic_text_visible_ms": text_visible_ms,
            "semantic_text_ratio": round(
                text_visible_ms / OUTPUT_DURATION_MS,
                6,
            ),
            "cues": [
                cue.model_dump(mode="json") for cue in kinetic_text
            ],
        },
    )
    _write_json(
        output_dir / artifacts["motion_events"],
        [event.model_dump(mode="json") for event in motion_events],
    )
    _write_json(
        output_dir / artifacts["sound_cue_sheet"],
        {
            "profile": "social-kinetic",
            "music_bpm": audio.music_bpm,
            "target_lufs": audio.integrated_lufs,
            "target_true_peak_dbtp": audio.true_peak_dbtp,
            "target_lra_lu": audio.target_lra_lu,
            "cues": [
                cue.model_dump(mode="json") for cue in audio.sfx_cues
            ],
            "speech_protection_windows": [
                window.model_dump(mode="json")
                for window in audio.speech_protection_windows
            ],
        },
    )
    layer_ids_by_shot: dict[str, list[str]] = {}
    for layer in layers:
        layer_ids_by_shot.setdefault(layer.shot_id, []).append(layer.id)
    evidence_by_role = {
        "rofx-case-reveal": ["cftc-rofx-robot-claim"],
        "rofx-identity": ["cftc-rofx-robot-claim"],
        "reserve-claim-proof": ["cftc-rofx-robot-claim"],
        "customer-number": ["cftc-rofx-customers"],
        "fund-scale-proof": ["cftc-rofx-58m"],
        "court-overview": ["court-no-trading"],
        "no-trading-proof": ["court-no-trading", "court-no-robot"],
        "fund-transfer-context": ["court-transfers"],
        "sanctions-proof": [
            "court-restitution",
            "court-penalty",
            "cftc-over-225m",
        ],
    }
    schedule = build_rofx_schedule()
    _write_json(
        output_dir / artifacts["storyboard"],
        [
            {
                **shot,
                "layer_ids": layer_ids_by_shot.get(shot["id"], []),
                "kinetic_text_ids": [
                    cue.id
                    for cue in kinetic_text
                    if cue.start_ms < shot["end_ms"]
                    and cue.end_ms > shot["start_ms"]
                ],
                "evidence_ids": evidence_by_role.get(
                    shot["editorial_role"],
                    [],
                ),
            }
            for shot in schedule
        ],
    )
    _write_json(
        output_dir / artifacts["reference_profile"],
        {
            "name": "social-kinetic",
            "story_profile": "rofx-case",
            "primary_reference": {
                "path": str(style_reference),
                "checksum_sha256": _sha256(style_reference),
                "role": "typography, pacing, color, motion and sound grammar",
            },
            "approved_golden": {
                "path": str(seed_dir / "edited.mp4"),
                "checksum_sha256": _sha256(seed_dir / "edited.mp4"),
            },
            "secondary_reference": {
                "training_reference": 10,
                "role": "factual evidence restraint only",
            },
            "targets": {
                "duration_seconds": [44.1, 44.7],
                "hard_cuts": [13, 16],
                "median_shot_seconds": [2.3, 3.0],
                "presenter_ratio": [0.58, 0.68],
                "flow_ratio_max": 0.18,
                "dark_frame_ratio_max": 0.06,
                "mean_luminance": [95, 108],
                "mean_saturation": [65, 85],
            },
        },
    )
    _write_json(
        output_dir / artifacts["flow_instructions"],
        {
            "card": [
                {
                    "text": (
                        "Premium bright portrait commercial cinematography. "
                        "One clear subject and one continuous camera move. "
                        "No readable text, UI, code, charts, numbers, "
                        "currencies, documents, captions, logos or watermarks."
                    )
                }
            ]
        },
    )
    _write_json(
        output_dir / artifacts["caption_plan"],
        {
            "profile": "social-kinetic",
            "pages": [],
            "reason": "Sparse semantic typography replaces continuous subtitles.",
        },
    )
    _write_json(
        output_dir / artifacts["capture_manifest"],
        {
            "source": {
                "path": str(source),
                "checksum_sha256": _sha256(source),
                "read_only": True,
            },
            "presenter_edl": {
                "path": _relative(output_dir, presenter),
                "checksum_sha256": _sha256(presenter),
                "privacy_reviewed": True,
            },
            "official_source_captures": [
                {
                    "path": _relative(output_dir, capture),
                    "checksum_sha256": _sha256(capture),
                }
                for capture in sorted(
                    (output_dir / "source-captures").glob("*.png")
                )
            ],
        },
    )
    _write_json(
        output_dir / artifacts["asset_manifest"],
        {
            "assets": [
                {
                    **asset.model_dump(mode="json"),
                    "checksum_sha256": _sha256(output_dir / asset.path),
                }
                for asset in assets
            ]
        },
    )
    _write_json(
        output_dir / artifacts["production_settings"],
        {
            "style_reference": str(style_reference),
            "reference_profile": "social-kinetic",
            "story_profile": "rofx-case",
            "voice_policy": "reference-compressed",
            "flow_operation_budget": flow_operation_budget,
            "maximum_attempts_per_flow_shot": 2,
            "automatic_retry": False,
            "human_final_approval_required": True,
        },
    )
    return artifacts
