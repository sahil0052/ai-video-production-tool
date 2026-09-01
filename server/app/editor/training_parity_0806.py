from __future__ import annotations

from pathlib import Path
import re

import numpy as np
from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont, ImageOps

from app.models import (
    AssetRef,
    AudioPlan,
    CaptionPage,
    CaptionToken,
    EvidenceItem,
    OutputSpec,
    VideoMetadata,
)
from app.production_models import (
    BlueprintLayerSpec,
    DialogueEditSegment,
    MotionEventSpec,
    ProductionBlueprint,
)
from app.editor.training_reference_0806 import (
    _layer,
    build_v7_audio_plan,
    build_shot_schedule as build_v7_shot_schedule,
    estimate_role_coverage,
)


DURATION_MS = 41_400


V8_MUSIC_CANDIDATE = {
    "id": "588",
    "name": "Feedback Dreams",
    "file": "feedback-dreams-588.mp3",
    "estimated_bpm": 94.5,
    "selection_start_seconds": 50,
    "provider": "Mixkit",
}

V8_CAPTURE_OVERRIDES = {
    "capture-mt5-hook-action": "mt5-hook-action-v2.mp4",
    "capture-metaeditor-open": "metaeditor-compile-action-v2.mp4",
    "capture-metaeditor-rule-highlight": (
        "metaeditor-rule-highlight-v2.mp4"
    ),
    "capture-mt5-navigator-ea": "mt5-navigator-action-v2.mp4",
    "capture-mt5-risk-inputs": "mt5-risk-input-action-v2.mp4",
    "capture-mt5-risk-alternate": (
        "mt5-risk-alternate-action-v2.mp4"
    ),
    "capture-mt5-attach-ea": "mt5-attach-action-v2.mp4",
    "capture-mt5-strategy-tester": (
        "mt5-strategy-tester-action-v2.mp4"
    ),
}


_CAPTION_SPECS = [
    (1_200, 2_340, "FOREX TRADING ROBOT?"),
    (2_800, 3_620, "IT IS SOFTWARE"),
    (3_760, 4_260, "THAT"),
    (4_560, 5_280, "SET RULES"),
    (5_280, 6_180, "AUTOMATICALLY"),
    (6_240, 7_200, "TRADES FOR YOU"),
    (8_000, 8_890, "EXPERT ADVISOR"),
    (9_040, 9_760, "IT IS CALLED"),
    (9_760, 10_500, "IN SHORT, EA."),
    (12_060, 12_700, "BUT"),
    (12_700, 13_480, "IF THE"),
    (13_480, 14_160, "RULES ARE WRONG"),
    (15_120, 15_760, "IN 2008"),
    (15_760, 16_950, "AUTOMATED TRADING"),
    (16_950, 17_450, "CHAMPIONSHIP"),
    (17_840, 18_930, "AN EXPERT ADVISOR"),
    (19_430, 20_730, "$110,000."),
    (20_730, 21_760, "$110,000."),
    (21_760, 22_310, "THE RISK"),
    (22_310, 23_610, "TURNED THE GAME"),
    (23_610, 23_960, "TURNED THE GAME"),
    (24_070, 24_710, "HIGH RISK"),
    (24_710, 25_710, "INCREASED RESULT"),
    (26_650, 27_780, "TURNED UPSIDE DOWN"),
    (27_970, 28_790, "LESSON IS SIMPLE"),
    (28_790, 29_470, "EXPERT ADVISOR"),
    (29_650, 30_450, "DOESN'T TRADE"),
    (30_940, 31_660, "BUT DOESN'T"),
    (31_730, 32_930, "CHOOSE SAFE RISK"),
    (33_410, 34_130, "IF YOU WANT"),
    (34_130, 34_690, "TO SEE HOW"),
    (34_690, 35_340, "EXPERT ADVISOR"),
    (35_490, 36_450, "TRADES"),
    (36_610, 37_490, "FOLLOW US"),
    (38_290, 38_930, "JOIN OUR"),
    (38_930, 39_650, "TELEGRAM GROUP"),
    (40_610, 41_350, "THANK YOU."),
]


def _tokens_for_page(
    text: str,
    *,
    start_ms: int,
    end_ms: int,
) -> list[CaptionToken]:
    words = re.findall(r"[\w$,'?!.]+", text)
    duration = end_ms - start_ms
    return [
        CaptionToken(
            text=word,
            start_ms=start_ms + round(duration * index / len(words)),
            end_ms=start_ms
            + round(duration * (index + 1) / len(words)),
            highlighted=False,
            confidence=None,
        )
        for index, word in enumerate(words)
    ]


def build_v8_caption_pages() -> list[CaptionPage]:
    return [
        CaptionPage(
            start_ms=start_ms,
            end_ms=end_ms,
            family="technical-mono",
            anchor="center-74",
            transition="hard-cut",
            max_width=480,
            tokens=_tokens_for_page(
                text,
                start_ms=start_ms,
                end_ms=end_ms,
            ),
        )
        for start_ms, end_ms, text in _CAPTION_SPECS
    ]


def build_v8_music_filter() -> str:
    return (
        "highpass=f=35,"
        "lowpass=f=7000,"
        "equalizer=f=2800:t=q:w=0.9:g=-2,"
        "afade=t=in:st=0:d=0.35,"
        "afade=t=out:st=41.0:d=0.4,"
        "atrim=duration=41.4,"
        "aresample=48000"
    )


def _fit_source(
    image: Image.Image,
    size: tuple[int, int],
    *,
    centering: tuple[float, float] = (0.5, 0.5),
) -> Image.Image:
    return ImageOps.fit(
        image.convert("RGB"),
        size,
        method=Image.Resampling.LANCZOS,
        centering=centering,
    )


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = (
        ("consolab.ttf", "arialbd.ttf")
        if bold
        else ("consola.ttf", "arial.ttf")
    )
    for name in names:
        path = Path(r"C:\Windows\Fonts") / name
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default(size=size)


def _source_canvas(
    label: str,
    *,
    source: Image.Image,
    panel_tint: str = "#EEE9DE",
    label_color: str = "#182328",
) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    canvas = Image.new("RGB", (1080, 1920), "#090E11")
    panel_box = (28, 128, 1_052, 1_850)
    panel_size = (
        panel_box[2] - panel_box[0],
        panel_box[3] - panel_box[1],
    )
    source_field = ImageOps.fit(
        source.convert("RGB"),
        panel_size,
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    ).filter(ImageFilter.GaussianBlur(radius=18))
    source_field = Image.blend(
        source_field,
        Image.new("RGB", panel_size, "#FAFAF7"),
        0.35,
    )
    tint = Image.new("RGB", panel_size, panel_tint)
    panel = Image.blend(source_field, tint, 0.68)
    rng = np.random.default_rng(sum(ord(character) for character in label))
    coarse_noise = rng.normal(
        0,
        2,
        (
            max(1, panel_size[1] // 16),
            max(1, panel_size[0] // 16),
        ),
    )
    noise = np.asarray(
        Image.fromarray(
            np.clip(coarse_noise + 128, 0, 255).astype(np.uint8),
            mode="L",
        ).resize(panel_size, Image.Resampling.BILINEAR),
        dtype=np.float32,
    ) - 128
    panel_pixels = np.asarray(panel, dtype=np.float32)
    horizontal_falloff = np.linspace(
        -10,
        10,
        panel_size[0],
        dtype=np.float32,
    )[None, :, None]
    panel = Image.fromarray(
        np.clip(
            panel_pixels + noise[:, :, None] + horizontal_falloff,
            0,
            255,
        ).astype(np.uint8),
        mode="RGB",
    )
    canvas.paste(panel, panel_box[:2])
    draw = ImageDraw.Draw(canvas)
    draw.rectangle(panel_box, outline="#344248", width=2)
    draw.text(
        (76, panel_box[1] + 56),
        label,
        font=_font(22),
        fill=label_color,
        anchor="lm",
    )
    draw.line(
        (76, 1_642, 1_004, 1_642),
        fill="#8A9699",
        width=2,
    )
    draw.text(
        (76, 1_682),
        "EDITORIAL EXCERPT / ORIGINAL SOURCE PIXELS",
        font=_font(18),
        fill="#46545A",
        anchor="lm",
    )
    return canvas, draw


def _paste_contained(
    canvas: Image.Image,
    source: Image.Image,
    *,
    box: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    left, top, right, bottom = box
    contained = ImageOps.contain(
        source.convert("RGB"),
        (right - left, bottom - top),
        method=Image.Resampling.LANCZOS,
    )
    x = left + (right - left - contained.width) // 2
    y = top + (bottom - top - contained.height) // 2
    canvas.paste(contained, (x, y))
    return (x, y, x + contained.width, y + contained.height)


def _crop_source(
    source: Image.Image,
    *,
    left: int,
    top: int,
    right: int,
    bottom: int,
) -> Image.Image:
    return source.crop(
        (
            max(0, min(source.width - 1, left)),
            max(0, min(source.height - 1, top)),
            max(1, min(source.width, right)),
            max(1, min(source.height, bottom)),
        )
    )


def prepare_v8_risk_reversal_graphic(output: Path) -> Path:
    image = Image.new("RGB", (1080, 1920), "#1A080D")
    draw = ImageDraw.Draw(image, "RGBA")
    draw.text(
        (72, 112),
        "RISK REVERSAL",
        font=_font(30),
        fill=(232, 93, 101, 255),
    )
    center = (540, 930)
    for radius, alpha in ((205, 54), (330, 34), (445, 22)):
        draw.ellipse(
            (
                center[0] - radius,
                center[1] - radius,
                center[0] + radius,
                center[1] + radius,
            ),
            outline=(232, 74, 83, alpha),
            width=3,
        )
    draw.line(
        (150, 1_350, 390, 760, 625, 495),
        fill=(86, 212, 195, 255),
        width=18,
        joint="curve",
    )
    draw.polygon(
        [(625, 495), (586, 584), (680, 552)],
        fill=(86, 212, 195, 255),
    )
    draw.line(
        (625, 495, 760, 980, 900, 1_445),
        fill=(232, 74, 83, 255),
        width=18,
        joint="curve",
    )
    draw.polygon(
        [(900, 1_445), (845, 1_370), (936, 1_345)],
        fill=(232, 74, 83, 255),
    )
    draw.text(
        (148, 1_465),
        "HIGH RISK",
        font=_font(55, bold=True),
        fill=(243, 245, 246, 255),
    )
    draw.text(
        (540, 405),
        "RESULT UP",
        font=_font(45),
        fill=(120, 226, 207, 255),
        anchor="mm",
    )
    draw.text(
        (540, 1_610),
        "THEN REVERSED",
        font=_font(57, bold=True),
        fill=(247, 114, 121, 255),
        anchor="mm",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    return output


def prepare_v8_solid_dark_backdrop(output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1080, 1920), "#05090A").save(output)
    return output


def prepare_v8_evidence_frames(
    *,
    history_source: Path,
    risk_source: Path,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    history = Image.open(history_source).convert("RGB")
    risk = Image.open(risk_source).convert("RGB")

    overview, _ = _source_canvas(
        "OFFICIAL SOURCE OVERVIEW / METAQUOTES",
        source=history,
        panel_tint="#E7ECEA",
    )
    _paste_contained(
        overview,
        history,
        box=(70, 160, 1_010, 1_810),
    )
    overview_path = output_dir / "history-source-overview.png"
    overview.save(overview_path)

    championship, championship_draw = _source_canvas(
        "PRIMARY SOURCE / ATC 2008 EXCERPT",
        source=risk,
        panel_tint="#F8F5EF",
    )
    _paste_contained(
        championship,
        Image.blend(
            risk.filter(ImageFilter.GaussianBlur(radius=1.6)),
            Image.new("RGB", risk.size, "#E8E0D3"),
            0.42,
        ),
        box=(110, 180, 970, 510),
    )
    atc_2008 = _crop_source(
        risk,
        left=0,
        top=round(risk.height * 0.58),
        right=round(risk.width * 0.536),
        bottom=round(risk.height * 0.69),
    )
    contest_subject = _crop_source(
        risk,
        left=0,
        top=round(risk.height * 0.68),
        right=round(risk.width * 0.31),
        bottom=round(risk.height * 0.79),
    )
    first_bounds = _paste_contained(
        championship,
        atc_2008,
        box=(70, 650, 1_010, 950),
    )
    championship_second_bounds = _paste_contained(
        championship,
        contest_subject,
        box=(70, 1_020, 1_010, 1_260),
    )
    championship_draw.rectangle(
        (80, first_bounds[3] + 18, 1_000, first_bounds[3] + 28),
        fill="#70D7D3",
    )
    championship_draw.rectangle(
        (
            80,
            championship_second_bounds[3] + 18,
            1_000,
            championship_second_bounds[3] + 26,
        ),
        fill="#AAB5B6",
    )
    championship_path = output_dir / "history-source-excerpt.png"
    championship.save(championship_path)

    risk_background, risk_draw = _source_canvas(
        "PRIMARY SOURCE / MQL5 ARTICLE 525",
        source=risk,
        panel_tint="#F3F7F6",
    )
    risk_reason = _crop_source(
        risk,
        left=0,
        top=round(risk.height * 0.82),
        right=round(risk.width * 0.50),
        bottom=round(risk.height * 0.91),
    )
    result_and_fall = _crop_source(
        risk,
        left=round(risk.width * 0.50),
        top=round(risk.height * 0.82),
        right=risk.width,
        bottom=round(risk.height * 0.91),
    )
    _paste_contained(
        risk_background,
        Image.blend(
            risk.filter(ImageFilter.GaussianBlur(radius=1.6)),
            Image.new("RGB", risk.size, "#EEF3F2"),
            0.42,
        ),
        box=(110, 180, 970, 510),
    )
    left_bounds = _paste_contained(
        risk_background,
        risk_reason,
        box=(70, 650, 1_010, 980),
    )
    risk_second_bounds = _paste_contained(
        risk_background,
        result_and_fall,
        box=(70, 1_050, 1_010, 1_380),
    )
    risk_draw.rectangle(
        (80, left_bounds[3] + 18, 1_000, left_bounds[3] + 28),
        fill="#70D7D3",
    )
    risk_draw.rectangle(
        (
            80,
            risk_second_bounds[3] + 18,
            1_000,
            risk_second_bounds[3] + 26,
        ),
        fill="#AAB5B6",
    )
    risk_excerpt_path = output_dir / "risk-source-excerpt.png"
    risk_background.save(risk_excerpt_path)

    number, number_draw = _source_canvas(
        "VERIFIED SOURCE MACRO / MQL5 ARTICLE 525",
        source=risk,
        panel_tint="#F7F1E7",
    )
    _paste_contained(
        number,
        Image.blend(
            risk.filter(ImageFilter.GaussianBlur(radius=1.6)),
            Image.new("RGB", risk.size, "#E7DED0"),
            0.42,
        ),
        box=(110, 180, 970, 510),
    )
    number_crop = _crop_source(
        risk,
        left=round(risk.width * 0.04),
        top=round(risk.height * 0.18),
        right=round(risk.width * 0.43),
        bottom=round(risk.height * 0.27),
    )
    answer_number_crop = _crop_source(
        risk,
        left=round(risk.width * 0.50),
        top=round(risk.height * 0.82),
        right=risk.width,
        bottom=round(risk.height * 0.91),
    )
    number_bounds = _paste_contained(
        number,
        number_crop,
        box=(70, 760, 1_010, 1_030),
    )
    answer_number_bounds = _paste_contained(
        number,
        answer_number_crop,
        box=(70, 1_100, 1_010, 1_370),
    )
    number_draw.rectangle(
        (
            80,
            number_bounds[3] + 18,
            1_000,
            number_bounds[3] + 30,
        ),
        fill="#70D7D3",
    )
    number_draw.rectangle(
        (
            80,
            answer_number_bounds[3] + 18,
            1_000,
            answer_number_bounds[3] + 26,
        ),
        fill="#AAB5B6",
    )
    number_path = output_dir / "risk-source-number.png"
    number.save(number_path)

    return {
        "evidence-history-original": history_source,
        "evidence-risk-original": risk_source,
        "evidence-history-overview": overview_path,
        "evidence-championship-excerpt": championship_path,
        "evidence-risk-excerpt": risk_excerpt_path,
        "evidence-risk-number": number_path,
    }


def caption_coverage_ratio(
    pages: list[CaptionPage],
    duration_ms: int,
) -> float:
    if duration_ms <= 0:
        return 0.0
    intervals = sorted((page.start_ms, page.end_ms) for page in pages)
    visible_ms = 0
    active_start: int | None = None
    active_end: int | None = None
    for start_ms, end_ms in intervals:
        if active_start is None:
            active_start, active_end = start_ms, end_ms
        elif start_ms <= int(active_end):
            active_end = max(int(active_end), end_ms)
        else:
            visible_ms += int(active_end) - active_start
            active_start, active_end = start_ms, end_ms
    if active_start is not None and active_end is not None:
        visible_ms += active_end - active_start
    return visible_ms / duration_ms


def technical_mono_caption_share(pages: list[CaptionPage]) -> float:
    total_ms = sum(page.end_ms - page.start_ms for page in pages)
    if total_ms <= 0:
        return 0.0
    technical_ms = sum(
        page.end_ms - page.start_ms
        for page in pages
        if page.family == "technical-mono"
    )
    return technical_ms / total_ms


def caption_token_window_violations(
    pages: list[CaptionPage],
) -> list[dict[str, object]]:
    violations: list[dict[str, object]] = []
    for index, page in enumerate(pages):
        for token in page.tokens:
            if (
                token.start_ms < page.start_ms
                or token.end_ms > page.end_ms
            ):
                violations.append(
                    {
                        "page_index": index,
                        "token": token.text,
                        "page_window": [page.start_ms, page.end_ms],
                        "token_window": [token.start_ms, token.end_ms],
                    }
                )
    return violations


def build_v8_shot_schedule() -> list[dict[str, object]]:
    return build_v7_shot_schedule()


def build_v8_audio_plan(
    transcript: list[dict[str, object]],
) -> AudioPlan:
    base = build_v7_audio_plan(transcript)
    payload = base.model_dump(mode="json")
    payload["music_gain_automation"] = [
        {
            **window,
            "gain_db": -10,
            "reason": "Duck documentary-tech music beneath narration",
        }
        for window in payload["music_gain_automation"]
    ]
    for cue in payload["sfx_cues"]:
        if cue["id"] == "sfx-reset":
            cue.update(
                {
                    "start_ms": 9_360,
                    "gain_db": -15,
                    "reason": "presenter reset aligned before speech onset",
                }
            )
        elif cue["id"] == "sfx-code-rule":
            cue.update(
                {
                    "start_ms": 10_700,
                    "gain_db": -16,
                    "reason": "code-to-rule layout change",
                }
            )
    return AudioPlan.model_validate(
        {
            **payload,
            "music_bpm": 95,
            "music_base_gain_db": -7,
            "music_duck_db": 10,
            "integrated_lufs": -14.2,
            "true_peak_dbtp": -1.2,
            "target_lra_lu": 2.8,
        }
    )


def build_v8_motion_events() -> list[MotionEventSpec]:
    specifications = [
        (
            "hook",
            240,
            520,
            "punch-crop",
            "layer-hook-product",
            0.80,
            "none",
        ),
        (
            "code-open",
            2_340,
            2_640,
            "proof-punch",
            "layer-metaeditor-open",
            0.75,
            "none",
        ),
        (
            "code-open-slide",
            2_340,
            2_640,
            "directional-jump",
            "layer-metaeditor-open",
            0.65,
            "left",
        ),
        (
            "code-rule",
            4_700,
            5_060,
            "proof-punch",
            "layer-code-macro",
            0.80,
            "none",
        ),
        (
            "code-rule-slide",
            4_700,
            5_060,
            "directional-jump",
            "layer-code-macro",
            0.65,
            "right",
        ),
        (
            "navigator",
            6_820,
            7_180,
            "directional-jump",
            "layer-navigator-ea",
            0.75,
            "right",
        ),
        (
            "wrong-rule",
            12_060,
            12_420,
            "proof-punch",
            "layer-wrong-rule",
            0.70,
            "none",
        ),
        (
            "evidence-macro",
            17_460,
            17_820,
            "proof-punch",
            "layer-evidence-result",
            0.75,
            "none",
        ),
        (
            "number",
            19_500,
            19_900,
            "proof-punch",
            "layer-evidence-number",
            0.80,
            "none",
        ),
        (
            "risk-input",
            21_820,
            22_180,
            "proof-punch",
            "layer-risk-inputs",
            0.80,
            "none",
        ),
        (
            "risk-input-slide",
            21_820,
            22_180,
            "directional-jump",
            "layer-risk-inputs",
            0.65,
            "up",
        ),
        (
            "reversal",
            25_800,
            26_220,
            "directional-jump",
            "layer-risk-reversal",
            0.75,
            "down",
        ),
        (
            "attach",
            33_020,
            33_380,
            "proof-punch",
            "layer-attach-ea",
            0.80,
            "none",
        ),
        (
            "attach-slide",
            33_020,
            33_380,
            "directional-jump",
            "layer-attach-ea",
            0.65,
            "right",
        ),
        (
            "tester",
            35_200,
            35_560,
            "proof-punch",
            "layer-strategy-tester",
            0.80,
            "none",
        ),
        (
            "tester-slide",
            35_200,
            35_560,
            "directional-jump",
            "layer-strategy-tester",
            0.65,
            "up",
        ),
        (
            "ending",
            39_800,
            40_160,
            "punch-crop",
            "layer-ending-presenter",
            0.70,
            "none",
        ),
    ]
    return [
        MotionEventSpec(
            id=f"motion-{event_id}",
            start_ms=start_ms,
            end_ms=end_ms,
            kind=kind,
            target_id=target_id,
            intensity=intensity,
            direction=direction,
        )
        for (
            event_id,
            start_ms,
            end_ms,
            kind,
            target_id,
            intensity,
            direction,
        ) in specifications
    ]


def create_v8_blueprint(
    *,
    source_filename: str,
    source_metadata: VideoMetadata,
    assets: list[AssetRef],
    evidence: list[EvidenceItem],
    transcript: list[dict[str, object]],
) -> ProductionBlueprint:
    return ProductionBlueprint(
        source_filename=source_filename,
        source_metadata=source_metadata,
        output=OutputSpec(width=1080, height=1920, fps=30),
        duration_ms=DURATION_MS,
        assets=assets,
        layers=build_v8_layers(),
        caption_pages=build_v8_caption_pages(),
        audio=build_v8_audio_plan(transcript),
        flow_shots=[],
        evidence=evidence,
        reference_profile="technical-reference",
        story_profile="automation-future-parity",
        voice_policy="preserve-verbatim",
        dialogue_edl=[
            DialogueEditSegment(
                id="dialogue-verbatim",
                source_start_ms=0,
                source_end_ms=DURATION_MS,
                output_start_ms=0,
                output_end_ms=DURATION_MS,
                playback_rate=1,
                preserve_pitch=True,
            )
        ],
        kinetic_text_cues=[],
        motion_events=build_v8_motion_events(),
    )


def build_v8_layers() -> list[BlueprintLayerSpec]:
    return [
        _layer(
            id="layer-hook-product",
            shot_id="shot-01",
            start_ms=0,
            end_ms=2_340,
            source_role="real-product",
            asset_id="capture-mt5-hook-action",
            source_start_ms=1_100,
            source_end_ms=3_440,
            bounds=(0, 0, 1080, 1100),
            crop=(0.23, 0.0, 0.65, 1.0),
            scale_start=1.02,
            scale_end=1.07,
            x_start=-20,
            x_end=20,
            contrast=1.06,
            saturation=1.04,
        ),
        _layer(
            id="layer-hook-presenter",
            shot_id="shot-01",
            start_ms=0,
            end_ms=2_340,
            source_role="presenter",
            asset_id="source-presenter",
            source_start_ms=0,
            source_end_ms=2_340,
            bounds=(0, 1100, 1080, 820),
            scale_start=1.02,
            scale_end=1.02,
            brightness=1.03,
        ),
        _layer(
            id="layer-hook-title",
            shot_id="shot-01",
            start_ms=240,
            end_ms=2_080,
            source_role="deterministic-graphic",
            asset_id="graphic-hook-title",
            kind="image",
            bounds=(90, 280, 900, 330),
            fit="contain",
            z_index=40,
            scale_end=1,
        ),
        _layer(
            id="layer-metaeditor-backdrop",
            shot_id="shot-02",
            start_ms=2_340,
            end_ms=4_700,
            source_role="deterministic-graphic",
            asset_id="graphic-dark-backdrop",
            kind="image",
            z_index=1,
            color_filter="brightness(0.55) saturate(0.60)",
            scale_end=1,
        ),
        _layer(
            id="layer-metaeditor-product-field",
            shot_id="shot-02",
            start_ms=2_340,
            end_ms=4_700,
            source_role="real-product",
            asset_id="capture-metaeditor-open",
            source_start_ms=700,
            source_end_ms=3_060,
            bounds=(150, 80, 780, 1_760),
            z_index=2,
            brightness=0.25,
            contrast=0.84,
            saturation=0.28,
            opacity_start=0.62,
            opacity_end=0.62,
            blur_px=42,
            color_filter="brightness(0.45) saturate(1.35)",
            scale_end=1,
        ),
        _layer(
            id="layer-metaeditor-open",
            shot_id="shot-02",
            start_ms=2_340,
            end_ms=4_700,
            source_role="real-product",
            asset_id="capture-metaeditor-open",
            source_start_ms=700,
            source_end_ms=3_060,
            bounds=(100, 350, 880, 1_080),
            crop=(0.18, 0.06, 0.62, 0.88),
            z_index=10,
            border_radius=14,
            scale_start=1,
            scale_end=1,
            x_start=0,
            x_end=0,
            brightness=1.15,
            contrast=1.08,
            saturation=1.04,
            blur_px=0.15,
        ),
        _layer(
            id="layer-code-backdrop",
            shot_id="shot-03",
            start_ms=4_700,
            end_ms=6_820,
            source_role="deterministic-graphic",
            asset_id="graphic-dark-backdrop",
            kind="image",
            z_index=1,
            scale_end=1,
        ),
        _layer(
            id="layer-code-accent",
            shot_id="shot-03",
            start_ms=4_700,
            end_ms=6_820,
            source_role="deterministic-graphic",
            asset_id="graphic-cool-backdrop",
            kind="image",
            bounds=(0, 0, 1_080, 420),
            z_index=2,
            color_filter="brightness(0.72) saturate(1.20)",
            scale_end=1,
        ),
        _layer(
            id="layer-code-context",
            shot_id="shot-03",
            start_ms=4_700,
            end_ms=6_820,
            source_role="licensed-context",
            asset_id="licensed-code-soft-backdrop",
            kind="image",
            z_index=3,
            brightness=0.25,
            contrast=0.75,
            saturation=0.25,
            opacity_start=0.03,
            opacity_end=0.03,
            scale_end=1,
        ),
        _layer(
            id="layer-code-product-field",
            shot_id="shot-03",
            start_ms=4_700,
            end_ms=6_820,
            source_role="real-product",
            asset_id="capture-metaeditor-rule-highlight",
            source_start_ms=2_700,
            source_end_ms=4_820,
            bounds=(150, 80, 780, 1_760),
            z_index=4,
            brightness=0.25,
            contrast=0.82,
            saturation=0.25,
            opacity_start=0.62,
            opacity_end=0.62,
            blur_px=42,
            color_filter="brightness(0.45) saturate(1.35)",
            scale_end=1,
        ),
        _layer(
            id="layer-code-macro",
            shot_id="shot-03",
            start_ms=4_700,
            end_ms=6_820,
            source_role="real-product",
            asset_id="capture-metaeditor-rule-highlight",
            source_start_ms=2_700,
            source_end_ms=4_820,
            bounds=(80, 500, 920, 920),
            crop=(0.18, 0.08, 0.56, 0.84),
            z_index=10,
            border_radius=14,
            scale_start=1,
            scale_end=1.07,
            x_start=30,
            x_end=-30,
            brightness=1.45,
            contrast=1.08,
            saturation=1.04,
            blur_px=0.15,
        ),
        _layer(
            id="layer-navigator-backdrop",
            shot_id="shot-04",
            start_ms=6_820,
            end_ms=9_420,
            source_role="deterministic-graphic",
            asset_id="graphic-dark-backdrop",
            kind="image",
            z_index=1,
            scale_end=1,
        ),
        _layer(
            id="layer-navigator-product-field",
            shot_id="shot-04",
            start_ms=6_820,
            end_ms=9_420,
            source_role="real-product",
            asset_id="capture-mt5-navigator-ea",
            source_start_ms=500,
            source_end_ms=3_100,
            bounds=(150, 80, 780, 1_760),
            z_index=2,
            brightness=0.25,
            contrast=0.84,
            saturation=0.30,
            opacity_start=0.62,
            opacity_end=0.62,
            blur_px=42,
            color_filter="brightness(0.45) saturate(1.35)",
            scale_end=1,
        ),
        _layer(
            id="layer-navigator-ea",
            shot_id="shot-04",
            start_ms=6_820,
            end_ms=9_420,
            source_role="real-product",
            asset_id="capture-mt5-navigator-ea",
            source_start_ms=500,
            source_end_ms=3_100,
            bounds=(40, 180, 720, 1_560),
            crop=(0.0, 0.03, 0.24, 0.94),
            z_index=10,
            border_radius=14,
            scale_start=1,
            scale_end=1.07,
            y_start=-30,
            y_end=30,
            brightness=1.40,
            contrast=1.08,
            saturation=1.04,
            blur_px=0.15,
        ),
        _layer(
            id="layer-reset-presenter",
            shot_id="shot-05",
            start_ms=9_420,
            end_ms=10_700,
            source_role="presenter",
            asset_id="source-presenter",
            source_start_ms=9_420,
            source_end_ms=10_700,
            scale_start=1.04,
            scale_end=1.04,
            brightness=1.03,
        ),
        _layer(
            id="layer-reset-backdrop",
            shot_id="shot-05",
            start_ms=10_700,
            end_ms=12_060,
            source_role="deterministic-graphic",
            asset_id="graphic-light-backdrop",
            kind="image",
            z_index=1,
            scale_end=1,
        ),
        _layer(
            id="layer-reset-code",
            shot_id="shot-05",
            start_ms=10_700,
            end_ms=12_060,
            source_role="real-product",
            asset_id="capture-metaeditor-rule-highlight",
            source_start_ms=3_500,
            source_end_ms=4_860,
            bounds=(40, 230, 1_000, 1_460),
            crop=(0.20, 0.02, 0.50, 0.96),
            z_index=10,
            border_radius=8,
            scale_start=1.015,
            scale_end=1.035,
            brightness=1.05,
            contrast=1.10,
            saturation=1.02,
        ),
        _layer(
            id="layer-wrong-rule-context",
            shot_id="shot-06",
            start_ms=12_060,
            end_ms=14_160,
            source_role="licensed-context",
            asset_id="licensed-code-soft-backdrop",
            kind="image",
            brightness=0.25,
            contrast=0.75,
            saturation=0.25,
            opacity_start=0.14,
            opacity_end=0.14,
            z_index=1,
            scale_end=1,
        ),
        _layer(
            id="layer-wrong-rule",
            shot_id="shot-06",
            start_ms=12_060,
            end_ms=14_160,
            source_role="deterministic-graphic",
            asset_id="graphic-wrong-rule",
            kind="image",
            bounds=(60, 170, 960, 1_580),
            fit="contain",
            z_index=10,
            illustrative_label=True,
            scale_start=1.01,
            scale_end=1.01,
        ),
        _layer(
            id="layer-evidence-overview-field",
            shot_id="shot-07",
            start_ms=14_160,
            end_ms=15_200,
            source_role="deterministic-graphic",
            asset_id="graphic-dark-backdrop",
            kind="image",
            fit="cover",
            z_index=1,
            scale_end=1,
        ),
        *[
            _layer(
                id=f"{layer_id}-field",
                shot_id=shot_id,
                start_ms=start_ms,
                end_ms=end_ms,
                source_role="direct-evidence",
                asset_id=asset_id,
                kind="image",
                fit="cover",
                z_index=1,
                brightness=0.80,
                contrast=0.80,
                saturation=0.35,
                blur_px=44,
                color_filter="brightness(0.82) saturate(0.45)",
                scale_end=1,
            )
            for layer_id, shot_id, start_ms, end_ms, asset_id in [
                (
                    "layer-evidence-championship",
                    "shot-08",
                    15_200,
                    17_460,
                    "evidence-championship-excerpt",
                ),
                (
                    "layer-evidence-result",
                    "shot-09",
                    17_460,
                    19_500,
                    "evidence-risk-excerpt",
                ),
                (
                    "layer-evidence-number",
                    "shot-10",
                    19_500,
                    21_820,
                    "evidence-risk-number",
                ),
            ]
        ],
        *[
            _layer(
                id=layer_id,
                shot_id=shot_id,
                start_ms=start_ms,
                end_ms=end_ms,
                source_role="direct-evidence",
                asset_id=asset_id,
                kind="image",
                fit="cover",
                bounds=(
                    (120, 170, 840, 1_580)
                    if layer_id == "layer-evidence-overview"
                    else (120, 0, 840, 1_920)
                ),
                z_index=10,
                brightness=1.40,
                contrast=1.04,
                x_start=(
                    -10
                    if layer_id == "layer-evidence-overview"
                    else 14
                    if layer_id == "layer-evidence-number"
                    else 0
                ),
                x_end=(
                    10
                    if layer_id == "layer-evidence-overview"
                    else -14
                    if layer_id == "layer-evidence-number"
                    else 0
                ),
                scale_start=1,
                scale_end=scale_end,
            )
            for (
                layer_id,
                shot_id,
                start_ms,
                end_ms,
                asset_id,
                scale_end,
            ) in [
                (
                    "layer-evidence-overview",
                    "shot-07",
                    14_160,
                    15_200,
                    "evidence-history-overview",
                    1.035,
                ),
                (
                    "layer-evidence-championship",
                    "shot-08",
                    15_200,
                    17_460,
                    "evidence-championship-excerpt",
                    1,
                ),
                (
                    "layer-evidence-result",
                    "shot-09",
                    17_460,
                    19_500,
                    "evidence-risk-excerpt",
                    1,
                ),
                (
                    "layer-evidence-number",
                    "shot-10",
                    19_500,
                    21_820,
                    "evidence-risk-number",
                    1.05,
                ),
            ]
        ],
        _layer(
            id="layer-risk-primary-dark-base",
            shot_id="shot-11",
            start_ms=21_820,
            end_ms=24_200,
            source_role="deterministic-graphic",
            asset_id="graphic-dark-backdrop",
            kind="image",
            z_index=1,
            color_filter="brightness(0.55) saturate(0.55)",
            scale_end=1,
        ),
        _layer(
            id="layer-risk-backdrop-primary",
            shot_id="shot-11",
            start_ms=21_820,
            end_ms=24_200,
            source_role="deterministic-graphic",
            asset_id="graphic-cool-backdrop",
            kind="image",
            bounds=(220, 80, 640, 1_760),
            z_index=2,
            color_filter="brightness(1.55) saturate(0.20)",
            scale_end=1,
        ),
        _layer(
            id="layer-risk-product-field",
            shot_id="shot-11",
            start_ms=21_820,
            end_ms=24_200,
            source_role="real-product",
            asset_id="capture-mt5-risk-inputs",
            source_start_ms=2_600,
            source_end_ms=4_980,
            bounds=(220, 80, 640, 1_760),
            z_index=3,
            brightness=0.60,
            contrast=0.96,
            saturation=0.70,
            opacity_start=0.55,
            opacity_end=0.55,
            blur_px=34,
            color_filter="brightness(0.92) saturate(0.85)",
            scale_end=1,
        ),
        _layer(
            id="layer-risk-inputs",
            shot_id="shot-11",
            start_ms=21_820,
            end_ms=24_200,
            source_role="real-product",
            asset_id="capture-mt5-risk-inputs",
            source_start_ms=2_600,
            source_end_ms=4_980,
            bounds=(210, 280, 660, 1_320),
            crop=(0.34, 0.14, 0.48, 0.72),
            z_index=10,
            border_radius=14,
            scale_start=1,
            scale_end=1.07,
            x_start=-30,
            x_end=30,
            brightness=1.65,
            contrast=1.15,
            saturation=1.02,
            blur_px=0.15,
            color_filter="brightness(1.15) saturate(0.90)",
        ),
        _layer(
            id="layer-risk-dark-base",
            shot_id="shot-12",
            start_ms=24_200,
            end_ms=25_800,
            source_role="deterministic-graphic",
            asset_id="graphic-dark-backdrop",
            kind="image",
            z_index=1,
            color_filter="brightness(0.55) saturate(0.55)",
            scale_end=1,
        ),
        _layer(
            id="layer-risk-backdrop",
            shot_id="shot-12",
            start_ms=24_200,
            end_ms=25_800,
            source_role="deterministic-graphic",
            asset_id="graphic-cool-backdrop",
            kind="image",
            bounds=(220, 80, 640, 1_760),
            z_index=2,
            color_filter="brightness(1.55) saturate(0.20)",
            scale_end=1,
        ),
        _layer(
            id="layer-risk-alt-product-field",
            shot_id="shot-12",
            start_ms=24_200,
            end_ms=25_800,
            source_role="real-product",
            asset_id="capture-mt5-risk-alternate",
            source_start_ms=2_700,
            source_end_ms=4_300,
            bounds=(220, 80, 640, 1_760),
            z_index=3,
            brightness=0.60,
            contrast=0.96,
            saturation=0.70,
            opacity_start=0.55,
            opacity_end=0.55,
            blur_px=34,
            color_filter="brightness(0.92) saturate(0.85)",
            scale_end=1,
        ),
        _layer(
            id="layer-risk-parameter",
            shot_id="shot-12",
            start_ms=24_200,
            end_ms=25_800,
            source_role="real-product",
            asset_id="capture-mt5-risk-alternate",
            source_start_ms=2_700,
            source_end_ms=4_300,
            bounds=(210, 280, 660, 1_320),
            crop=(0.34, 0.14, 0.48, 0.72),
            z_index=10,
            border_radius=14,
            scale_start=1,
            scale_end=1.07,
            x_start=30,
            x_end=-30,
            brightness=1.65,
            contrast=1.15,
            saturation=1.02,
            blur_px=0.15,
            color_filter="brightness(1.15) saturate(0.90)",
        ),
        _layer(
            id="layer-risk-reversal",
            shot_id="shot-13",
            start_ms=25_800,
            end_ms=27_780,
            source_role="deterministic-graphic",
            asset_id="graphic-risk-reversal",
            kind="image",
            illustrative_label=True,
            reference_role="secondary-4",
            scale_start=1.01,
            scale_end=1.01,
            color_filter="brightness(0.98)",
        ),
        _layer(
            id="layer-lesson-presenter",
            shot_id="shot-14",
            start_ms=27_780,
            end_ms=29_000,
            source_role="presenter",
            asset_id="source-presenter",
            source_start_ms=27_780,
            source_end_ms=29_000,
            scale_start=1.04,
            scale_end=1.04,
            brightness=1.03,
        ),
        _layer(
            id="layer-lesson-graphic",
            shot_id="shot-14",
            start_ms=29_000,
            end_ms=30_200,
            source_role="licensed-context",
            asset_id="licensed-code-screen",
            source_start_ms=14_500,
            source_end_ms=15_700,
            crop=(0.04, 0.0, 0.92, 1.0),
            scale_start=1.02,
            scale_end=1.06,
            x_start=-20,
            x_end=20,
            brightness=1.60,
            contrast=1.08,
            saturation=1.05,
        ),
        _layer(
            id="layer-rules-risk-dark-base",
            shot_id="shot-15",
            start_ms=30_200,
            end_ms=32_200,
            source_role="deterministic-graphic",
            asset_id="graphic-dark-backdrop",
            kind="image",
            z_index=1,
            color_filter="brightness(0.45) saturate(0.50)",
            scale_end=1,
        ),
        _layer(
            id="layer-rules-risk-context",
            shot_id="shot-15",
            start_ms=30_200,
            end_ms=32_200,
            source_role="licensed-context",
            asset_id="licensed-typing",
            source_start_ms=6_880,
            source_end_ms=8_880,
            bounds=(0, 0, 1_080, 300),
            crop=(0.05, 0.0, 0.90, 1.0),
            z_index=2,
            scale_start=1.02,
            scale_end=1.04,
            brightness=0.86,
            contrast=1.08,
            saturation=1.02,
        ),
        _layer(
            id="layer-rules-risk",
            shot_id="shot-15",
            start_ms=30_200,
            end_ms=32_200,
            source_role="deterministic-graphic",
            asset_id="graphic-rules-versus-risk",
            kind="image",
            bounds=(150, 280, 780, 1_360),
            fit="contain",
            z_index=10,
            illustrative_label=True,
            scale_start=1.01,
            scale_end=1.01,
            brightness=1.35,
            contrast=0.78,
            saturation=0.90,
        ),
        _layer(
            id="layer-tactile-bridge",
            shot_id="shot-16",
            start_ms=32_200,
            end_ms=33_020,
            source_role="licensed-context",
            asset_id="licensed-typing",
            source_start_ms=4_000,
            source_end_ms=4_820,
            crop=(0.05, 0.0, 0.90, 1.0),
            scale_start=1.02,
            scale_end=1.02,
            brightness=1.20,
            contrast=1.06,
            saturation=1.04,
        ),
        _layer(
            id="layer-attach-backdrop",
            shot_id="shot-17",
            start_ms=33_020,
            end_ms=35_200,
            source_role="deterministic-graphic",
            asset_id="graphic-dark-backdrop",
            kind="image",
            z_index=1,
            color_filter="brightness(0.45) saturate(0.50)",
            scale_end=1,
        ),
        _layer(
            id="layer-attach-product-field",
            shot_id="shot-17",
            start_ms=33_020,
            end_ms=35_200,
            source_role="real-product",
            asset_id="capture-mt5-attach-ea",
            source_start_ms=1_500,
            source_end_ms=3_680,
            bounds=(150, 80, 780, 1_760),
            z_index=2,
            brightness=0.25,
            contrast=0.84,
            saturation=0.30,
            opacity_start=0.62,
            opacity_end=0.62,
            blur_px=42,
            color_filter="brightness(0.45) saturate(1.35)",
            scale_end=1,
        ),
        _layer(
            id="layer-attach-context",
            shot_id="shot-17",
            start_ms=33_020,
            end_ms=35_200,
            source_role="licensed-context",
            asset_id="licensed-code-soft-backdrop",
            kind="image",
            z_index=3,
            brightness=0.25,
            contrast=0.75,
            saturation=0.25,
            opacity_start=0.04,
            opacity_end=0.04,
            scale_end=1,
        ),
        _layer(
            id="layer-attach-ea",
            shot_id="shot-17",
            start_ms=33_020,
            end_ms=35_200,
            source_role="real-product",
            asset_id="capture-mt5-attach-ea",
            source_start_ms=1_500,
            source_end_ms=3_680,
            bounds=(80, 300, 920, 1_320),
            crop=(0.0, 0.04, 0.55, 0.88),
            z_index=10,
            border_radius=14,
            scale_start=1,
            scale_end=1.07,
            y_start=-30,
            y_end=30,
            brightness=1.50,
            contrast=0.80,
            saturation=1.00,
            blur_px=0.15,
        ),
        _layer(
            id="layer-tester-dark",
            shot_id="shot-18",
            start_ms=35_200,
            end_ms=37_160,
            source_role="deterministic-graphic",
            asset_id="graphic-dark-backdrop",
            kind="image",
            z_index=1,
            color_filter="brightness(0.45) saturate(0.50)",
            scale_end=1,
        ),
        _layer(
            id="layer-tester-light",
            shot_id="shot-18",
            start_ms=35_200,
            end_ms=37_160,
            source_role="deterministic-graphic",
            asset_id="graphic-light-backdrop",
            kind="image",
            bounds=(0, 0, 1_080, 520),
            z_index=2,
            color_filter="brightness(0.75) saturate(0.50)",
            scale_end=1,
        ),
        _layer(
            id="layer-tester-product-field",
            shot_id="shot-18",
            start_ms=35_200,
            end_ms=37_160,
            source_role="real-product",
            asset_id="capture-mt5-strategy-tester",
            source_start_ms=1_600,
            source_end_ms=3_560,
            bounds=(0, 330, 1_080, 1_400),
            z_index=3,
            brightness=0.25,
            contrast=0.84,
            saturation=0.30,
            opacity_start=0.62,
            opacity_end=0.62,
            blur_px=42,
            color_filter="brightness(0.45) saturate(1.35)",
            scale_end=1,
        ),
        _layer(
            id="layer-tester-backdrop",
            shot_id="shot-18",
            start_ms=35_200,
            end_ms=37_160,
            source_role="licensed-context",
            asset_id="licensed-keyboard-soft-backdrop",
            kind="image",
            z_index=1,
            brightness=0.25,
            contrast=0.75,
            saturation=0.25,
            opacity_start=0.03,
            opacity_end=0.03,
            scale_end=1,
        ),
        _layer(
            id="layer-strategy-tester",
            shot_id="shot-18",
            start_ms=35_200,
            end_ms=37_160,
            source_role="real-product",
            asset_id="capture-mt5-strategy-tester",
            source_start_ms=1_600,
            source_end_ms=3_560,
            bounds=(60, 430, 960, 1_200),
            crop=(0.0, 0.56, 1.0, 0.40),
            z_index=10,
            border_radius=14,
            scale_start=1,
            scale_end=1,
            x_start=0,
            x_end=0,
            brightness=1.25,
            contrast=1.15,
            saturation=1.10,
            blur_px=0.15,
        ),
        _layer(
            id="layer-cta-presenter",
            shot_id="shot-19",
            start_ms=37_160,
            end_ms=38_600,
            source_role="presenter",
            asset_id="source-presenter",
            source_start_ms=37_160,
            source_end_ms=38_600,
            scale_start=1.06,
            scale_end=1.06,
            brightness=1.03,
        ),
        _layer(
            id="layer-cta-backdrop",
            shot_id="shot-19",
            start_ms=38_600,
            end_ms=39_800,
            source_role="deterministic-graphic",
            asset_id="graphic-light-backdrop",
            kind="image",
            z_index=1,
            scale_end=1,
        ),
        _layer(
            id="layer-cta-product",
            shot_id="shot-19",
            start_ms=38_600,
            end_ms=39_800,
            source_role="real-product",
            asset_id="capture-mt5-attach-ea",
            source_start_ms=3_300,
            source_end_ms=4_500,
            bounds=(130, 420, 820, 940),
            crop=(0.34, 0.14, 0.48, 0.72),
            z_index=10,
            border_radius=14,
            scale_start=1.01,
            scale_end=1.01,
            brightness=1.06,
            contrast=1.10,
            saturation=1.04,
        ),
        _layer(
            id="layer-ending-presenter",
            shot_id="shot-20",
            start_ms=39_800,
            end_ms=41_400,
            source_role="presenter",
            asset_id="source-presenter",
            source_start_ms=39_800,
            source_end_ms=41_400,
            scale_start=1.13,
            scale_end=1.13,
            brightness=1.03,
        ),
        _layer(
            id="layer-ending-logo",
            shot_id="shot-20",
            start_ms=39_900,
            end_ms=41_200,
            source_role="deterministic-graphic",
            asset_id="brand-logo-original",
            kind="image",
            bounds=(875, 70, 130, 130),
            fit="contain",
            z_index=40,
            scale_end=1,
        ),
    ]
