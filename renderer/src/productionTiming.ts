export type TransformValue = {
  at_ms: number;
  x: number;
  y: number;
  scale: number;
  rotate_deg: number;
};

export const interpolateLayerKeyframes = (
  keyframes: TransformValue[],
  timeMs: number,
) => {
  const ordered = [...keyframes].sort((a, b) => a.at_ms - b.at_ms);
  if (timeMs <= ordered[0].at_ms) {
    return {
      x: ordered[0].x,
      y: ordered[0].y,
      scale: ordered[0].scale,
      rotate_deg: ordered[0].rotate_deg,
    };
  }
  const last = ordered[ordered.length - 1];
  if (timeMs >= last.at_ms) {
    return {
      x: last.x,
      y: last.y,
      scale: last.scale,
      rotate_deg: last.rotate_deg,
    };
  }
  const upperIndex = ordered.findIndex(
    (keyframe) => keyframe.at_ms >= timeMs,
  );
  const lower = ordered[upperIndex - 1];
  const upper = ordered[upperIndex];
  const progress =
    (timeMs - lower.at_ms) / (upper.at_ms - lower.at_ms);
  const lerp = (from: number, to: number) =>
    from + (to - from) * progress;
  return {
    x: lerp(lower.x, upper.x),
    y: lerp(lower.y, upper.y),
    scale: lerp(lower.scale, upper.scale),
    rotate_deg: lerp(lower.rotate_deg, upper.rotate_deg),
  };
};
