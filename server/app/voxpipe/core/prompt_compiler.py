from __future__ import annotations

import random
from typing import Literal, Optional

StyleBlockKey = Literal["flat_parallax", "deep_diorama", "locked_stage"]

STYLE_BLOCKS = {
    "flat_parallax": (
        "Use the attached style sheet as the strict visual system — match its aged-newsprint collage surface, "
        "desaturated archival palette with one hot accent, condensed headline caps with giant stat numbers, "
        "halftone black-and-white cutout people with rough white keylines and offset accent strokes, and its print-grain finish. "
        "Do NOT copy the sheet's layout; it defines the language, not the composition. "
        "Layers sit at distinct depths like a paper diorama — true parallax, never glossy 3D. "
        "Backgrounds are muted archival fields, varying per clip within this palette. "
        "ALERT WASH means the whole frame floods toward the hot accent tone. "
        "Motion: spring pop-ups with overshoot, staggered entrances, ticking counters, underline swipes; one slow camera move per clip. "
        "Audio: sound design only — paper pops, thwips, stamps, ticks, low newsroom hum. No music. No voice-over."
    ),
    "deep_diorama": (
        "Use the attached style sheet for materials only — aged-print collage textures, "
        "halftone black-and-white cutout people with rough keylines and offset accent strokes, giant stat numbers, print grain. "
        "Do NOT copy the sheet's layout or its flatness: every clip is a deep 3D paper diorama — "
        "cutouts are physical layers separated in real space, strong shallow depth of field, foreground elements crossing close to the lens. "
        "The camera is an actor: it flies between layers, orbits, dives, whips, racks focus — one committed cinematic move per clip. "
        "Backgrounds change per clip, always within the sheet's palette. "
        "ALERT WASH means the entire frame floods to the hot accent tone in one beat. "
        "Motion: springs with overshoot, staggered entrances, ticking counters. "
        "Audio: sound design only — paper pops, whooshes, stamps, ticks. No music. No voice-over."
    ),
    "locked_stage": (
        "Documentary cutout-collage stage: a locked, muted archival map/texture background that never changes. "
        "Midground: black-and-white halftone cutouts with a rough white keyline and an offset red marker stroke behind each. "
        "Foreground: structures, props, and big stat numbers in full color. Condensed bold headline caps; numbers rendered huge, as characters. "
        "Desaturated palette plus one hot red accent, secondary mustard. "
        "Spring pop-ups with slight overshoot, staggered entrances, counters ticking up, red underline swipes. "
        "Camera: subtle slow drift only, never cuts."
    ),
}

AVOID_BLOCKS = {
    "flat_parallax": (
        "AVOID: no glossy CG 3D, no lens flares, no camera cuts within the clip, "
        "no full-color midground portraits (people stay halftone black-and-white), "
        "no warped or gibberish text, no invented logos, no watermarks, no simultaneous entrances, "
        "no music, no soundtrack, no voice-over, no narration, no lyrics, no UI or glass elements"
    ),
    "deep_diorama": (
        "AVOID: no flat single-plane composition, no static locked-off camera, "
        "no glossy plastic CG (depth stays papercraft), no full-color midground portraits (people stay halftone black-and-white), "
        "no warped or gibberish text, no invented logos, no watermarks, "
        "no music, no soundtrack, no voice-over, no narration, no lyrics, no UI or glass elements"
    ),
    "locked_stage": (
        "AVOID: no glossy CG 3D, no lens flares, no camera cuts within the clip, "
        "no full-color midground portraits (people stay halftone black-and-white), "
        "no warped or gibberish text, no invented logos, no watermarks, "
        "no music, no soundtrack, no voice-over, no narration, no lyrics"
    ),
}

BACKGROUND_SLOTS = [
    "a faded world map tilted in perspective, far out of focus",
    "a torn 1920s banking ledger page with columns of inked accounts at depth",
    "stacked newspaper headline pages receding in deep perspective",
    "an aged blueprint grid with architectural schematics and circuit traces",
    "a sepia financial chart engraving with etched grid lines and depth falloff",
]

CAMERA_MOVES = [
    ("Camera orbits a quarter turn, focus racking front to back.", "AUDIO: paper pops, whip whoosh, low newsroom hum"),
    ("Camera dives low between physical paper cutout layers with shallow depth of field.", "AUDIO: submerge whoosh, deep pressure thud, paper thwip"),
    ("Camera pushes in steadily through a torn paper opening onto the central figure.", "AUDIO: paper tear, friction slide, low hum"),
    ("Camera performs a fast lateral track then hard stops with elastic overshoot.", "AUDIO: track rumble, stall click, paper pop"),
    ("Camera cranes up slowly over the layered stack while racking focus.", "AUDIO: riser whoosh, stamp thud, low newsroom hum"),
]


def compile_cl3_prompt(
    topic: str,
    concept_summary: str,
    style_key: StyleBlockKey = "deep_diorama",
    custom_camera_idx: Optional[int] = None,
) -> dict[str, str]:
    """Compiles a rigorous CL3 Vox prompt obeying STYLE BLOCK -> SHOT -> AUDIO -> AVOID."""
    style_block = STYLE_BLOCKS[style_key]
    avoid_block = AVOID_BLOCKS[style_key]
    bg = random.choice(BACKGROUND_SLOTS)

    if custom_camera_idx is not None:
        cam_move, audio_line = CAMERA_MOVES[custom_camera_idx % len(CAMERA_MOVES)]
    else:
        cam_move, audio_line = random.choice(CAMERA_MOVES)

    shot_body = (
        f"Background: {bg}. "
        f"FG: authentic paper collage cutouts representing {concept_summary} snap in at three distinct depth planes with rough white keylines and offset red marker strokes. "
        f"Connective elements activate as red ink marker arrows draw connections and giant stat numbers stamp down. "
        f"{cam_move} Settle on {topic} in sharp focus."
    )

    full_video_prompt = (
        f"{style_block}\n\n"
        f"SHOT: {shot_body}\n\n"
        f"{audio_line} — sound design only, no music, no narration.\n\n"
        f"{avoid_block}"
    )

    image_plate_prompt = (
        f"Authentic Vox and Johnny Harris style deep paper collage diorama of {topic}: {concept_summary}. "
        f"Background: {bg}. Foreground: layered halftone black-and-white cutout figures with rough white keylines, "
        f"aged vintage paper textures, giant typography stamps, offset red marker accents, 8k resolution, cinematic lighting."
    )

    return {
        "full_video_prompt": full_video_prompt,
        "shot_body": shot_body,
        "image_plate_prompt": image_plate_prompt,
    }
