import { describe, expect, test } from "vitest";

import {
  activeCaptionTokenIndex,
  interpolateReframe,
  millisecondsToFrames,
} from "./timing";

describe("renderer timing", () => {
  test("converts milliseconds to deterministic frame boundaries", () => {
    expect(millisecondsToFrames(500, 30)).toBe(15);
    expect(millisecondsToFrames(1000, 60)).toBe(60);
  });

  test("finds the active spoken token", () => {
    const tokens = [
      { start_ms: 0, end_ms: 250 },
      { start_ms: 250, end_ms: 500 },
    ];

    expect(activeCaptionTokenIndex(tokens, 249)).toBe(0);
    expect(activeCaptionTokenIndex(tokens, 250)).toBe(1);
    expect(activeCaptionTokenIndex(tokens, 700)).toBe(-1);
  });

  test("smoothly interpolates face tracking keyframes", () => {
    const result = interpolateReframe(
      [
        { time_ms: 0, x: 0.4, y: 0.4, scale: 1.0 },
        { time_ms: 1000, x: 0.6, y: 0.5, scale: 1.2 },
      ],
      500,
    );

    expect(result.x).toBeCloseTo(0.5);
    expect(result.y).toBeCloseTo(0.45);
    expect(result.scale).toBeCloseTo(1.1);
  });
});
