from __future__ import annotations

from pathlib import Path
from typing import Any

from app.production_models import DialogueEditSegment
from story_0813_live_common import (
    StoryConfig,
    build_audio_plan as _build_audio_plan,
    build_caption_pages as _build_caption_pages,
    build_story,
    dialogue_edl as _dialogue_edl,
    shot,
)


SERVER_DIR = Path(__file__).resolve().parent
WORKSPACE = SERVER_DIR.parent
STORY_ID = "lot-size"
SOURCE = Path(r"D:\Downloads\0813 (3).mp4")
SEED_OUTPUT = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0813-production-v3-live-footage-take-3"
)
OUTPUT = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0813-production-v7-semantic-visuals-take-3"
)
TRANSCRIPT_PATH = (
    SEED_OUTPUT / "analysis" / "transcript-deepgram.json"
)
DURATION_MS = 46_000
PLAYBACK_RATE = 1.06


EDL_ROWS = [
    (0, 40, 0, 38),
    (42, 578, 38, 543),
    (819, 2704, 543, 2322),
    (3167, 3706, 2322, 2830),
    (3889, 4087, 2830, 3017),
    (4089, 5928, 3017, 4752),
    (6027, 7403, 4752, 6050),
    (7733, 8782, 6050, 7040),
    (8800, 26269, 7040, 23520),
    (26280, 28040, 23520, 25180),
    (28122, 28223, 25180, 25275),
    (28252, 29880, 25275, 26811),
    (29908, 33207, 26811, 29924),
    (33218, 34707, 29924, 31328),
    (34884, 37187, 31328, 33501),
    (37206, 38426, 33501, 34652),
    (38460, 38754, 34652, 34929),
    (39000, 39079, 34929, 35004),
    (39133, 41869, 35004, 37585),
    (41920, 43687, 37585, 39252),
    (43791, 45817, 39252, 41163),
    (45879, 46170, 41163, 41438),
    (46191, 50129, 41438, 45153),
    (50212, 50291, 45153, 45227),
    (50388, 51088, 45227, 45888),
    (51127, 51206, 45888, 45962),
    (51327, 51367, 45962, 46000),
]


BOUNDARIES = [
    0,
    2_353,
    4_802,
    7_040,
    11_000,
    14_375,
    18_375,
    20_200,
    25_244,
    29_935,
    33_501,
    36_500,
    39_252,
    41_438,
    44_500,
    46_000,
]


SHOT_SPECS = [
    shot(
        "mt5-risk-inputs",
        1_600,
        "lot-size-product-hook",
        visual_job="presenter-supported",
        zoom=1.18,
        crop_y=0.60,
        secondary_asset_id="presenter-edl",
        secondary_source_start_ms=0,
    ),
    shot(
        "pexels-13441351",
        0,
        "one-pizza",
        visual_job="literal-action",
        zoom=1.06,
    ),
    shot(
        "pexels-7362641",
        0,
        "many-pizzas-and-total",
        visual_job="presenter-supported",
        zoom=1.05,
        secondary_asset_id="presenter-edl",
        secondary_source_start_ms=4_802,
    ),
    shot(
        "presenter-edl",
        7_040,
        "quantity-definition",
        visual_job="presenter-explanation",
        zoom=1.08,
    ),
    shot(
        "mt5-risk-alternate",
        1_900,
        "large-position-and-impact",
        visual_job="real-product",
        zoom=1.20,
        crop_x=0.52,
        crop_y=0.62,
    ),
    shot(
        "presenter-edl",
        14_375,
        "currency-pair-example",
        visual_job="presenter-explanation",
        zoom=1.08,
    ),
    shot(
        "pexels-8480283",
        1_000,
        "currency-pair-move",
        visual_job="literal-action",
        zoom=1.10,
    ),
    shot(
        "presenter-edl",
        20_200,
        "small-large-profit-loss",
        visual_job="presenter-explanation",
        zoom=1.09,
    ),
    shot(
        "presenter-edl",
        25_244,
        "stop-loss-and-distance",
        visual_job="presenter-explanation",
        zoom=1.08,
    ),
    shot(
        "presenter-edl",
        29_935,
        "actual-risk-and-robot-benefit",
        visual_job="presenter-explanation",
        zoom=1.10,
    ),
    shot(
        "metaeditor-open",
        1_200,
        "maximum-lot-and-fixed-risk-rule",
        visual_job="real-product",
        zoom=1.18,
        crop_x=0.36,
    ),
    shot(
        "presenter-edl",
        36_500,
        "wrong-setting-repeat",
        visual_job="presenter-explanation",
        zoom=1.10,
    ),
    shot(
        "presenter-edl",
        39_252,
        "risk-lesson",
        visual_job="presenter-explanation",
        zoom=1.10,
    ),
    shot(
        "mt5-attach-ea",
        2_200,
        "entry-versus-lot-product-bridge",
        visual_job="real-product",
        zoom=1.22,
        crop_x=0.58,
        crop_y=0.62,
    ),
    shot(
        "presenter-edl",
        44_500,
        "clean-cta",
        visual_job="presenter-explanation",
        zoom=1.06,
    ),
]


CAPTION_GROUPS = [
    (0, 2, "DO YOU KNOW?"),
    (3, 5, "FOREX MARKET MEIN"),
    (6, 10, "LOT SIZE KYA HAI?"),
    (11, 11, "SOCHIYE"),
    (12, 15, "ORDER ONE PIZZA"),
    (16, 18, "OR 100 PIZZAS"),
    (19, 23, "PRICE PER PIZZA SAME"),
    (24, 27, "TOTAL BILL CHANGES"),
    (28, 31, "FOREX LOT SIZE"),
    (32, 37, "TRADE KI QUANTITY"),
    (38, 40, "CHHOTA LOT"),
    (41, 43, "CHHOTA POSITION SIZE"),
    (44, 46, "BADA LOT"),
    (47, 51, "BIGGER MARKET IMPACT"),
    (52, 56, "EXAMPLE KE LIYE"),
    (57, 64, "CURRENCY MOVES ONE WAY"),
    (65, 68, "SMALL LOT"),
    (69, 71, "SMALL ACCOUNT CHANGE"),
    (72, 75, "LARGE LOT"),
    (76, 78, "BIGGER ACCOUNT CHANGE"),
    (79, 83, "PROFIT AUR LOSS"),
    (84, 87, "LOT SIZE KE"),
    (88, 91, "SAATH CHANGE HOTE"),
    (92, 97, "STOP LOSS ENOUGH NAHI"),
    (98, 102, "STOP DISTANCE + LOT"),
    (103, 107, "MAKES ACTUAL RISK"),
    (108, 113, "ROBOT KA FAYDA"),
    (114, 118, "MAXIMUM LOT LIMIT"),
    (119, 123, "FIXED RISK RULE"),
    (124, 126, "AUTO FOLLOW"),
    (127, 131, "GALAT SETTING BHI"),
    (132, 135, "PERFECTLY REPEAT"),
    (136, 141, "ENTRY = WHERE"),
    (142, 145, "LOT SIZE BATATA"),
    (146, 148, "RISK KITNA HAI"),
    (149, 154, "FOREX MARKET"),
    (155, 158, "INFORMATIVE VIDEOS"),
    (159, 161, "FOLLOW FOR MORE"),
    (162, 163, "THANK YOU"),
]


FACT_OVERLAYS = [
    {
        "id": "hook-title",
        "text": "LOT SIZE\n= TRADE QUANTITY",
        "start_ms": 100,
        "end_ms": 1_150,
        "width": 850,
        "height": 190,
        "x": 115,
        "y": 700,
        "style": "serif-hook",
        "evidence_id": None,
        "transparent": True,
    },
    {
        "id": "pizza-scale",
        "text": "1 PIZZA ↔ 100 PIZZAS",
        "start_ms": 2_400,
        "end_ms": 4_750,
        "width": 760,
        "height": 136,
        "x": 160,
        "y": 220,
        "style": "source",
        "evidence_id": None,
        "transparent": True,
    },
    {
        "id": "small-lot",
        "text": "SMALL LOT = SMALL POSITION",
        "start_ms": 8_300,
        "end_ms": 11_500,
        "width": 820,
        "height": 118,
        "x": 130,
        "y": 220,
        "style": "positive",
        "evidence_id": None,
        "transparent": True,
    },
    {
        "id": "large-lot",
        "text": "LARGE LOT = BIGGER IMPACT",
        "start_ms": 11_900,
        "end_ms": 14_300,
        "width": 800,
        "height": 118,
        "x": 140,
        "y": 220,
        "style": "negative",
        "evidence_id": None,
        "transparent": True,
    },
    {
        "id": "same-move",
        "text": "SAME MOVE • DIFFERENT IMPACT",
        "start_ms": 18_300,
        "end_ms": 22_200,
        "width": 850,
        "height": 118,
        "x": 115,
        "y": 220,
        "style": "technical",
        "evidence_id": None,
        "transparent": True,
    },
    {
        "id": "risk-equation",
        "text": "STOP DISTANCE + LOT SIZE = RISK",
        "start_ms": 25_200,
        "end_ms": 29_800,
        "width": 900,
        "height": 118,
        "x": 90,
        "y": 220,
        "style": "technical",
        "evidence_id": None,
        "transparent": True,
    },
    {
        "id": "robot-rules",
        "text": "MAX LOT LIMIT • FIXED RISK",
        "start_ms": 31_300,
        "end_ms": 34_900,
        "width": 820,
        "height": 118,
        "x": 130,
        "y": 220,
        "style": "positive",
        "evidence_id": None,
        "transparent": True,
    },
    {
        "id": "wrong-settings",
        "text": "WRONG SETTINGS REPEAT",
        "start_ms": 35_000,
        "end_ms": 37_500,
        "width": 720,
        "height": 136,
        "x": 180,
        "y": 220,
        "style": "negative",
        "evidence_id": None,
        "transparent": True,
    },
    {
        "id": "entry-risk",
        "text": "ENTRY = WHERE • LOT = RISK",
        "start_ms": 37_600,
        "end_ms": 41_300,
        "width": 830,
        "height": 118,
        "x": 125,
        "y": 220,
        "style": "technical",
        "evidence_id": None,
        "transparent": True,
    },
]


STORY_ASSETS = WORKSPACE / "storage" / "assets" / "0813-stories"
PRODUCT_ASSETS = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0806-production-v8-training-parity"
    / "assets"
    / "product"
)
PPI_ASSETS = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0813-production-v3-live-footage"
)


def _pixabay(asset_id: str, *, creator: str) -> dict[str, Any]:
    remote_id = asset_id.removeprefix("pixabay-")
    return {
        "source": STORY_ASSETS / f"{asset_id}.mp4",
        "folder": "licensed",
        "source_kind": "licensed-context",
        "provider": "Pixabay",
        "remote_id": remote_id,
        "creator": creator,
        "source_url": f"https://pixabay.com/videos/id-{remote_id}/",
        "license": "Pixabay Content License",
        "license_url": "https://pixabay.com/service/license-summary/",
    }


def _product(filename: str) -> dict[str, Any]:
    return {
        "source": PRODUCT_ASSETS / filename,
        "folder": "product",
        "source_kind": "real-product",
        "provider": "Local capture",
        "license": "User-owned privacy-reviewed capture",
    }


def _pexels(
    asset_id: str,
    *,
    creator: str,
    source_url: str,
) -> dict[str, Any]:
    remote_id = asset_id.removeprefix("pexels-")
    return {
        "source": STORY_ASSETS / f"{asset_id}.mp4",
        "folder": "licensed",
        "source_kind": "licensed-context",
        "provider": "Pexels",
        "remote_id": remote_id,
        "creator": creator,
        "source_url": source_url,
        "license": "Pexels License",
        "license_url": "https://www.pexels.com/license/",
    }


ASSET_SOURCES = {
    "pexels-13441351": _pexels(
        "pexels-13441351",
        creator="Mizuno K",
        source_url=(
            "https://www.pexels.com/video/"
            "a-young-couple-choosing-pizza-slices-from-the-box-13441351/"
        ),
    ),
    "pexels-7362641": _pexels(
        "pexels-7362641",
        creator="RDNE Stock project",
        source_url=(
            "https://www.pexels.com/video/"
            "a-delivery-woman-holding-boxes-of-pizza-7362641/"
        ),
    ),
    "mt5-risk-inputs": _product("capture-mt5-risk-inputs.mp4"),
    "mt5-risk-alternate": _product("capture-mt5-risk-alternate.mp4"),
    "metaeditor-open": _product("capture-metaeditor-open.mp4"),
    "mt5-attach-ea": _product("capture-mt5-attach-ea.mp4"),
    "pexels-8480283": {
        "source": PPI_ASSETS / "assets" / "licensed" / "pexels-8480283.mp4",
        "folder": "licensed",
        "source_kind": "licensed-context",
        "provider": "Pexels",
        "remote_id": "8480283",
        "creator": "ArtHouse Studio",
        "source_url": "https://www.pexels.com/video/8480283/",
        "license": "Pexels License",
        "license_url": "https://www.pexels.com/license/",
    },
}


DESIRED_SFX = [
    ("hook-settle", "sfx-impact", 650, 90, -22.0),
    ("pizza-scale", "sfx-whoosh", 2_300, 100, -24.0),
    ("quantity-field", "sfx-click", 7_000, 70, -24.0),
    ("small-large-turn", "sfx-snap", 11_800, 70, -24.0),
    ("impact-change", "sfx-impact", 18_200, 90, -23.0),
    ("risk-equation", "sfx-whoosh", 25_100, 100, -24.0),
    ("robot-rule", "sfx-click", 31_200, 70, -24.0),
    ("wrong-setting", "sfx-impact", 34_900, 90, -23.0),
    ("cta-lift", "sfx-riser", 41_200, 100, -26.0),
]


PROTECTED_TOKENS = [
    "do",
    "you",
    "lot",
    "size",
    "100",
    "pizza",
    "profit",
    "loss",
    "stop",
    "risk",
    "maximum",
    "robot",
    "entry",
    "follow",
    "thank",
    "you",
]


CONFIG = StoryConfig(
    story_id=STORY_ID,
    title="0813 Take 3 — Lot Size and Risk",
    source=SOURCE,
    output=OUTPUT,
    transcript_path=TRANSCRIPT_PATH,
    duration_ms=DURATION_MS,
    playback_rate=PLAYBACK_RATE,
    edl_rows=EDL_ROWS,
    boundaries=BOUNDARIES,
    shot_specs=SHOT_SPECS,
    caption_groups=CAPTION_GROUPS,
    fact_overlays=FACT_OVERLAYS,
    asset_sources=ASSET_SOURCES,
    desired_sfx=DESIRED_SFX,
    protected_tokens=PROTECTED_TOKENS,
    music_source_start_seconds=32,
    visual_summary=[
        "Open on the genuine MT5 lot/volume input with presenter support.",
        "Use real moving pizza footage for the one-versus-one-hundred analogy.",
        "Show genuine MT5 position/risk settings for small and large lots.",
        "Use moving trader screens for identical-market-move comparisons.",
        "Show stop distance and lot-size controls together for actual risk.",
        "Finish with real rule/EA footage and a clean presenter CTA.",
    ],
    risks=[
        "No fabricated profit/loss, balance, or result chart may appear.",
        "The pizza comparison is illustrative and must not look like evidence.",
        "The compact MT5 fields require tight portrait crops without obstruction.",
    ],
)


def dialogue_edl() -> list[DialogueEditSegment]:
    return _dialogue_edl(CONFIG)


def build_caption_pages(
    transcript: dict[str, Any],
    edl: list[DialogueEditSegment],
) -> list[dict[str, Any]]:
    return _build_caption_pages(
        transcript=transcript,
        edl=edl,
        groups=CAPTION_GROUPS,
        duration_ms=DURATION_MS,
    )


def build_audio_plan(
    transcript: dict[str, Any],
    edl: list[DialogueEditSegment],
) -> dict[str, Any]:
    return _build_audio_plan(
        transcript=transcript,
        edl=edl,
        desired_sfx=DESIRED_SFX,
        duration_ms=DURATION_MS,
    )


def fact_overlay_specs() -> list[dict[str, Any]]:
    return FACT_OVERLAYS


def evidence_items() -> list[dict[str, Any]]:
    return []


def overlay_requires_evidence(item: dict[str, Any]) -> bool:
    return False


def caption_anchor_y(start_ms: int) -> int:
    return 1_520 if start_ms >= 41_438 else 1_545


def split_layout_for_shot(shot_number: int) -> str | None:
    return "presenter-bottom" if shot_number == 1 else None


def main() -> int:
    return build_story(CONFIG)


if __name__ == "__main__":
    raise SystemExit(main())
