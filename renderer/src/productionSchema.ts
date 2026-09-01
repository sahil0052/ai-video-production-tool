import { z } from "zod";

import { captionFamilySchema } from "./schema";

const captionAnchorSchema = z.enum([
  "center-69",
  "center-71",
  "center-74",
  "center-76",
  "center-78",
  "lower-82",
  "upper-46",
  "upper-56",
  "upper-62",
]);

const captionTransitionSchema = z.enum([
  "hard-cut",
  "fade-up",
  "scale-in",
]);

const captionTokenSchema = z
  .object({
    text: z.string().min(1),
    start_ms: z.number().int().nonnegative(),
    end_ms: z.number().int().positive(),
    highlighted: z.boolean().default(false),
    confidence: z.number().min(0).max(1).nullable().default(null),
  })
  .refine((token) => token.end_ms > token.start_ms, {
    message: "Caption token must have positive duration",
  });

const captionPageSchema = z
  .object({
    start_ms: z.number().int().nonnegative(),
    end_ms: z.number().int().positive(),
    tokens: z.array(captionTokenSchema).min(1).max(5),
    family: captionFamilySchema,
    anchor: captionAnchorSchema,
    transition: captionTransitionSchema,
    max_width: z.number().int().min(320).max(980),
  })
  .refine((page) => page.end_ms > page.start_ms, {
    message: "Caption page must have positive duration",
  });

const assetSchema = z
  .object({
    id: z.string().min(1),
    kind: z.enum(["image", "video", "audio", "font"]),
    path: z.string().min(1),
    keywords: z.array(z.string()).default([]),
    provenance: z.string().min(1),
    license: z.string().nullable().default(null),
    provider: z.string().nullable().default(null),
    remote_id: z.string().nullable().default(null),
    creator: z.string().nullable().default(null),
    source_url: z.string().nullable().default(null),
    license_url: z.string().nullable().default(null),
    search_query: z.string().nullable().default(null),
    start_ms: z.number().int().nonnegative().nullable().optional(),
    end_ms: z.number().int().positive().nullable().optional(),
  })
  .refine(
    (asset) =>
      (asset.start_ms == null && asset.end_ms == null) ||
      (asset.start_ms != null &&
        asset.end_ms != null &&
        asset.end_ms > asset.start_ms),
    { message: "Asset schedule must have positive duration" },
  );

const transformKeyframeSchema = z.object({
  at_ms: z.number().int().nonnegative(),
  x: z.number(),
  y: z.number(),
  scale: z.number().positive().max(4),
  rotate_deg: z.number().min(-360).max(360),
});

const opacityKeyframeSchema = z.object({
  at_ms: z.number().int().nonnegative(),
  value: z.number().min(0).max(1),
});

const effectKeyframeSchema = z.object({
  at_ms: z.number().int().nonnegative(),
  brightness: z.number().min(0.25).max(2).default(1),
  contrast: z.number().min(0.25).max(2).default(1),
  saturation: z.number().min(0).max(2).default(1),
  blur_px: z.number().min(0).max(80).default(0),
});

const dialogueEditSegmentSchema = z
  .object({
    id: z.string().min(1),
    source_start_ms: z.number().int().nonnegative(),
    source_end_ms: z.number().int().positive(),
    output_start_ms: z.number().int().nonnegative(),
    output_end_ms: z.number().int().positive(),
    playback_rate: z.number().min(0.5).max(1.06).default(1),
    preserve_pitch: z.boolean().default(true),
  })
  .refine(
    (segment) =>
      segment.source_end_ms > segment.source_start_ms &&
      segment.output_end_ms > segment.output_start_ms,
    { message: "Dialogue edit segment must have positive duration" },
  )
  .refine(
    (segment) =>
      Math.abs(
        segment.output_end_ms -
          segment.output_start_ms -
          (segment.source_end_ms - segment.source_start_ms) /
            segment.playback_rate,
      ) <= 4,
    {
      message:
        "Dialogue output duration must match its playback rate",
    },
  )
  .refine((segment) => segment.preserve_pitch, {
    message: "Dialogue speed changes must preserve pitch",
  });

const kineticTextCueSchema = z
  .object({
    id: z.string().min(1),
    start_ms: z.number().int().nonnegative(),
    end_ms: z.number().int().positive(),
    text: z.string().min(1),
    family: z.enum([
      "serif-hook",
      "hero-condensed",
      "outlined-stack",
      "cyan-secondary",
      "gradient-number",
      "correction-symbol",
      "cta-quote",
      "micro-source",
    ]),
    x: z.number().int().min(-1080).max(2160).default(540),
    y: z.number().int().min(-1920).max(3840).default(1320),
    max_width: z.number().int().min(160).max(1080).default(940),
    align: z.enum(["left", "center", "right"]).default("center"),
    animation: z
      .enum([
        "hard-cut",
        "slam",
        "stack",
        "rise",
        "glow",
        "draw",
        "quote-pop",
      ])
      .default("hard-cut"),
    accent: z.string().nullable().default(null),
    secondary_text: z.string().nullable().default(null),
    rotation_deg: z.number().min(-30).max(30).default(0),
    z_index: z.number().int().min(0).max(1000).default(60),
  })
  .refine((cue) => cue.end_ms > cue.start_ms, {
    message: "Kinetic text cue must have positive duration",
  });

const motionEventSchema = z
  .object({
    id: z.string().min(1),
    start_ms: z.number().int().nonnegative(),
    end_ms: z.number().int().positive(),
    kind: z.enum([
      "punch-crop",
      "text-reveal",
      "pip-pop",
      "logo-build",
      "directional-jump",
      "highlight-sweep",
      "impact-flash",
      "question-pulse",
      "proof-punch",
    ]),
    target_id: z.string().min(1),
    intensity: z.number().min(0).max(1).default(0.5),
    direction: z
      .enum(["none", "left", "right", "up", "down"])
      .default("none"),
  })
  .refine((event) => event.end_ms > event.start_ms, {
    message: "Motion event must have positive duration",
  });

const visualLayerSchema = z
  .object({
    id: z.string().min(1),
    shot_id: z.string().min(1),
    start_ms: z.number().int().nonnegative(),
    end_ms: z.number().int().positive(),
    source_role: z.enum([
      "presenter",
      "real-product",
      "direct-evidence",
      "deterministic-graphic",
      "licensed-context",
      "flow-illustrative",
    ]),
    kind: z.enum(["video", "image"]),
    asset_id: z.string().min(1),
    source_start_ms: z.number().int().nonnegative().nullable(),
    source_end_ms: z.number().int().positive().nullable(),
    bounds: z.object({
      x: z.number().int(),
      y: z.number().int(),
      width: z.number().int().positive(),
      height: z.number().int().positive(),
    }),
    crop: z.object({
      x: z.number().min(0).max(1),
      y: z.number().min(0).max(1),
      width: z.number().positive().max(1),
      height: z.number().positive().max(1),
    }),
    fit: z.enum(["cover", "contain", "fill"]),
    transform_keyframes: z.array(transformKeyframeSchema).min(1),
    opacity_keyframes: z.array(opacityKeyframeSchema).min(1),
    effect_keyframes: z
      .array(effectKeyframeSchema)
      .min(1)
      .default([
        {
          at_ms: 0,
          brightness: 1,
          contrast: 1,
          saturation: 1,
          blur_px: 0,
        },
      ]),
    blend_mode: z.enum([
      "normal",
      "multiply",
      "screen",
      "overlay",
      "soft-light",
    ]),
    z_index: z.number().int().min(0).max(1000),
    muted: z.boolean(),
    loop: z.boolean(),
    playback_rate: z.number().min(0.25).max(4),
    illustrative_label: z.boolean(),
    border_radius: z.number().int().min(0).max(240),
    color_filter: z.string().nullable(),
    reference_role: z.string().refine(
      (value) =>
        [
          "primary-10",
          "primary-13",
          "secondary-4",
          "primary-human",
          "secondary-10",
          "supporting",
          "profit-bricks-brand",
        ].includes(value) ||
        /^reference-(4|5|10|13)-[a-z0-9][a-z0-9-]*$/.test(value),
      {
        message:
          "reference_role must name a locked reference and editorial role",
      },
    ),
  })
  .refine((layer) => layer.end_ms > layer.start_ms, {
    message: "Visual layer must have positive duration",
  })
  .refine(
    (layer) =>
      layer.crop.x + layer.crop.width <= 1.000001 &&
      layer.crop.y + layer.crop.height <= 1.000001,
    { message: "Visual layer crop exceeds source bounds" },
  )
  .refine(
    (layer) =>
      (layer.source_start_ms == null &&
        layer.source_end_ms == null) ||
      (layer.source_start_ms != null &&
        layer.source_end_ms != null &&
        layer.source_end_ms > layer.source_start_ms),
    { message: "Visual layer source trim must have positive duration" },
  )
  .refine(
    (layer) =>
      layer.source_role !== "flow-illustrative" ||
      (layer.muted && layer.illustrative_label && !layer.loop),
    {
      message:
        "Flow layers must be muted, non-looping and labelled illustrative",
    },
  );

const gainAutomationSchema = z
  .object({
    start_ms: z.number().int().nonnegative(),
    end_ms: z.number().int().positive(),
    gain_db: z.number().min(-12).max(0),
    reason: z.string().min(1),
  })
  .refine((window) => window.end_ms > window.start_ms, {
    message: "Gain automation must have positive duration",
  });

const speechProtectionSchema = z
  .object({
    start_ms: z.number().int().nonnegative(),
    end_ms: z.number().int().positive(),
    word: z.string().min(1),
  })
  .refine((window) => window.end_ms > window.start_ms, {
    message: "Speech protection must have positive duration",
  });

const audioPlanSchema = z.object({
  integrated_lufs: z.number(),
  true_peak_dbtp: z.number(),
  target_lra_lu: z.number().min(1).max(10).default(5),
  music_bpm: z.number().int().min(80).max(145),
  dialogue_asset_id: z.string().nullable(),
  dialogue_offset_ms: z.number().int().min(-500).max(500),
  music_asset_id: z.string().nullable(),
  music_duck_db: z.number().min(4).max(12),
  music_base_gain_db: z.number().min(-40).max(0),
  music_gain_automation: z.array(gainAutomationSchema),
  speech_protection_windows: z.array(speechProtectionSchema),
  sfx_asset_ids: z.array(z.string()),
  sfx_cues: z.array(
    z.object({
      id: z.string().min(1),
      asset_id: z.string().min(1),
      start_ms: z.number().int().nonnegative(),
      source_start_ms: z.number().int().nonnegative().default(0),
      duration_ms: z.number().int().positive(),
      volume: z.number().min(0).max(1),
      gain_db: z.number().min(-30).max(0),
      kind: z.enum([
        "whoosh",
        "click",
        "impact",
        "riser",
        "notification",
      ]),
      reason: z.string(),
    }),
  ),
});

export const productionEditPlanSchema = z
  .object({
    version: z.literal("2.0"),
    profile: z.literal("production-tech-story-v4"),
    source_filename: z.string().min(1),
    source_metadata: z.object({
      width: z.number().int().positive(),
      height: z.number().int().positive(),
      fps: z.number().positive(),
      frame_count: z.number().int().positive(),
      duration_seconds: z.number().positive(),
    }),
    output: z.object({
      width: z.number().int().positive(),
      height: z.number().int().positive(),
      fps: z.union([z.literal(30), z.literal(60)]),
    }),
    duration_ms: z.number().int().positive(),
    assets: z.array(assetSchema),
    visual_layers: z.array(visualLayerSchema).min(1),
    caption_pages: z.array(captionPageSchema),
    audio: audioPlanSchema,
    reference_profile: z
      .enum(["technical-reference", "social-kinetic"])
      .nullable()
      .default(null),
    story_profile: z
      .enum([
        "automation-future",
        "automation-future-parity",
        "rofx-case",
        "cpi-inflation",
        "cpi-inflation-training",
        "ppi-training-v8",
        "backtest-training-v8",
        "lot-size-training-v8",
        "ppi-training-v9",
        "backtest-training-v9",
        "lot-size-training-v9",
      ])
      .nullable()
      .default(null),
    style_reference_path: z.string().nullable().default(null),
    voice_policy: z
      .enum([
        "retime-safe",
        "preserve-verbatim",
        "reference-compressed",
        "natural-1x",
      ])
      .nullable()
      .default(null),
    dialogue_edl: z.array(dialogueEditSegmentSchema).default([]),
    kinetic_text_cues: z.array(kineticTextCueSchema).default([]),
    motion_events: z.array(motionEventSchema).default([]),
  })
  .superRefine((plan, context) => {
    const assetIds = new Set<string>();
    const audioAssetIds = new Set<string>();
    plan.assets.forEach((asset, index) => {
      if (assetIds.has(asset.id)) {
        context.addIssue({
          code: "custom",
          path: ["assets", index, "id"],
          message: "Production asset identifiers must be unique",
        });
      }
      assetIds.add(asset.id);
      if (asset.kind === "audio") {
        audioAssetIds.add(asset.id);
      }
      if (
        asset.path.toLowerCase().includes("training videos data") ||
        asset.provenance.toLowerCase().includes("training-video")
      ) {
        context.addIssue({
          code: "custom",
          path: ["assets", index],
          message: "Training-video media cannot be used as an asset",
        });
      }
    });

    const layerIds = new Set<string>();
    plan.visual_layers.forEach((layer, index) => {
      if (layerIds.has(layer.id)) {
        context.addIssue({
          code: "custom",
          path: ["visual_layers", index, "id"],
          message: "Visual layer identifiers must be unique",
        });
      }
      layerIds.add(layer.id);
      if (!assetIds.has(layer.asset_id)) {
        context.addIssue({
          code: "custom",
          path: ["visual_layers", index, "asset_id"],
          message: "Visual layer references an unknown asset",
        });
      }
      if (layer.end_ms > plan.duration_ms) {
        context.addIssue({
          code: "custom",
          path: ["visual_layers", index, "end_ms"],
          message: "Visual layer exceeds output duration",
        });
      }
      const duration = layer.end_ms - layer.start_ms;
      for (const [key, keyframes] of [
        ["transform_keyframes", layer.transform_keyframes],
        ["opacity_keyframes", layer.opacity_keyframes],
        ["effect_keyframes", layer.effect_keyframes],
      ] as const) {
        if (keyframes.some((keyframe) => keyframe.at_ms > duration)) {
          context.addIssue({
            code: "custom",
            path: ["visual_layers", index, key],
            message: "Layer keyframe exceeds layer duration",
          });
        }
      }
    });

    const kineticIds = new Set<string>();
    plan.kinetic_text_cues.forEach((cue, index) => {
      if (kineticIds.has(cue.id)) {
        context.addIssue({
          code: "custom",
          path: ["kinetic_text_cues", index, "id"],
          message: "Kinetic text identifiers must be unique",
        });
      }
      kineticIds.add(cue.id);
      if (cue.end_ms > plan.duration_ms) {
        context.addIssue({
          code: "custom",
          path: ["kinetic_text_cues", index, "end_ms"],
          message: "Kinetic text cue exceeds output duration",
        });
      }
    });

    const motionIds = new Set<string>();
    const knownMotionTargets = new Set([
      ...layerIds,
      ...kineticIds,
      "composition",
    ]);
    plan.motion_events.forEach((event, index) => {
      if (motionIds.has(event.id)) {
        context.addIssue({
          code: "custom",
          path: ["motion_events", index, "id"],
          message: "Motion event identifiers must be unique",
        });
      }
      motionIds.add(event.id);
      if (!knownMotionTargets.has(event.target_id)) {
        context.addIssue({
          code: "custom",
          path: ["motion_events", index, "target_id"],
          message: "Motion event references an unknown target",
        });
      }
      if (event.end_ms > plan.duration_ms) {
        context.addIssue({
          code: "custom",
          path: ["motion_events", index, "end_ms"],
          message: "Motion event exceeds output duration",
        });
      }
    });

    let previousDialogueOutputEnd = 0;
    let previousDialogueSourceEnd = -1;
    plan.dialogue_edl.forEach((segment, index) => {
      if (segment.output_start_ms !== previousDialogueOutputEnd) {
        context.addIssue({
          code: "custom",
          path: ["dialogue_edl", index, "output_start_ms"],
          message: "Dialogue EDL output ranges must be contiguous",
        });
      }
      if (
        index > 0 &&
        segment.source_start_ms < previousDialogueSourceEnd
      ) {
        context.addIssue({
          code: "custom",
          path: ["dialogue_edl", index, "source_start_ms"],
          message: "Dialogue EDL source ranges must be ordered",
        });
      }
      if (segment.output_end_ms > plan.duration_ms) {
        context.addIssue({
          code: "custom",
          path: ["dialogue_edl", index, "output_end_ms"],
          message: "Dialogue EDL exceeds output duration",
        });
      }
      previousDialogueOutputEnd = segment.output_end_ms;
      previousDialogueSourceEnd = segment.source_end_ms;
    });

    let previousCaptionEnd = -1;
    plan.caption_pages.forEach((page, index) => {
      const duration = page.end_ms - page.start_ms;
      if (page.end_ms > plan.duration_ms) {
        context.addIssue({
          code: "custom",
          path: ["caption_pages", index, "end_ms"],
          message: "Caption page exceeds output duration",
        });
      }
      if (duration < 350 || duration > 1300) {
        context.addIssue({
          code: "custom",
          path: ["caption_pages", index],
          message: "Caption page must remain visible for 350-1300 ms",
        });
      }
      if (page.start_ms < previousCaptionEnd) {
        context.addIssue({
          code: "custom",
          path: ["caption_pages", index, "start_ms"],
          message: "Caption pages must not overlap",
        });
      }
      previousCaptionEnd = page.end_ms;
      page.tokens.forEach((token, tokenIndex) => {
        if (
          token.end_ms <= page.start_ms ||
          token.start_ms >= page.end_ms
        ) {
          context.addIssue({
            code: "custom",
            path: ["caption_pages", index, "tokens", tokenIndex],
            message: "Caption token must overlap its visible page",
          });
        }
      });
    });

    for (const [key, assetId] of [
      ["dialogue_asset_id", plan.audio.dialogue_asset_id],
      ["music_asset_id", plan.audio.music_asset_id],
    ] as const) {
      if (assetId != null && !audioAssetIds.has(assetId)) {
        context.addIssue({
          code: "custom",
          path: ["audio", key],
          message: "Audio plan references an unknown audio asset",
        });
      }
    }
    for (const assetId of [
      ...plan.audio.sfx_asset_ids,
      ...plan.audio.sfx_cues.map((cue) => cue.asset_id),
    ]) {
      if (!audioAssetIds.has(assetId)) {
        context.addIssue({
          code: "custom",
          path: ["audio", "sfx_asset_ids"],
          message: "Sound effects must reference audio assets",
        });
      }
    }
  });

export const productionPropsSchema = z.object({
  plan: productionEditPlanSchema,
});

export type ProductionEditPlan = z.infer<
  typeof productionEditPlanSchema
>;
export type ProductionProps = z.infer<typeof productionPropsSchema>;
export type ProductionVisualLayer =
  ProductionEditPlan["visual_layers"][number];
