import type { ReframeKeyframe } from "./schema";

export const millisecondsToFrames = (milliseconds: number, fps: number) =>
  Math.round((milliseconds / 1000) * fps);

export const activeCaptionTokenIndex = (
  tokens: Array<{ start_ms: number; end_ms: number }>,
  timeMs: number,
) =>
  tokens.findIndex(
    (token) => token.start_ms <= timeMs && token.end_ms > timeMs,
  );

export const interpolateReframe = (
  keyframes: ReframeKeyframe[],
  timeMs: number,
): ReframeKeyframe => {
  if (keyframes.length === 0) {
    return { time_ms: timeMs, x: 0.5, y: 0.42, scale: 1.12 };
  }
  if (timeMs <= keyframes[0].time_ms) {
    return { ...keyframes[0], time_ms: timeMs };
  }
  const last = keyframes[keyframes.length - 1];
  if (timeMs >= last.time_ms) {
    return { ...last, time_ms: timeMs };
  }
  const rightIndex = keyframes.findIndex(
    (keyframe) => keyframe.time_ms >= timeMs,
  );
  const left = keyframes[rightIndex - 1];
  const right = keyframes[rightIndex];
  const duration = Math.max(1, right.time_ms - left.time_ms);
  const progress = (timeMs - left.time_ms) / duration;
  const mix = (from: number, to: number) => from + (to - from) * progress;
  return {
    time_ms: timeMs,
    x: mix(left.x, right.x),
    y: mix(left.y, right.y),
    scale: mix(left.scale, right.scale),
  };
};
