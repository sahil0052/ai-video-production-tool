from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from build_0813_v8_common import make_blueprint, shot


SOURCE = Path(r"D:\Downloads\0813 (1).mp4")
TRANSCRIPT = Path(
    r"C:\websites\ai video production tool\storage\deliverables"
    r"\0813-production-v3-live-footage\analysis"
    r"\transcript-deepgram.json"
)
DURATION_MS = 47_830


def build_blueprint():
    specs = [
        shot(1, 0, 700, phrase="chai se pehle doodh", source_role="licensed-context", reference_role="reference-13-news-hook", subject="milk pour", action="pours into tea", treatment="full-frame-macro", treatment_class="tactile-context", asset_id="pexels-27093700", caption_family="display-emphasis", source_start_ms=800, zoom=1.10),
        shot(2, 700, 1_450, phrase="cheeni", source_role="licensed-context", reference_role="reference-13-news-hook", subject="sugar spoon over tea", action="stirs the ingredient into the cup", treatment="tight-object-cut", treatment_class="macro-detail", asset_id="pexels-29817236", caption_family="display-emphasis", source_start_ms=8_000, zoom=1.14),
        shot(3, 1_450, 2_200, phrase="paper cup", source_role="licensed-context", reference_role="reference-13-news-hook", subject="paper coffee cup", action="moves in a hand-held close-up", treatment="full-frame-macro", treatment_class="tactile-context", asset_id="pexels-13850344", caption_family="display-emphasis", source_start_ms=500, zoom=1.13),
        shot(4, 2_200, 3_200, phrase="supplier rates badhate hain", source_role="licensed-context", reference_role="reference-13-literal-action", subject="warehouse supplier cart", action="moves packaged goods through the aisle", treatment="tracked-full-frame", treatment_class="supplier-action", asset_id="pexels-29604470", caption_family="technical-mono", source_start_ms=1_000, zoom=1.10),
        shot(5, 3_200, 4_200, phrase="producer level price", source_role="licensed-context", reference_role="reference-13-literal-action", subject="manufacturing line macro", action="moves produced units along the line", treatment="hard-cut-action", treatment_class="factory-action", asset_id="pexels-7222345", caption_family="technical-mono", source_start_ms=4_000, zoom=1.12),
        shot(6, 4_200, 5_200, phrase="maal bechne se pehle", source_role="licensed-context", reference_role="reference-13-literal-action", subject="warehouse storage bins", action="shows a worker selecting inventory", treatment="full-frame-motion", treatment_class="warehouse-action", asset_id="pexels-7019230", caption_family="technical-mono", source_start_ms=5_000, zoom=1.12),
        shot(7, 5_200, 6_400, phrase="producer", source_role="deterministic-graphic", reference_role="reference-10-system-flow", subject="producer node", action="sends price upstream", treatment="flat-node-flow", treatment_class="designed-flow", asset_id="graphic-ppi-producer", caption_family="technical-mono", illustrative=True),
        shot(8, 6_400, 7_600, phrase="wholesale", source_role="deterministic-graphic", reference_role="reference-10-system-flow", subject="wholesale node", action="passes changed price", treatment="tracked-arrow-step", treatment_class="process-step", asset_id="graphic-ppi-wholesale", caption_family="technical-mono", illustrative=True),
        shot(9, 7_600, 8_800, phrase="retail", source_role="deterministic-graphic", reference_role="reference-10-system-flow", subject="retail node", action="receives upstream price", treatment="flat-node-flow", treatment_class="designed-flow", asset_id="graphic-ppi-retail", caption_family="technical-mono", illustrative=True),
        shot(10, 8_800, 10_100, phrase="customer final price CPI", source_role="licensed-context", reference_role="reference-13-news-comparison", subject="checkout customer", action="pays final retail price", treatment="literal-full-frame", treatment_class="customer-context", asset_id="pexels-37101039", caption_family="technical-mono", source_start_ms=1_200, zoom=1.10),
        shot(11, 10_100, 11_400, phrase="factory producer PPI", source_role="licensed-context", reference_role="reference-13-news-comparison", subject="factory worker", action="produces goods before retail", treatment="action-match-cut", treatment_class="factory-action", asset_id="pexels-38362060", caption_family="technical-mono", source_start_ms=2_700, zoom=1.14),
        shot(12, 11_400, 12_800, phrase="CPI versus PPI", source_role="deterministic-graphic", reference_role="reference-10-comparison-diagram", subject="CPI and PPI labels", action="separate customer and producer stages", treatment="two-stage-diagram", treatment_class="comparison-diagram", asset_id="graphic-cpi-vs-ppi", caption_family="technical-mono", illustrative=True),
        shot(13, 12_800, 15_100, phrase="13 August 2026 release", source_role="presenter", reference_role="reference-13-presenter-reset", subject="presenter", action="introduces the release date", treatment="clean-presenter-reset", treatment_class="presenter-reset", asset_id="presenter-edited", caption_family="technical-mono", source_start_ms=12_800, zoom=1.04),
        shot(14, 15_100, 15_800, phrase="13 August 2026", source_role="direct-evidence", reference_role="reference-13-evidence-overview", subject="BLS release page", action="appears as a brief full-source overview", treatment="source-page-overview", treatment_class="evidence-overview", asset_id="bls-ppi-july-2026", caption_family="documentary-clean", evidence_crop="overview"),
        shot(15, 15_800, 16_800, phrase="America ka July PPI", source_role="direct-evidence", reference_role="reference-13-evidence-excerpt", subject="BLS release heading", action="fills the frame at readable size", treatment="source-line-highlight", treatment_class="evidence-highlight", asset_id="bls-ppi-july-2026", caption_family="documentary-clean", evidence_crop="zero-attribution"),
        shot(16, 16_800, 17_700, phrase="July PPI aaya", source_role="direct-evidence", reference_role="reference-13-evidence-excerpt", subject="official July release title", action="holds with attribution", treatment="source-pixel-macro", treatment_class="evidence-macro", asset_id="bls-ppi-july-2026", caption_family="documentary-clean", evidence_crop="actual"),
        shot(17, 17_700, 19_400, phrase="market expected 0.2 percent", source_role="direct-evidence", reference_role="reference-13-evidence-excerpt", subject="CNBC forecast headline", action="shows the 0.2 percent expectation", treatment="editorial-source-macro", treatment_class="evidence-highlight", asset_id="bls-ppi-july-2026", caption_family="documentary-clean", evidence_crop="forecast"),
        shot(18, 19_400, 21_100, phrase="increase expect kar raha tha", source_role="direct-evidence", reference_role="reference-13-proof-punch", subject="forecast key point", action="fills the frame with the sourced expectation line", treatment="editorial-proof-hold", treatment_class="evidence-macro", asset_id="bls-ppi-july-2026", caption_family="documentary-clean", evidence_crop="forecast-detail"),
        shot(19, 21_100, 22_850, phrase="but actual result", source_role="direct-evidence", reference_role="reference-13-proof-punch", subject="official actual-value excerpt", action="cuts to the sourced result only when it is spoken", treatment="editorial-source-macro", treatment_class="evidence-highlight", asset_id="bls-ppi-july-2026", caption_family="documentary-clean", evidence_crop="actual"),
        shot(20, 22_850, 24_000, phrase="actual result zero", source_role="direct-evidence", reference_role="reference-13-evidence-excerpt", subject="official unchanged result", action="shows the verified 0.0 percent result", treatment="source-pixel-macro", treatment_class="evidence-macro", asset_id="bls-ppi-july-2026", caption_family="documentary-clean", evidence_crop="zero"),
        shot(21, 24_000, 25_000, phrase="zero ka matlab flat nahi", source_role="deterministic-graphic", reference_role="reference-10-mechanism", subject="zero result", action="splits into moving components", treatment="dark-mechanism-card", treatment_class="mechanism-diagram", asset_id="graphic-zero-not-flat", caption_family="technical-mono", illustrative=True),
        shot(22, 25_000, 26_500, phrase="goods prices 0.7 percent gire", source_role="direct-evidence", reference_role="reference-13-evidence-excerpt", subject="goods source excerpt", action="fills the frame with the verified negative line", treatment="source-pixel-macro", treatment_class="evidence-macro", asset_id="bls-ppi-july-2026", caption_family="documentary-clean", evidence_crop="goods"),
        shot(23, 26_500, 27_950, phrase="goods prices fell", source_role="direct-evidence", reference_role="reference-13-evidence-excerpt", subject="goods value and attribution", action="holds for phone reading", treatment="source-line-highlight", treatment_class="evidence-highlight", asset_id="bls-ppi-july-2026", caption_family="documentary-clean", evidence_crop="goods"),
        shot(24, 27_950, 29_400, phrase="services 0.2 percent badhi", source_role="direct-evidence", reference_role="reference-13-evidence-excerpt", subject="services source excerpt", action="shows the verified positive line", treatment="source-pixel-macro", treatment_class="evidence-macro", asset_id="bls-ppi-july-2026", caption_family="documentary-clean", evidence_crop="services"),
        shot(25, 29_400, 30_800, phrase="total result zero", source_role="direct-evidence", reference_role="reference-13-evidence-excerpt", subject="goods and services source excerpts", action="alternate as verified source pixels", treatment="source-line-highlight", treatment_class="evidence-highlight", asset_id="bls-ppi-july-2026", caption_family="documentary-clean", evidence_crop="goods-services"),
        shot(26, 30_800, 32_300, phrase="opposite directions", source_role="deterministic-graphic", reference_role="reference-10-reversal", subject="two directional arrows", action="separate upward and downward", treatment="red-cyan-reversal", treatment_class="reversal-diagram", asset_id="graphic-opposing-arrows", caption_family="technical-mono", illustrative=True),
        shot(27, 32_300, 33_820, phrase="andar prices opposite directions", source_role="deterministic-graphic", reference_role="reference-10-comparison-diagram", subject="combined result marker", action="returns to zero", treatment="qualitative-balance", treatment_class="comparison-diagram", asset_id="graphic-net-zero", caption_family="technical-mono", illustrative=True),
        shot(28, 33_820, 35_820, phrase="inflation expected se kam", source_role="licensed-context", reference_role="reference-13-market-context", subject="market data screen", action="updates after the release", treatment="full-frame-market", treatment_class="market-context", asset_id="pexels-34433115", caption_family="technical-mono", source_start_ms=6_800, zoom=1.12),
        shot(29, 35_820, 38_190, phrase="spread limit", source_role="real-product", reference_role="reference-10-product-macro", subject="MT5 spread limit field", action="changes through a visible cursor", treatment="tight-ui-macro", treatment_class="product-macro", asset_id="mt5-risk-inputs", caption_family="outlined-demo", source_start_ms=1_600, crop_y=0.62, zoom=1.24),
        shot(30, 38_190, 39_400, phrase="confirmation", source_role="real-product", reference_role="reference-10-cursor-action", subject="MT5 confirmation controls", action="switch to a confirmed setting", treatment="cursor-state-change", treatment_class="cursor-state-change", asset_id="mt5-risk-alternate", caption_family="outlined-demo", source_start_ms=1_900, crop_x=0.65, crop_y=0.62, zoom=1.28),
        shot(31, 39_400, 40_980, phrase="spread and confirmation rule", source_role="deterministic-graphic", reference_role="reference-10-code-rule", subject="spread and confirmation rules", action="connect to execution safety", treatment="code-rule-card", treatment_class="code-rule", asset_id="graphic-ppi-risk-rule", caption_family="technical-mono", illustrative=True),
        shot(32, 40_980, 43_270, phrase="robot number market reason", source_role="presenter", reference_role="reference-13-presenter-reset", subject="presenter", action="delivers the final lesson", treatment="clean-presenter-reset", treatment_class="presenter-reset", asset_id="presenter-edited", caption_family="technical-mono", source_start_ms=40_980, zoom=1.07),
        shot(33, 43_270, 45_670, phrase="informative videos", source_role="presenter", reference_role="reference-13-cta", subject="presenter", action="introduces the follow call to action", treatment="clean-cta", treatment_class="cta", asset_id="presenter-edited", caption_family="compact-pill", source_start_ms=43_270, zoom=1.10),
        shot(34, 45_670, 47_380, phrase="follow kijiye", source_role="presenter", reference_role="profit-bricks-brand", subject="presenter and brand mark", action="delivers the final CTA phrase", treatment="brand-cta", treatment_class="brand-close", asset_id="presenter-edited", caption_family="compact-pill", source_start_ms=45_670, zoom=1.08),
        shot(35, 47_380, 47_830, phrase="thank you", source_role="presenter", reference_role="profit-bricks-brand", subject="presenter and brand mark", action="holds cleanly to the final frame", treatment="clean-ending", treatment_class="cta", asset_id="presenter-edited", caption_family="compact-pill", source_start_ms=47_380, zoom=1.06),
    ]
    replacements = {
        1: {
            "asset_id": "composite-ppi-hook-milk",
            "treatment": "reference-hook-split",
            "treatment_class": "presenter-hook",
            "source_start_ms": 0,
            "metadata": {
                "contains_presenter": True,
                "presenter_fraction": 0.44,
                "top_asset_id": "pexels-27093700",
                "top_source_start_ms": 800,
            },
        },
        3: {
            "asset_id": "composite-ppi-hook-cup",
            "treatment": "reference-hook-split",
            "treatment_class": "presenter-hook",
            "source_start_ms": 0,
            "metadata": {
                "contains_presenter": True,
                "presenter_fraction": 0.44,
                "top_asset_id": "pexels-13850344",
                "top_source_start_ms": 500,
            },
        },
        7: {
            "source_role": "licensed-context",
            "asset_id": "pexels-32953312",
            "treatment": "full-frame-factory-action",
            "treatment_class": "factory-action",
            "source_start_ms": 600,
            "illustrative": False,
        },
        8: {
            "source_role": "licensed-context",
            "asset_id": "pexels-7019230",
            "treatment": "tracked-warehouse-action",
            "treatment_class": "warehouse-action",
            "source_start_ms": 4_300,
            "illustrative": False,
        },
        9: {
            "source_role": "licensed-context",
            "asset_id": "pexels-37101039",
            "treatment": "retail-checkout-action",
            "treatment_class": "customer-context",
            "source_start_ms": 1_200,
            "illustrative": False,
        },
        21: {
            "source_role": "direct-evidence",
            "asset_id": "composite-ppi-zero-proof",
            "treatment": "evidence-presenter-split",
            "treatment_class": "evidence-explanation",
            "source_start_ms": 0,
            "illustrative": False,
            "metadata": {
                "contains_presenter": True,
                "presenter_fraction": 0.44,
                "top_asset_id": "bls-zero-proof-static",
                "top_source_start_ms": 0,
            },
        },
        23: {
            "source_role": "licensed-context",
            "asset_id": "pexels-32953312",
            "treatment": "goods-production-action",
            "treatment_class": "factory-action",
            "source_start_ms": 3_200,
            "illustrative": False,
            "metadata": {},
        },
        25: {
            "source_role": "deterministic-graphic",
            "asset_id": "graphic-zero-balance",
            "treatment": "qualitative-balance",
            "treatment_class": "comparison-diagram",
            "source_start_ms": 0,
            "illustrative": True,
            "metadata": {},
        },
        27: {
            "source_role": "licensed-context",
            "asset_id": "composite-ppi-net-zero",
            "treatment": "context-presenter-split",
            "treatment_class": "presenter-explanation",
            "source_start_ms": 0,
            "illustrative": False,
            "metadata": {
                "contains_presenter": True,
                "presenter_fraction": 0.44,
                "top_asset_id": "pexels-32953312",
                "top_source_start_ms": 4_500,
            },
        },
        28: {
            "asset_id": "pexels-38870320",
            "source_start_ms": 500,
            "treatment": "full-frame-market-analysis",
        },
        31: {
            "source_role": "real-product",
            "asset_id": "metaeditor-rule-highlight",
            "treatment": "code-rule-highlight",
            "treatment_class": "code-rule",
            "source_start_ms": 1_200,
            "illustrative": False,
        },
    }
    specs = [
        replace(spec, **replacements[index])
        if index in replacements
        else spec
        for index, spec in enumerate(specs, start=1)
    ]
    return make_blueprint(
        story_id="ppi",
        title="Producer Price Index",
        source=SOURCE,
        transcript_path=TRANSCRIPT,
        duration_ms=DURATION_MS,
        music_bpm=100,
        shots=specs,
    )


if __name__ == "__main__":
    from build_0813_v8_pipeline import build_story

    raise SystemExit(build_story(build_blueprint()))
