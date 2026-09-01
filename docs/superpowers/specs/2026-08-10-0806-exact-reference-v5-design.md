# 0806 Exact Reference V5 Design

## Goal

Rebuild `0806.mp4` to match the user-provided
`Trading_Reel 02(06-08-26).mp4` rather than the earlier training-reference
blend. Preserve the reference and V4 as read-only comparison inputs.

## Audit findings

- Reference duration: 34.93 seconds; V4 duration: 41.40 seconds.
- Reference cuts: 12; V4 cuts: 23.
- Reference median shot: 2.67 seconds; V4: 1.60 seconds.
- The reference keeps the presenter visible for about 72% of the runtime.
- It uses only three sparse typography sequences:
  `Forex Trading / ROBOT`, `Expert Adviser / EA`, and
  `An Expert Adviser / $1,10,000`.
- It uses four contextual/evidence sections: trading robot, 2008
  championship card, trader at screens, and dark risk shot.
- Emotional explanation is carried by punch crops, monochrome treatment and
  one warm flash, not UI demonstrations or explanatory diagrams.
- The reference narration maps to the raw source at an average 1.20x speed,
  with take-specific rates and pause compression.
- The reference audio measures about -13.26 LUFS and -0.03 dBTP. That is
  stylistically dense but has insufficient true-peak headroom.

## Chosen approach

Use a golden reconstruction, not a renamed copy:

1. Conform the original presenter footage to the reference's six source-take
   timing blocks.
2. Recreate punch crops and slow digital pushes from measured face geometry.
3. Derive the three typography treatments from reference pixels, retaining
   exact glyph geometry, color and placement while rebuilding their shadows
   and entrance motion deterministically.
4. Use the user-provided reference's clean B-roll/evidence/effect sections
   where exact source provenance is otherwise unknowable. Record them as
   `user-provided-reference` assets, never as training footage.
5. Use the reference audio as the exact comparison mix. Also create a
   posting-safe copy normalized with at least 1 dB true-peak headroom.
6. Compare every rendered frame against the supplied reference and require
   matching duration, cuts, pacing, color ranges, audio alignment and
   narrative keyframes.

## Locked timeline

| Time | Treatment |
|---|---|
| 0.000-2.267 | Raw presenter hook; two-line white/yellow headline. |
| 2.267-5.733 | User-provided robot/trading contextual clip. |
| 5.733-9.533 | Raw presenter; slow push; white `Expert Adviser`, then green `EA`. |
| 9.533-11.767 | Raw presenter 1.20x punch crop for the wrong-rule question. |
| 11.767-14.433 | User-provided 2008 Championship evidence animation. |
| 14.433-18.167 | Raw presenter; white/green verified-number emphasis. |
| 18.167-19.700 | Raw presenter close crop for risk reversal. |
| 19.700-22.633 | User-provided monochrome presenter reversal. |
| 22.633-23.667 | User-provided warm lesson flash/reset. |
| 23.667-25.667 | User-provided trader/emotion context. |
| 25.667-27.400 | User-provided dark risk context. |
| 27.400-30.433 | Raw presenter CTA with restrained push. |
| 30.433-34.933 | Raw presenter clean ending. |

## Acceptance

- 1080x1920, 30 FPS, 34.93 seconds.
- Twelve detected hard cuts and roughly 2.67-second median shots.
- No continuous subtitles, evidence cards, MetaTrader UI or diagrams.
- Exact typography wording, geometry and accent colors.
- Frame comparison at all narrative anchors plus every-frame aggregate
  similarity.
- Reference audio comparison output and a separate posting-safe output.
- V4 remains untouched.

