# 0813 Semantic Visual Rebuild Design

## Goal

Rebuild all three 0813 edits so the presenter appears for explanation,
interpretation, judgment, warnings, lessons, and CTA, while unique moving
visuals appear only for literal actions, product demonstrations, or factual
evidence.

V6 remains unchanged. V7 renders to:

- `storage/deliverables/0813-production-v7-semantic-visuals`
- `storage/deliverables/0813-production-v7-semantic-visuals-take-2`
- `storage/deliverables/0813-production-v7-semantic-visuals-take-3`

## Audit Basis

The approved human reference keeps the presenter visible for approximately
66.4% of its timeline and never leaves the presenter absent for more than
3.8 seconds. V6 keeps the presenter visible for only 44–45% and reuses
non-presenter sources for 22–40% of each reel.

The existing release gates encode the wrong target: 38–42% presenter pixels,
20–25 shots, and up to 7.5 seconds without the presenter. They validate that
media is real but do not validate that it explains the spoken sentence.

## Editorial Allocation Rules

Every narration beat receives one visual job:

- `presenter-explanation`: definitions, interpretation, causal reasoning,
  warnings, conclusions, and CTA.
- `literal-action`: a unique moving clip that directly depicts the spoken
  noun or action.
- `real-product`: one readable software action with a visible state change.
- `direct-evidence`: genuine source pixels for exact factual values.
- `presenter-supported`: presenter remains visible while a small supporting
  visual or deterministic overlay clarifies the sentence.

Full-frame B-roll is forbidden for abstract statements when it does not
literally depict the claim. A non-presenter asset may occur only once across
the complete three-video set. Presenter footage may repeat because it is the
narrative anchor.

## Locked Targets

- 14–17 meaningful shots per video.
- Presenter pixel coverage: 58–68%.
- Maximum presenter-free run: 3.8 seconds.
- No more than two consecutive full-frame non-presenter shots.
- Zero repeated non-presenter asset IDs within or across the three edits.
- At least six semantic visual jobs per video.
- Exact V6 Roman-Hinglish captions remain unchanged.
- Original 48 kHz narration, 10 ms alignment, music ducking, and clean-voice
  policy remain unchanged.

## Story Direction

### PPI

Use tea preparation, producer action, checkout, one factory action, official
BLS evidence, distinct goods and services footage, and one market reaction
clip. Put the presenter on definitions, zero interpretation, opposite
directions, risk controls, the robot-versus-market lesson, and CTA. Remove all
repeated tablet-production footage.

### Backtest

Use a short cricket hook, one Strategy Tester action, one code-rule action,
one live-execution context clip, one student analogy clip, and one forward
test action. Put the presenter on the practice-match definition, historical
rules, testing assumptions, live-market friction, overfitting, risk, lesson,
and CTA.

### Lot Size

Use one risk-input hook, real pizza footage, real pizza-box quantity footage,
one alternate lot-size screen, one market-move context clip, one code-rule
action, and one final EA/product action. Put the presenter on quantity,
small-versus-large impact, profit/loss, stop distance, actual risk, wrong
settings, lesson, and CTA. Remove the fireplace clip.

## Verification

The release report must include:

- exact caption-source coverage;
- presenter pixel coverage and longest presenter-free run;
- non-presenter asset uniqueness within and across all three videos;
- semantic-role validation for every shot;
- perceptual duplicate-frame scan;
- encoded audio alignment, ASR retention, loudness, and true peak;
- full shot and caption contact sheets.

Automation may pass only when every gate succeeds. Human approval remains
separate.
