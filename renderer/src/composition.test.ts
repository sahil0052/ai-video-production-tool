import { readFileSync } from "node:fs";

import { describe, expect, test } from "vitest";

import {
  calculateTechStoryMetadata,
  findSceneAtTime,
  getPresenterLayout,
  getReference0806V3PresenterTransform,
  getTimelineSegmentFrameRange,
} from "./Composition";
import { editPlanSchema } from "./schema";

const plan = editPlanSchema.parse({
  version: "1.0",
  profile: "tech-story-v1",
  source_filename: "source.mp4",
  source_url: "source.mp4",
  source_metadata: {
    width: 720,
    height: 1280,
    fps: 30,
    frame_count: 120,
    duration_seconds: 4,
  },
  output: { width: 1080, height: 1920, fps: 30 },
  duration_ms: 3500,
  style_variant: "tech-news",
  timeline: [
    {
      source_start_ms: 100,
      source_end_ms: 1700,
      output_start_ms: 0,
      output_end_ms: 1600,
    },
    {
      source_start_ms: 1900,
      source_end_ms: 3800,
      output_start_ms: 1600,
      output_end_ms: 3500,
    },
  ],
  caption_pages: [],
  scenes: [
    {
      id: "scene-1",
      start_ms: 0,
      end_ms: 1800,
      role: "hook",
      layout: "presenter",
      zoom: 1,
    },
    {
      id: "scene-2",
      start_ms: 1800,
      end_ms: 3500,
      role: "payoff",
      layout: "graphic",
      zoom: 1.12,
    },
  ],
  reframing: [],
  graphics: [],
  assets: [],
  audio: {
    integrated_lufs: -14.2,
    true_peak_dbtp: -1,
    music_bpm: 120,
    music_asset_id: null,
    music_duck_db: 6,
    sfx_asset_ids: [],
    sfx_cues: [],
  },
  qc_targets: {
    integrated_lufs: -14.2,
    loudness_tolerance: 0.5,
    true_peak_dbtp: -1,
    max_silence_ms: 120,
    max_black_frame_ratio: 0.001,
    max_freeze_frame_ratio: 0.08,
    min_cuts_per_minute: 30,
    max_cuts_per_minute: 75,
    min_median_shot_ms: 800,
    max_median_shot_ms: 1800,
    min_cut_onset_percent: 70,
    min_style_score: 80,
  },
});

describe("TechStory composition", () => {
  test("derives frame count and dimensions from EditPlanV1", async () => {
    const metadata = await calculateTechStoryMetadata({
      props: { plan },
      defaultProps: { plan },
      abortSignal: new AbortController().signal,
      compositionId: "TechStory",
      isRendering: true,
    });

    expect(metadata.durationInFrames).toBe(105);
    expect(metadata.width).toBe(1080);
    expect(metadata.height).toBe(1920);
    expect(metadata.fps).toBe(30);
  });

  test("selects the active visual scene", () => {
    expect(findSceneAtTime(plan.scenes, 1000)?.id).toBe("scene-1");
    expect(findSceneAtTime(plan.scenes, 2000)?.id).toBe("scene-2");
    expect(findSceneAtTime(plan.scenes, 4000)).toBeUndefined();
  });

  test("makes presenter visibility and framing scene-layout driven", () => {
    expect(getPresenterLayout("presenter")).toMatchObject({
      visible: true,
      top: 0,
      height: "100%",
      width: "100%",
    });
    expect(getPresenterLayout("graphic")).toMatchObject({
      visible: false,
    });
    expect(getPresenterLayout("split-screen")).toMatchObject({
      visible: true,
      top: "58%",
      height: "42%",
      width: "100%",
    });
    expect(getPresenterLayout("presenter-pip")).toMatchObject({
      visible: true,
      top: 1020,
      left: 650,
      width: 350,
      height: 620,
    });
  });

  test("uses a controlled final punch crop for the V3 clean ending", () => {
    expect(
      getReference0806V3PresenterTransform(
        "0806-v3-presenter-ending",
      ),
    ).toEqual({ scale: 1, translateY: 0 });
    expect(
      getReference0806V3PresenterTransform("0806-v3-clean-ending"),
    ).toEqual({ scale: 1.16, translateY: -26 });
  });

  test("validates EditPlanV1 before calculating render metadata", () => {
    const invalid = structuredClone(plan);
    invalid.timeline[1].output_start_ms += 1;
    invalid.timeline[1].output_end_ms += 1;
    invalid.duration_ms += 1;

    expect(() =>
      calculateTechStoryMetadata({
        props: { plan: invalid },
        defaultProps: { plan },
        abortSignal: new AbortController().signal,
        compositionId: "TechStory",
        isRendering: true,
      }),
    ).toThrow(/contiguous/i);
  });

  test("keeps trimmed timeline media populated across rounded cuts", () => {
    const first = getTimelineSegmentFrameRange(
      {
        source_start_ms: 33150,
        source_end_ms: 36410,
        output_start_ms: 25770,
        output_end_ms: 29030,
      },
      30,
    );
    const second = getTimelineSegmentFrameRange(
      {
        source_start_ms: 36690,
        source_end_ms: 39710,
        output_start_ms: 29030,
        output_end_ms: 32050,
      },
      30,
    );

    expect(first.from + first.durationInFrames).toBe(second.from);
    expect(first.trimAfter - first.trimBefore).toBeGreaterThanOrEqual(
      first.durationInFrames,
    );
    expect(second.trimAfter - second.trimBefore).toBeGreaterThanOrEqual(
      second.durationInFrames,
    );
  });
});

test("all presenter source video layers are muted for separate dialogue mixing", () => {
  const source = readFileSync(
    new URL("./Composition.tsx", import.meta.url),
    "utf8",
  );
  const presenterVideos = [
    ...source.matchAll(
      /<Video[\s\S]*?src=\{staticFile\(plan\.source_url\)\}[\s\S]*?\/>/g,
    ),
  ];

  expect(presenterVideos.length).toBeGreaterThan(0);
  for (const [block] of presenterVideos) {
    expect(block).toMatch(/\bmuted\b/);
  }
});
