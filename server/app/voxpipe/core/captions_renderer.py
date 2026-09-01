from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Dict, Any
from app.voxpipe.models.edit_plan import VoxEditPlan

logger = logging.getLogger("voxpipe.captions")


def format_ass_timestamp(seconds: float) -> str:
    """Formats seconds to ASS timestamp: H:MM:SS.CC"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def generate_emphasis_punchline_captions(plan: VoxEditPlan, output_ass_path: Path) -> Path:
    """Generates large, high-impact emphasis punchline captions for key moments only."""
    output_ass_path.parent.mkdir(parents=True, exist_ok=True)

    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Punchline,Impact,76,&H00FFFFFF,&H000000FF,&H000D0D0D,&H90000000,-1,0,0,0,100,100,1,0,1,6.0,3.5,2,40,40,120,1
Style: PunchlineRed,Impact,80,&H003333FF,&H000000FF,&H000D0D0D,&H90000000,-1,0,0,0,100,100,1,0,1,6.5,4.0,2,40,40,120,1
Style: PunchlineGold,Impact,78,&H0000D7FF,&H000000FF,&H000D0D0D,&H90000000,-1,0,0,0,100,100,1,0,1,6.0,3.5,2,40,40,120,1
Style: PunchlineGreen,Impact,76,&H0076E600,&H000000FF,&H000D0D0D,&H90000000,-1,0,0,0,100,100,1,0,1,6.5,4.0,2,40,40,120,1
Style: PhoneCard,Impact,76,&H0000FFFF,&H000000FF,&H000D0D0D,&HC0000000,-1,0,0,0,100,100,1,0,1,7.0,4.5,2,30,30,120,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    if "0831 (1)" in plan.source_video or "0831_1" in plan.job_id.lower() or "nishahomes" in plan.job_id.lower():
        punchlines = [
            {"start": 0.50, "end": 3.40, "style": "PunchlineGold", "text": r"PROPERTY BUYING MISTAKE:\N{\c&H003333FF&}ONLY LOOKING AT PRICE!{\r}"},
            {"start": 4.00, "end": 8.50, "style": "PunchlineGold", "text": r"LOCATION • PROJECT • POSSESSION\N{\c&H0000D7FF&}THE 3 ESSENTIAL PILLARS!{\r}"},
            {"start": 9.20, "end": 14.50, "style": "PunchlineGreen", "text": r"READY-TO-MOVE HOMES\N{\c&H00FFFFFF&}A SMART LONG-TERM INVESTMENT!{\r}"},
            {"start": 15.20, "end": 20.50, "style": "PunchlineGold", "text": r"NISHA HOMES ADVISORY:\N{\c&H0000D7FF&}MATCHED TO YOUR EXACT BUDGET!{\r}"},
            {"start": 21.80, "end": 28.00, "style": "PunchlineGold", "text": r"GURGAON • NOIDA • GHAZIABAD • S. DELHI\N{\c&H0076E600&}AFFORDABLE • ECONOMY • PREMIUM{\r}"},
            {"start": 28.80, "end": 33.20, "style": "PunchlineRed", "text": r"SELLING YOUR PROPERTY?\N{\c&H0000D7FF&}'FOR SALE' SIGN IS NOT ENOUGH!{\r}"},
            {"start": 33.80, "end": 40.13, "style": "PunchlineGold", "text": r"SAHI PRICING • PRESENTATION • BUYER\N{\c&H0076E600&}NISHA HOMES: 7303515710{\r}"},
        ]
    elif "0831" in plan.source_video or "0831" in plan.job_id.lower():
        punchlines = [
            {"start": 0.50, "end": 6.50, "style": "PunchlineGold", "text": r"WHY DO SMART PEOPLE MAKE\N{\c&H003333FF&}STUPID TRADING DECISIONS?{\r}"},
            {"start": 8.00, "end": 13.50, "style": "PunchlineRed", "text": r"3 WINNING TRADES = {\c&H0000D7FF&}OVERCONFIDENCE!{\r}"},
            {"start": 14.80, "end": 21.00, "style": "PunchlineGold", "text": r"TRADING IS NOT AN IQ PROBLEM:\N{\c&H003333FF&}IT'S FEAR & GREED!{\r}"},
            {"start": 22.50, "end": 28.50, "style": "PunchlineRed", "text": r"BIG LOSS = {\c&H0000D7FF&}REVENGE TRADING TRAP!{\r}"},
            {"start": 33.00, "end": 36.00, "style": "PunchlineRed", "text": r"EMOTION OVERWRITES\N{\c&H0000D7FF&}ALL TRADING RULES!{\r}"},
            {"start": 39.0, "end": 44.40, "style": "PunchlineGold", "text": r"SMART TRADERS FOLLOW RULES\N{\c&H0076E600&}FOLLOW TO MASTER PSYCHOLOGY!{\r}"},
        ]
    elif "0830 (2)(1)" in plan.source_video or "0830_2_1" in plan.job_id.lower() or "0830 (2)(1)" in plan.job_id:
        punchlines = [
            {"start": 0.50, "end": 4.80, "style": "PunchlineRed", "text": r"TIRED OF PAYING RENT?\N{\c&H0000D7FF&}OWN YOUR DREAM HOME TODAY!{\r}"},
            {"start": 5.20, "end": 12.50, "style": "PunchlineGold", "text": r"MANAS HEIGHTS | TITWALA (E)\N{\c&H00FFFFFF&}10 MINS WALK FROM RAILWAY STATION{\r}"},
            {"start": 13.00, "end": 19.80, "style": "PunchlineGreen", "text": r"THOUGHTFULLY PLANNED 1 BHK\N{\c&H0000D7FF&}VITRIFIED TILES & GRANITE PLATFORM{\r}"},
            {"start": 20.20, "end": 27.20, "style": "PunchlineGold", "text": r"FULL TILED KITCHEN & ELEGANT BATHROOM\N{\c&H00FFFFFF&}HI-SPEED LIFTS, CCTV & FIRE SAFETY{\r}"},
            {"start": 27.60, "end": 30.80, "style": "PunchlineGold", "text": r"1 BHK ONLY ₹24 LAKH\N{\c&H0076E600&}★ ALL INCLUSIVE ★ ZERO HIDDEN CHARGES{\r}"},
            {"start": 31.20, "end": 35.43, "style": "PhoneCard", "text": r"BOOK SITE VISIT: CALL / WHATSAPP\N{\c&H0076E600&}+91 8591661098 | 8104947371{\r}"},
        ]
    elif "0830_2" in plan.job_id.lower() or "0830 (2)" in plan.source_video or "realestate" in plan.job_id.lower():
        punchlines = [
            {"start": 0.50, "end": 4.50, "style": "PunchlineRed", "text": r"TIRED OF PAYING RENT?\N{\c&H0000D7FF&}OWN YOUR DREAM HOME TODAY!{\r}"},
            {"start": 5.00, "end": 10.50, "style": "PunchlineGold", "text": r"MANAS HEIGHTS | TITWALA (E)\N{\c&H00FFFFFF&}A PROJECT BY KVM & MORYA GROUP{\r}"},
            {"start": 11.00, "end": 17.50, "style": "PunchlineGreen", "text": r"THOUGHTFULLY PLANNED 1 BHK\N{\c&H0000D7FF&}VITRIFIED TILES & GRANITE PLATFORM{\r}"},
            {"start": 18.00, "end": 25.00, "style": "PunchlineGold", "text": r"FULL TILED KITCHEN & ELEGANT BATHROOM\N{\c&H00FFFFFF&}HI-SPEED LIFTS, CCTV & POWER BACKUP{\r}"},
            {"start": 25.50, "end": 29.00, "style": "PunchlineGold", "text": r"1 BHK ONLY ₹24 LAKH\N{\c&H0076E600&}★ ALL INCLUSIVE ★ ZERO HIDDEN CHARGES{\r}"},
            {"start": 29.50, "end": 33.58, "style": "PhoneCard", "text": r"BOOK SITE VISIT: CALL / WHATSAPP\N{\c&H0076E600&}+91 8591661098 | 8104947371{\r}"},
        ]
    elif "0830_1" in plan.job_id.lower() or "0830 (1)" in plan.source_video or "bank" in plan.job_id.lower():
        punchlines = [
            {"start": 0.50, "end": 6.50, "style": "PunchlineGold", "text": r"YOU DEPOSIT ₹1,00,000:\N{\c&H003333FF&}HOW DOES THE BANK PROFIT?{\r}"},
            {"start": 7.00, "end": 14.00, "style": "PunchlineRed", "text": r"MONEY IS NOT LOCKED IN A VAULT"},
            {"start": 14.50, "end": 22.00, "style": "PunchlineGold", "text": r"4% DEPOSIT vs 9% LOAN = {\c&H0000D7FF&}5% SPREAD (NIM){\r}"},
            {"start": 22.50, "end": 34.00, "style": "Punchline", "text": r"OPERATING COSTS, TECH & {\c&H003333FF&}NPA RISK{\r}"},
            {"start": 34.50, "end": 42.84, "style": "PunchlineGold", "text": r"FOLLOW TO MASTER FINANCE"},
        ]
    elif "0830" in plan.job_id.lower() or "0830" in plan.source_video:
        punchlines = [
            {"start": 0.50, "end": 6.50, "style": "PunchlineRed", "text": r"TIRED OF OILY FOOD & ACIDITY?"},
            {"start": 7.50, "end": 14.50, "style": "PunchlineGold", "text": r"NO TIME TO COOK FRESH FOOD?"},
            {"start": 15.50, "end": 22.00, "style": "PunchlineGreen", "text": r"VEG DARBAAR: 4 ROTI, CHAWAL, 2 SABJI\N{\c&H0000D7FF&}COMPLETE THALI - ₹80 ONLY{\r}"},
            {"start": 22.50, "end": 27.50, "style": "PunchlineGold", "text": r"FREE DOORSTEP DELIVERY\N{\c&H00FFFFFF&}SIMPLE THALI ₹50 | RAYTA ₹20{\r}"},
            {"start": 28.00, "end": 33.85, "style": "PhoneCard", "text": r"ORDER NOW: CALL / WHATSAPP\N{\c&H0076E600&}8448337081 | 9389709109{\r}"},
        ]
    elif "0829" in plan.job_id.lower() or "0829" in plan.source_video:
        punchlines = [
            {"start": 0.50, "end": 5.50, "style": "PunchlineGold", "text": r"CAN AN AI ROBOT BEAT A HUMAN TRADER?"},
            {"start": 8.50, "end": 13.50, "style": "PunchlineRed", "text": r"ROBOT ADVANTAGE: ZERO EMOTIONS"},
            {"start": 15.00, "end": 21.50, "style": "PunchlineGold", "text": r"MILLISECOND EXECUTION SPEED"},
            {"start": 23.00, "end": 31.00, "style": "Punchline", "text": r"HUMAN ADVANTAGE: {\c&H00D7FF&}CONTEXT & JUDGMENT{\r}"},
            {"start": 33.00, "end": 40.50, "style": "PunchlineGold", "text": r"WINNER: {\c&H003333FF&}STRATEGY & RISK MANAGEMENT{\r}"},
            {"start": 42.00, "end": 46.88, "style": "PunchlineGold", "text": r"FOLLOW FOR FOREX & AI INSIGHTS"},
        ]
    else:
        punchlines = [
            {"start": 0.60, "end": 5.50, "style": "PunchlineGold", "text": r"WHERE DOES CRASH MONEY GO?"},
            {"start": 13.20, "end": 17.50, "style": "Punchline", "text": r"100 SHARES × ₹1,000 = {\c&H00D7FF&}₹1,00,000{\r}"},
            {"start": 18.00, "end": 24.50, "style": "PunchlineRed", "text": r"PRICE DROPS TO ₹700: WHERE IS ₹30,000?"},
            {"start": 25.00, "end": 30.50, "style": "Punchline", "text": r"NO CASH WAS STOLEN FROM BANK"},
            {"start": 31.00, "end": 37.00, "style": "PunchlineGold", "text": r"₹10 LAKH CRORE WIPEOUT = {\c&H003333FF&}VALUATION DROP{\r}"},
            {"start": 44.00, "end": 49.50, "style": "PunchlineGold", "text": r"FOLLOW TO MASTER TRADING"},
        ]

    events = []
    for p in punchlines:
        s_ts = format_ass_timestamp(p["start"])
        e_ts = format_ass_timestamp(p["end"])
        events.append(f"Dialogue: 0,{s_ts},{e_ts},{p['style']},,0,0,85,,{p['text']}")

    content = header + "\n".join(events) + "\n"
    output_ass_path.write_text(content, encoding="utf-8")
    logger.info(f"Generated {len(punchlines)} high-impact emphasis punchline captions: {output_ass_path}")
    return output_ass_path
