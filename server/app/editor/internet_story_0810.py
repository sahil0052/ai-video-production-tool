from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

import cv2
from imageio_ffmpeg import get_ffmpeg_exe
import numpy as np
from app.models import (
    AssetRef,
    AudioPlan,
    CaptionPage,
    CaptionToken,
    EvidenceItem,
    GainAutomation,
    OutputSpec,
    SfxCue,
    SpeechProtectionWindow,
    TranscriptSegment,
    TranscriptWord,
)
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from app.production_models import (
    BlueprintLayerSpec,
    EditPlanV2,
    LayerBounds,
    OpacityKeyframe,
    ProductionBlueprint,
    ProductionJobRecord,
    ProductionStateEvent,
    TransformKeyframe,
)


STORY_DURATION_MS = 49_500
_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_STYLE_REFERENCE = Path(
    r"D:\Downloads\Trading_Reel 02(06-08-26).mp4"
)
_DEFAULT_BRAND_LOGO = (
    _WORKSPACE_ROOT
    / "storage"
    / "assets"
    / "brand"
    / "profit-bricks-forex-automation.png"
)
_AUDIO_SOURCE_ROOT = (
    _WORKSPACE_ROOT
    / "storage"
    / "deliverables"
    / "0806-production-v4"
    / "assets"
    / "audio"
)
_SAFE_CORRECTED_FIRST_SEGMENT = (
    "2008 me teen mahine ke ek automated trading contest me ek forex "
    "robot yaani EA ka balance peak aaj ke hisab se dekhein to 1 crore "
    "ke aas paas tak pahunch gaya tha."
)


def build_0810_schedule() -> list[dict[str, Any]]:
    specs = [
        (0, 1_100, "presenter", "source-presenter", "hook-presenter"),
        (
            1_100,
            3_000,
            "direct-evidence",
            "evidence-atc-three-months",
            "atc-three-months",
        ),
        (3_000, 5_000, "licensed-context", "robot-line-47257", "robot-history"),
        (
            5_000,
            7_200,
            "direct-evidence",
            "evidence-mql5-110k",
            "balance-peak",
        ),
        (7_200, 9_000, "licensed-context", "market-online-47213", "market-scale"),
        (
            9_000,
            10_560,
            "direct-evidence",
            "evidence-mql5-risk",
            "risk-foreshadow",
        ),
        (10_560, 12_800, "presenter", "source-presenter", "future-question"),
        (
            12_800,
            14_980,
            "licensed-context",
            "numbers-glasses-47792",
            "future-monitoring",
        ),
        (
            14_980,
            17_260,
            "licensed-context",
            "payment-phone-5610",
            "upi-payment",
        ),
        (
            17_260,
            19_840,
            "licensed-context",
            "robot-line-47257",
            "upi-analogy",
        ),
        (
            19_840,
            23_360,
            "licensed-context",
            "charts-tablet-45706",
            "fewer-clicks",
        ),
        (
            23_360,
            25_280,
            "direct-evidence",
            "evidence-mt5-robot-actions",
            "robot-actions",
        ),
        (
            25_280,
            26_980,
            "licensed-context",
            "market-trend-9607",
            "orders-execute",
        ),
        (26_980, 29_580, "presenter", "source-presenter", "human-rules"),
        (
            29_580,
            32_320,
            "licensed-context",
            "numbers-glasses-47792",
            "risk-remains",
        ),
        (
            32_320,
            34_220,
            "licensed-context",
            "robot-line-47257",
            "robot-manager",
        ),
        (
            34_220,
            36_320,
            "licensed-context",
            "data-center-engineers-22966",
            "manager-supervision",
        ),
        (36_320, 38_400, "presenter", "source-presenter", "brand-focus"),
        (
            38_400,
            40_880,
            "licensed-context",
            "numbers-glasses-47792",
            "disciplined-risk",
        ),
        (40_880, 43_700, "presenter", "source-presenter", "cta-open"),
        (
            43_700,
            44_560,
            "licensed-context",
            "market-online-47213",
            "cta-brand",
        ),
        (44_560, 46_540, "presenter", "source-presenter", "cta-demo"),
        (
            46_540,
            STORY_DURATION_MS,
            "presenter",
            "source-presenter",
            "cta-details",
        ),
    ]
    return [
        {
            "id": f"shot-{index:02d}",
            "start_ms": start_ms,
            "end_ms": end_ms,
            "source_role": source_role,
            "asset_id": asset_id,
            "editorial_role": editorial_role,
            "reference_role": "supporting",
        }
        for index, (
            start_ms,
            end_ms,
            source_role,
            asset_id,
            editorial_role,
        ) in enumerate(specs, start=1)
    ]


def load_0810_transcript(output_dir: Path) -> list[TranscriptSegment]:
    output_dir = output_dir.expanduser().resolve()
    raw_path = output_dir / "transcript-groq-raw.json"
    corrected_path = output_dir / "transcript-corrected-texts.json"
    if not raw_path.is_file():
        raise FileNotFoundError(raw_path)
    if not corrected_path.is_file():
        raise FileNotFoundError(corrected_path)
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    corrected_texts = json.loads(
        corrected_path.read_text(encoding="utf-8")
    )
    raw_words = list(raw.get("words") or [])
    raw_segments = list(raw.get("segments") or [])
    if len(raw_segments) != len(corrected_texts):
        raise ValueError(
            "Groq segment count does not match corrected transcript count"
        )
    corrected_texts = [
        " ".join(str(text).split()) for text in corrected_texts
    ]
    corrected_texts[0] = _SAFE_CORRECTED_FIRST_SEGMENT
    corrected_texts[-1] = corrected_texts[-1].replace(
        "free life demo",
        "free live demo",
    )
    corrected_tokens = [
        token
        for text in corrected_texts
        for token in text.split()
    ]
    if len(corrected_tokens) != len(raw_words):
        raise ValueError(
            "0810 conservative correction must preserve the source word "
            f"count ({len(corrected_tokens)} != {len(raw_words)})"
        )
    aligned = _repair_monotonic_words(
        [
            TranscriptWord(
                start=float(raw_word["start"]),
                end=float(raw_word["end"]),
                text=token,
                confidence=raw_word.get("confidence"),
            )
            for raw_word, token in zip(
                raw_words,
                corrected_tokens,
                strict=True,
            )
        ]
    )
    segments: list[TranscriptSegment] = []
    cursor = 0
    for text in corrected_texts:
        token_count = len(text.split())
        words = aligned[cursor : cursor + token_count]
        cursor += token_count
        if not words:
            raise ValueError("0810 transcript contains an empty segment")
        segments.append(
            TranscriptSegment(
                start=words[0].start,
                end=words[-1].end,
                text=text,
                words=words,
            )
        )
    return segments


def _repair_monotonic_words(
    words: list[TranscriptWord],
) -> list[TranscriptWord]:
    repaired: list[TranscriptWord] = []
    previous_end = 0.0
    duration_seconds = STORY_DURATION_MS / 1000
    for word in words:
        start = max(0.0, float(word.start), previous_end)
        end = max(float(word.end), start + 0.04)
        end = min(duration_seconds, end)
        if end <= start:
            start = max(previous_end, duration_seconds - 0.04)
            end = duration_seconds
        repaired_word = word.model_copy(
            update={"start": start, "end": end}
        )
        repaired.append(repaired_word)
        previous_end = end
    return repaired


def build_0810_caption_pages(
    segments: list[TranscriptSegment],
) -> list[CaptionPage]:
    pages: list[CaptionPage] = []
    for segment in segments:
        words = list(segment.words)
        if not words:
            continue
        family = _caption_family(round(segment.start * 1000))
        for group in _caption_groups(words):
            start_ms = round(group[0].start * 1000)
            spoken_end_ms = max(round(word.end * 1000) for word in group)
            emphasis_index = _caption_emphasis_index(group)
            pages.append(
                CaptionPage(
                    start_ms=start_ms,
                    end_ms=max(spoken_end_ms, start_ms + 1),
                    tokens=[
                        CaptionToken(
                            text=word.text,
                            start_ms=round(word.start * 1000),
                            end_ms=max(
                                round(word.end * 1000),
                                round(word.start * 1000) + 1,
                            ),
                            highlighted=index == emphasis_index,
                            confidence=word.confidence,
                        )
                        for index, word in enumerate(group)
                    ],
                    family=family,
                    anchor=_caption_anchor(family, start_ms),
                    transition="hard-cut",
                    max_width=940,
                )
            )
    pages.sort(key=lambda page: (page.start_ms, page.end_ms))
    return _normalize_caption_holds(pages)


def build_0810_layers() -> list[BlueprintLayerSpec]:
    layers: list[BlueprintLayerSpec] = []
    contained_assets = {"upi-banner"}
    source_windows = {
        "robot-history": (1_000, 3_000),
        "market-scale": (1_200, 3_000),
        "future-monitoring": (800, 2_980),
        "upi-payment": (5_200, 7_480),
        "upi-analogy": (8_500, 11_080),
        "fewer-clicks": (7_300, 10_820),
        "orders-execute": (2_000, 3_700),
        "risk-remains": (7_000, 9_740),
        "robot-manager": (9_000, 10_900),
        "manager-supervision": (4_000, 6_100),
        "disciplined-risk": (10_000, 12_480),
        "cta-brand": (15_000, 15_860),
    }
    presenter_index = 0
    for shot in build_0810_schedule():
        start_ms = int(shot["start_ms"])
        end_ms = int(shot["end_ms"])
        duration_ms = end_ms - start_ms
        asset_id = str(shot["asset_id"])
        role = str(shot["source_role"])
        editorial_role = str(shot["editorial_role"])
        source_start_ms: int | None = None
        source_end_ms: int | None = None
        playback_rate = 1.0
        start_scale = 1.0
        end_scale = 1.035
        color_filter: str | None = None
        kind = "video" if role in {"presenter", "licensed-context"} else "image"

        if role == "presenter":
            presenter_index += 1
            source_start_ms = start_ms
            source_end_ms = end_ms
            scale_cycle = (1.0, 1.07, 1.12, 1.045)
            start_scale = scale_cycle[(presenter_index - 1) % len(scale_cycle)]
            end_scale = start_scale + 0.022
            color_filter = "brightness(1.025) contrast(1.025) saturate(1.01)"
        elif role == "licensed-context":
            source_start_ms, source_end_ms = source_windows.get(
                editorial_role,
                (0, duration_ms),
            )
            playback_rate = (source_end_ms - source_start_ms) / duration_ms
            end_scale = 1.055
            color_filter = "brightness(0.98) contrast(1.06) saturate(0.92)"
        elif role == "direct-evidence":
            end_scale = 1.025

        common = {
            "shot_id": str(shot["id"]),
            "start_ms": start_ms,
            "end_ms": end_ms,
            "source_role": role,
            "kind": kind,
            "asset_id": asset_id,
            "source_start_ms": source_start_ms,
            "source_end_ms": source_end_ms,
            "transform_keyframes": [
                TransformKeyframe(at_ms=0, scale=start_scale),
                TransformKeyframe(at_ms=duration_ms, scale=end_scale),
            ],
            "opacity_keyframes": [OpacityKeyframe(at_ms=0, value=1)],
            "muted": True,
            "playback_rate": playback_rate,
            "reference_role": "supporting",
        }
        if asset_id in contained_assets:
            layers.append(
                BlueprintLayerSpec(
                    id=f"base-{editorial_role}",
                    **common,
                    bounds=LayerBounds(),
                    fit="cover",
                    color_filter=(
                        "blur(18px) brightness(0.48) "
                        "contrast(1.08) saturate(0.78)"
                    ),
                    z_index=10,
                )
            )
            layers.append(
                BlueprintLayerSpec(
                    id=f"foreground-{editorial_role}",
                    **common,
                    bounds=LayerBounds(x=40, y=350, width=1_000, height=1_220),
                    fit="contain",
                    color_filter="brightness(1.02) contrast(1.04)",
                    border_radius=26,
                    z_index=20,
                )
            )
            continue
        layers.append(
            BlueprintLayerSpec(
                id=f"base-{editorial_role}",
                **common,
                bounds=LayerBounds(),
                fit="cover" if kind == "video" else "fill",
                color_filter=color_filter,
                z_index=10,
            )
        )
    layers.extend(
        [
            BlueprintLayerSpec(
                id="evidence-atc-proof-punch",
                shot_id="shot-02",
                start_ms=1_600,
                end_ms=3_000,
                source_role="direct-evidence",
                kind="image",
                asset_id="evidence-atc-three-months-proof",
                bounds=LayerBounds(),
                fit="fill",
                transform_keyframes=[
                    TransformKeyframe(at_ms=0, y=0, scale=1),
                    TransformKeyframe(at_ms=1_400, y=-20, scale=1.065),
                ],
                opacity_keyframes=[
                    OpacityKeyframe(at_ms=0, value=0),
                    OpacityKeyframe(at_ms=100, value=1),
                ],
                z_index=25,
                muted=True,
                reference_role="supporting",
            ),
            BlueprintLayerSpec(
                id="overlay-hook-year",
                shot_id="shot-01",
                start_ms=0,
                end_ms=1_100,
                source_role="deterministic-graphic",
                kind="image",
                asset_id="hook-year-overlay",
                bounds=LayerBounds(),
                fit="fill",
                opacity_keyframes=[
                    OpacityKeyframe(at_ms=0, value=0),
                    OpacityKeyframe(at_ms=120, value=1),
                ],
                z_index=30,
                muted=True,
                reference_role="supporting",
            ),
            BlueprintLayerSpec(
                id="overlay-upi-logo",
                shot_id="shot-09",
                start_ms=15_140,
                end_ms=17_260,
                source_role="licensed-context",
                kind="image",
                asset_id="upi-logo",
                bounds=LayerBounds(x=650, y=92, width=350, height=175),
                fit="contain",
                opacity_keyframes=[
                    OpacityKeyframe(at_ms=0, value=0),
                    OpacityKeyframe(at_ms=140, value=1),
                ],
                border_radius=18,
                z_index=30,
                muted=True,
                reference_role="supporting",
            ),
            BlueprintLayerSpec(
                id="fewer-clicks-action-punch",
                shot_id="shot-11",
                start_ms=21_840,
                end_ms=23_360,
                source_role="licensed-context",
                kind="video",
                asset_id="charts-tablet-45706",
                source_start_ms=9_300,
                source_end_ms=10_820,
                bounds=LayerBounds(),
                fit="cover",
                transform_keyframes=[
                    TransformKeyframe(at_ms=0, scale=1.12),
                    TransformKeyframe(at_ms=1_520, scale=1.2),
                ],
                opacity_keyframes=[OpacityKeyframe(at_ms=0, value=1)],
                color_filter=(
                    "brightness(1.02) contrast(1.09) saturate(0.96)"
                ),
                z_index=22,
                muted=True,
                playback_rate=1.0,
                reference_role="supporting",
            ),
            BlueprintLayerSpec(
                id="overlay-cta-demo",
                shot_id="shot-22",
                start_ms=44_560,
                end_ms=49_020,
                source_role="deterministic-graphic",
                kind="image",
                asset_id="cta-demo-overlay",
                bounds=LayerBounds(),
                fit="fill",
                opacity_keyframes=[
                    OpacityKeyframe(at_ms=0, value=0),
                    OpacityKeyframe(at_ms=180, value=1),
                ],
                z_index=30,
                muted=True,
                reference_role="supporting",
            ),
        ]
    )
    layers.append(
        BlueprintLayerSpec(
            id="brand-logo-focus",
            shot_id="shot-18",
            start_ms=36_440,
            end_ms=38_400,
            source_role="deterministic-graphic",
            kind="image",
            asset_id="brand-profit-bricks-logo",
            bounds=LayerBounds(x=315, y=70, width=450, height=300),
            fit="contain",
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=180, value=1),
            ],
            z_index=30,
            muted=True,
            reference_role="supporting",
        )
    )
    return layers


def build_0810_evidence_items(output_dir: Path) -> list[EvidenceItem]:
    output_dir = output_dir.expanduser().resolve()
    required = {
        "source-captures/mql5-110k-mobile-excerpt.png",
        "source-captures/mql5-risk-mobile-excerpt.png",
        "source-captures/mt5-three-months-mobile-excerpt.png",
        "source-captures/mt5-robot-actions-mobile-excerpt.png",
    }
    missing = [
        path
        for path in sorted(required)
        if not (output_dir / path).is_file()
    ]
    if missing:
        raise FileNotFoundError(", ".join(missing))
    accessed_at = datetime.now(UTC)
    return [
        EvidenceItem(
            id="mql5-110k-peak",
            claim=(
                "In the 2008 championship, Leonid Velichkovsky's "
                "multicurrency neural network earned $110,000 at one point."
            ),
            source_title=(
                'Interview with Leonid Velichkovsky: "The Biggest Myth '
                'about Neural Networks is Super-Profitability"'
            ),
            source_url="https://www.mql5.com/en/articles/525",
            source_type="official",
            capture_path="source-captures/mql5-110k-mobile-excerpt.png",
            accessed_at=accessed_at,
            status="verified",
            visible_excerpt="earning $110,000 in a certain moment",
            notes=(
                "The primary source describes a peak reached at one point, "
                "not a verified final balance. The edit must not label it as "
                "a final balance."
            ),
        ),
        EvidenceItem(
            id="mql5-aggressive-risk",
            claim=(
                "The same official source says the system later fell victim "
                "to aggressive money management."
            ),
            source_title=(
                'Interview with Leonid Velichkovsky: "The Biggest Myth '
                'about Neural Networks is Super-Profitability"'
            ),
            source_url="https://www.mql5.com/en/articles/525",
            source_type="official",
            capture_path="source-captures/mql5-risk-mobile-excerpt.png",
            accessed_at=accessed_at,
            status="verified",
            visible_excerpt=(
                "eventually fell victim to its own aggressive money management"
            ),
        ),
        EvidenceItem(
            id="mt5-atc-three-months",
            claim=(
                "MetaQuotes describes Automated Trading Championships in "
                "which Expert Advisors traded for three months."
            ),
            source_title="Algorithmic (automated) trading in MetaTrader 5",
            source_url="https://www.metatrader5.com/en/automated-trading",
            source_type="official",
            capture_path="source-captures/mt5-three-months-mobile-excerpt.png",
            accessed_at=accessed_at,
            status="verified",
            visible_excerpt="for a period of three months",
        ),
        EvidenceItem(
            id="mt5-robot-actions",
            claim=(
                "MetaTrader states that trading robots can analyze quotes and "
                "execute trade operations."
            ),
            source_title="Algorithmic (automated) trading in MetaTrader 5",
            source_url="https://www.metatrader5.com/en/automated-trading",
            source_type="official",
            capture_path="source-captures/mt5-robot-actions-mobile-excerpt.png",
            accessed_at=accessed_at,
            status="verified",
            visible_excerpt=(
                "analyze quotes of financial instruments, as well as execute "
                "trade operations"
            ),
        ),
    ]


def build_0810_editorial_cards(output_dir: Path) -> list[AssetRef]:
    output_dir = output_dir.expanduser().resolve()
    graphics_dir = output_dir / "assets" / "graphics"
    graphics_dir.mkdir(parents=True, exist_ok=True)
    specs = [
        (
            "evidence-atc-three-months",
            "source-captures/mt5-three-months-mobile-excerpt.png",
            "OFFICIAL METAQUOTES HISTORY",
            "2008 • THREE-MONTH ATC",
            "EXPERT ADVISORS TRADED AUTOMATICALLY",
            "#D9FF45",
            (0.0, 0.54, 0.43, 0.25),
        ),
        (
            "evidence-mql5-110k",
            "source-captures/mql5-110k-mobile-excerpt.png",
            "OFFICIAL MQL5 INTERVIEW",
            "$110,000 AT ONE POINT",
            "A PEAK — NOT A VERIFIED FINAL BALANCE",
            "#D9FF45",
            (0.0, 0.30, 0.42, 0.19),
        ),
        (
            "evidence-mql5-risk",
            "source-captures/mql5-risk-mobile-excerpt.png",
            "THE SAME OFFICIAL SOURCE",
            "AGGRESSIVE MONEY MANAGEMENT",
            "THE SYSTEM LATER GAVE BACK THE PEAK",
            "#FF625F",
            (0.35, 0.30, 0.63, 0.19),
        ),
        (
            "evidence-mt5-robot-actions",
            "source-captures/mt5-robot-actions-mobile-excerpt.png",
            "OFFICIAL METATRADER 5",
            "ANALYZE QUOTES",
            "AND EXECUTE TRADE OPERATIONS",
            "#8EDADD",
            (0.54, 0.27, 0.44, 0.27),
        ),
    ]
    assets: list[AssetRef] = []
    for (
        asset_id,
        source_name,
        eyebrow,
        headline,
        supporting,
        accent,
        focus_crop,
    ) in specs:
        source = output_dir / source_name
        if not source.is_file():
            raise FileNotFoundError(source)
        destination = graphics_dir / f"{asset_id}.png"
        _build_evidence_card(
            source=source,
            destination=destination,
            eyebrow=eyebrow,
            headline=headline,
            supporting=supporting,
            accent=accent,
            focus_crop=focus_crop,
        )
        assets.append(
            AssetRef(
                id=asset_id,
                kind="image",
                path=destination.relative_to(output_dir).as_posix(),
                keywords=["official evidence", headline.lower()],
                provenance=(
                    "official-source-capture-derived-editorial-card"
                ),
                license="Official source excerpt used as editorial evidence",
            )
        )

    atc_proof_source = (
        output_dir
        / "source-captures"
        / "mt5-three-months-mobile-excerpt.png"
    )
    atc_proof = graphics_dir / "evidence-atc-three-months-proof.png"
    _build_atc_proof_card(
        source=atc_proof_source,
        destination=atc_proof,
    )
    assets.append(
        AssetRef(
            id="evidence-atc-three-months-proof",
            kind="image",
            path=atc_proof.relative_to(output_dir).as_posix(),
            keywords=["official evidence", "three months proof macro"],
            provenance=(
                "official-source-capture-derived-editorial-proof-macro"
            ),
            license="Official source excerpt used as editorial evidence",
        )
    )

    hook = graphics_dir / "hook-year-overlay.png"
    _build_hook_overlay(hook)
    assets.append(
        AssetRef(
            id="hook-year-overlay",
            kind="image",
            path=hook.relative_to(output_dir).as_posix(),
            keywords=["hook typography", "2008"],
            provenance="deterministic-production-typography",
        )
    )
    cta = graphics_dir / "cta-demo-overlay.png"
    _build_cta_overlay(cta)
    assets.append(
        AssetRef(
            id="cta-demo-overlay",
            kind="image",
            path=cta.relative_to(output_dir).as_posix(),
            keywords=["call to action", "comment demo"],
            provenance="deterministic-production-typography",
        )
    )
    return assets


def _build_evidence_card(
    *,
    source: Path,
    destination: Path,
    eyebrow: str,
    headline: str,
    supporting: str,
    accent: str,
    focus_crop: tuple[float, float, float, float],
) -> None:
    canvas = Image.new("RGB", (1_080, 1_920), "#E7E8EA")
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 1_080, 286), fill="#0E141D")
    draw.rectangle((0, 0, 18, 286), fill=accent)
    draw.text((58, 52), eyebrow, font=_font(26, bold=True), fill=accent)
    headline_font = _fit_font(headline, max_width=960, start_size=68)
    draw.text(
        (58, 108),
        headline,
        font=headline_font,
        fill="#FFFFFF",
    )
    draw.text(
        (58, 218),
        supporting,
        font=_fit_font(supporting, max_width=960, start_size=31),
        fill="#D8DEE8",
    )

    excerpt = Image.open(source).convert("RGB")
    viewport_path = source.with_name(
        source.name.replace("-mobile-excerpt", "-viewport")
    )
    page_source = (
        Image.open(viewport_path).convert("RGB")
        if viewport_path.is_file()
        else excerpt
    )
    page = _contain_image(page_source, (970, 1_020), "#F8F8F6")
    page_shadow = Image.new("RGBA", (1_024, 1_074), (0, 0, 0, 0))
    ImageDraw.Draw(page_shadow).rounded_rectangle(
        (22, 22, 1_002, 1_052),
        radius=22,
        fill=(0, 0, 0, 96),
    )
    page_shadow = page_shadow.filter(ImageFilter.GaussianBlur(16))
    canvas.paste(page_shadow.convert("RGB"), (28, 284))
    canvas.paste(page, (55, 310))
    draw.rounded_rectangle(
        (55, 310, 1_025, 1_330),
        radius=16,
        outline="#B9BCC2",
        width=2,
    )

    crop_x, crop_y, crop_width, crop_height = focus_crop
    left = round(excerpt.width * crop_x)
    top = round(excerpt.height * crop_y)
    right = max(left + 1, round(excerpt.width * (crop_x + crop_width)))
    bottom = max(top + 1, round(excerpt.height * (crop_y + crop_height)))
    focus = excerpt.crop(
        (
            max(0, left),
            max(0, top),
            min(excerpt.width, right),
            min(excerpt.height, bottom),
        )
    )
    focus = _contain_image(focus, (940, 190), "#FFFFFF")
    focus_y = 1_030
    focus_shadow = Image.new("RGBA", (988, 238), (0, 0, 0, 0))
    ImageDraw.Draw(focus_shadow).rounded_rectangle(
        (18, 18, 970, 220),
        radius=18,
        fill=(0, 0, 0, 112),
    )
    focus_shadow = focus_shadow.filter(ImageFilter.GaussianBlur(13))
    canvas.paste(focus_shadow.convert("RGB"), (46, focus_y - 22))
    canvas.paste(focus, (70, focus_y))
    draw.rounded_rectangle(
        (70, focus_y, 1_010, focus_y + 190),
        radius=12,
        outline=accent,
        width=5,
    )

    draw.rectangle((0, 1_345, 1_080, 1_920), fill="#0C121A")
    draw.text(
        (58, 1_375),
        "DIRECT OFFICIAL SOURCE PIXELS",
        font=_font(24, bold=True),
        fill=accent,
    )
    draw.line(
        (58, 1_424, 1_022, 1_424),
        fill="#293342",
        width=2,
    )
    draw.text(
        (540, 1_825),
        "SOURCE: MQL5 / METATRADER 5",
        font=_font(24, bold=True),
        fill="#CAD2DE",
        anchor="mm",
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, optimize=True)


def _build_hook_overlay(destination: Path) -> None:
    image = Image.new("RGBA", (1_080, 1_920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (115, 1_260, 965, 1_535),
        radius=28,
        fill=(7, 10, 14, 212),
    )
    draw.text(
        (540, 1_326),
        "2008 • FOREX TRADING",
        font=_font(43, bold=True),
        fill="#FFFFFF",
        anchor="mm",
    )
    draw.text(
        (540, 1_450),
        "ROBOT",
        font=_font(102, bold=True),
        fill="#D9FF45",
        anchor="mm",
    )
    image.save(destination, optimize=True)


def _build_atc_proof_card(
    *,
    source: Path,
    destination: Path,
) -> None:
    excerpt = Image.open(source).convert("RGB")
    width, height = excerpt.size
    proof_crop = excerpt.crop(
        (
            0,
            round(height * 0.60),
            round(width * 0.40),
            round(height * 0.80),
        )
    )
    proof = _contain_image(proof_crop, (920, 300), "#FFFFFF")

    canvas = Image.new("RGB", (1_080, 1_920), "#0B1119")
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 18, 1_920), fill="#D9FF45")
    draw.text(
        (62, 92),
        "OFFICIAL METAQUOTES EVIDENCE",
        font=_font(28, bold=True),
        fill="#D9FF45",
    )
    draw.text(
        (62, 185),
        "FOR A PERIOD OF",
        font=_font(48, bold=True),
        fill="#FFFFFF",
    )
    draw.text(
        (62, 290),
        "THREE MONTHS",
        font=_font(108, bold=True),
        fill="#D9FF45",
    )
    draw.rounded_rectangle(
        (42, 520, 1_038, 1_010),
        radius=24,
        fill="#FFFFFF",
        outline="#D9FF45",
        width=6,
    )
    canvas.paste(proof, (80, 600))
    draw.line((90, 885, 990, 885), fill="#D9FF45", width=6)
    draw.rounded_rectangle(
        (62, 1_085, 1_018, 1_285),
        radius=20,
        fill="#131C28",
        outline="#39485A",
        width=2,
    )
    draw.text(
        (540, 1_185),
        "EXPERT ADVISORS TRADED AUTOMATICALLY",
        font=_fit_font(
            "EXPERT ADVISORS TRADED AUTOMATICALLY",
            max_width=900,
            start_size=38,
        ),
        fill="#FFFFFF",
        anchor="mm",
    )
    draw.text(
        (62, 1_465),
        "DIRECT SOURCE PIXELS • PHONE-LEGIBLE PROOF CROP",
        font=_font(25, bold=True),
        fill="#94A3B8",
    )
    draw.line((62, 1_520, 1_018, 1_520), fill="#293648", width=2)
    draw.text(
        (540, 1_800),
        "SOURCE: METATRADER 5 • AUTOMATED TRADING",
        font=_font(25, bold=True),
        fill="#D3DBE7",
        anchor="mm",
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, optimize=True)


def _build_cta_overlay(destination: Path) -> None:
    image = Image.new("RGBA", (1_080, 1_920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (110, 990, 970, 1_395),
        radius=30,
        fill=(8, 13, 21, 230),
        outline=(142, 218, 221, 220),
        width=3,
    )
    draw.text(
        (540, 1_060),
        "FREE LIVE DEMO",
        font=_font(52, bold=True),
        fill="#FFFFFF",
        anchor="mm",
    )
    draw.text(
        (540, 1_185),
        'COMMENT "DEMO"',
        font=_font(76, bold=True),
        fill="#D9FF45",
        anchor="mm",
    )
    draw.text(
        (540, 1_315),
        "TEAM WILL SHARE THE DETAILS",
        font=_font(29, bold=True),
        fill="#D8DEE8",
        anchor="mm",
    )
    image.save(destination, optimize=True)


def _contain_image(
    image: Image.Image,
    size: tuple[int, int],
    background: str,
) -> Image.Image:
    target_width, target_height = size
    contained = Image.new("RGB", size, background)
    scale = min(
        target_width / max(1, image.width),
        target_height / max(1, image.height),
    )
    resized = image.resize(
        (
            max(1, round(image.width * scale)),
            max(1, round(image.height * scale)),
        ),
        Image.Resampling.LANCZOS,
    )
    contained.paste(
        resized,
        (
            (target_width - resized.width) // 2,
            (target_height - resized.height) // 2,
        ),
    )
    return contained


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path(r"C:\Windows\Fonts\arialbd.ttf")
        if bold
        else Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\segoeuib.ttf")
        if bold
        else Path(r"C:\Windows\Fonts\segoeui.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default(size=size)


def _fit_font(
    text: str,
    *,
    max_width: int,
    start_size: int,
) -> ImageFont.FreeTypeFont:
    size = start_size
    while size >= 24:
        font = _font(size, bold=True)
        if font.getlength(text) <= max_width:
            return font
        size -= 2
    return _font(24, bold=True)


def _caption_family(start_ms: int) -> str:
    return "outlined-demo"


def _caption_anchor(family: str, start_ms: int) -> str:
    return "lower-82"


def _caption_emphasis_index(words: list[TranscriptWord]) -> int:
    low_value_words = {
        "a",
        "and",
        "aur",
        "ek",
        "hai",
        "hain",
        "hi",
        "ka",
        "ke",
        "ki",
        "me",
        "mein",
        "ne",
        "par",
        "se",
        "so",
        "to",
        "ye",
        "yeh",
    }
    for index in range(len(words) - 1, -1, -1):
        normalized = "".join(
            character
            for character in words[index].text.casefold()
            if character.isalnum()
        )
        if normalized and normalized not in low_value_words:
            return index
    return len(words) - 1


def _caption_groups(
    words: list[TranscriptWord],
) -> list[list[TranscriptWord]]:
    groups: list[list[TranscriptWord]] = []
    index = 0
    while index < len(words):
        best_end = index + 1
        for end in range(index + 1, min(len(words), index + 4) + 1):
            duration_ms = round((words[end - 1].end - words[index].start) * 1000)
            if duration_ms > 1_300:
                break
            best_end = end
            if duration_ms >= 650 and end - index >= 2:
                if end - index >= 3 or _ends_clause(words[end - 1].text):
                    break
        groups.append(words[index:best_end])
        index = best_end
    for group_index in range(len(groups) - 1, 0, -1):
        group = groups[group_index]
        duration_ms = round(
            (group[-1].end - group[0].start) * 1000
        )
        if duration_ms >= 350:
            continue
        previous = groups[group_index - 1]
        if len(previous) > 1 and len(group) < 4:
            group.insert(0, previous.pop())
            continue
        combined = [*previous, *group]
        combined_duration_ms = round(
            (combined[-1].end - combined[0].start) * 1000
        )
        if len(combined) <= 4 and combined_duration_ms <= 1_300:
            groups[group_index - 1] = combined
            groups.pop(group_index)
    return groups


def _ends_clause(text: str) -> bool:
    return text.rstrip().endswith((",", ";", ":", ".", "?", "!"))


def _normalize_caption_holds(
    pages: list[CaptionPage],
) -> list[CaptionPage]:
    normalized: list[CaptionPage] = []
    for index, page in enumerate(pages):
        next_start = (
            pages[index + 1].start_ms
            if index + 1 < len(pages)
            else STORY_DURATION_MS
        )
        end_ms = min(
            max(page.end_ms, page.start_ms + 350),
            page.start_ms + 1_300,
            next_start,
        )
        if end_ms - page.start_ms < 350:
            raise ValueError(
                f"Caption hold below 350 ms at {page.start_ms}: "
                f"{' '.join(token.text for token in page.tokens)}"
            )
        normalized.append(page.model_copy(update={"end_ms": end_ms}))
    return normalized


def build_0810_audio_plan(
    segments: list[TranscriptSegment],
) -> AudioPlan:
    protection = [
        SpeechProtectionWindow(
            start_ms=max(0, round(word.start * 1000) - 100),
            end_ms=min(
                STORY_DURATION_MS,
                round(word.start * 1000) + 120,
            ),
            word=word.text.strip(),
        )
        for segment in segments
        for word in segment.words
        if word.text.strip()
    ]
    automation = [
        GainAutomation(
            start_ms=max(0, round(segment.start * 1000) - 80),
            end_ms=min(
                STORY_DURATION_MS,
                round(segment.end * 1000) + 100,
            ),
            gain_db=-5.5,
            reason="duck music beneath narration",
        )
        for segment in segments
        if segment.end > segment.start
    ]
    candidate_cues = [
        SfxCue(
            id="future-question-turn",
            asset_id="sfx-label-snap",
            start_ms=10_980,
            duration_ms=90,
            volume=0.36,
            gain_db=-18,
            kind="click",
            reason="clean pause before the future-facing question",
        ),
        SfxCue(
            id="brand-focus-turn",
            asset_id="sfx-product-click",
            start_ms=35_620,
            duration_ms=80,
            volume=0.34,
            gain_db=-18,
            kind="click",
            reason="subtle brand-focus transition",
        ),
    ]
    cues = [
        cue
        for cue in candidate_cues
        if not any(
            cue.start_ms < window.end_ms
            and cue.start_ms + cue.duration_ms > window.start_ms
            for window in protection
        )
    ]
    return AudioPlan(
        dialogue_asset_id="dialogue-processed",
        music_asset_id="music-reference-score",
        music_base_gain_db=-20,
        music_duck_db=5.5,
        music_gain_automation=automation,
        speech_protection_windows=protection,
        sfx_asset_ids=sorted({cue.asset_id for cue in cues}),
        sfx_cues=cues,
    )


def build_0810_blueprint(
    *,
    source: Path,
    output_dir: Path,
    style_reference: Path | None = None,
    brand_logo: Path | None = None,
    force: bool = False,
) -> dict[str, str]:
    from app.editor.analysis import probe_video, validate_source
    from app.editor.remotion import prepare_renderer_source_proxy
    from app.editor.production_v4 import ProductionStore

    source = source.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    style_reference = (
        style_reference.expanduser().resolve()
        if style_reference is not None
        else _DEFAULT_STYLE_REFERENCE
    )
    brand_logo = (
        brand_logo.expanduser().resolve()
        if brand_logo is not None
        else _DEFAULT_BRAND_LOGO
    )
    if not source.is_file():
        raise FileNotFoundError(source)
    output_dir.mkdir(parents=True, exist_ok=True)
    store = ProductionStore(output_dir)
    if store.record_path.is_file() and not force:
        existing = store.load()
        if (
            existing.id == "production-0810-internet-sourced-v1"
            and (output_dir / "blueprint.json").is_file()
        ):
            return dict(existing.artifacts)

    metadata = probe_video(source)
    validate_source(metadata)
    if abs(metadata.duration_seconds * 1000 - STORY_DURATION_MS) > 150:
        raise ValueError(
            "The 0810 production blueprint expects a 49.5-second source"
        )
    presenter_path = (
        output_dir / "assets" / "presenter" / "source-presenter.mp4"
    )
    prepare_renderer_source_proxy(
        executable=Path(get_ffmpeg_exe()),
        source=source,
        output=presenter_path,
        fps=30,
    )
    segments = load_0810_transcript(output_dir)
    captions = build_0810_caption_pages(segments)
    evidence = build_0810_evidence_items(output_dir)
    editorial_assets = build_0810_editorial_cards(output_dir)
    brand_path = _prepare_0810_brand_logo(
        source=brand_logo,
        output=output_dir / "assets" / "brand" / "profit-bricks-logo.png",
    )
    audio_paths = _prepare_0810_audio(
        source=source,
        output_dir=output_dir,
    )
    assets = _build_0810_assets(
        output_dir=output_dir,
        presenter_path=presenter_path,
        brand_path=brand_path,
        editorial_assets=editorial_assets,
        audio_paths=audio_paths,
    )
    layers = build_0810_layers()
    audio = build_0810_audio_plan(segments)
    blueprint = ProductionBlueprint(
        source_filename=source.name,
        source_metadata=metadata,
        output=OutputSpec(width=1080, height=1920, fps=30),
        duration_ms=STORY_DURATION_MS,
        assets=assets,
        layers=layers,
        caption_pages=captions,
        audio=audio,
        flow_shots=[],
        evidence=evidence,
    )
    artifacts = {
        "blueprint": "blueprint.json",
        "storyboard": "storyboard.json",
        "evidence": "evidence.json",
        "caption_plan": "caption-plan.json",
        "asset_manifest": "asset-manifest.json",
        "capture_manifest": "capture-manifest.json",
        "transcript": "transcript-aligned.json",
        "production_settings": "production-settings.json",
        "flow_shot_plan": "flow-shot-plan.json",
    }
    _write_json(
        output_dir / artifacts["blueprint"],
        blueprint.model_dump(mode="json"),
    )
    _write_json(
        output_dir / artifacts["transcript"],
        [segment.model_dump(mode="json") for segment in segments],
    )
    _write_json(
        output_dir / artifacts["evidence"],
        [item.model_dump(mode="json") for item in evidence],
    )
    _write_json(
        output_dir / artifacts["caption_plan"],
        {
            "primary_reference": str(style_reference),
            "secondary_reference": 10,
            "continuous_captions": True,
            "pages": [
                page.model_dump(mode="json") for page in captions
            ],
        },
    )
    layer_ids_by_shot: dict[str, list[str]] = {}
    for layer in layers:
        layer_ids_by_shot.setdefault(layer.shot_id, []).append(layer.id)
    _write_json(
        output_dir / artifacts["storyboard"],
        [
            {
                **shot,
                "layer_ids": layer_ids_by_shot.get(str(shot["id"]), []),
                "evidence_ids": _0810_evidence_ids(
                    str(shot["editorial_role"])
                ),
                "caption_family": _caption_family_at(
                    captions,
                    int(shot["start_ms"]),
                ),
            }
            for shot in build_0810_schedule()
        ],
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
    _write_json(output_dir / artifacts["flow_shot_plan"], [])
    _write_json(
        output_dir / artifacts["production_settings"],
        {
            "primary_reference": str(style_reference),
            "secondary_reference": 10,
            "quality_target": "reference-style-internet-sourced",
            "asset_policy": "official-and-free-licensed-internet-only",
            "voice_policy": "preserve-verbatim-audio",
            "caption_policy": "continuous-role-adaptive-source-timed",
            "flow_policy": "disabled-no-generated-visuals",
            "visual_api_required": False,
        },
    )
    _write_json(
        output_dir / "style-reference-audit.json",
        {
            "path": str(style_reference),
            "available": style_reference.is_file(),
            "role": "visual grammar only; never rendered as an output asset",
        },
    )
    now = datetime.now(UTC)
    record = ProductionJobRecord(
        id="production-0810-internet-sourced-v1",
        source_path=str(source),
        output_dir=str(output_dir),
        state="blueprint-ready",
        primary_reference=10,
        secondary_reference=4,
        flow_operation_budget=0,
        artifacts=artifacts,
        state_history=[
            ProductionStateEvent(
                state="analyzing",
                at=now,
                detail=(
                    "0810 narration, claims, source structure, and "
                    "internet assets analyzed."
                ),
            ),
            ProductionStateEvent(
                state="blueprint-ready",
                at=now,
                detail=(
                    "Internet-sourced blueprint persisted with continuous "
                    "captions and zero generated visuals."
                ),
            ),
        ],
        created_at=now,
        updated_at=now,
    )
    if store.record_path.is_file():
        store.save(record)
    else:
        store.create(record)
    return artifacts


def _prepare_0810_brand_logo(*, source: Path, output: Path) -> Path:
    if not source.is_file():
        raise FileNotFoundError(source)
    image = Image.open(source).convert("RGBA")
    pixels = np.array(image)
    rgb = pixels[:, :, :3].astype(np.int16)
    distance_from_white = 255 - np.min(rgb, axis=2)
    alpha = np.clip((distance_from_white - 6) * 9, 0, 255).astype(
        np.uint8
    )
    source_alpha = pixels[:, :, 3]
    pixels[:, :, 3] = np.minimum(alpha, source_alpha)
    processed = Image.fromarray(pixels, "RGBA")
    bounding = processed.getchannel("A").getbbox()
    if bounding:
        processed = processed.crop(bounding)
    output.parent.mkdir(parents=True, exist_ok=True)
    processed.save(output, optimize=True)
    return output


def _prepare_0810_audio(
    *,
    source: Path,
    output_dir: Path,
) -> dict[str, Path]:
    audio_dir = output_dir / "assets" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    executable = Path(get_ffmpeg_exe())
    original = audio_dir / "dialogue-original.wav"
    processed = audio_dir / "dialogue-processed.wav"
    _run_command(
        [
            str(executable),
            "-hide_banner",
            "-y",
            "-i",
            str(source),
            "-map",
            "0:a:0",
            "-vn",
            "-ac",
            "2",
            "-ar",
            "48000",
            "-c:a",
            "pcm_s24le",
            str(original),
        ]
    )
    _run_command(
        [
            str(executable),
            "-hide_banner",
            "-y",
            "-i",
            str(original),
            "-af",
            (
                "highpass=f=65,"
                "acompressor=threshold=-20dB:ratio=1.75:"
                "attack=18:release=170:makeup=1.12"
            ),
            "-ac",
            "2",
            "-ar",
            "48000",
            "-c:a",
            "pcm_s24le",
            str(processed),
        ]
    )
    music_source = _AUDIO_SOURCE_ROOT / "reference-10-micro-score.wav"
    music = audio_dir / "reference-style-score.wav"
    _run_command(
        [
            str(executable),
            "-hide_banner",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(music_source),
            "-t",
            f"{STORY_DURATION_MS / 1000:.3f}",
            "-af",
            "afade=t=in:st=0:d=0.35,afade=t=out:st=48.8:d=0.7",
            "-ac",
            "2",
            "-ar",
            "48000",
            "-c:a",
            "pcm_s16le",
            str(music),
        ]
    )
    outputs = {
        "dialogue-original": original,
        "dialogue-processed": processed,
        "music-reference-score": music,
    }
    for asset_id, filename in {
        "sfx-label-snap": "label-snap.wav",
        "sfx-product-click": "product-click.wav",
    }.items():
        destination = audio_dir / filename
        shutil.copy2(_AUDIO_SOURCE_ROOT / filename, destination)
        outputs[asset_id] = destination
    return outputs


def _build_0810_assets(
    *,
    output_dir: Path,
    presenter_path: Path,
    brand_path: Path,
    editorial_assets: list[AssetRef],
    audio_paths: dict[str, Path],
) -> list[AssetRef]:
    assets = [
        AssetRef(
            id="source-presenter",
            kind="video",
            path=_relative(output_dir, presenter_path),
            keywords=["presenter", "source narration"],
            provenance="user-provided",
            license="User-provided source footage",
        ),
        AssetRef(
            id="brand-profit-bricks-logo",
            kind="image",
            path=_relative(output_dir, brand_path),
            keywords=["Profit Bricks", "brand"],
            provenance="user-provided-brand-asset",
            license="User-provided",
        ),
        *editorial_assets,
    ]
    creator_by_id = {
        "5610": "DC_Studio",
        "47213": "olegbadak",
        "47792": "olegbadak",
        "45706": "utaem2022",
        "47257": "TheStockStudio",
        "22966": "FrameStock",
        "9607": "Mixkit contributor",
    }
    mixkit_manifest = json.loads(
        (output_dir / "mixkit-assets.json").read_text(encoding="utf-8")
    )
    for item in mixkit_manifest:
        path = output_dir / str(item["path"])
        _verify_manifest_checksum(path, str(item["sha256"]))
        assets.append(
            AssetRef(
                id=str(item["id"]),
                kind="video",
                path=str(item["path"]),
                keywords=[
                    "licensed internet footage",
                    str(item.get("search_query") or ""),
                ],
                provenance="internet:licensed-stock-video",
                license=str(item["license"]),
                provider=str(item["provider"]),
                remote_id=str(item["remote_id"]),
                creator=creator_by_id.get(str(item["remote_id"])),
                source_url=str(item["source_url"]),
                license_url=str(item["license_url"]),
                search_query=str(item.get("search_query") or ""),
            )
        )
    wikimedia_manifest = json.loads(
        (output_dir / "wikimedia-assets.json").read_text(
            encoding="utf-8"
        )
    )
    for item in wikimedia_manifest:
        path = output_dir / str(item["path"])
        _verify_manifest_checksum(path, str(item["sha256"]))
        assets.append(
            AssetRef(
                id=str(item["id"]),
                kind="image",
                path=str(item["path"]),
                keywords=["UPI", "public-domain internet visual"],
                provenance="internet:public-domain-media",
                license=str(item["license"]),
                provider=str(item["provider"]),
                remote_id=str(item["remote_id"]),
                creator=str(item.get("creator") or ""),
                source_url=str(item["source_url"]),
                license_url=(
                    str(item.get("license_url"))
                    if item.get("license_url")
                    else "https://commons.wikimedia.org/wiki/Commons:Licensing"
                ),
                search_query="UPI official visual",
            )
        )
    for asset_id, path in audio_paths.items():
        assets.append(
            AssetRef(
                id=asset_id,
                kind="audio",
                path=_relative(output_dir, path),
                keywords=["production audio", asset_id],
                provenance=(
                    "source-dialogue-master"
                    if asset_id.startswith("dialogue-")
                    else "local-production-audio"
                ),
            )
        )
    return assets


def assemble_0810_story(
    *,
    output_dir: Path,
) -> dict[str, Any]:
    from app.editor.production_assembly import (
        compile_production_plan,
        render_production_plan,
    )
    from app.editor.production_v4 import ProductionStore
    from app.editor.reference_story import master_reference_story_render

    output_dir = output_dir.expanduser().resolve()
    store = ProductionStore(output_dir)
    record = store.load()
    if record.state not in {
        "blueprint-ready",
        "automated-review",
        "awaiting-final-approval",
    }:
        raise ValueError(
            f"0810 assembly is not allowed from state {record.state}"
        )
    store.transition(
        "assembling",
        detail="0810 internet-sourced edit is rendering.",
        updates={
            "automated_pass": False,
            "human_approved": False,
            "final_reviewer": None,
            "error": None,
        },
    )
    try:
        plan = compile_production_plan(output_dir)
        rendered = output_dir / "rendered-internet-story.mp4"
        edited = output_dir / "edited.mp4"
        render_production_plan(
            output_dir=output_dir,
            plan=plan,
            output=rendered,
        )
        master_reference_story_render(
            plan=plan,
            rendered=rendered,
            output=edited,
        )
        store.transition(
            "automated-review",
            detail=(
                "0810 render complete; caption, pixel, provenance, and "
                "audio gates are running."
            ),
        )
        report = run_0810_review(
            output_dir=output_dir,
            plan=plan,
            edited=edited,
        )
    except Exception:
        current = store.load()
        if current.state in {"assembling", "automated-review"}:
            store.transition(
                "blueprint-ready",
                detail=(
                    "0810 assembly failed; sourced assets and blueprint "
                    "were preserved for repair."
                ),
                updates={
                    "automated_pass": False,
                    "human_approved": False,
                    "error": "0810 assembly failed.",
                },
            )
        raise
    artifacts = {
        **record.artifacts,
        "audio_master": "audio-master.json",
        "edit_plan": "edit-plan.json",
        "rendered_video": "rendered-internet-story.mp4",
        "edited_video": "edited.mp4",
        "frame_audit": "frame-audit.json",
        "audio_continuity": "audio-continuity.json",
        "review_report": "review-report.json",
        "contact_sheet": "review/contact-sheet-0810.jpg",
        "comparison_sheet": "review/style-comparison-0810.jpg",
        "caption_family_sheet": "review/caption-families-0810.jpg",
    }
    if report["automated_pass"]:
        updated = store.transition(
            "awaiting-final-approval",
            detail=(
                "0810 automated gates passed; human viewing approval is "
                "still required."
            ),
            updates={
                "automated_pass": True,
                "human_approved": False,
                "artifacts": artifacts,
                "error": None,
            },
        )
    else:
        updated = store.transition(
            "blueprint-ready",
            detail=(
                "0810 automated gates blocked release; revise and rerender."
            ),
            updates={
                "automated_pass": False,
                "human_approved": False,
                "artifacts": artifacts,
                "error": (
                    "0810 automated gates failed. Review "
                    "review-report.json."
                ),
            },
        )
    return {
        **updated.model_dump(mode="json"),
        "edited_video": "edited.mp4",
        "review_report": "review-report.json",
    }


def run_0810_review(
    *,
    output_dir: Path,
    plan: EditPlanV2,
    edited: Path,
) -> dict[str, Any]:
    from app.editor.ffmpeg import (
        measure_loudness_for_master,
        verify_render,
    )
    from app.editor.production_assembly import (
        _measure_audio_continuity,
        calculate_layer_coverage,
    )
    from app.editor.production_audit import measure_frame_audit

    metadata = verify_render(
        edited,
        expected_width=1080,
        expected_height=1920,
        expected_fps=30,
        require_h264_aac=True,
        require_yuv420p=True,
    )
    frame_audit = measure_frame_audit(edited)
    coverage = calculate_layer_coverage(plan)
    loudness_measurement = measure_loudness_for_master(
        edited,
        clean_completed_mix=False,
    )
    audio = _measure_audio_continuity(plan=plan, edited=edited)
    caption_durations = [
        page.end_ms - page.start_ms for page in plan.caption_pages
    ]
    caption_overlap = any(
        left.end_ms > right.start_ms
        for left, right in zip(
            plan.caption_pages,
            plan.caption_pages[1:],
            strict=False,
        )
    )
    unsafe_caption_text = [
        " ".join(token.text for token in page.tokens)
        for page in plan.caption_pages
        if any(
            phrase in " ".join(
                token.text for token in page.tokens
            ).casefold()
            for phrase in ("final balance", "7 lakh", "free life demo")
        )
    ]
    sfx_conflicts = [
        cue.id
        for cue in plan.audio.sfx_cues
        if any(
            cue.start_ms < window.end_ms
            and cue.start_ms + cue.duration_ms > window.start_ms
            for window in plan.audio.speech_protection_windows
        )
    ]
    static_overruns = [
        layer.id
        for layer in plan.visual_layers
        if layer.kind == "image"
        and layer.z_index <= 20
        and layer.end_ms - layer.start_ms > 2_500
    ]
    checks = [
        _check(
            "duration",
            abs(metadata.duration_seconds - STORY_DURATION_MS / 1000) <= 0.1,
            metadata.duration_seconds,
            "49.5 +/- 0.1 seconds",
        ),
        _check(
            "rendered-hard-cuts",
            16 <= int(frame_audit["rendered_cut_count"]) <= 30,
            frame_audit["rendered_cut_count"],
            "16-30",
        ),
        _check(
            "median-shot",
            1_400 <= float(frame_audit["median_shot_ms"]) <= 2_800,
            frame_audit["median_shot_ms"],
            "1400-2800 ms",
        ),
        _check(
            "presenter-coverage",
            0.23 <= float(coverage["presenter_ratio"]) <= 0.36,
            coverage["presenter_ratio"],
            "0.23-0.36 visible pixels",
        ),
        _check(
            "evidence-coverage",
            0.13 <= float(coverage["direct_evidence_ratio"]) <= 0.21,
            coverage["direct_evidence_ratio"],
            "0.13-0.21 visible pixels",
        ),
        _check(
            "licensed-internet-coverage",
            float(coverage["licensed_context_ratio"]) >= 0.43,
            coverage["licensed_context_ratio"],
            ">= 0.43 visible pixels",
        ),
        _check(
            "zero-generated-visuals",
            float(coverage["flow_ratio"]) == 0,
            coverage["flow_ratio"],
            0,
        ),
        _check(
            "visual-source-diversity",
            int(coverage["visual_source_count"]) >= 12,
            coverage["visual_source_count"],
            ">= 12 rendered assets",
        ),
        _check(
            "caption-duration",
            bool(caption_durations)
            and min(caption_durations) >= 350
            and max(caption_durations) <= 1_300,
            {
                "count": len(caption_durations),
                "minimum_ms": min(caption_durations, default=0),
                "maximum_ms": max(caption_durations, default=0),
            },
            "all pages 350-1300 ms",
        ),
        _check(
            "caption-continuity",
            not caption_overlap and not unsafe_caption_text,
            {
                "overlap": caption_overlap,
                "unsafe_text": unsafe_caption_text,
            },
            "no overlaps or unsupported visible claims",
        ),
        _check(
            "static-source-hold",
            not static_overruns,
            static_overruns,
            "no static base source > 2500 ms",
        ),
        _check(
            "motion",
            2.7 <= float(frame_audit["motion_score"]) <= 8.5,
            frame_audit["motion_score"],
            "2.7-8.5",
        ),
        _check(
            "darkness",
            float(frame_audit["dark_frame_ratio"]) <= 0.48,
            frame_audit["dark_frame_ratio"],
            "<= 0.48",
        ),
        _check(
            "luminance",
            65 <= float(frame_audit["mean_luminance"]) <= 115,
            frame_audit["mean_luminance"],
            "65-115",
        ),
        _check(
            "saturation",
            35 <= float(frame_audit["mean_saturation"]) <= 115,
            frame_audit["mean_saturation"],
            "35-115",
        ),
        _check(
            "audio-continuity",
            bool(audio["delay_passed"])
            and bool(audio["duration_passed"])
            and bool(audio["spectral_passed"]),
            audio,
            "dialogue timing, duration, and speech band preserved",
        ),
        _check(
            "loudness",
            -14.7 <= loudness_measurement.input_i <= -13.7
            and loudness_measurement.input_tp <= -1.0,
            {
                "integrated_lufs": loudness_measurement.input_i,
                "true_peak_dbtp": loudness_measurement.input_tp,
            },
            "-14.2 +/- 0.5 LUFS; <= -1 dBTP",
        ),
        _check(
            "speech-protected-sfx",
            not sfx_conflicts,
            sfx_conflicts,
            "zero SFX over protected speech onsets",
        ),
        _check(
            "verified-evidence",
            len(json.loads(
                (output_dir / "evidence.json").read_text(encoding="utf-8")
            ))
            == 4,
            4,
            "four verified primary-source beats",
        ),
    ]
    report = {
        "automated_pass": all(check["passed"] for check in checks),
        "human_approved": False,
        "checks": checks,
        "metadata": {
            "width": metadata.width,
            "height": metadata.height,
            "fps": metadata.fps,
            "frame_count": metadata.frame_count,
            "duration_seconds": metadata.duration_seconds,
        },
        "frame_audit": frame_audit,
        "coverage": coverage,
        "audio_continuity": audio,
        "loudness": {
            "integrated_lufs": loudness_measurement.input_i,
            "true_peak_dbtp": loudness_measurement.input_tp,
            "loudness_range": loudness_measurement.input_lra,
        },
        "caption_summary": {
            "pages": len(plan.caption_pages),
            "families": sorted(
                {page.family for page in plan.caption_pages}
            ),
            "unsafe_text": unsafe_caption_text,
        },
        "visual_policy": {
            "generated_visuals": 0,
            "internet_visual_api_required": False,
            "human_final_approval_required": True,
        },
    }
    _write_json(output_dir / "frame-audit.json", frame_audit)
    _write_json(output_dir / "audio-continuity.json", audio)
    _write_json(output_dir / "review-report.json", report)
    _create_0810_contact_sheet(
        video=edited,
        output=output_dir / "review" / "contact-sheet-0810.jpg",
    )
    _create_0810_style_comparison(
        reference=_DEFAULT_STYLE_REFERENCE,
        edited=edited,
        output=output_dir / "review" / "style-comparison-0810.jpg",
    )
    _create_0810_caption_sheet(
        video=edited,
        pages=plan.caption_pages,
        output=output_dir / "review" / "caption-families-0810.jpg",
    )
    return report


def _create_0810_contact_sheet(*, video: Path, output: Path) -> None:
    schedule = build_0810_schedule()
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise RuntimeError(f"Unable to inspect {video}")
    cells: list[np.ndarray] = []
    try:
        for shot in schedule:
            timestamp_ms = (
                int(shot["start_ms"]) + int(shot["end_ms"])
            ) // 2
            frame = _frame_at(capture, timestamp_ms / 1000)
            cell = cv2.resize(frame, (270, 480))
            cv2.rectangle(cell, (0, 0), (270, 38), (0, 0, 0), -1)
            label = (
                f"{str(shot['id']).replace('shot-', '')} "
                f"{timestamp_ms / 1000:04.1f}s"
            )
            cv2.putText(
                cell,
                label,
                (8, 26),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.58,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
            cells.append(cell)
    finally:
        capture.release()
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(
        str(output),
        _contact_sheet_grid(cells, columns=4),
        [cv2.IMWRITE_JPEG_QUALITY, 93],
    )


def _contact_sheet_grid(
    cells: list[np.ndarray],
    *,
    columns: int,
) -> np.ndarray:
    if not cells:
        raise ValueError("Contact sheet requires at least one frame")
    if columns <= 0:
        raise ValueError("Contact sheet columns must be positive")
    expected_shape = cells[0].shape
    if any(cell.shape != expected_shape for cell in cells):
        raise ValueError("Contact sheet cells must have matching dimensions")
    blank = np.zeros_like(cells[0])
    rows: list[np.ndarray] = []
    for index in range(0, len(cells), columns):
        row = list(cells[index : index + columns])
        row.extend(blank.copy() for _ in range(columns - len(row)))
        rows.append(np.hstack(row))
    return np.vstack(rows)


def _create_0810_style_comparison(
    *,
    reference: Path,
    edited: Path,
    output: Path,
) -> None:
    if not reference.is_file():
        return
    pairs = [
        ("HOOK", 1.1, 0.7),
        ("ROBOT", 4.0, 4.0),
        ("EVIDENCE", 13.1, 6.1),
        ("RISK", 16.3, 9.7),
        ("RESET", 10.7, 11.5),
        ("CONTEXT", 24.7, 16.2),
        ("ACTIONS", 4.0, 22.8),
        ("MANAGER", 24.7, 32.7),
        ("BRAND", 28.9, 36.8),
        ("ENDING", 32.7, 47.2),
    ]
    reference_capture = cv2.VideoCapture(str(reference))
    edited_capture = cv2.VideoCapture(str(edited))
    if not reference_capture.isOpened() or not edited_capture.isOpened():
        reference_capture.release()
        edited_capture.release()
        return
    pair_cells: list[np.ndarray] = []
    try:
        for label, reference_time, edited_time in pairs:
            reference_frame = cv2.resize(
                _frame_at(reference_capture, reference_time),
                (270, 480),
            )
            edited_frame = cv2.resize(
                _frame_at(edited_capture, edited_time),
                (270, 480),
            )
            for cell, suffix in (
                (reference_frame, "REF"),
                (edited_frame, "0810"),
            ):
                cv2.rectangle(cell, (0, 0), (270, 38), (0, 0, 0), -1)
                cv2.putText(
                    cell,
                    f"{label} | {suffix}",
                    (8, 26),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.51,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )
            pair_cells.append(np.hstack([reference_frame, edited_frame]))
    finally:
        reference_capture.release()
        edited_capture.release()
    rows = [
        np.hstack(pair_cells[index : index + 2])
        for index in range(0, len(pair_cells), 2)
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(
        str(output),
        np.vstack(rows),
        [cv2.IMWRITE_JPEG_QUALITY, 93],
    )


def _create_0810_caption_sheet(
    *,
    video: Path,
    pages: list[CaptionPage],
    output: Path,
) -> None:
    first_by_family: dict[str, CaptionPage] = {}
    for page in pages:
        first_by_family.setdefault(page.family, page)
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise RuntimeError(f"Unable to inspect {video}")
    cells: list[np.ndarray] = []
    try:
        for family, page in sorted(first_by_family.items()):
            timestamp = (page.start_ms + page.end_ms) / 2 / 1000
            frame = cv2.resize(_frame_at(capture, timestamp), (270, 480))
            cv2.rectangle(frame, (0, 0), (270, 38), (0, 0, 0), -1)
            cv2.putText(
                frame,
                family,
                (8, 26),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
            cells.append(frame)
    finally:
        capture.release()
    if not cells:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(
        str(output),
        np.hstack(cells),
        [cv2.IMWRITE_JPEG_QUALITY, 94],
    )


def _frame_at(capture: cv2.VideoCapture, timestamp: float) -> np.ndarray:
    capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
    ok, frame = capture.read()
    if not ok:
        raise RuntimeError(f"Unable to read frame at {timestamp:.3f}s")
    return frame


def _0810_evidence_ids(editorial_role: str) -> list[str]:
    return {
        "atc-three-months": ["mt5-atc-three-months"],
        "balance-peak": ["mql5-110k-peak"],
        "risk-foreshadow": ["mql5-aggressive-risk"],
        "robot-actions": ["mt5-robot-actions"],
    }.get(editorial_role, [])


def _caption_family_at(
    captions: list[CaptionPage],
    start_ms: int,
) -> str | None:
    page = next(
        (
            candidate
            for candidate in captions
            if candidate.start_ms <= start_ms < candidate.end_ms
        ),
        None,
    )
    if page is None:
        page = next(
            (
                candidate
                for candidate in captions
                if candidate.start_ms >= start_ms
            ),
            None,
        )
    return page.family if page is not None else None


def _verify_manifest_checksum(path: Path, expected: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = _sha256(path)
    if actual.casefold() != expected.casefold():
        raise ValueError(f"Asset checksum changed: {path}")


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _run_command(command: list[str]) -> None:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=3600,
        check=False,
        shell=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            completed.stderr[-6000:].strip() or "Media command failed"
        )


def _check(
    name: str,
    passed: bool,
    measured: Any,
    target: Any,
) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "measured": measured,
        "target": target,
    }
