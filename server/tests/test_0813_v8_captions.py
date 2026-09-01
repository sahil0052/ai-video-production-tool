from __future__ import annotations

from app.editor.training_caption_planner import (
    covered_ms,
    duration_ms,
    plan_captions,
)


def test_backtest_is_reference_10_mono() -> None:
    pages = plan_captions(
        "backtest",
        words=[
            {"text": "Backtest", "start_ms": 0, "end_ms": 420},
            {"text": "practice", "start_ms": 500, "end_ms": 840},
            {"text": "match", "start_ms": 850, "end_ms": 1_100},
            {"text": "hai", "start_ms": 1_120, "end_ms": 1_320},
        ],
        duration_ms=1_800,
    )

    visible = sum(page.end_ms - page.start_ms for page in pages)
    technical = sum(
        page.end_ms - page.start_ms
        for page in pages
        if page.family == "technical-mono"
    )
    assert technical / visible >= 0.96
    assert all(31 <= page.font_size <= 34 for page in pages)
    assert all(page.max_width <= 500 for page in pages)


def test_caption_coverage_is_not_continuous() -> None:
    pages = plan_captions(
        "ppi",
        words=[
            {"text": "Actual", "start_ms": 0, "end_ms": 320},
            {"text": "result", "start_ms": 340, "end_ms": 650},
            {"text": "zero", "start_ms": 720, "end_ms": 1_020},
        ],
        duration_ms=1_500,
    )

    coverage = covered_ms(pages) / duration_ms(pages)
    assert 0.68 <= coverage <= 0.75


def test_lot_size_product_action_uses_outlined_demo() -> None:
    pages = plan_captions(
        "lot-size",
        words=[
            {"text": "LOT", "start_ms": 100, "end_ms": 430},
            {"text": "SIZE", "start_ms": 450, "end_ms": 780},
        ],
        duration_ms=1_100,
        role_spans=[
            {
                "start_ms": 0,
                "end_ms": 1_100,
                "role": "product-action",
            }
        ],
    )

    assert {page.family for page in pages} == {"outlined-demo"}
    assert all(52 <= page.font_size <= 64 for page in pages)


def test_caption_pages_are_short_positive_and_keep_word_timing() -> None:
    words = [
        {"text": "RISK", "start_ms": 50, "end_ms": 290},
        {"text": "LIMIT", "start_ms": 330, "end_ms": 690},
        {"text": "RULE", "start_ms": 730, "end_ms": 1_020},
    ]
    pages = plan_captions(
        "backtest",
        words=words,
        duration_ms=1_500,
    )

    assert all(350 <= page.end_ms - page.start_ms <= 1_300 for page in pages)
    assert all(page.end_ms > page.start_ms for page in pages)
    assert [
        (token.start_ms, token.end_ms)
        for page in pages
        for token in page.tokens
    ] == [(50, 290), (330, 690), (730, 1_020)]


def test_backtest_keeps_compact_cta_below_four_percent() -> None:
    words = [
        {
            "text": f"word{index}",
            "start_ms": index * 250,
            "end_ms": index * 250 + 180,
        }
        for index in range(20)
    ]
    pages = plan_captions(
        "backtest",
        words=words,
        duration_ms=5_500,
        role_spans=[
            {"start_ms": 0, "end_ms": 4_500, "role": "explanation"},
            {"start_ms": 4_500, "end_ms": 5_500, "role": "presenter-cta"},
        ],
    )
    visible = covered_ms(pages)
    technical = sum(
        page.end_ms - page.start_ms
        for page in pages
        if page.family == "technical-mono"
    )

    assert technical / visible >= 0.96
