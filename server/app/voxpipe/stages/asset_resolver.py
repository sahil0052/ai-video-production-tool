from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

from app.voxpipe.models.edit_plan import VoxEditPlan
from app.voxpipe.core.encode_standards import WORKSPACE_ROOT

logger = logging.getLogger("voxpipe.asset_resolver")
FLOW_VIDEOS_DIR = WORKSPACE_ROOT / "renderer" / "public" / "flow_videos"
RE_SEGMENTS_DIR = WORKSPACE_ROOT / "storage" / "deliverables" / "voxpipe_0830_2_realestate" / "rendered_segments"


SEGMENTS_0831_1_DIR = WORKSPACE_ROOT / "storage" / "deliverables" / "voxpipe_0831_1_nishahomes" / "rendered_segments"
SEGMENTS_0831_DIR = WORKSPACE_ROOT / "storage" / "deliverables" / "voxpipe_0831" / "rendered_segments"


def resolve_assets_for_plan(plan: VoxEditPlan) -> VoxEditPlan:
    """Maps each narrative beat 1:1 to a dedicated, unique 3D Google Flow or real estate segment video."""
    logger.info(f"Resolving assets for {len(plan.beats)} beats in job {plan.job_id}...")

    is_0831_1 = ("0831 (1)" in plan.source_video or "0831_1" in plan.job_id.lower() or "nishahomes" in plan.job_id.lower())
    is_0831 = ("0831" in plan.source_video or "0831" in plan.job_id.lower()) and not is_0831_1
    is_0830_2 = ("0830_2" in plan.job_id.lower() or "0830 (2)" in plan.source_video or "realestate" in plan.job_id.lower()) and not is_0831 and not is_0831_1
    is_0830_1 = ("0830_1" in plan.job_id.lower() or "0830 (1)" in plan.source_video or "bank" in plan.job_id.lower()) and not is_0830_2 and not is_0831 and not is_0831_1
    is_0830_veg = ("0830" in plan.job_id.lower() or "0830" in plan.source_video) and not is_0830_1 and not is_0830_2 and not is_0831 and not is_0831_1
    is_0829 = ("0829" in plan.job_id.lower() or "0829" in plan.source_video)
    is_crash = ("crash" in plan.job_id.lower() or "0828 (2)" in plan.source_video or "0828_2" in plan.job_id.lower())

    if is_0831_1:
        semantic_map = {
            1: SEGMENTS_0831_1_DIR / "seg1_price_trap.mp4",
            2: SEGMENTS_0831_1_DIR / "seg2_three_pillars.mp4",
            3: SEGMENTS_0831_1_DIR / "seg3_ready_investment.mp4",
            4: SEGMENTS_0831_1_DIR / "seg4_real_walkthrough.mp4",
            5: SEGMENTS_0831_1_DIR / "seg5_four_cities_tiers.mp4",
            6: SEGMENTS_0831_1_DIR / "seg6_selling_ready.mp4",
            7: SEGMENTS_0831_1_DIR / "seg7_cta_endcard.mp4",
        }
    elif is_0831:
        semantic_map = {
            1: SEGMENTS_0831_DIR / "seg1_flow_brain_faceoff.mp4",
            2: SEGMENTS_0831_DIR / "seg2_flow_profit_breakout.mp4",
            3: SEGMENTS_0831_DIR / "seg3_flow_fear_greed_scale.mp4",
            4: SEGMENTS_0831_DIR / "seg4_flow_crash_drop.mp4",
            5: SEGMENTS_0831_DIR / "seg5_flow_emotion_override.mp4",
            6: SEGMENTS_0831_DIR / "seg6_flow_discipline_trophy.mp4",
        }
    elif is_0830_2:
        semantic_map = {
            1: RE_SEGMENTS_DIR / "seg1_rent_vs_own.mp4",
            2: RE_SEGMENTS_DIR / "seg2_elevation.mp4",
            3: RE_SEGMENTS_DIR / "seg3_real_living_kitchen.mp4",
            4: RE_SEGMENTS_DIR / "seg4_real_bathroom_amenities.mp4",
            5: RE_SEGMENTS_DIR / "seg5_pricing_showcase.mp4",
            6: RE_SEGMENTS_DIR / "seg6_official_cta.mp4",
        }
    elif is_0830_1:
        semantic_map = {
            1: FLOW_VIDEOS_DIR / "flow0830_bank_01_deposit_mystery.mp4",
            2: FLOW_VIDEOS_DIR / "flow0830_bank_02_vault_vs_circulation.mp4",
            3: FLOW_VIDEOS_DIR / "flow0830_bank_03_interest_spread_nim.mp4",
            4: FLOW_VIDEOS_DIR / "flow0830_bank_04_operating_costs_npa.mp4",
            5: FLOW_VIDEOS_DIR / "flow0830_bank_05_financial_engine_follow_cta.mp4",
        }
    elif is_0830_veg:
        tiffin_asset = FLOW_VIDEOS_DIR / "flow0830_03_veg_darbaar_exact_tiffin.mp4"
        if not tiffin_asset.exists():
            tiffin_asset = FLOW_VIDEOS_DIR / "flow0830_03_veg_darbaar_grand_thali.mp4"

        paratha_asset = FLOW_VIDEOS_DIR / "flow0830_05_crispy_paratha_and_rayta.mp4"
        if not paratha_asset.exists():
            paratha_asset = FLOW_VIDEOS_DIR / "flow0830_05_crispy_paratha_order_cta.mp4"

        semantic_map = {
            1: FLOW_VIDEOS_DIR / "flow0830_01_oily_fastfood_dilemma.mp4",
            2: FLOW_VIDEOS_DIR / "flow0830_02_office_lunch_craving.mp4",
            3: tiffin_asset,
            4: FLOW_VIDEOS_DIR / "flow0830_04_hot_doorstep_delivery.mp4",
            5: paratha_asset,
        }
    elif is_0829:
        semantic_map = {
            1: FLOW_VIDEOS_DIR / "flow0829_01_human_vs_robot_faceoff.mp4",
            2: FLOW_VIDEOS_DIR / "flow0829_02_zero_emotion_processor.mp4",
            3: FLOW_VIDEOS_DIR / "flow0829_03_millisecond_speed_execution.mp4",
            4: FLOW_VIDEOS_DIR / "flow0829_04_human_judgment_news_context.mp4",
            5: FLOW_VIDEOS_DIR / "flow0829_05_strategy_risk_management_trophy.mp4",
            6: FLOW_VIDEOS_DIR / "flow0829_06_forex_ai_follow_cta.mp4",
        }
    elif is_crash:
        semantic_map = {
            1: FLOW_VIDEOS_DIR / "flow_crash_01_missing_money_mystery.mp4",
            2: FLOW_VIDEOS_DIR / "flow_crash_02_100_shares_1000.mp4",
            3: FLOW_VIDEOS_DIR / "flow_crash_03_price_drops_700_question.mp4",
            4: FLOW_VIDEOS_DIR / "flow_crash_04_buyer_willingness_auction.mp4",
            5: FLOW_VIDEOS_DIR / "flow_crash_05_10_lakh_crore_wipeout_headline.mp4",
            6: FLOW_VIDEOS_DIR / "flow_crash_06_trading_value_follow_cta.mp4",
        }
    else:
        semantic_map = {
            1: FLOW_VIDEOS_DIR / "flow0828_01_crore_announcement.mp4",
            2: FLOW_VIDEOS_DIR / "flow0828_02_money_printer_overdrive.mp4",
            3: FLOW_VIDEOS_DIR / "flow0828_02b_inflation_dial_surge.mp4",
            4: FLOW_VIDEOS_DIR / "flow0828_03b_price_jump_300_to_3000.mp4",
            5: FLOW_VIDEOS_DIR / "flow0828_04_currency_crash_zimbabwe.mp4",
            6: FLOW_VIDEOS_DIR / "flow0828_04b_purchasing_power_zero.mp4",
            7: FLOW_VIDEOS_DIR / "flow0828_05a_real_goods_factories.mp4",
            8: FLOW_VIDEOS_DIR / "flow0828_05_economic_reality_follow_cta.mp4",
        }

    for b in plan.beats:
        if b.id in semantic_map:
            candidate = semantic_map[b.id]
            if candidate.exists():
                b.asset_path = str(candidate)
                b.asset_engine = "flow_i2v"
                logger.info(f" -> Beat {b.id} ({b.duration:.1f}s): Resolved asset -> {candidate.name}")
            else:
                logger.warning(f"Asset not yet on disk: {candidate.name}")

    return plan
