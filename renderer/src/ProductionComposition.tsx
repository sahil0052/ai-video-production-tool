import {
  AbsoluteFill,
  CalculateMetadataFunction,
  Composition,
  Easing,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

import { AudioLayer } from "./components/AudioLayer";
import { CaptionLayer } from "./components/CaptionLayer";
import { KineticTextLayer } from "./components/KineticTextLayer";
import { ProductionVisualLayer } from "./components/ProductionVisualLayer";
import {
  productionPropsSchema,
  type ProductionEditPlan,
  type ProductionProps,
} from "./productionSchema";
export { interpolateLayerKeyframes } from "./productionTiming";
import { millisecondsToFrames } from "./timing";

export const calculateProductionMetadata: CalculateMetadataFunction<
  ProductionProps
> = ({ props }) => {
  const validated = productionPropsSchema.parse(props);
  return {
    durationInFrames: millisecondsToFrames(
      validated.plan.duration_ms,
      validated.plan.output.fps,
    ),
    width: validated.plan.output.width,
    height: validated.plan.output.height,
    fps: validated.plan.output.fps,
    defaultOutName: "cutline-production-v4.mp4",
  };
};

export const visualGradeForProfile = (
  profile: ProductionEditPlan["reference_profile"],
) =>
  profile === "social-kinetic"
    ? "brightness(0.76) saturate(1.86)"
    : undefined;

export const ProductionTechStory: React.FC<ProductionProps> = ({
  plan,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const timeMs = (frame / fps) * 1000;
  const page = plan.caption_pages.find(
    (candidate) =>
      candidate.start_ms <= timeMs && candidate.end_ms > timeMs,
  );
  const pageLocalFrame = page
    ? frame - millisecondsToFrames(page.start_ms, fps)
    : 0;
  const captionEntrance = interpolate(
    pageLocalFrame,
    [0, 5],
    [0, 1],
    {
      easing: Easing.bezier(0.34, 1.56, 0.64, 1),
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    },
  );

  return (
    <AbsoluteFill
      style={{
        overflow: "hidden",
        background:
          "linear-gradient(180deg, #101617 0%, #0B0F10 100%)",
      }}
    >
      <AudioLayer plan={plan} />
      <AbsoluteFill
        style={{ filter: visualGradeForProfile(plan.reference_profile) }}
      >
        {[...plan.visual_layers]
          .sort((a, b) => a.z_index - b.z_index)
          .map((layer) => (
            <ProductionVisualLayer
              key={layer.id}
              layer={layer}
              assets={plan.assets}
              motionEvents={plan.motion_events}
            />
          ))}
      </AbsoluteFill>
      <KineticTextLayer
        cues={plan.kinetic_text_cues}
        timeMs={timeMs}
      />
      <CaptionLayer
        pages={plan.caption_pages}
        timeMs={timeMs}
        styleVariant="technical-explanation"
        entranceProgress={captionEntrance}
      />
    </AbsoluteFill>
  );
};

const placeholderSvg =
  "data:image/svg+xml;charset=utf-8," +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920"><rect width="1080" height="1920" fill="#101617"/></svg>',
  );

const defaultProductionPlan: ProductionEditPlan = {
  version: "2.0",
  profile: "production-tech-story-v4",
  source_filename: "placeholder.mp4",
  source_metadata: {
    width: 1080,
    height: 1920,
    fps: 30,
    frame_count: 30,
    duration_seconds: 1,
  },
  output: { width: 1080, height: 1920, fps: 30 },
  duration_ms: 1000,
  assets: [
    {
      id: "placeholder",
      kind: "image",
      path: placeholderSvg,
      keywords: [],
      provenance: "deterministic-placeholder",
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
      id: "placeholder-layer",
      shot_id: "shot-01",
      start_ms: 0,
      end_ms: 1000,
      source_role: "deterministic-graphic",
      kind: "image",
      asset_id: "placeholder",
      source_start_ms: null,
      source_end_ms: null,
      bounds: { x: 0, y: 0, width: 1080, height: 1920 },
      crop: { x: 0, y: 0, width: 1, height: 1 },
      fit: "fill",
      transform_keyframes: [
        { at_ms: 0, x: 0, y: 0, scale: 1, rotate_deg: 0 },
      ],
      opacity_keyframes: [{ at_ms: 0, value: 1 }],
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
      z_index: 1,
      muted: true,
      loop: false,
      playback_rate: 1,
      illustrative_label: false,
      border_radius: 0,
      color_filter: null,
      reference_role: "supporting",
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

export const ProductionTechStoryComposition = () => (
  <Composition
    id="ProductionTechStoryV4"
    component={ProductionTechStory}
    durationInFrames={30}
    fps={30}
    width={1080}
    height={1920}
    defaultProps={{ plan: defaultProductionPlan }}
    schema={productionPropsSchema}
    calculateMetadata={calculateProductionMetadata}
  />
);
