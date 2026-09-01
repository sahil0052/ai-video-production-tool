import { readFileSync } from "node:fs";

import { describe, expect, test } from "vitest";

import {
  calculateProductionMetadata,
  interpolateLayerKeyframes,
} from "./ProductionComposition";
import { productionEditPlanSchema } from "./productionSchema";

const plan = productionEditPlanSchema.parse({
  version: "2.0",
  profile: "production-tech-story-v4",
  source_filename: "source.mp4",
  source_metadata: {
    width: 1080,
    height: 1920,
    fps: 30,
    frame_count: 90,
    duration_seconds: 3,
  },
  output: { width: 1080, height: 1920, fps: 30 },
  duration_ms: 3000,
  assets: [
    {
      id: "presenter",
      kind: "video",
      path: "assets/presenter.mp4",
      keywords: [],
      provenance: "user-provided",
      license: null,
      provider: null,
      remote_id: null,
      creator: null,
      source_url: null,
      license_url: null,
      search_query: null,
      start_ms: null,
      end_ms: null,
    },
  ],
  visual_layers: [
    {
      id: "presenter-layer",
      shot_id: "shot-01",
      start_ms: 0,
      end_ms: 3000,
      source_role: "presenter",
      kind: "video",
      asset_id: "presenter",
      source_start_ms: 0,
      source_end_ms: 3000,
      bounds: { x: 0, y: 0, width: 1080, height: 1920 },
      crop: { x: 0, y: 0, width: 1, height: 1 },
      fit: "cover",
      transform_keyframes: [
        { at_ms: 0, x: 0, y: 0, scale: 1, rotate_deg: 0 },
        { at_ms: 3000, x: 30, y: -10, scale: 1.1, rotate_deg: 0 },
      ],
      opacity_keyframes: [{ at_ms: 0, value: 1 }],
      blend_mode: "normal",
      z_index: 10,
      muted: true,
      loop: false,
      playback_rate: 1,
      illustrative_label: false,
      border_radius: 0,
      color_filter: null,
      reference_role: "primary-10",
    },
  ],
  caption_pages: [],
  audio: {
    integrated_lufs: -14.2,
    true_peak_dbtp: -1,
    music_bpm: 120,
    dialogue_asset_id: null,
    dialogue_offset_ms: 0,
    music_asset_id: null,
    music_duck_db: 6,
    music_base_gain_db: -20,
    music_gain_automation: [],
    speech_protection_windows: [],
    sfx_asset_ids: [],
    sfx_cues: [],
  },
});

describe("ProductionTechStoryV4", () => {
  test("derives composition metadata from EditPlanV2", async () => {
    const metadata = await calculateProductionMetadata({
      props: { plan },
      defaultProps: { plan },
      abortSignal: new AbortController().signal,
      compositionId: "ProductionTechStoryV4",
      isRendering: true,
    });

    expect(metadata.durationInFrames).toBe(90);
    expect(metadata.width).toBe(1080);
    expect(metadata.height).toBe(1920);
  });

  test("interpolates deterministic layer transforms", () => {
    expect(
      interpolateLayerKeyframes(
        plan.visual_layers[0].transform_keyframes,
        1500,
      ),
    ).toEqual({
      x: 15,
      y: -5,
      scale: 1.05,
      rotate_deg: 0,
    });
  });

  test("does not loop media or add global fake-motion textures", () => {
    const source = readFileSync(
      new URL("./ProductionComposition.tsx", import.meta.url),
      "utf8",
    );

    expect(source).not.toContain("<Loop");
    expect(source).not.toContain("repeating-linear-gradient");
    expect(source).not.toContain("backgroundPosition");
    expect(source).toContain("ProductionVisualLayer");
  });

  test("keeps deterministic overlays transparent and applies video cover through the media prop", () => {
    const source = readFileSync(
      new URL("./components/ProductionVisualLayer.tsx", import.meta.url),
      "utf8",
    );

    expect(source).toContain(
      'layer.source_role === "deterministic-graphic"',
    );
    expect(source).toContain('layer.source_role === "direct-evidence"');
    expect(source).toContain('layer.fit === "contain"');
    expect(source).toContain('background: layerBackground');
    expect(source).toContain("objectFit={layer.fit}");
    expect(source).not.toContain("#F4F1EA");
    expect(source).toContain("#091012");
  });

  test("honors each explicit visual-layer loop policy", () => {
    const source = readFileSync(
      new URL("./components/ProductionVisualLayer.tsx", import.meta.url),
      "utf8",
    );

    expect(source).toContain("loop={layer.loop}");
  });

  test("renders sparse kinetic typography separately from captions", () => {
    const source = readFileSync(
      new URL("./ProductionComposition.tsx", import.meta.url),
      "utf8",
    );

    expect(source).toContain("KineticTextLayer");
    expect(source).toContain("kinetic_text_cues");
  });

  test("applies interpolated visual effect keyframes", () => {
    const source = readFileSync(
      new URL("./components/ProductionVisualLayer.tsx", import.meta.url),
      "utf8",
    );

    expect(source).toContain("effect_keyframes");
    expect(source).toContain("brightness(");
    expect(source).toContain("saturate(");
  });

  test("feeds planned motion events into their target visual layers", () => {
    const composition = readFileSync(
      new URL("./ProductionComposition.tsx", import.meta.url),
      "utf8",
    );
    const layer = readFileSync(
      new URL("./components/ProductionVisualLayer.tsx", import.meta.url),
      "utf8",
    );

    expect(composition).toContain("motionEvents={plan.motion_events}");
    expect(layer).toContain("activeMotion");
    expect(layer).toContain('event.target_id === layer.id');
  });

  test("applies the measured social-kinetic visual grade before typography", () => {
    const source = readFileSync(
      new URL("./ProductionComposition.tsx", import.meta.url),
      "utf8",
    );

    expect(source).toContain("visualGradeForProfile");
    expect(source).toContain("brightness(0.76)");
    expect(source).toContain("saturate(1.86)");
  });
});
