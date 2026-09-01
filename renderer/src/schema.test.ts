import { describe, expect, test } from "vitest";

import { editPlanSchema, type EditPlan } from "./schema";

const validPlan = {
  version: "1.0",
  profile: "tech-story-v1",
  source_filename: "source.mp4",
  source_url: "source.mp4",
  source_metadata: {
    width: 720,
    height: 1280,
    fps: 30,
    frame_count: 90,
    duration_seconds: 3,
  },
  output: { width: 1080, height: 1920, fps: 30 },
  duration_ms: 2500,
  style_variant: "technical-explanation",
  timeline: [
    {
      source_start_ms: 100,
      source_end_ms: 2600,
      output_start_ms: 0,
      output_end_ms: 2500,
    },
  ],
  caption_pages: [
    {
      start_ms: 0,
      end_ms: 600,
      family: "technical-mono",
      anchor: "center-74",
      transition: "hard-cut",
      max_width: 900,
      tokens: [
        {
          text: "AI",
          start_ms: 0,
          end_ms: 300,
          highlighted: true,
          confidence: 0.99,
        },
        {
          text: "works",
          start_ms: 300,
          end_ms: 600,
          highlighted: false,
          confidence: 0.99,
        },
      ],
    },
  ],
  scenes: [
    {
      id: "scene-1",
      start_ms: 0,
      end_ms: 2500,
      role: "hook",
      layout: "presenter",
      zoom: 1.12,
    },
  ],
  reframing: [{ time_ms: 0, x: 0.5, y: 0.42, scale: 1.12 }],
  graphics: [
    {
      id: "graphic-hook",
      start_ms: 0,
      end_ms: 1800,
      kind: "headline",
      text: "AI works",
      accent: "#D7FF64",
    },
  ],
  assets: [] as EditPlan["assets"],
  audio: {
    integrated_lufs: -14.2,
    true_peak_dbtp: -1,
    music_bpm: 120,
    music_asset_id: null,
    music_duck_db: 6,
    sfx_asset_ids: [],
    sfx_cues: [] as EditPlan["audio"]["sfx_cues"],
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
};

describe("editPlanSchema", () => {
  test("accepts the Python EditPlanV1 wire format", () => {
    const parsed = editPlanSchema.parse(validPlan);

    expect(parsed.output).toEqual({ width: 1080, height: 1920, fps: 30 });
    expect(parsed.caption_pages[0].family).toBe("technical-mono");
    expect(parsed.caption_pages[0].anchor).toBe("center-74");
    expect(parsed.caption_pages[0].max_width).toBe(900);
  });

  test("accepts the upper presenter-safe caption anchor", () => {
    const withUpperAnchor = structuredClone(validPlan);
    withUpperAnchor.caption_pages[0].anchor = "upper-46";

    expect(
      editPlanSchema.parse(withUpperAnchor).caption_pages[0].anchor,
    ).toBe("upper-46");
  });

  test("rejects timeline segments with mismatched durations", () => {
    const invalid = structuredClone(validPlan);
    invalid.timeline[0].output_end_ms = 2000;

    expect(() => editPlanSchema.parse(invalid)).toThrow(/duration/i);
  });

  test("preserves scheduled asset timing and provenance", () => {
    const withAsset = structuredClone(validPlan);
    withAsset.assets = [
      {
        id: "asset-1",
        kind: "image",
        path: "assets/asset-1.png",
        keywords: ["ai", "chip"],
        provenance: "local-library",
        license: "Internal",
        provider: null,
        remote_id: null,
        creator: null,
        source_url: null,
        license_url: null,
        search_query: null,
        start_ms: 700,
        end_ms: 1600,
      },
    ];

    const parsed = editPlanSchema.parse(withAsset);

    expect(parsed.assets[0].start_ms).toBe(700);
    expect(parsed.assets[0].end_ms).toBe(1600);
  });

  test("preserves internet asset creator and license provenance", () => {
    const withAsset = structuredClone(validPlan);
    withAsset.assets = [
      {
        id: "internet-asset-1",
        kind: "image",
        path: "assets/internet-asset-1.jpg",
        keywords: ["forex"],
        provenance: "internet:wikimedia-commons",
        license: "CC BY-SA 4.0",
        provider: "wikimedia-commons",
        remote_id: "10",
        creator: "Creator",
        source_url:
          "https://commons.wikimedia.org/wiki/File:Forex.jpg",
        license_url:
          "https://creativecommons.org/licenses/by-sa/4.0/",
        search_query: "forex market",
        start_ms: 700,
        end_ms: 1600,
      },
    ];

    const parsed = editPlanSchema.parse(withAsset);

    expect(parsed.assets[0].provider).toBe("wikimedia-commons");
    expect(parsed.assets[0].creator).toBe("Creator");
    expect(parsed.assets[0].license_url).toContain(
      "creativecommons.org",
    );
  });

  test("preserves sparse sound-effect cues", () => {
    const withCue = structuredClone(validPlan);
    withCue.assets = [
      {
        id: "generated-impact",
        kind: "audio",
        path: "assets/generated-impact.wav",
        keywords: ["impact"],
        provenance: "generated-original",
        license: "Original procedural audio",
        provider: null,
        remote_id: null,
        creator: null,
        source_url: null,
        license_url: null,
        search_query: null,
        start_ms: null,
        end_ms: null,
      },
    ];
    withCue.audio.sfx_cues = [
      {
        id: "sfx-1",
        asset_id: "generated-impact",
        start_ms: 0,
        source_start_ms: 0,
        duration_ms: 180,
        volume: 0.4,
        gain_db: -15,
        kind: "impact",
        reason: "Opening reveal",
      },
    ];

    const parsed = editPlanSchema.parse(withCue);

    expect(parsed.audio.sfx_cues[0].kind).toBe("impact");
    expect(parsed.audio.sfx_cues[0].volume).toBe(0.4);
  });

  test("preserves dialogue, gain automation, and speech protection metadata", () => {
    const withAutomation = structuredClone(validPlan);
    withAutomation.assets = [
      {
        id: "dialogue",
        kind: "audio",
        path: "assets/dialogue.wav",
        keywords: ["dialogue"],
        provenance: "user-provided-extracted-audio",
        license: "User-provided",
        provider: "user",
        remote_id: null,
        creator: "user",
        source_url: null,
        license_url: null,
        search_query: null,
        start_ms: null,
        end_ms: null,
      },
    ];
    Object.assign(withAutomation.audio, {
      dialogue_asset_id: "dialogue",
      dialogue_offset_ms: -70,
      music_base_gain_db: -18,
      music_gain_automation: [
        {
          start_ms: 200,
          end_ms: 1120,
          gain_db: -6,
          reason: "dialogue duck",
        },
      ],
      speech_protection_windows: [
        {
          start_ms: 100,
          end_ms: 320,
          word: "Do",
        },
      ],
    });

    const parsed = editPlanSchema.parse(withAutomation);

    expect(parsed.audio.dialogue_asset_id).toBe("dialogue");
    expect(parsed.audio.dialogue_offset_ms).toBe(-70);
    expect(parsed.audio.music_gain_automation[0].gain_db).toBe(-6);
    expect(parsed.audio.speech_protection_windows[0].word).toBe("Do");
  });

  test("preserves bespoke reference-scene direction", () => {
    const withReferenceScene = structuredClone(validPlan);
    Object.assign(withReferenceScene.scenes[0], {
      treatment: "0806-code-rule-trace",
      asset_id: "metaquotes-automated-trading-page",
      motion: "animated",
    });

    const parsed = editPlanSchema.parse(withReferenceScene);

    expect(parsed.scenes[0]).toMatchObject({
      treatment: "0806-code-rule-trace",
      asset_id: "metaquotes-automated-trading-page",
      motion: "animated",
    });
  });

  test("preserves semantic editorial visuals and scene references", () => {
    type VisualPlanInput = typeof validPlan & {
      scenes: Array<
        (typeof validPlan.scenes)[number] & { visual_id?: string }
      >;
      editorial_visuals: Array<{
        id: string;
        start_ms: number;
        end_ms: number;
        kind: string;
        title: string;
        subtitle: string;
        accent: string;
        value: string | null;
        items: string[];
        direction: string;
      }>;
    };
    const withVisual = structuredClone(
      validPlan,
    ) as unknown as VisualPlanInput;
    withVisual.scenes[0].layout = "graphic";
    withVisual.scenes[0].visual_id = "visual-1";
    withVisual.editorial_visuals = [
      {
        id: "visual-1",
        start_ms: 0,
        end_ms: 2500,
        kind: "trading-chart",
        title: "FOREX RULE ENGINE",
        subtitle: "Fixed rules execute every trade",
        accent: "#00E5FF",
        value: null,
        items: ["MARKET DATA", "RULES", "TRADE"],
        direction: "up",
      },
    ];

    const parsed = editPlanSchema.parse(withVisual);

    expect(parsed.scenes[0].visual_id).toBe("visual-1");
    expect(parsed.editorial_visuals).toHaveLength(1);
    expect(parsed.editorial_visuals[0].kind).toBe("trading-chart");
  });

  test("rejects a noncontiguous output timeline", () => {
    const invalid = structuredClone(validPlan);
    invalid.timeline = [
      {
        source_start_ms: 100,
        source_end_ms: 1100,
        output_start_ms: 0,
        output_end_ms: 1000,
      },
      {
        source_start_ms: 1200,
        source_end_ms: 2600,
        output_start_ms: 1100,
        output_end_ms: 2500,
      },
    ];

    expect(() => editPlanSchema.parse(invalid)).toThrow(/contiguous/i);
  });

  test("rejects layers outside the output duration", () => {
    const invalid = structuredClone(validPlan);
    invalid.scenes[0].end_ms = invalid.duration_ms + 1;

    expect(() => editPlanSchema.parse(invalid)).toThrow(/output duration/i);
  });

  test("rejects training-video media assets", () => {
    const invalid = structuredClone(validPlan);
    invalid.assets = [
      {
        id: "forbidden-reference",
        kind: "video",
        path: "C:/training videos data/reference.mp4",
        keywords: ["reference"],
        provenance: "training-video",
        license: null,
        provider: null,
        remote_id: null,
        creator: null,
        source_url: null,
        license_url: null,
        search_query: null,
        start_ms: 0,
        end_ms: 500,
      },
    ];

    expect(() => editPlanSchema.parse(invalid)).toThrow(/training-video/i);
  });
});
