import { describe, expect, test } from "vitest";

import {
  productionEditPlanSchema,
  type ProductionEditPlan,
} from "./productionSchema";

const validPlan: ProductionEditPlan = {
  version: "2.0",
  profile: "production-tech-story-v4",
  source_filename: "0806.mp4",
  source_metadata: {
    width: 1080,
    height: 1920,
    fps: 30,
    frame_count: 60,
    duration_seconds: 2,
  },
  output: { width: 1080, height: 1920, fps: 30 },
  duration_ms: 2000,
  assets: [
    {
      id: "flow",
      kind: "video",
      path: "assets/flow.mp4",
      keywords: [],
      provenance: "google-flow-veo-illustrative",
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
      id: "layer-flow",
      shot_id: "shot-01",
      start_ms: 0,
      end_ms: 2000,
      source_role: "flow-illustrative",
      kind: "video",
      asset_id: "flow",
      source_start_ms: 0,
      source_end_ms: 1500,
      bounds: { x: 70, y: 260, width: 940, height: 1120 },
      crop: { x: 0, y: 0, width: 1, height: 1 },
      fit: "cover",
      transform_keyframes: [
        { at_ms: 0, x: 0, y: 0, scale: 1, rotate_deg: 0 },
        { at_ms: 2000, x: 0, y: 0, scale: 1.02, rotate_deg: 0 },
      ],
      opacity_keyframes: [
        { at_ms: 0, value: 0 },
        { at_ms: 150, value: 1 },
      ],
      effect_keyframes: [
        {
          at_ms: 0,
          brightness: 1,
          contrast: 1,
          saturation: 1,
          blur_px: 0,
        },
      ],
      blend_mode: "normal",
      z_index: 20,
      muted: true,
      loop: false,
      playback_rate: 0.75,
      illustrative_label: true,
      border_radius: 28,
      color_filter: null,
      reference_role: "primary-10",
    },
  ],
  caption_pages: [],
  reference_profile: null,
  story_profile: null,
  style_reference_path: null,
  voice_policy: null,
  dialogue_edl: [],
  kinetic_text_cues: [],
  motion_events: [],
  audio: {
    integrated_lufs: -14.2,
    true_peak_dbtp: -1,
    target_lra_lu: 5,
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
};

describe("productionEditPlanSchema", () => {
  test("accepts slower technical-documentary music tempos", () => {
    const technical = structuredClone(validPlan);
    technical.audio.music_bpm = 94;

    expect(productionEditPlanSchema.parse(technical).audio.music_bpm).toBe(
      94,
    );
  });

  test("accepts the 0806 training-parity story profile", () => {
    const parityPlan = {
      ...structuredClone(validPlan),
      story_profile: "automation-future-parity",
    };

    expect(
      productionEditPlanSchema.parse(parityPlan).story_profile,
    ).toBe("automation-future-parity");
  });

  test("accepts explicit V8 story, voice and reference roles", () => {
    const v8 = structuredClone(validPlan);
    v8.story_profile = "ppi-training-v8";
    v8.voice_policy = "natural-1x";
    v8.visual_layers[0].reference_role =
      "reference-13-evidence-excerpt";

    const parsed = productionEditPlanSchema.parse(v8);

    expect(parsed.story_profile).toBe("ppi-training-v8");
    expect(parsed.voice_policy).toBe("natural-1x");
    expect(parsed.visual_layers[0].reference_role).toBe(
      "reference-13-evidence-excerpt",
    );
  });

  test("accepts the three V9 training-match profiles", () => {
    for (const storyProfile of [
      "ppi-training-v9",
      "backtest-training-v9",
      "lot-size-training-v9",
    ] as const) {
      const plan = structuredClone(validPlan);
      plan.story_profile = storyProfile;

      expect(productionEditPlanSchema.parse(plan).story_profile).toBe(
        storyProfile,
      );
    }
  });

  test("accepts explicit V2 layers and playback control", () => {
    const parsed = productionEditPlanSchema.parse(validPlan);

    expect(parsed.visual_layers[0].source_role).toBe(
      "flow-illustrative",
    );
    expect(parsed.visual_layers[0].playback_rate).toBe(0.75);
  });

  test("preserves a source-trimmed sound-effect attack", () => {
    const withSfx = structuredClone(validPlan);
    withSfx.assets.push({
      id: "impact",
      kind: "audio",
      path: "assets/impact.mp3",
      keywords: [],
      provenance: "licensed-sfx",
      license: "Licensed",
      provider: null,
      remote_id: null,
      creator: null,
      source_url: null,
      license_url: null,
      search_query: null,
      start_ms: null,
      end_ms: null,
    });
    withSfx.audio.sfx_asset_ids = ["impact"];
    withSfx.audio.sfx_cues = [
      {
        id: "impact-cut",
        asset_id: "impact",
        start_ms: 500,
        source_start_ms: 340,
        duration_ms: 100,
        volume: 0.35,
        gain_db: -15,
        kind: "impact",
        reason: "Cut accent",
      },
    ];

    const parsed = productionEditPlanSchema.parse(withSfx);

    expect(parsed.audio.sfx_cues[0].source_start_ms).toBe(340);
  });

  test("accepts social-kinetic dialogue, typography, motion and effects", () => {
    const social = structuredClone(validPlan);
    social.reference_profile = "social-kinetic";
    social.style_reference_path =
      "D:/Downloads/Profit Bricks_Reel 04.mp4";
    social.voice_policy = "reference-compressed";
    social.dialogue_edl = [
      {
        id: "dialogue-001",
        source_start_ms: 0,
        source_end_ms: 1000,
        output_start_ms: 0,
        output_end_ms: 1000,
        playback_rate: 1,
        preserve_pitch: true,
      },
    ];
    social.kinetic_text_cues = [
      {
        id: "hook-year",
        start_ms: 200,
        end_ms: 900,
        text: "2008",
        family: "hero-condensed",
        x: 540,
        y: 1330,
        max_width: 900,
        align: "center",
        animation: "slam",
        accent: null,
        secondary_text: null,
        rotation_deg: 0,
        z_index: 60,
      },
    ];
    social.motion_events = [
      {
        id: "hook-punch",
        start_ms: 0,
        end_ms: 240,
        kind: "punch-crop",
        target_id: "layer-flow",
        intensity: 0.55,
        direction: "none",
      },
    ];
    social.visual_layers[0].effect_keyframes = [
      {
        at_ms: 0,
        brightness: 1,
        contrast: 1,
        saturation: 1,
        blur_px: 0,
      },
      {
        at_ms: 2000,
        brightness: 1.04,
        contrast: 1.03,
        saturation: 0.94,
        blur_px: 0,
      },
    ];
    social.visual_layers[0].reference_role = "primary-human";

    const parsed = productionEditPlanSchema.parse(social);
    expect(parsed.kinetic_text_cues[0].family).toBe(
      "hero-condensed",
    );
    expect(
      parsed.visual_layers[0].effect_keyframes[1].saturation,
    ).toBe(0.94);
  });

  test("backfills empty social-kinetic arrays for legacy V2 plans", () => {
    const legacy = structuredClone(validPlan) as Record<string, unknown>;
    delete legacy.reference_profile;
    delete legacy.style_reference_path;
    delete legacy.voice_policy;
    delete legacy.dialogue_edl;
    delete legacy.kinetic_text_cues;
    delete legacy.motion_events;
    const legacyLayers = legacy.visual_layers as Array<
      Record<string, unknown>
    >;
    legacyLayers.forEach((layer) => delete layer.effect_keyframes);
    const parsed = productionEditPlanSchema.parse(legacy);

    expect(parsed.dialogue_edl).toEqual([]);
    expect(parsed.kinetic_text_cues).toEqual([]);
    expect(parsed.motion_events).toEqual([]);
    expect(parsed.visual_layers[0].effect_keyframes).toHaveLength(1);
  });

  test("accepts the lower safe caption anchor", () => {
    const withCaption = structuredClone(validPlan);
    withCaption.caption_pages = [
      {
        start_ms: 0,
        end_ms: 700,
        tokens: [
          {
            text: "ROBOT",
            start_ms: 0,
            end_ms: 700,
            highlighted: true,
            confidence: 0.99,
          },
        ],
        family: "outlined-demo",
        anchor: "lower-82",
        transition: "hard-cut",
        max_width: 940,
      },
    ];

    expect(
      productionEditPlanSchema.parse(withCaption).caption_pages[0].anchor,
    ).toBe("lower-82");
  });

  test("blocks unsafe Flow rendering", () => {
    for (const patch of [
      { muted: false },
      { illustrative_label: false },
      { loop: true },
    ]) {
      const invalid = structuredClone(validPlan);
      Object.assign(invalid.visual_layers[0], patch);
      expect(() => productionEditPlanSchema.parse(invalid)).toThrow(
        /flow|illustrative|loop|muted/i,
      );
    }
  });

  test("rejects unknown assets and out-of-range layers", () => {
    const unknown = structuredClone(validPlan);
    unknown.visual_layers[0].asset_id = "missing";
    expect(() => productionEditPlanSchema.parse(unknown)).toThrow(
      /unknown asset/i,
    );

    const tooLong = structuredClone(validPlan);
    tooLong.visual_layers[0].end_ms = 2001;
    expect(() => productionEditPlanSchema.parse(tooLong)).toThrow(
      /duration/i,
    );
  });

  test("rejects overlapping caption pages and fully masked tokens", () => {
    const overlapping = structuredClone(validPlan);
    overlapping.caption_pages = [
      {
        start_ms: 0,
        end_ms: 800,
        tokens: [
          {
            text: "First",
            start_ms: 0,
            end_ms: 500,
            highlighted: false,
            confidence: 0.99,
          },
        ],
        family: "technical-mono",
        anchor: "center-74",
        // eslint-disable-next-line @remotion/non-pure-animation
        transition: "hard-cut",
        max_width: 820,
      },
      {
        start_ms: 700,
        end_ms: 1400,
        tokens: [
          {
            text: "Second",
            start_ms: 700,
            end_ms: 1000,
            highlighted: false,
            confidence: 0.99,
          },
        ],
        family: "technical-mono",
        anchor: "center-74",
        // eslint-disable-next-line @remotion/non-pure-animation
        transition: "hard-cut",
        max_width: 820,
      },
    ];
    expect(() => productionEditPlanSchema.parse(overlapping)).toThrow(
      /overlap/i,
    );

    const masked = structuredClone(validPlan);
    masked.caption_pages = [
      {
        start_ms: 0,
        end_ms: 800,
        tokens: [
          {
            text: "Hidden",
            start_ms: 900,
            end_ms: 1100,
            highlighted: false,
            confidence: 0.99,
          },
        ],
        family: "technical-mono",
        anchor: "center-74",
        // eslint-disable-next-line @remotion/non-pure-animation
        transition: "hard-cut",
        max_width: 820,
      },
    ];
    expect(() => productionEditPlanSchema.parse(masked)).toThrow(
      /visible page/i,
    );
  });
});
