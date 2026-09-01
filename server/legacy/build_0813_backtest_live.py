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
STORY_ID = "backtest"
SOURCE = Path(r"D:\Downloads\0813 (2).mp4")
SEED_OUTPUT = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0813-production-v3-live-footage-take-2"
)
OUTPUT = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0813-production-v7-semantic-visuals-take-2"
)
TRANSCRIPT_PATH = (
    SEED_OUTPUT / "analysis" / "transcript-deepgram.json"
)
DURATION_MS = 46_000
PLAYBACK_RATE = 1.06


EDL_ROWS = [
    (0, 1860, 0, 1755),
    (2108, 3950, 1755, 3492),
    (3982, 4067, 3492, 3573),
    (4088, 4122, 3573, 3605),
    (4431, 4466, 3605, 3638),
    (4527, 4723, 3638, 3823),
    (4855, 8339, 3823, 7109),
    (8377, 10791, 7109, 9387),
    (11238, 13337, 9387, 11367),
    (13623, 14595, 11367, 12284),
    (14620, 14908, 12284, 12556),
    (14917, 15503, 12556, 13108),
    (15532, 16591, 13108, 14108),
    (16611, 26630, 14108, 23559),
    (26671, 27565, 23559, 24403),
    (27731, 28357, 24403, 24993),
    (28891, 32094, 24993, 28015),
    (32431, 34222, 28015, 29705),
    (34241, 34452, 29705, 29904),
    (34525, 37327, 29904, 32547),
    (37329, 37626, 32547, 32827),
    (37937, 38972, 32827, 33804),
    (39084, 39550, 33804, 34243),
    (39579, 39957, 34243, 34600),
    (40043, 42759, 34600, 37162),
    (42799, 43188, 37162, 37529),
    (43307, 48009, 37529, 41965),
    (48011, 51578, 41965, 45330),
    (51615, 52145, 45330, 45830),
    (52147, 52310, 45830, 45984),
    (52350, 52367, 45984, 46000),
]


BOUNDARIES = [
    0,
    1_700,
    3_492,
    5_000,
    9_000,
    11_367,
    14_108,
    15_800,
    19_763,
    21_600,
    24_993,
    28_000,
    30_003,
    34_400,
    37_578,
    43_800,
    46_000,
]


SHOT_SPECS = [
    shot(
        "pixabay-281621",
        300,
        "cricket-practice-hook",
        visual_job="presenter-supported",
        zoom=1.05,
        crop_x=0.37,
        secondary_asset_id="presenter-edl",
        secondary_source_start_ms=0,
    ),
    shot(
        "pixabay-39549",
        5_500,
        "net-practice-wide",
        visual_job="literal-action",
        zoom=1.10,
    ),
    shot(
        "pixabay-138691",
        6_000,
        "first-over-wicket",
        visual_job="literal-action",
        zoom=1.08,
    ),
    shot(
        "presenter-edl",
        5_000,
        "backtest-strong-versus-weak",
        visual_job="presenter-explanation",
        zoom=1.07,
    ),
    shot(
        "pexels-38870320",
        600,
        "practice-match-definition",
        visual_job="literal-action",
        zoom=1.05,
    ),
    shot(
        "presenter-edl",
        11_367,
        "historical-rules-explanation",
        visual_job="presenter-explanation",
        zoom=1.08,
    ),
    shot(
        "pexels-33314914",
        600,
        "old-market-rules",
        visual_job="literal-action",
        zoom=1.06,
    ),
    shot(
        "presenter-edl",
        15_800,
        "testing-assumptions",
        visual_job="presenter-explanation",
        zoom=1.09,
    ),
    shot(
        "pexels-7580269",
        1_200,
        "live-execution-friction",
        visual_job="literal-action",
        zoom=1.10,
    ),
    shot(
        "presenter-edl",
        21_600,
        "live-market-friction",
        visual_job="presenter-explanation",
        zoom=1.09,
    ),
    shot(
        "presenter-edl",
        24_993,
        "overfitting-explanation",
        visual_job="presenter-explanation",
        zoom=1.12,
    ),
    shot(
        "student-writing",
        400,
        "student-memory-analogy",
        visual_job="literal-action",
        zoom=1.13,
        crop_x=0.55,
    ),
    shot(
        "presenter-edl",
        30_003,
        "memorization-and-live-risk",
        visual_job="presenter-explanation",
        zoom=1.09,
    ),
    shot(
        "mt5-strategy-tester",
        2_600,
        "forward-test-demo",
        visual_job="real-product",
        zoom=1.22,
        crop_x=0.52,
        crop_y=0.82,
    ),
    shot(
        "presenter-edl",
        37_578,
        "forward-test-and-guarantee-lesson",
        visual_job="presenter-explanation",
        zoom=1.10,
    ),
    shot(
        "presenter-edl",
        43_800,
        "clean-cta",
        visual_job="presenter-explanation",
        zoom=1.06,
    ),
]


CAPTION_GROUPS = [
    (0, 2, "CRICKET NETS"),
    (3, 5, "EVERY BALL = 6"),
    (6, 9, "BUT REAL MATCH"),
    (10, 13, "FIRST OVER OUT"),
    (14, 17, "TRADING ROBOT BACKTEST"),
    (18, 20, "LOOKS STRONG"),
    (21, 24, "LIVE MARKET: WEAK"),
    (25, 28, "WHY?"),
    (29, 32, "BACKTEST, SIMPLE LANGUAGE"),
    (33, 35, "PRACTICE MATCH"),
    (36, 40, "OLD MARKET DATA"),
    (41, 43, "ROBOT GETS HISTORY"),
    (44, 48, "THEN WE CHECK"),
    (49, 52, "THE RULES"),
    (53, 56, "PAST PERFORMANCE"),
    (57, 60, "WRONG TEST SETTINGS"),
    (61, 63, "ROBOT GETS"),
    (64, 65, "PERFECT PRICES"),
    (66, 67, "FIXED SPREAD"),
    (68, 70, "INSTANT EXECUTION"),
    (71, 73, "CAN LOOK EASY"),
    (74, 77, "LIVE MARKET DELAY"),
    (78, 80, "CHANGING SPREAD"),
    (81, 86, "DIFFERENT PRICE"),
    (87, 91, "PROBLEM: OVERFITTING"),
    (92, 97, "STUDENT MEMORIZES"),
    (98, 103, "OLD ANSWER SHEETS"),
    (104, 108, "ROBOT MEMORIZES DATA"),
    (109, 111, "NOT THE CONCEPT"),
    (112, 115, "STRONG BACKTEST"),
    (116, 122, "DIRECT LIVE = RISKY"),
    (123, 128, "REAL MARKET DATA"),
    (129, 134, "DEMO FORWARD TEST"),
    (135, 139, "CHECK IT AGAIN"),
    (140, 142, "LESSON SIMPLE"),
    (143, 149, "BACKTEST = PRACTICE SCORE"),
    (150, 154, "NO LIVE GUARANTEE"),
    (155, 160, "FOREX MARKET"),
    (161, 164, "INFORMATIVE VIDEOS"),
    (165, 167, "FOLLOW FOR MORE"),
    (168, 169, "THANK YOU"),
]


FACT_OVERLAYS = [
    {
        "id": "hook-title",
        "text": "PRACTICE NETS\n≠ REAL MATCH",
        "start_ms": 120,
        "end_ms": 1_650,
        "width": 860,
        "height": 190,
        "x": 110,
        "y": 690,
        "style": "serif-hook",
        "evidence_id": None,
        "transparent": True,
    },
    {
        "id": "backtest-strong",
        "text": "BACKTEST: STRONG",
        "start_ms": 3_900,
        "end_ms": 5_800,
        "width": 650,
        "height": 136,
        "x": 215,
        "y": 220,
        "style": "positive",
        "evidence_id": None,
        "transparent": True,
    },
    {
        "id": "live-weak",
        "text": "LIVE: WEAK",
        "start_ms": 5_800,
        "end_ms": 7_300,
        "width": 560,
        "height": 136,
        "x": 260,
        "y": 220,
        "style": "negative",
        "evidence_id": None,
        "transparent": True,
    },
    {
        "id": "historical-data",
        "text": "OLD MARKET DATA",
        "start_ms": 9_400,
        "end_ms": 11_800,
        "width": 650,
        "height": 118,
        "x": 215,
        "y": 220,
        "style": "technical",
        "evidence_id": None,
        "transparent": True,
    },
    {
        "id": "perfect-settings",
        "text": "PERFECT PRICES • FIXED SPREAD",
        "start_ms": 14_400,
        "end_ms": 17_600,
        "width": 840,
        "height": 118,
        "x": 120,
        "y": 220,
        "style": "technical",
        "evidence_id": None,
        "transparent": True,
    },
    {
        "id": "live-friction",
        "text": "DELAY • CHANGING SPREAD",
        "start_ms": 19_760,
        "end_ms": 22_800,
        "width": 790,
        "height": 118,
        "x": 145,
        "y": 220,
        "style": "negative",
        "evidence_id": None,
        "transparent": True,
    },
    {
        "id": "overfitting",
        "text": "OVERFITTING",
        "start_ms": 23_600,
        "end_ms": 25_000,
        "width": 560,
        "height": 136,
        "x": 260,
        "y": 240,
        "style": "negative",
        "evidence_id": None,
        "transparent": True,
    },
    {
        "id": "forward-test",
        "text": "DEMO FORWARD TEST",
        "start_ms": 34_500,
        "end_ms": 37_200,
        "width": 700,
        "height": 118,
        "x": 190,
        "y": 220,
        "style": "positive",
        "evidence_id": None,
        "transparent": True,
    },
    {
        "id": "lesson",
        "text": "PRACTICE SCORE ≠ GUARANTEE",
        "start_ms": 37_600,
        "end_ms": 41_900,
        "width": 840,
        "height": 118,
        "x": 120,
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
    "pixabay-281621": _pixabay(
        "pixabay-281621",
        creator="PatternsWorld",
    ),
    "pixabay-39549": _pixabay("pixabay-39549", creator="CarryVix"),
    "pixabay-138691": _pixabay(
        "pixabay-138691",
        creator="MuneerKhan92",
    ),
    "student-writing": _pixabay("pixabay-355580", creator="rcp24"),
    "mt5-strategy-tester": _product("capture-mt5-strategy-tester.mp4"),
    "pexels-38870320": _pexels(
        "pexels-38870320",
        creator="Jakub Zerdzicki",
        source_url=(
            "https://www.pexels.com/video/"
            "analyzing-financial-data-on-tablet-and-monitors-38870320/"
        ),
    ),
    "pexels-33314914": _pexels(
        "pexels-33314914",
        creator="Jakub Zerdzicki",
        source_url=(
            "https://www.pexels.com/video/"
            "modern-workspace-with-coding-on-screen-33314914/"
        ),
    ),
    "pexels-7580269": {
        "source": (
            PPI_ASSETS
            / "asset-candidates"
            / "live-search"
            / "pexels-7580269.mp4"
        ),
        "folder": "licensed",
        "source_kind": "licensed-context",
        "provider": "Pexels",
        "remote_id": "7580269",
        "creator": "Tima Miroshnichenko",
        "source_url": "https://www.pexels.com/video/7580269/",
        "license": "Pexels License",
        "license_url": "https://www.pexels.com/license/",
    },
}


DESIRED_SFX = [
    ("hook-settle", "sfx-impact", 650, 90, -22.0),
    ("match-turn", "sfx-whoosh", 3_450, 100, -24.0),
    ("backtest-open", "sfx-click", 7_350, 70, -24.0),
    ("settings-warning", "sfx-snap", 14_100, 70, -24.0),
    ("live-friction", "sfx-impact", 19_700, 90, -23.0),
    ("overfitting", "sfx-whoosh", 23_500, 100, -24.0),
    ("direct-live-risk", "sfx-impact", 30_000, 90, -23.0),
    ("forward-test", "sfx-click", 34_500, 70, -24.0),
    ("cta-lift", "sfx-riser", 42_000, 100, -26.0),
]


PROTECTED_TOKENS = [
    "cricket",
    "6",
    "backtest",
    "live",
    "perfect",
    "spread",
    "execution",
    "overfitting",
    "demo",
    "forward",
    "guarantee",
    "follow",
    "thank",
    "you",
]


CONFIG = StoryConfig(
    story_id=STORY_ID,
    title="0813 Take 2 — Backtest vs Live Market",
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
    music_source_start_seconds=8,
    visual_summary=[
        "Open on real cricket practice, then a real wicket/match contrast.",
        "Show the MT5 Strategy Tester exactly when backtesting is explained.",
        "Use real MetaEditor rule highlights for historical-rule discussion.",
        "Use moving trader/market footage for live execution friction.",
        "Use a real student writing clip for the overfitting analogy.",
        "Finish on real demo/forward-testing setup and presenter CTA.",
    ],
    risks=[
        "Fast dialogue requires conservative silence cuts plus 1.06x playback.",
        "No backtest result, balance, or profitability screen may be invented.",
        "Landscape cricket and MT5 captures require intentional portrait crops.",
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
    return 1_520 if start_ms >= 42_256 else 1_545


def split_layout_for_shot(shot_number: int) -> str | None:
    return "presenter-bottom" if shot_number == 1 else None


def main() -> int:
    return build_story(CONFIG)


if __name__ == "__main__":
    raise SystemExit(main())
