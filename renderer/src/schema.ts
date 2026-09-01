import { z } from "zod";

const timelineSegmentSchema = z
  .object({
    source_start_ms: z.number().int().nonnegative(),
    source_end_ms: z.number().int().positive(),
    output_start_ms: z.number().int().nonnegative(),
    output_end_ms: z.number().int().positive(),
  })
  .refine(
    (segment) =>
      segment.source_end_ms > segment.source_start_ms &&
      segment.output_end_ms > segment.output_start_ms,
    { message: "Timeline ranges must have a positive duration" },
  )
  .refine(
    (segment) =>
      segment.source_end_ms - segment.source_start_ms ===
      segment.output_end_ms - segment.output_start_ms,
    { message: "Timeline source and output duration must match" },
  );

const captionTokenSchema = z.object({
  text: z.string().min(1),
  start_ms: z.number().int().nonnegative(),
  end_ms: z.number().int().positive(),
  highlighted: z.boolean(),
  confidence: z.number().min(0).max(1).nullable(),
}).refine((token) => token.end_ms > token.start_ms, {
  message: "Caption token must have a positive duration",
});

export const captionFamilySchema = z.enum([
  "technical-mono",
  "documentary-clean",
  "compact-pill",
  "outlined-demo",
  "display-emphasis",
]);

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

const gainAutomationSchema = z
  .object({
    start_ms: z.number().int().nonnegative(),
    end_ms: z.number().int().positive(),
    gain_db: z.number().min(-12).max(0),
    reason: z.string().min(1),
  })
  .refine((window) => window.end_ms > window.start_ms, {
    message: "Gain automation must have a positive duration",
  });

const speechProtectionSchema = z
  .object({
    start_ms: z.number().int().nonnegative(),
    end_ms: z.number().int().positive(),
    word: z.string().min(1),
  })
  .refine((window) => window.end_ms > window.start_ms, {
    message: "Speech protection must have a positive duration",
  });

export const editPlanSchema = z.object({
  version: z.literal("1.0"),
  profile: z.literal("tech-story-v1"),
  source_filename: z.string().min(1),
  source_url: z.string().min(1),
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
  style_variant: z.enum([
    "tech-news",
    "cinematic-concept",
    "technical-explanation",
    "product-demo",
    "hardware-launch",
    "hyper-montage",
  ]),
  timeline: z.array(timelineSegmentSchema).min(1),
  caption_pages: z.array(
    z.object({
      start_ms: z.number().int().nonnegative(),
      end_ms: z.number().int().positive(),
      tokens: z.array(captionTokenSchema).min(1).max(5),
      family: captionFamilySchema.default("compact-pill"),
      anchor: captionAnchorSchema.default("center-76"),
      transition: captionTransitionSchema.default("fade-up"),
      max_width: z.number().int().min(320).max(980).default(920),
    }).refine((page) => page.end_ms > page.start_ms, {
      message: "Caption page must have a positive duration",
    }),
  ),
  scenes: z.array(
    z.object({
      id: z.string().min(1),
      start_ms: z.number().int().nonnegative(),
      end_ms: z.number().int().positive(),
      role: z.enum([
        "hook",
        "claim",
        "evidence",
        "explanation",
        "demonstration",
        "contrast",
        "payoff",
        "cta",
      ]),
      layout: z.enum([
        "presenter",
        "split-screen",
        "graphic",
        "asset-full",
        "presenter-pip",
      ]),
      zoom: z.union([z.literal(1), z.literal(1.12), z.literal(1.24)]),
      visual_id: z.string().min(1).nullable().default(null),
      treatment: z.string().min(1).nullable().default(null),
      asset_id: z.string().min(1).nullable().default(null),
      motion: z
        .enum(["live-footage", "animated", "document-pan", "static"])
        .default("live-footage"),
    }).refine((scene) => scene.end_ms > scene.start_ms, {
      message: "Scene must have a positive duration",
    }),
  ),
  reframing: z.array(
    z.object({
      time_ms: z.number().int().nonnegative(),
      x: z.number().min(0).max(1),
      y: z.number().min(0).max(1),
      scale: z.number().min(1).max(1.5),
    }),
  ),
  graphics: z.array(
    z.object({
      id: z.string().min(1),
      start_ms: z.number().int().nonnegative(),
      end_ms: z.number().int().positive(),
      kind: z.enum([
        "headline",
        "callout",
        "label",
        "counter",
        "progress",
        "browser",
        "phone",
        "chat",
      ]),
      text: z.string(),
      accent: z.string(),
    }).refine((graphic) => graphic.end_ms > graphic.start_ms, {
      message: "Graphic cue must have a positive duration",
    }),
  ),
  editorial_visuals: z
    .array(
      z
        .object({
          id: z.string().min(1),
          start_ms: z.number().int().nonnegative(),
          end_ms: z.number().int().positive(),
          kind: z.enum([
            "trading-chart",
            "rule-flow",
            "code-terminal",
            "evidence-card",
            "metric-reveal",
            "risk-meter",
            "comparison",
            "chat-cta",
          ]),
          title: z.string().min(1),
          subtitle: z.string(),
          accent: z.string(),
          value: z.string().nullable(),
          items: z.array(z.string()).max(5),
          direction: z.enum(["up", "down", "neutral"]),
        })
        .refine((visual) => visual.end_ms > visual.start_ms, {
          message: "Editorial visual must have a positive duration",
        }),
    )
    .default([]),
  assets: z.array(
    z
      .object({
        id: z.string().min(1),
        kind: z.enum(["image", "video", "audio", "font"]),
        path: z.string(),
        keywords: z.array(z.string()),
        provenance: z.string(),
        license: z.string().nullable(),
        provider: z.string().nullable().default(null),
        remote_id: z.string().nullable().default(null),
        creator: z.string().nullable().default(null),
        source_url: z.string().url().nullable().default(null),
        license_url: z.string().url().nullable().default(null),
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
        { message: "Asset schedule must have a positive duration" },
      ),
  ),
  audio: z.object({
    integrated_lufs: z.number(),
    true_peak_dbtp: z.number(),
    music_bpm: z.number().int().min(80).max(145),
    dialogue_asset_id: z.string().nullable().default(null),
    dialogue_offset_ms: z.number().int().min(-500).max(500).default(0),
    music_asset_id: z.string().nullable(),
    music_duck_db: z.number().min(4).max(8),
    music_base_gain_db: z.number().min(-40).max(0).default(-18),
    music_gain_automation: z
      .array(gainAutomationSchema)
      .default([]),
    speech_protection_windows: z
      .array(speechProtectionSchema)
      .default([]),
    sfx_asset_ids: z.array(z.string()),
    sfx_cues: z.array(
      z.object({
        id: z.string().min(1),
        asset_id: z.string().min(1),
        start_ms: z.number().int().nonnegative(),
        source_start_ms: z.number().int().nonnegative().default(0),
        duration_ms: z.number().int().positive().default(100),
        volume: z.number().min(0).max(1),
        gain_db: z.number().min(-30).max(0).default(-15),
        kind: z.enum([
          "whoosh",
          "click",
          "impact",
          "riser",
          "notification",
        ]),
        reason: z.string().default(""),
      }),
    ),
  }),
  qc_targets: z.object({
    integrated_lufs: z.number(),
    loudness_tolerance: z.number().positive(),
    true_peak_dbtp: z.number(),
    max_silence_ms: z.number().int().nonnegative(),
    max_black_frame_ratio: z.number().min(0).max(1),
    max_freeze_frame_ratio: z.number().min(0).max(1),
    min_cuts_per_minute: z.number().nonnegative(),
    max_cuts_per_minute: z.number().positive(),
    min_median_shot_ms: z.number().int().nonnegative(),
    max_median_shot_ms: z.number().int().positive(),
    min_cut_onset_percent: z.number().min(0).max(100),
    min_meaningful_visual_coverage: z
      .number()
      .min(0)
      .max(1)
      .default(0.55),
    min_style_score: z.number().min(0).max(100),
  }),
}).superRefine((plan, context) => {
  const sourceDurationMs = Math.round(
    plan.source_metadata.duration_seconds * 1000,
  );
  let previousOutputEnd = 0;
  let previousSourceEnd = -1;
  plan.timeline.forEach((segment, index) => {
    if (segment.output_start_ms !== previousOutputEnd) {
      context.addIssue({
        code: "custom",
        path: ["timeline", index, "output_start_ms"],
        message: "Output timeline must be ordered and contiguous",
      });
    }
    if (index > 0 && segment.source_start_ms < previousSourceEnd) {
      context.addIssue({
        code: "custom",
        path: ["timeline", index, "source_start_ms"],
        message: "Source timeline must be ordered and non-overlapping",
      });
    }
    if (segment.source_end_ms > sourceDurationMs + 1) {
      context.addIssue({
        code: "custom",
        path: ["timeline", index, "source_end_ms"],
        message: "Timeline exceeds source duration",
      });
    }
    previousOutputEnd = segment.output_end_ms;
    previousSourceEnd = segment.source_end_ms;
  });
  if (previousOutputEnd !== plan.duration_ms) {
    context.addIssue({
      code: "custom",
      path: ["duration_ms"],
      message: "Timeline must end at the output duration",
    });
  }

  let previousSceneEnd = 0;
  plan.scenes.forEach((scene, index) => {
    if (scene.start_ms !== previousSceneEnd) {
      context.addIssue({
        code: "custom",
        path: ["scenes", index, "start_ms"],
        message: "Scenes must be ordered and contiguous",
      });
    }
    if (scene.end_ms > plan.duration_ms) {
      context.addIssue({
        code: "custom",
        path: ["scenes", index, "end_ms"],
        message: "Scene exceeds output duration",
      });
    }
    previousSceneEnd = scene.end_ms;
  });
  if (previousSceneEnd !== plan.duration_ms) {
    context.addIssue({
      code: "custom",
      path: ["scenes"],
      message: "Scenes must end at the output duration",
    });
  }

  plan.caption_pages.forEach((page, pageIndex) => {
    if (page.end_ms > plan.duration_ms) {
      context.addIssue({
        code: "custom",
        path: ["caption_pages", pageIndex, "end_ms"],
        message: "Caption page exceeds output duration",
      });
    }
    let previousTokenStart = -1;
    page.tokens.forEach((token, tokenIndex) => {
      if (token.start_ms < previousTokenStart) {
        context.addIssue({
          code: "custom",
          path: ["caption_pages", pageIndex, "tokens", tokenIndex],
          message: "Caption source timings must be ordered",
        });
      }
      previousTokenStart = token.start_ms;
    });
  });

  plan.graphics.forEach((graphic, index) => {
    if (graphic.end_ms > plan.duration_ms) {
      context.addIssue({
        code: "custom",
        path: ["graphics", index, "end_ms"],
        message: "Graphic cue exceeds output duration",
      });
    }
  });
  const visualIds = new Set<string>();
  plan.editorial_visuals.forEach((visual, index) => {
    if (visualIds.has(visual.id)) {
      context.addIssue({
        code: "custom",
        path: ["editorial_visuals", index, "id"],
        message: "Editorial visual identifiers must be unique",
      });
    }
    visualIds.add(visual.id);
    if (visual.end_ms > plan.duration_ms) {
      context.addIssue({
        code: "custom",
        path: ["editorial_visuals", index, "end_ms"],
        message: "Editorial visual exceeds output duration",
      });
    }
  });
  plan.scenes.forEach((scene, index) => {
    if (scene.visual_id == null) {
      return;
    }
    const visual = plan.editorial_visuals.find(
      (candidate) => candidate.id === scene.visual_id,
    );
    if (!visual) {
      context.addIssue({
        code: "custom",
        path: ["scenes", index, "visual_id"],
        message: "Scene must reference an editorial visual",
      });
      return;
    }
    if (
      visual.start_ms !== scene.start_ms ||
      visual.end_ms !== scene.end_ms
    ) {
      context.addIssue({
        code: "custom",
        path: ["scenes", index, "visual_id"],
        message: "Editorial visual timing must match its scene",
      });
    }
  });
  plan.reframing.forEach((keyframe, index) => {
    if (keyframe.time_ms >= plan.duration_ms) {
      context.addIssue({
        code: "custom",
        path: ["reframing", index, "time_ms"],
        message: "Reframe keyframe exceeds output duration",
      });
    }
  });
  plan.audio.sfx_cues.forEach((cue, index) => {
    if (cue.start_ms >= plan.duration_ms) {
      context.addIssue({
        code: "custom",
        path: ["audio", "sfx_cues", index, "start_ms"],
        message: "Sound-effect cue exceeds output duration",
      });
    }
  });

  const assetIds = new Set<string>();
  const audioAssetIds = new Set<string>();
  plan.assets.forEach((asset, index) => {
    if (assetIds.has(asset.id)) {
      context.addIssue({
        code: "custom",
        path: ["assets", index, "id"],
        message: "Asset identifiers must be unique",
      });
    }
    assetIds.add(asset.id);
    if (asset.kind === "audio") {
      audioAssetIds.add(asset.id);
    }
    const normalizedPath = asset.path.replace(/\\/g, "/").toLowerCase();
    if (
      asset.provenance.toLowerCase().includes("training-video") ||
      normalizedPath.includes("training videos data")
    ) {
      context.addIssue({
        code: "custom",
        path: ["assets", index],
        message: "Training-video media cannot be used as an asset",
      });
    }
    if (asset.provenance.toLowerCase().startsWith("internet:")) {
      if (
        asset.provider == null ||
        asset.source_url == null ||
        asset.license == null ||
        asset.license_url == null
      ) {
        context.addIssue({
          code: "custom",
          path: ["assets", index],
          message:
            "Internet assets require provider, source and license metadata",
        });
      }
      for (const [field, url] of [
        ["source_url", asset.source_url],
        ["license_url", asset.license_url],
      ] as const) {
        if (url != null && !url.startsWith("https://")) {
          context.addIssue({
            code: "custom",
            path: ["assets", index, field],
            message: "Asset metadata URLs must use HTTPS",
          });
        }
      }
    }
    if (asset.end_ms != null && asset.end_ms > plan.duration_ms) {
      context.addIssue({
        code: "custom",
        path: ["assets", index, "end_ms"],
        message: "Asset schedule exceeds output duration",
      });
    }
  });
  if (
    plan.audio.music_asset_id != null &&
    !audioAssetIds.has(plan.audio.music_asset_id)
  ) {
    context.addIssue({
      code: "custom",
      path: ["audio", "music_asset_id"],
      message: "Music asset must reference an audio asset",
    });
  }
  if (
    plan.audio.dialogue_asset_id != null &&
    !audioAssetIds.has(plan.audio.dialogue_asset_id)
  ) {
    context.addIssue({
      code: "custom",
      path: ["audio", "dialogue_asset_id"],
      message: "Dialogue asset must reference an audio asset",
    });
  }
  const referencedSfx = new Set([
    ...plan.audio.sfx_asset_ids,
    ...plan.audio.sfx_cues.map((cue) => cue.asset_id),
  ]);
  referencedSfx.forEach((assetId) => {
    if (!audioAssetIds.has(assetId)) {
      context.addIssue({
        code: "custom",
        path: ["audio", "sfx_asset_ids"],
        message: "Sound effects must reference audio assets",
      });
    }
  });
});

export const techStoryPropsSchema = z.object({
  plan: editPlanSchema,
});

export type EditPlan = z.infer<typeof editPlanSchema>;
export type TechStoryProps = z.infer<typeof techStoryPropsSchema>;
export type CaptionToken = EditPlan["caption_pages"][number]["tokens"][number];
export type CaptionFamily = EditPlan["caption_pages"][number]["family"];
export type ReframeKeyframe = EditPlan["reframing"][number];
