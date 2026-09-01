from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from build_0813_v8_common import make_blueprint, shot


SOURCE = Path(r"D:\Downloads\0813 (3).mp4")
TRANSCRIPT = Path(
    r"C:\websites\ai video production tool\storage\deliverables"
    r"\0813-production-v3-live-footage-take-3\analysis"
    r"\transcript-deepgram.json"
)
DURATION_MS = 50_550


def build_blueprint():
    specs = [
        shot(1, 0, 2_200, phrase="forex mein lot size", source_role="real-product", reference_role="reference-5-product-hook", subject="MT5 lot input", action="changes through a visible cursor", treatment="tight-ui-hook", treatment_class="product-macro", asset_id="mt5-risk-inputs", caption_family="outlined-demo", source_start_ms=1_500, crop_y=0.62, zoom=1.25, dark_ui=True),
        shot(2, 2_200, 3_900, phrase="ek pizza", source_role="licensed-context", reference_role="reference-10-literal-analogy", subject="single pizza", action="is selected from the box", treatment="full-frame-food-action", treatment_class="tactile-context", asset_id="pexels-13441351", caption_family="technical-mono", source_start_ms=0, zoom=1.08),
        shot(3, 3_900, 5_800, phrase="ya sau pizzas", source_role="licensed-context", reference_role="reference-10-literal-analogy", subject="stack of pizza boxes", action="moves toward delivery", treatment="quantity-match-cut", treatment_class="quantity-context", asset_id="pexels-7362641", caption_family="technical-mono", source_start_ms=0, zoom=1.08),
        shot(4, 5_800, 7_350, phrase="price per pizza same", source_role="deterministic-graphic", reference_role="reference-10-equation", subject="one unit price", action="stays constant", treatment="flat-multiplication-card", treatment_class="equation-diagram", asset_id="graphic-unit-price", caption_family="technical-mono", illustrative=True),
        shot(5, 7_350, 8_900, phrase="total bill different", source_role="deterministic-graphic", reference_role="reference-10-comparison-diagram", subject="quantity multiplier", action="increases the total qualitatively", treatment="qualitative-total-bars", treatment_class="comparison-diagram", asset_id="graphic-different-total", caption_family="technical-mono", illustrative=True),
        shot(6, 8_900, 11_200, phrase="lot size trade ki quantity hai", source_role="presenter", reference_role="reference-10-presenter-reset", subject="presenter", action="defines lot size as quantity", treatment="clean-presenter-reset", treatment_class="presenter-reset", asset_id="presenter-edited", caption_family="technical-mono", source_start_ms=8_900, zoom=1.06),
        shot(7, 11_200, 12_700, phrase="lot input", source_role="real-product", reference_role="reference-5-product-macro", subject="MT5 volume field", action="receives a tracked highlight", treatment="tight-ui-macro", treatment_class="product-macro", asset_id="mt5-risk-inputs", caption_family="outlined-demo", source_start_ms=1_600, crop_y=0.62, zoom=1.26),
        shot(8, 12_700, 14_200, phrase="quantity changes", source_role="real-product", reference_role="reference-5-cursor-action", subject="MT5 volume value", action="changes to an alternate setting", treatment="cursor-state-change", treatment_class="cursor-state-change", asset_id="mt5-risk-alternate", caption_family="outlined-demo", source_start_ms=1_900, crop_y=0.62, zoom=1.26),
        shot(9, 14_200, 16_300, phrase="small lot small position", source_role="real-product", reference_role="reference-5-product-comparison", subject="small lot field", action="holds beside a small position label", treatment="matched-ui-small", treatment_class="product-macro", asset_id="mt5-risk-inputs", caption_family="outlined-demo", source_start_ms=1_400, crop_x=0.38, crop_y=0.62, zoom=1.20),
        shot(10, 16_300, 18_400, phrase="large lot bigger impact", source_role="real-product", reference_role="reference-5-product-comparison", subject="larger lot field", action="changes while the impact label grows", treatment="matched-ui-large", treatment_class="cursor-state-change", asset_id="mt5-risk-alternate", caption_family="outlined-demo", source_start_ms=2_000, crop_x=0.62, crop_y=0.62, zoom=1.32),
        shot(11, 18_400, 20_450, phrase="same market move", source_role="deterministic-graphic", reference_role="reference-10-comparison-diagram", subject="one market move", action="feeds two position sizes", treatment="normalized-impact-bars", treatment_class="comparison-diagram", asset_id="graphic-same-move", caption_family="technical-mono", illustrative=True),
        shot(12, 20_450, 22_500, phrase="different account impact", source_role="deterministic-graphic", reference_role="reference-10-system-flow", subject="small and large relative bars", action="end at different qualitative impact", treatment="relative-impact-flow", treatment_class="mechanism-diagram", asset_id="graphic-relative-impact", caption_family="technical-mono", illustrative=True),
        shot(13, 22_500, 25_800, phrase="profit and loss both change", source_role="presenter", reference_role="reference-10-presenter-reset", subject="presenter", action="explains symmetric profit and loss scale", treatment="clean-presenter-reset", treatment_class="presenter-reset", asset_id="presenter-edited", caption_family="technical-mono", source_start_ms=22_500, zoom=1.08),
        shot(14, 25_800, 28_300, phrase="stop distance", source_role="deterministic-graphic", reference_role="reference-10-risk-equation", subject="stop distance lane", action="sets the distance component", treatment="dark-risk-equation", treatment_class="equation-diagram", asset_id="graphic-stop-distance", caption_family="technical-mono", illustrative=True),
        shot(15, 28_300, 30_800, phrase="lot size makes actual risk", source_role="deterministic-graphic", reference_role="reference-10-risk-equation", subject="lot size and stop distance", action="combine into qualitative risk", treatment="risk-combination-flow", treatment_class="mechanism-diagram", asset_id="graphic-risk-equation", caption_family="technical-mono", illustrative=True),
        shot(16, 30_800, 33_100, phrase="maximum lot limit", source_role="real-product", reference_role="reference-5-product-macro", subject="maximum lot setting", action="receives a visible cursor change", treatment="tight-ui-macro", treatment_class="product-macro", asset_id="mt5-risk-alternate", caption_family="outlined-demo", source_start_ms=1_800, crop_y=0.62, zoom=1.25),
        shot(17, 33_100, 35_500, phrase="fixed risk rule", source_role="real-product", reference_role="reference-10-code-rule", subject="fixed-risk code rule", action="is tracked line by line", treatment="code-rule-highlight", treatment_class="code-rule", asset_id="metaeditor-rule-highlight", caption_family="technical-mono", source_start_ms=1_200, crop_x=0.36, zoom=1.22),
        shot(18, 35_500, 37_150, phrase="wrong setting repeats", source_role="deterministic-graphic", reference_role="reference-10-loop-diagram", subject="wrong-setting loop", action="repeats without correction", treatment="restrained-loop", treatment_class="rule-diagram", asset_id="graphic-wrong-repeat", caption_family="technical-mono", illustrative=True),
        shot(19, 37_150, 38_800, phrase="robot perfectly repeats", source_role="real-product", reference_role="reference-10-code-rule", subject="unchanged code condition", action="receives a second tracked highlight", treatment="code-rule-highlight", treatment_class="code-rule", asset_id="metaeditor-rule-highlight", caption_family="technical-mono", source_start_ms=2_300, crop_x=0.36, zoom=1.22),
        shot(20, 38_800, 40_600, phrase="entry tells where", source_role="deterministic-graphic", reference_role="reference-10-system-flow", subject="entry marker", action="points to trade location", treatment="three-part-rule", treatment_class="comparison-diagram", asset_id="graphic-entry-lot-risk", caption_family="technical-mono", illustrative=True, stage="entry"),
        shot(21, 40_600, 42_400, phrase="lot size and risk tell consequence", source_role="deterministic-graphic", reference_role="reference-10-system-flow", subject="lot and risk markers", action="separate size from consequence", treatment="relationship-flow", treatment_class="mechanism-diagram", asset_id="graphic-entry-lot-risk", caption_family="technical-mono", illustrative=True, stage="risk"),
        shot(22, 42_400, 44_350, phrase="real EA action", source_role="real-product", reference_role="reference-5-product-action", subject="EA attachment dialog", action="opens with a visible cursor", treatment="cursor-state-change", treatment_class="cursor-state-change", asset_id="mt5-attach-ea", caption_family="outlined-demo", source_start_ms=2_100, crop_x=0.38, crop_y=0.62, zoom=1.18),
        shot(23, 44_350, 46_300, phrase="product close", source_role="real-product", reference_role="reference-5-product-close", subject="EA settings", action="settle on the risk controls", treatment="product-close", treatment_class="product-close", asset_id="mt5-risk-inputs", caption_family="outlined-demo", source_start_ms=2_400, crop_x=0.62, crop_y=0.62, zoom=1.34),
        shot(24, 46_300, 50_550, phrase="follow and thank you", source_role="presenter", reference_role="profit-bricks-brand", subject="presenter and brand mark", action="delivers the CTA and holds cleanly", treatment="clean-cta", treatment_class="cta", asset_id="presenter-edited", caption_family="compact-pill", source_start_ms=46_300, zoom=1.08),
    ]
    retimed = {
        12: (20_450, 23_000),
        13: (23_000, 25_450),
        14: (25_450, 27_690),
        15: (27_690, 30_280),
        16: (30_280, 33_070),
        17: (33_070, 35_530),
        18: (35_530, 38_200),
        19: (38_200, 40_000),
        20: (40_000, 40_860),
        21: (40_860, 43_570),
        22: (43_570, 45_000),
        23: (45_000, 46_360),
        24: (46_360, 50_550),
    }
    specs = [
        (
            replace(spec, start_ms=retimed[spec_number][0], end_ms=retimed[spec_number][1])
            if spec_number in retimed
            else spec
        )
        for spec_number, spec in enumerate(specs, start=1)
    ]
    specs[12] = replace(
        specs[12],
        narration_phrase="large lot par impact zyada",
        source_role="deterministic-graphic",
        reference_role="reference-10-comparison-diagram",
        primary_subject="large relative impact bar",
        action="grows while the market move stays constant",
        treatment="relative-impact-flow",
        treatment_class="comparison-diagram",
        asset_id="graphic-relative-impact-large",
        caption_family="technical-mono",
        source_start_ms=0,
        illustrative=True,
    )
    specs[13] = replace(
        specs[13],
        narration_phrase="profit aur loss donon change hote hain",
        source_role="presenter",
        reference_role="reference-10-presenter-reset",
        primary_subject="presenter",
        action="explains symmetric profit and loss scaling",
        treatment="clean-presenter-reset",
        treatment_class="presenter-reset",
        asset_id="presenter-edited",
        caption_family="technical-mono",
        source_start_ms=25_450,
        illustrative=False,
    )
    specs[14] = replace(
        specs[14],
        narration_phrase="stop loss enough nahi",
        asset_id="graphic-stop-distance",
        treatment="dark-risk-equation",
        treatment_class="equation-diagram",
    )
    specs[15] = replace(
        specs[15],
        narration_phrase="stop distance aur lot size actual risk",
        source_role="deterministic-graphic",
        reference_role="reference-10-risk-equation",
        primary_subject="stop distance and lot size",
        action="combine into actual risk",
        treatment="risk-combination-flow",
        treatment_class="mechanism-diagram",
        asset_id="graphic-risk-equation",
        caption_family="technical-mono",
        source_start_ms=0,
        illustrative=True,
    )
    specs[16] = replace(
        specs[16],
        narration_phrase="maximum lot limit",
        source_role="real-product",
        reference_role="reference-5-product-macro",
        primary_subject="maximum lot setting",
        action="changes through a visible cursor",
        treatment="tight-ui-macro",
        treatment_class="product-macro",
        asset_id="mt5-risk-alternate",
        caption_family="outlined-demo",
        source_start_ms=1_800,
        illustrative=False,
    )
    specs[17] = replace(
        specs[17],
        narration_phrase="fixed risk rule automatically follow",
        source_role="real-product",
        reference_role="reference-10-code-rule",
        primary_subject="fixed-risk code rule",
        action="is tracked line by line",
        treatment="code-rule-highlight",
        treatment_class="code-rule",
        asset_id="metaeditor-rule-highlight",
        caption_family="technical-mono",
        source_start_ms=1_200,
        illustrative=False,
    )
    specs[18] = replace(
        specs[18],
        narration_phrase="ghalat setting repeat",
        source_role="deterministic-graphic",
        reference_role="reference-10-loop-diagram",
        primary_subject="wrong-setting loop",
        action="repeats without correction",
        treatment="restrained-loop",
        treatment_class="rule-diagram",
        asset_id="graphic-wrong-repeat",
        caption_family="technical-mono",
        source_start_ms=0,
        illustrative=True,
    )
    specs[19] = replace(
        specs[19],
        narration_phrase="robot perfectly repeat karega",
        source_role="real-product",
        reference_role="reference-10-code-rule",
        primary_subject="unchanged code condition",
        action="receives a second tracked highlight",
        treatment="code-rule-highlight",
        treatment_class="code-rule",
        asset_id="metaeditor-rule-highlight",
        caption_family="technical-mono",
        source_start_ms=2_300,
        illustrative=False,
    )
    specs[20] = replace(
        specs[20],
        narration_phrase="entry lot size risk",
        source_role="deterministic-graphic",
        reference_role="reference-10-system-flow",
        primary_subject="entry lot and risk markers",
        action="separate where, size and consequence",
        treatment="relationship-flow",
        treatment_class="mechanism-diagram",
        asset_id="graphic-entry-lot-risk",
        caption_family="technical-mono",
        source_start_ms=0,
        illustrative=True,
    )
    specs[21] = replace(specs[21], source_start_ms=2_100)
    specs[22] = replace(specs[22], source_start_ms=2_400)
    specs[23] = replace(specs[23], source_start_ms=46_360)
    replacements = {
        1: {
            "asset_id": "composite-lot-size-hook",
            "treatment": "reference-hook-split",
            "treatment_class": "presenter-hook",
            "source_start_ms": 0,
            "metadata": {
                "contains_presenter": True,
                "presenter_fraction": 0.44,
                "top_asset_id": "mt5-risk-inputs",
                "top_source_start_ms": 1_500,
            },
        },
        4: {
            "source_role": "deterministic-graphic",
            "asset_id": "graphic-unit-price",
            "source_start_ms": 0,
            "treatment": "flat-multiplication-card",
            "treatment_class": "equation-diagram",
            "illustrative": True,
            "metadata": {},
        },
        5: {
            "source_role": "deterministic-graphic",
            "asset_id": "graphic-different-total",
            "source_start_ms": 0,
            "treatment": "qualitative-total-bars",
            "treatment_class": "comparison-diagram",
            "illustrative": True,
            "metadata": {},
        },
        9: {
            "source_role": "real-product",
            "asset_id": "composite-lot-size-small-lot",
            "source_start_ms": 0,
            "treatment": "product-presenter-split",
            "treatment_class": "presenter-explanation",
            "illustrative": False,
            "metadata": {
                "contains_presenter": True,
                "presenter_fraction": 0.44,
                "top_asset_id": "mt5-risk-inputs",
                "top_source_start_ms": 1_400,
            },
        },
        11: {
            "source_role": "licensed-context",
            "asset_id": "composite-lot-size-impact",
            "source_start_ms": 0,
            "treatment": "market-presenter-split",
            "treatment_class": "presenter-explanation",
            "illustrative": False,
            "metadata": {
                "contains_presenter": True,
                "presenter_fraction": 0.44,
                "top_asset_id": "pexels-38870320",
                "top_source_start_ms": 1_000,
            },
        },
        12: {
            "source_role": "licensed-context",
            "asset_id": "pexels-38870320",
            "source_start_ms": 3_000,
            "treatment": "different-impact-action",
            "treatment_class": "market-context",
            "illustrative": False,
        },
        13: {
            "source_role": "real-product",
            "asset_id": "mt5-risk-alternate",
            "source_start_ms": 1_700,
            "treatment": "large-lot-product-macro",
            "treatment_class": "product-macro",
            "illustrative": False,
        },
        15: {
            "source_role": "real-product",
            "asset_id": "mt5-risk-inputs",
            "source_start_ms": 1_500,
            "treatment": "stop-distance-product-macro",
            "treatment_class": "product-macro",
            "illustrative": False,
        },
        19: {
            "source_role": "real-product",
            "asset_id": "composite-lot-size-wrong-setting",
            "source_start_ms": 0,
            "treatment": "code-presenter-split",
            "treatment_class": "presenter-explanation",
            "illustrative": False,
            "metadata": {
                "contains_presenter": True,
                "presenter_fraction": 0.44,
                "top_asset_id": "metaeditor-rule-highlight",
                "top_source_start_ms": 1_800,
            },
        },
        21: {
            "source_role": "deterministic-graphic",
            "asset_id": "graphic-entry-lot-risk",
            "source_start_ms": 0,
            "treatment": "relationship-flow",
            "treatment_class": "mechanism-diagram",
            "illustrative": True,
            "metadata": {},
        },
    }
    specs = [
        replace(spec, **replacements[index])
        if index in replacements
        else spec
        for index, spec in enumerate(specs, start=1)
    ]
    specs = [
        (
            replace(
                spec,
                metadata={**spec.metadata, "product_grade": "balanced"},
            )
            if spec.source_role == "real-product"
            else spec
        )
        for spec in specs
    ]
    return make_blueprint(
        story_id="lot-size",
        title="Forex Lot Size",
        source=SOURCE,
        transcript_path=TRANSCRIPT,
        duration_ms=DURATION_MS,
        music_bpm=96,
        shots=specs,
    )


if __name__ == "__main__":
    from build_0813_v8_pipeline import build_story

    raise SystemExit(build_story(build_blueprint()))
