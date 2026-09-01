from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from build_0813_v8_common import make_blueprint, shot


SOURCE = Path(r"D:\Downloads\0813 (2).mp4")
TRANSCRIPT = Path(
    r"C:\websites\ai video production tool\storage\deliverables"
    r"\0813-production-v3-live-footage-take-2\analysis"
    r"\transcript-deepgram.json"
)
DURATION_MS = 50_680


def build_blueprint():
    specs = [
        shot(1, 0, 1_400, phrase="cricket nets mein har ball six", source_role="licensed-context", reference_role="reference-10-analogy-hook", subject="cricket batter in nets", action="hits a practice ball", treatment="full-frame-action", treatment_class="sports-action", asset_id="pixabay-281621", caption_family="technical-mono", source_start_ms=300, crop_x=0.37, zoom=1.08),
        shot(2, 1_400, 2_800, phrase="real match first over out", source_role="licensed-context", reference_role="reference-4-cinematic-contrast", subject="wicket in match", action="falls on the first over", treatment="hard-contrast-cut", treatment_class="cinematic-contrast", asset_id="pixabay-138691", caption_family="technical-mono", source_start_ms=6_000, zoom=1.10),
        shot(3, 2_800, 4_400, phrase="backtest strong", source_role="real-product", reference_role="reference-10-product-macro", subject="MT5 Strategy Tester", action="opens its setup controls", treatment="tight-ui-macro", treatment_class="product-macro", asset_id="mt5-strategy-tester", caption_family="technical-mono", source_start_ms=1_000, crop_y=0.78, zoom=1.23, dark_ui=True),
        shot(4, 4_400, 6_000, phrase="live market weak", source_role="licensed-context", reference_role="reference-4-live-friction", subject="live market screen", action="updates with changing prices", treatment="full-frame-market", treatment_class="market-context", asset_id="pexels-7580269", caption_family="technical-mono", source_start_ms=1_200, zoom=1.11),
        shot(5, 6_000, 9_200, phrase="kyon ho sakta hai", source_role="presenter", reference_role="reference-10-presenter-reset", subject="presenter", action="asks why the result changes", treatment="clean-presenter-reset", treatment_class="presenter-reset", asset_id="presenter-edited", caption_family="technical-mono", source_start_ms=6_000, zoom=1.06),
        shot(6, 9_200, 12_700, phrase="backtest practice match hai", source_role="deterministic-graphic", reference_role="reference-10-system-diagram", subject="practice and live lanes", action="separate simulation from live execution", treatment="flat-practice-diagram", treatment_class="comparison-diagram", asset_id="graphic-backtest-practice", caption_family="technical-mono", illustrative=True),
        shot(7, 12_700, 14_200, phrase="purana market data", source_role="deterministic-graphic", reference_role="reference-10-timeline", subject="historical data timeline", action="travels from past to tester", treatment="tracked-timeline", treatment_class="timeline", asset_id="graphic-historical-data", caption_family="technical-mono", illustrative=True),
        shot(8, 14_200, 16_000, phrase="rules pehle kaise perform karte the", source_role="real-product", reference_role="reference-10-product-macro", subject="Strategy Tester date controls", action="change through visible cursor movement", treatment="cursor-state-change", treatment_class="cursor-state-change", asset_id="mt5-strategy-tester", caption_family="technical-mono", source_start_ms=2_000, crop_y=0.80, zoom=1.25, dark_ui=True),
        shot(9, 16_000, 17_500, phrase="perfect prices", source_role="real-product", reference_role="reference-10-condition-macro", subject="tester price model", action="receives a precise highlight", treatment="tight-ui-macro", treatment_class="product-macro", asset_id="mt5-strategy-tester", caption_family="technical-mono", source_start_ms=2_600, crop_y=0.80, zoom=1.26, dark_ui=True),
        shot(10, 17_500, 19_000, phrase="fixed spread", source_role="deterministic-graphic", reference_role="reference-10-condition-card", subject="fixed spread condition", action="locks while live spread moves", treatment="condition-card", treatment_class="condition-diagram", asset_id="graphic-fixed-spread", caption_family="technical-mono", illustrative=True),
        shot(11, 19_000, 20_500, phrase="instant execution", source_role="real-product", reference_role="reference-10-condition-macro", subject="execution mode control", action="is highlighted in the tester", treatment="tight-ui-macro", treatment_class="product-macro", asset_id="mt5-strategy-tester", caption_family="technical-mono", source_start_ms=3_200, crop_y=0.78, zoom=1.25, dark_ui=True),
        shot(12, 20_500, 22_800, phrase="live changing spread", source_role="real-product", reference_role="reference-10-live-product", subject="MT5 spread readout", action="changes while ticks arrive", treatment="live-state-change", treatment_class="cursor-state-change", asset_id="mt5-risk-inputs", caption_family="technical-mono", source_start_ms=1_500, crop_y=0.64, zoom=1.23),
        shot(13, 22_800, 25_200, phrase="delay and different price", source_role="deterministic-graphic", reference_role="reference-4-delay-mechanism", subject="order path", action="encounters delay and slippage", treatment="dark-delay-path", treatment_class="mechanism-diagram", asset_id="graphic-delay-slippage", caption_family="technical-mono", illustrative=True),
        shot(14, 25_200, 27_700, phrase="overfitting", source_role="deterministic-graphic", reference_role="reference-10-overfit-diagram", subject="historical fit path", action="follows old samples too closely", treatment="qualitative-overfit-curve", treatment_class="comparison-diagram", asset_id="graphic-overfit-history", caption_family="technical-mono", illustrative=True),
        shot(15, 27_700, 30_200, phrase="unseen data", source_role="deterministic-graphic", reference_role="reference-4-cinematic-technical", subject="unseen-data path", action="diverges from the memorized fit", treatment="dark-unseen-data", treatment_class="mechanism-diagram", asset_id="graphic-overfit-unseen", caption_family="technical-mono", illustrative=True),
        shot(16, 30_200, 33_000, phrase="student answer sheets yaad kare", source_role="licensed-context", reference_role="reference-4-tactile-analogy", subject="student answer sheet", action="writes while reviewing prior answers", treatment="tactile-full-frame", treatment_class="tactile-context", asset_id="student-writing", caption_family="technical-mono", source_start_ms=400, crop_x=0.55, zoom=1.13),
        shot(17, 33_000, 35_200, phrase="demo forward testing", source_role="real-product", reference_role="reference-10-product-macro", subject="Strategy Tester configuration", action="selects forward-test controls", treatment="tight-ui-macro", treatment_class="product-macro", asset_id="mt5-strategy-tester", caption_family="technical-mono", source_start_ms=2_000, crop_y=0.80, zoom=1.25),
        shot(18, 35_200, 37_400, phrase="real market data and changing spreads", source_role="real-product", reference_role="reference-10-cursor-action", subject="tester date and mode controls", action="change without showing results", treatment="cursor-state-change", treatment_class="cursor-state-change", asset_id="mt5-strategy-tester", caption_family="technical-mono", source_start_ms=3_000, crop_y=0.78, zoom=1.25),
        shot(19, 37_400, 39_700, phrase="practice score guarantee nahi", source_role="deterministic-graphic", reference_role="reference-10-rule-diagram", subject="practice score and guarantee labels", action="separate with a not-equal rule", treatment="not-equal-rule", treatment_class="rule-diagram", asset_id="graphic-practice-not-guarantee", caption_family="technical-mono", illustrative=True),
        shot(20, 39_700, 42_000, phrase="lesson simple hai", source_role="presenter", reference_role="reference-10-presenter-reset", subject="presenter", action="states the backtest lesson", treatment="clean-presenter-reset", treatment_class="presenter-reset", asset_id="presenter-edited", caption_family="technical-mono", source_start_ms=39_700, zoom=1.08),
        shot(21, 42_000, 46_500, phrase="forward test before live", source_role="real-product", reference_role="reference-10-product-close", subject="Strategy Tester setup", action="finishes the safe configuration sequence", treatment="product-close", treatment_class="product-close", asset_id="mt5-strategy-tester", caption_family="technical-mono", source_start_ms=1_200, crop_y=0.80, zoom=1.22),
        shot(22, 46_500, 50_680, phrase="follow and thank you", source_role="presenter", reference_role="profit-bricks-brand", subject="presenter and brand mark", action="delivers the CTA and holds cleanly", treatment="clean-cta", treatment_class="cta", asset_id="presenter-edited", caption_family="compact-pill", source_start_ms=46_500, zoom=1.08),
    ]
    retimed = {
        11: (19_000, 21_700),
        12: (21_700, 24_000),
        13: (24_000, 27_180),
        14: (27_180, 29_000),
        15: (29_000, 30_180),
        16: (30_180, 32_330),
        17: (32_330, 34_950),
        18: (34_950, 37_330),
        19: (37_330, 39_930),
        20: (39_930, 41_500),
        21: (41_500, 45_380),
        22: (45_380, 50_680),
    }
    specs = [
        (
            replace(spec, start_ms=retimed[spec_number][0], end_ms=retimed[spec_number][1])
            if spec_number in retimed
            else spec
        )
        for spec_number, spec in enumerate(specs, start=1)
    ]
    specs[16] = replace(
        specs[16],
        narration_phrase="robot purane data ko memorize karta hai",
        source_role="deterministic-graphic",
        reference_role="reference-4-cinematic-technical",
        primary_subject="memorized historical path",
        action="diverges before the live-risk decision",
        treatment="dark-unseen-data",
        treatment_class="mechanism-diagram",
        asset_id="graphic-overfit-unseen",
        caption_family="technical-mono",
        source_start_ms=0,
        illustrative=True,
    )
    specs[18] = replace(
        specs[18],
        narration_phrase="demo account par forward testing",
        source_role="real-product",
        reference_role="reference-10-cursor-action",
        primary_subject="Strategy Tester forward controls",
        action="change without showing a result",
        treatment="cursor-state-change",
        treatment_class="cursor-state-change",
        asset_id="mt5-strategy-tester",
        caption_family="technical-mono",
        source_start_ms=3_000,
        illustrative=False,
    )
    specs[20] = replace(
        specs[20],
        narration_phrase="practice score live guarantee nahi",
        source_role="deterministic-graphic",
        reference_role="reference-10-rule-diagram",
        primary_subject="practice score and guarantee labels",
        action="separate through a not-equal rule",
        treatment="not-equal-rule",
        treatment_class="rule-diagram",
        asset_id="graphic-practice-not-guarantee",
        caption_family="technical-mono",
        source_start_ms=0,
        illustrative=True,
    )
    specs[21] = replace(specs[21], source_start_ms=45_380)
    replacements = {
        1: {
            "asset_id": "composite-backtest-hook",
            "treatment": "reference-hook-split",
            "treatment_class": "presenter-hook",
            "source_start_ms": 0,
            "metadata": {
                "contains_presenter": True,
                "presenter_fraction": 0.44,
                "top_asset_id": "pexels-36088031",
                "top_source_start_ms": 500,
            },
        },
        2: {
            "asset_id": "pexels-36088020",
            "source_start_ms": 1_000,
            "treatment": "hard-match-action",
            "treatment_class": "sports-action",
        },
        4: {
            "asset_id": "pexels-38870320",
            "source_start_ms": 800,
            "treatment": "full-frame-market-analysis",
            "metadata": {"dark_context": True},
        },
        6: {
            "source_role": "deterministic-graphic",
            "asset_id": "graphic-backtest-practice",
            "source_start_ms": 0,
            "treatment": "flat-practice-diagram",
            "treatment_class": "comparison-diagram",
            "illustrative": True,
            "metadata": {},
        },
        7: {
            "source_role": "real-product",
            "asset_id": "mt5-strategy-tester",
            "source_start_ms": 1_600,
            "treatment": "historical-controls-macro",
            "treatment_class": "product-macro",
            "illustrative": False,
            "metadata": {"dark_ui": True},
        },
        9: {
            "source_role": "deterministic-graphic",
            "asset_id": "graphic-perfect-prices",
            "source_start_ms": 0,
            "treatment": "perfect-price-condition-card",
            "treatment_class": "condition-diagram",
            "illustrative": True,
            "metadata": {},
        },
        10: {
            "source_role": "real-product",
            "asset_id": "composite-backtest-fixed-spread",
            "source_start_ms": 0,
            "treatment": "product-presenter-split",
            "treatment_class": "presenter-explanation",
            "illustrative": False,
            "metadata": {
                "contains_presenter": True,
                "presenter_fraction": 0.44,
                "top_asset_id": "mt5-risk-inputs",
                "top_source_start_ms": 1_500,
            },
        },
        12: {
            "crop_x": 0.72,
            "zoom": 1.32,
            "metadata": {"product_grade": "balanced"},
        },
        13: {
            "source_role": "deterministic-graphic",
            "asset_id": "graphic-delay-slippage",
            "source_start_ms": 0,
            "treatment": "dark-delay-path",
            "treatment_class": "mechanism-diagram",
            "illustrative": True,
            "metadata": {},
        },
        14: {
            "source_role": "licensed-context",
            "asset_id": "composite-backtest-overfit",
            "source_start_ms": 0,
            "treatment": "analogy-presenter-split",
            "treatment_class": "presenter-explanation",
            "illustrative": False,
            "metadata": {
                "contains_presenter": True,
                "presenter_fraction": 0.44,
                "top_asset_id": "pexels-6830019",
                "top_source_start_ms": 500,
            },
        },
        15: {
            "source_role": "deterministic-graphic",
            "asset_id": "graphic-overfit-unseen-bright",
            "source_start_ms": 0,
            "treatment": "dark-unseen-data",
            "treatment_class": "mechanism-diagram",
            "illustrative": True,
            "metadata": {},
        },
        17: {
            "source_role": "real-product",
            "asset_id": "composite-backtest-memorize",
            "source_start_ms": 0,
            "treatment": "code-presenter-split",
            "treatment_class": "presenter-explanation",
            "illustrative": False,
            "metadata": {
                "contains_presenter": True,
                "presenter_fraction": 0.44,
                "top_asset_id": "metaeditor-rule-highlight",
                "top_source_start_ms": 1_200,
            },
        },
        21: {
            "source_role": "licensed-context",
            "asset_id": "composite-backtest-not-guarantee",
            "source_start_ms": 0,
            "treatment": "lesson-presenter-split",
            "treatment_class": "presenter-explanation",
            "illustrative": False,
            "metadata": {
                "contains_presenter": True,
                "presenter_fraction": 0.44,
                "top_asset_id": "pexels-36088020",
                "top_source_start_ms": 5_200,
            },
        },
    }
    specs = [
        replace(spec, **replacements[index])
        if index in replacements
        else spec
        for index, spec in enumerate(specs, start=1)
    ]
    return make_blueprint(
        story_id="backtest",
        title="Backtest Versus Live Market",
        source=SOURCE,
        transcript_path=TRANSCRIPT,
        duration_ms=DURATION_MS,
        music_bpm=92,
        shots=specs,
    )


if __name__ == "__main__":
    from build_0813_v8_pipeline import build_story

    raise SystemExit(build_story(build_blueprint()))
