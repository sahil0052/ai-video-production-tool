import { spring, type SpringConfig } from "remotion";

/**
 * Shared spring tuning used across every "semantic" motion event in this
 * module. Snappy but not bouncy: emphasis punches should feel like a real
 * camera operator's push-in, not a cartoon bounce.
 */
export const PUNCH_SPRING_CONFIG: SpringConfig = {
  mass: 0.6,
  damping: 14,
  stiffness: 210,
  overshootClamping: false,
};

export const DIVIDER_MORPH_SPRING_CONFIG: SpringConfig = {
  mass: 0.9,
  damping: 18,
  stiffness: 120,
  overshootClamping: false,
};

/** J-cut / L-cut lead time: audio (SFX or the next line's dialogue level)
 * should be perceptible before the matching visual cut lands. */
export const J_CUT_LEAD_MS = 150;

/**
 * Given a hard visual cut timestamp, return the timestamp at which the
 * associated audio cue (whoosh, dialogue emphasis, stinger) should start,
 * so the audio leads the picture by J_CUT_LEAD_MS. Clamped to timeline
 * start.
 */
export const jCutAudioStartMs = (visualCutMs: number, leadMs: number = J_CUT_LEAD_MS) =>
  Math.max(0, visualCutMs - leadMs);

/**
 * Given a hard visual cut timestamp, return the timestamp at which the
 * outgoing shot's audio should trail off (L-cut): the previous line keeps
 * playing briefly under the new picture instead of cutting dead.
 */
export const lCutAudioEndMs = (visualCutMs: number, trailMs: number = J_CUT_LEAD_MS) =>
  visualCutMs + trailMs;

export type PunchWindow = {
  /** ms timestamp the emphasis word or pause boundary lands at */
  triggerMs: number;
  /** base scale before the punch, almost always 1.0 */
  fromScale?: number;
  /** peak scale at the punch, per the brief: 1.0 -> 1.12x */
  toScale?: number;
  /** how long the punch holds before easing back, in ms */
  holdMs?: number;
};

/**
 * Speech-coupled punch-in: scales from `fromScale` to `toScale` on a
 * spring anchored at `triggerMs` (an emphasis word start or a detected
 * pause boundary from word_timestamps.json), then eases back to
 * `fromScale` after `holdMs`. Two independent springs (in and out) so the
 * release doesn't fight the attack.
 */
export const punchInScale = (
  timeMs: number,
  fps: number,
  window: PunchWindow,
) => {
  const fromScale = window.fromScale ?? 1;
  const toScale = window.toScale ?? 1.12;
  const holdMs = window.holdMs ?? 260;
  const attackFrame = (timeMs - window.triggerMs) / 1000 * fps;
  const releaseStartMs = window.triggerMs + holdMs;
  const releaseFrame = (timeMs - releaseStartMs) / 1000 * fps;

  if (timeMs < window.triggerMs) {
    return fromScale;
  }

  if (timeMs < releaseStartMs) {
    return spring({
      frame: attackFrame,
      fps,
      config: PUNCH_SPRING_CONFIG,
      from: fromScale,
      to: toScale,
    });
  }

  return spring({
    frame: releaseFrame,
    fps,
    config: PUNCH_SPRING_CONFIG,
    from: toScale,
    to: fromScale,
  });
};

/**
 * Resolves the active punch window (if any) for a list of trigger
 * timestamps, so a layer only needs to pass its emphasis-word/pause-
 * boundary list once and get back a single scale multiplier per frame.
 */
export const activePunchScale = (
  timeMs: number,
  fps: number,
  triggers: number[],
  options?: Omit<PunchWindow, "triggerMs">,
) => {
  const holdMs = options?.holdMs ?? 260;
  const activeTrigger = [...triggers]
    .sort((a, b) => a - b)
    .filter((triggerMs) => timeMs >= triggerMs && timeMs < triggerMs + holdMs + 400)
    .pop();

  if (activeTrigger === undefined) {
    return options?.fromScale ?? 1;
  }

  return punchInScale(timeMs, fps, { ...options, triggerMs: activeTrigger });
};

export type DividerMorphState = {
  /** 0 = full split-screen (each pane 960px tall on a 1920 canvas),
   *  1 = fully morphed to a single 1920px pane. */
  progress: number;
  /** current top pane height in px, per the brief's 960 -> 1920 morph */
  topPaneHeightPx: number;
  /** current divider glow intensity, 0-1, used to drive drop-shadow blur/opacity */
  glowIntensity: number;
};

/**
 * Morphing split-screen divider: instead of a hard cut between split and
 * full-frame layouts, the top pane's height springs from 960px to 1920px
 * (or back). `edgeMs` controls how many ms before/after `cutMs` the morph
 * spans, so it always resolves before the next caption page starts.
 */
export const dividerMorphState = (
  timeMs: number,
  fps: number,
  cutMs: number,
  direction: "split-to-full" | "full-to-split",
  edgeMs: number = 380,
): DividerMorphState => {
  const localFrame = ((timeMs - (cutMs - edgeMs / 2)) / 1000) * fps;
  const fromHeight = direction === "split-to-full" ? 960 : 1920;
  const toHeight = direction === "split-to-full" ? 1920 : 960;

  const heightPx = spring({
    frame: localFrame,
    fps,
    config: DIVIDER_MORPH_SPRING_CONFIG,
    from: fromHeight,
    to: toHeight,
  });

  const progress =
    direction === "split-to-full"
      ? (heightPx - 960) / (1920 - 960)
      : (1920 - heightPx) / (1920 - 960);

  // Glow peaks mid-morph, not at rest, so the gold divider sheens as it moves.
  const glowIntensity = 1 - Math.abs(progress - 0.5) * 2;

  return {
    progress: Math.max(0, Math.min(1, progress)),
    topPaneHeightPx: heightPx,
    glowIntensity: Math.max(0, Math.min(1, glowIntensity)),
  };
};

/**
 * Auto-centered headroom stabilization: given a detected face/head
 * bounding-box top-Y within a split pane, return a vertical crop offset
 * that keeps at least `minHeadroomPx` of clearance above the head,
 * without cropping below the pane's own bounds.
 */
export const headroomStabilizedOffsetPx = (
  paneHeightPx: number,
  detectedHeadTopPx: number,
  minHeadroomPx: number = 120,
) => {
  const currentHeadroom = detectedHeadTopPx;
  if (currentHeadroom >= minHeadroomPx) {
    return 0;
  }
  const deficit = minHeadroomPx - currentHeadroom;
  return Math.min(deficit, paneHeightPx * 0.25);
};

export type MatchCutMomentum = {
  translateXPx: number;
  translateYPx: number;
};

/**
 * Directional match-cut continuity: the outgoing shot exits and the
 * incoming shot enters along the same vector, so motion reads as
 * continuous rather than as two independent animations meeting at a cut.
 */
export const matchCutMomentum = (
  progress: number,
  direction: "left" | "right" | "up" | "down",
  distancePx: number = 60,
): MatchCutMomentum => {
  const clamped = Math.max(0, Math.min(1, progress));
  const eased = clamped * clamped * (3 - 2 * clamped); // smoothstep
  const remaining = (1 - eased) * distancePx;

  switch (direction) {
    case "left":
      return { translateXPx: remaining, translateYPx: 0 };
    case "right":
      return { translateXPx: -remaining, translateYPx: 0 };
    case "up":
      return { translateXPx: 0, translateYPx: remaining };
    case "down":
      return { translateXPx: 0, translateYPx: -remaining };
  }
};
