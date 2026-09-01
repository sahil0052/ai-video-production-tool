# 0809 Visual Upgrade V2 Design

## Objective

Create a stronger visual revision of the accepted 0809 edit without changing
the narration, factual claims, evidence, timing, or V1 deliverable.

Output:

`storage/deliverables/0809-production-v2-visual-upgrade`

V1 remains read-only at:

`storage/deliverables/0809-production-v1-reference-style`

## Audit Findings

V1 passes every technical gate, but its visuals still underperform the supplied
`Trading_Reel 02(06-08-26).mp4` reference in six areas:

1. The 0-2.2 second hook is a static presenter headline instead of a designed
   reveal with an internal visual reset.
2. Generic stock footage carries the software-update, chart, and server beats.
3. Evidence pages are factual and readable but mostly static; the reference
   uses overview-to-detail visual progression.
4. The same forex-screen asset appears twice.
5. The 34.9-42.5 second lesson section holds presenter-plus-overlay treatments
   too long and lacks cinematic escalation.
6. The CTA card remains on screen for more than five seconds and feels like a
   template rather than an edited ending.

## Chosen Direction

Use a reference-faithful cinematic/evidence hybrid:

- Preserve the presenter as the emotional anchor.
- Keep SEC source pixels as the factual anchor.
- Replace three generic context shots with short Google Flow illustrative
  plates.
- Build all exact text, numbers, diagrams, highlights, and brand controls as
  deterministic graphics.
- Increase internal visual progression without adding noisy transitions.
- Preserve the verified V1 audio master and its zero-delay remaster path.

No training footage or reference audio will be reused.

## Shot Upgrade Map

| Time | V2 treatment |
|---|---|
| 0.00-0.75 | Clean presenter punch crop with date line. |
| 0.75-1.45 | Abstract order-lane graphic, verified `4 MILLION` callout. |
| 1.45-2.20 | Presenter return with the complete hook headline. |
| 2.20-4.50 | Existing licensed trader footage with a tighter crop and moving market-open accent. |
| 4.50-6.80 | Presenter with animated scale counter and two-step text reveal. |
| 6.80-9.50 | Loss sequence split into chart context, `$460 MILLION`, then a brief clean hold. |
| 9.50-11.00 | High-contrast presenter reset. |
| 11.00-12.80 | Flow plate: physical software module entering a precision system. |
| 12.80-14.80 | Licensed code macro with deterministic `NORMAL UPDATE / BIG LOSS?` overlay. |
| 14.80-15.55 | SEC overview card. |
| 15.55-16.70 | Tight SEC excerpt with highlighted `4 million` and `$460 million` source lines. |
| 16.70-18.60 | Flow plate: server-rack propagation with one silent dark branch. |
| 18.60-20.30 | Animated deterministic eight-server diagram; seven update, one misses. |
| 20.30-21.15 | SEC email excerpt. |
| 21.15-22.00 | Source-backed `97` email callout over the excerpt. |
| 22.00-23.80 | Presenter plus three compact alert rows. |
| 23.80-25.60 | Clean presenter lesson reset. |
| 25.60-27.50 | New deterministic incident-to-forex bridge; remove repeated chart footage. |
| 27.50-28.35 | SEC deployment overview. |
| 28.35-29.25 | Tight source excerpt with deployment line highlighted. |
| 29.25-30.10 | Deterministic `45 MINUTES` repeated-error timeline. |
| 30.10-32.10 | Presenter verification failure beat. |
| 32.10-33.60 | SEC controls excerpt. |
| 33.60-34.90 | Presenter emergency-stop beat. |
| 34.90-38.30 | Three separate Profit Bricks control cards: order limits, controlled automation, equity protection. |
| 38.30-39.80 | Presenter: `RISK IS NOT ZERO`. |
| 39.80-41.80 | Flow plate: unstable energy contained by a precision safety mechanism. |
| 41.80-42.50 | Presenter: `REPEATED DAMAGE LIMITED`. |
| 42.50-45.20 | Clean presenter CTA setup with compact `FREE LIVE DEMO`. |
| 45.20-47.20 | Brief three-control recap card. |
| 47.20-50.20 | Smaller CTA card with brighter brand mark and `DETAILS IN DM`. |
| 50.20-50.833 | Clean presenter ending with no card. |

## Flow Design

Use one dedicated Flow project and three sequential `veo-lite` portrait I2V
operations. Existing user authorization covers the paid operations.

### Plate 1: software update mechanism

- Duration used: 1.8 seconds.
- Visual: a clean precision module physically locks into a graphite system.
- Palette: graphite, cool cyan, restrained amber.
- Forbidden: text, code, UI, charts, numbers, documents, logos.

### Plate 2: server propagation

- Duration used: 1.9 seconds.
- Visual: a pulse travels through a server corridor while one side path remains
  dark.
- The exact eight-server fact remains in the following deterministic graphic.
- Forbidden: readable indicators, numbers, dashboards, text, logos.

### Plate 3: risk containment

- Duration used: 2.0 seconds.
- Visual: an unstable red energy load is caught and stabilized by a mechanical
  safety ring.
- Forbidden: charts, percentages, balances, UI, text, logos.

Every candidate must pass the existing technical gates, score at least 24/30,
have no category below three, and use an accepted 700-2200 ms window.

## Visual Language

- Base palette: off-white, near-black, cool gray.
- Hook/scale accent: warm yellow.
- Technical/system accent: cyan.
- Risk/failure accent: restrained red.
- Brand accent: existing Profit Bricks violet with higher contrast.
- Hard cuts dominate.
- Motion comes from subject movement, punch crops, masked evidence highlights,
  and short deterministic card entrances.
- No persistent HUD, progress bar, grain wash, glitch, shake, or decorative
  particles.

## Evidence Policy

- Reuse the verified SEC captures and evidence records from V1.
- Exact numbers remain attached to SEC evidence identifiers.
- Flow never depicts evidence or exact facts.
- The eight-server diagram and timeline remain deterministic and visibly
  labelled `ILLUSTRATIVE`.
- Profit Bricks controls use the user-provided brand asset and existing
  user-approved control language.

## Acceptance Targets

- 24-30 genuine visual cuts.
- Median shot length: 1.5-2.4 seconds.
- Motion score: 4.0-6.5.
- Real/direct source pixels: at least 55%.
- Flow coverage: 8-14%, never above 22%.
- Direct evidence: 15-20%.
- Deterministic graphics: at most 25%.
- No repeated source for more than two consecutive shots.
- No static primitive held longer than 2.5 seconds.
- 1080x1920 H.264/AAC, 30 fps, yuv420p.
- Audio delay at or below 20 ms.
- Loudness near -14.2 LUFS and true peak at or below -1 dBTP.
- Content-token retention at least 99% with every protected term present.
- Automation may advance only to `awaiting-final-approval`.

