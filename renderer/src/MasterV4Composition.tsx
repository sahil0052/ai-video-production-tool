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
import { KineticWordHighlight } from "./captions/KineticWordHighlight";
import {
  dividerMorphState,
  activePunchScale,
} from "./motion/transitions";
import {
  productionPropsSchema,
  type ProductionEditPlan,
  type ProductionProps,
} from "./productionSchema";
import { millisecondsToFrames } from "./timing";

/**
 * Timestamps (ms) at which a split-screen <-> full-frame morph should run.
 * Each entry pairs a cut time with a direction; the divider animates
 * across it instead of hard-cutting. Presenter-facing metadata only,
 * kept local to this composition so the core productionEditPlanSchema
 * does not need a breaking migration to ship this feature.
 */
export type DividerCue = {
  atMs: number;
  direction: "split-to-full" | "full-to-split";
};

/**
 * Timestamps (ms) of emphasis words or detected pause boundaries that
 * should trigger a speech-coupled punch-in (1.0x -> 1.12x) on a target
 * visual layer id.
 */
export type PunchCue = {
  targetLayerId: string;
  triggerMsList: number[];
};

/** Caption page indices that should render with the word-by-word
 * marker-swipe kinetic highlight instead of the static CaptionLayer
 * treatment. */
export type MasterV4Props = ProductionProps & {
  dividerCues?: DividerCue[];
  punchCues?: PunchCue[];
  kineticMarkerPageIndexes?: number[];
  grainOpacity?: number;
};

export const calculateMasterV4Metadata: CalculateMetadataFunction<
  MasterV4Props
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
    defaultOutName: "master-v4-broadcast.mp4",
  };
};

/**
 * Seamless tiled paper-grain noise, generated with an inline SVG
 * feTurbulence filter so no binary asset needs to ship in the repo.
 * mix-blend-mode: overlay at a low, fixed opacity per the brief
 * ("unified tone-mapping and vintage paper grain overlay ... 6% opacity").
 */
const GrainOverlay: React.FC<{ opacity: number }> = ({ opacity }) => (
  <AbsoluteFill
    data-grain-overlay="true"
    style={{
      zIndex: 90,
      pointerEvents: "none",
      opacity,
      mixBlendMode: "overlay",
      backgroundImage:
        "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix type='matrix' values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.55 0'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>\")",
      backgroundSize: "240px 240px",
    }}
  />
);

/**
 * Morphing split-screen divider: renders a glowing gold (#FFD700) line
 * whose vertical position and glow intensity are driven by
 * dividerMorphState, replacing a hard cut between split and full-frame
 * layouts with a spring-driven height morph (960px <-> 1920px).
 */
const MorphingDivider: React.FC<{
  cues: DividerCue[];
  timeMs: number;
  fps: number;
  canvasHeight: number;
}> = ({ cues, timeMs, fps, canvasHeight }) => {
  const activeCue = [...cues]
    .sort((a, b) => a.atMs - b.atMs)
    .filter((cue) => timeMs >= cue.atMs - 400 && timeMs <= cue.atMs + 400)
    .pop();

  if (!activeCue) {
    return null;
  }

  const state = dividerMorphState(timeMs, fps, activeCue.atMs, activeCue.direction);
  const topPx = Math.min(state.topPaneHeightPx, canvasHeight - 4);

  return (
    <div
      data-morphing-divider="true"
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        top: topPx - 2,
        height: 4,
        zIndex: 80,
        background: "#FFD700",
        boxShadow: `0 0 ${8 + state.glowIntensity * 22}px ${
          2 + state.glowIntensity * 4
        }px rgba(255, 215, 0, ${0.45 + state.glowIntensity * 0.4})`,
        pointerEvents: "none",
      }}
    />
  );
};

export const MasterV4TechStory: React.FC<MasterV4Props> = ({
  plan,
  dividerCues = [],
  punchCues = [],
  kineticMarkerPageIndexes = [],
  grainOpacity = 0.06,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const timeMs = (frame / fps) * 1000;

  const pageIndex = plan.caption_pages.findIndex(
    (candidate) => candidate.start_ms <= timeMs && candidate.end_ms > timeMs,
  );
  const page = pageIndex >= 0 ? plan.caption_pages[pageIndex] : undefined;
  const useKineticMarker =
    pageIndex >= 0 && kineticMarkerPageIndexes.indexOf(pageIndex) !== -1;

  const pageLocalFrame = page
    ? frame - millisecondsToFrames(page.start_ms, fps)
    : 0;
  const captionEntrance = interpolate(pageLocalFrame, [0, 5], [0, 1], {
    easing: Easing.bezier(0.34, 1.56, 0.64, 1),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        overflow: "hidden",
        background: "linear-gradient(180deg, #101617 0%, #0B0F10 100%)",
      }}
    >
      <AudioLayer plan={plan} />
      <AbsoluteFill>
        {[...plan.visual_layers]
          .sort((a, b) => a.z_index - b.z_index)
          .map((layer) => {
            const cue = punchCues.find((c) => c.targetLayerId === layer.id);
            const punchScale = cue
              ? activePunchScale(timeMs, fps, cue.triggerMsList)
              : 1;
            return (
              <div
                key={layer.id}
                data-punch-wrapper={layer.id}
                style={{
                  position: "absolute",
                  inset: 0,
                  transform: `scale(${punchScale})`,
                  transformOrigin: "center",
                }}
              >
                <ProductionVisualLayer
                  layer={layer}
                  assets={plan.assets}
                  motionEvents={plan.motion_events}
                />
              </div>
            );
          })}
      </AbsoluteFill>

      <MorphingDivider
        cues={dividerCues}
        timeMs={timeMs}
        fps={fps}
        canvasHeight={plan.output.height}
      />

      <KineticTextLayer cues={plan.kinetic_text_cues} timeMs={timeMs} />

      {useKineticMarker && page ? (
        <div
          style={{
            position: "absolute",
            zIndex: 40,
            top: "78%",
            left: 72,
            right: 72,
            display: "flex",
            justifyContent: "center",
            pointerEvents: "none",
          }}
        >
          <KineticWordHighlight
            page={page}
            timeMs={timeMs}
            fontSize={38}
            fontFamily='"Inter Tight", Arial, sans-serif'
            fontWeight={800}
            letterSpacing="-0.025em"
            color="#FFFFFF"
          />
        </div>
      ) : (
        <CaptionLayer
          pages={plan.caption_pages}
          timeMs={timeMs}
          styleVariant="technical-explanation"
          entranceProgress={captionEntrance}
        />
      )}

      <GrainOverlay opacity={grainOpacity} />
    </AbsoluteFill>
  );
};

const placeholderSvg =
  "data:image/svg+xml;charset=utf-8," +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920"><rect width="1080" height="1920" fill="#101617"/></svg>',
  );

const defaultMasterV4Plan: ProductionEditPlan = {
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
        { at_ms: 0, brightness: 1, contrast: 1, saturation: 1, blur_px: 0 },
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
    integrated_lufs: -14,
    true_peak_dbtp: -1.5,
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

export const MasterV4Composition = () => (
  <Composition
    id="MasterV4Broadcast"
    component={MasterV4TechStory}
    durationInFrames={30}
    fps={30}
    width={1080}
    height={1920}
    defaultProps={{
      plan: defaultMasterV4Plan,
      dividerCues: [],
      punchCues: [],
      kineticMarkerPageIndexes: [],
      grainOpacity: 0.06,
    }}
    calculateMetadata={calculateMasterV4Metadata}
  />
);
