# 0806 V8 Training-Parity Design

## Objective

Produce a separate `0806-production-v8-training-parity` edit that matches the
production grammar of training reference #10 more closely than V7. Preserve
V7 unchanged. Reference #4 remains limited to the risk-reversal beat.

## Evidence from the V7 parity audit

V7 passes broad pacing, color and loudness gates, but those gates hide visible
style mismatches:

- V7 local edge density is `0.1173`; reference #10 is `0.0733`. V7 frames
  contain too much tiny UI detail.
- V7 near-static non-cut frame-pair ratio is `0.0000`; reference #10 is
  `0.4102`. V7 moves almost every frame while #10 deliberately holds clean
  code, diagrams and source pages.
- V7 bright uniform blank P90 is `0.4935`; reference #10 is `0.4150`.
  Evidence layouts leave too much pale empty space.
- V7 dark uniform negative space is `0.1597`; reference #10 is `0.3609`.
  V7 dark frames are cluttered product screens instead of clean technical
  compositions.
- Only `64.36%` of V7 caption time uses the reference #10 monospace family.
  Evidence and CTA use visibly different type systems.
- Ten caption tokens extend outside their visible page window.
- V7 presenter coverage is near the previous `20%` ceiling, while reference
  #10 uses the presenter as shorter connective resets.
- The rendered V7 mixed-pulse estimate is `113.5 BPM`; reference #10 is
  approximately `90 BPM`.

## Editorial design

Keep the 41.4-second untouched narration and factual structure. Use 20-22
genuine cuts, but create density through role-specific internal events rather
than continuous camera movement.

### Visual allocation

- Presenter pixels: `12-16%`.
- Real MT5/product pixels: `34-42%`.
- Direct source evidence: `17-21%`.
- Deterministic explanation graphics: `20-27%`.
- Licensed tactile context: `6-10%`.
- Flow: exactly `0%`.

### Visual grammar changes

1. Retain the current split hook, but reduce its continuous drift.
2. Crop MetaEditor to one readable action or rule at a time. Remove toolbars,
   comments and unrelated code from the primary field of view.
3. Replace pale floating product cards with dark full-frame technical macros.
4. Shorten the first presenter reset to roughly 1.3 seconds; continue the
   explanation with code/action pixels.
5. Show official evidence as source page, source excerpt, highlighted sentence
   and source-number macro. Use raw captured pixels; no redesigned document
   cards.
6. Crop risk, attachment and Strategy Tester actions so the active control
   occupies at least 55% of the frame width.
7. Hold code/evidence/diagram frames still for meaningful intervals. Permit
   one restrained punch, tracked highlight or crop change per shot.
8. Use a tight presenter ending comparable to reference #10. Do not finish on
   a split-screen product panel.

## Caption design

- Use the reference #10 `technical-mono` family for every body, evidence,
  presenter and CTA caption. The serif hook remains separate.
- Keep 31-34 px Share Tech Mono, square near-black fitted boxes and hard
  replacement.
- Build page timing from the Deepgram Nova-2 English-India spoken-word
  timestamps, while retaining the approved English caption text.
- Every matched spoken window must be fully covered.
- Pages remain 350-1300 ms. A word longer than 1300 ms may use consecutive
  identical pages so the rendered caption remains visually continuous.
- Keep phrases to one to three words normally, four only for an inseparable
  phrase.
- Target 70-74% visible caption coverage.

## Audio design

- Replace the current Cyberpunk City bed with the licensed Feedback Dreams
  candidate, processed as an uninterrupted 87-92 BPM documentary-tech bed.
- Keep music psychologically behind speech, with the existing 5.5 dB speech
  duck and approximately -28 dB base gain.
- Retain no more than ten semantic effects, but retime them to the revised
  cuts and visible actions.
- Target a rendered mixed-pulse estimate of 84-100 BPM, approximately
  -14.2 LUFS, no peak above -1 dBTP and 2.3-3.5 LU LRA.

## New parity gates

In addition to existing technical checks:

- local edge density: `0.060-0.090`;
- near-static non-cut frame-pair ratio: `0.25-0.50`;
- bright uniform blank P90: no more than `0.43`;
- dark uniform negative-space mean: at least `0.28`;
- presenter pixel ratio: `0.12-0.16`;
- technical-mono share of caption time: at least `0.96`;
- zero token/page containment violations;
- mixed-pulse estimate: `84-100 BPM`;
- evidence source content fills at least 75% of the usable frame;
- no product action whose active control is unreadable at phone size.

## Verification

Generate a role-matched comparison for hook, code action, rule diagram,
evidence overview, evidence macro, risk input, product action and ending.
Inspect every rendered frame, the full mix, caption page timing and source
provenance. Automation may advance only to `awaiting-final-approval`.
