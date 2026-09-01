import { Video } from "@remotion/media";
import {
  AbsoluteFill,
  CalculateMetadataFunction,
  Composition,
  Easing,
  interpolate,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

import {
  AssetLayer,
  findActiveAsset,
} from "./components/AssetLayer";
import { AudioLayer } from "./components/AudioLayer";
import { CaptionLayer } from "./components/CaptionLayer";
import {
  EditorialVisualLayer,
  findEditorialVisual,
} from "./components/EditorialVisualLayer";
import { GraphicLayer } from "./components/GraphicLayer";
import {
  isReference0806Scene,
  Reference0806VisualLayer,
} from "./components/Reference0806VisualLayer";
import {
  isReference0806V3Scene,
  Reference0806V3VisualLayer,
} from "./components/Reference0806V3VisualLayer";
import { defaultPlan } from "./defaultPlan";
import {
  techStoryPropsSchema,
  type EditPlan,
  type TechStoryProps,
} from "./schema";
import { interpolateReframe, millisecondsToFrames } from "./timing";

export const calculateTechStoryMetadata: CalculateMetadataFunction<
  TechStoryProps
> = ({ props }) => {
  const validated = techStoryPropsSchema.parse(props);
  return {
    durationInFrames: millisecondsToFrames(
      validated.plan.duration_ms,
      validated.plan.output.fps,
    ),
    width: validated.plan.output.width,
    height: validated.plan.output.height,
    fps: validated.plan.output.fps,
    defaultOutName: "cutline-tech-story.mp4",
  };
};

export const findSceneAtTime = (
  scenes: EditPlan["scenes"],
  timeMs: number,
) =>
  scenes.find(
    (scene) => scene.start_ms <= timeMs && scene.end_ms > timeMs,
  );

export const getTimelineSegmentFrameRange = (
  segment: EditPlan["timeline"][number],
  fps: number,
) => {
  const from = millisecondsToFrames(segment.output_start_ms, fps);
  const until = millisecondsToFrames(segment.output_end_ms, fps);
  return {
    from,
    durationInFrames: Math.max(1, until - from),
    trimBefore: Math.floor((segment.source_start_ms / 1000) * fps),
    trimAfter: Math.ceil((segment.source_end_ms / 1000) * fps),
  };
};

export const getPresenterLayout = (
  layout: EditPlan["scenes"][number]["layout"],
) => {
  if (layout === "graphic" || layout === "asset-full") {
    return {
      visible: false,
      top: 0 as const,
      left: 0 as const,
      width: "100%" as const,
      height: "100%" as const,
      borderRadius: 0,
      zIndex: 10,
    };
  }
  if (layout === "split-screen") {
    return {
      visible: true,
      top: "58%" as const,
      left: 0 as const,
      width: "100%" as const,
      height: "42%" as const,
      borderRadius: 0,
      zIndex: 24,
    };
  }
  if (layout === "presenter-pip") {
    return {
      visible: true,
      top: 1020,
      left: 650,
      width: 350,
      height: 620,
      borderRadius: 34,
      zIndex: 24,
    };
  }
  return {
    visible: true,
    top: 0 as const,
    left: 0 as const,
    width: "100%" as const,
    height: "100%" as const,
    borderRadius: 0,
    zIndex: 10,
  };
};

export const getReference0806V3PresenterTransform = (
  treatment: string | null | undefined,
) =>
  treatment === "0806-v3-clean-ending"
    ? { scale: 1.16, translateY: -26 }
    : { scale: 1, translateY: 0 };

export const TechStory: React.FC<TechStoryProps> = ({ plan }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const timeMs = (frame / fps) * 1000;
  const scene =
    findSceneAtTime(plan.scenes, timeMs) ??
    plan.scenes[plan.scenes.length - 1];
  const reframe = interpolateReframe(plan.reframing, timeMs);
  const sceneZoom = scene?.zoom ?? 1;
  const scale = Math.min(1.48, reframe.scale * sceneZoom);
  const page = plan.caption_pages.find(
    (candidate) =>
      candidate.start_ms <= timeMs && candidate.end_ms > timeMs,
  );
  const pageLocalFrame = page
    ? frame - millisecondsToFrames(page.start_ms, fps)
    : 0;
  const captionEntrance = interpolate(pageLocalFrame, [0, 5], [0, 1], {
    easing: Easing.bezier(0.34, 1.56, 0.64, 1),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const activeGraphic = plan.graphics.find(
    (graphic) =>
      graphic.start_ms <= timeMs && graphic.end_ms > timeMs,
  );
  const graphicLocalFrame = activeGraphic
    ? frame - millisecondsToFrames(activeGraphic.start_ms, fps)
    : 0;
  const graphicEntrance = interpolate(graphicLocalFrame, [0, 8], [0, 1], {
    easing: Easing.bezier(0.16, 1, 0.3, 1),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const activeAsset = findActiveAsset(plan.assets, timeMs);
  const assetLocalFrame = activeAsset?.start_ms != null
    ? frame - millisecondsToFrames(activeAsset.start_ms, fps)
    : 0;
  const assetEntrance = interpolate(assetLocalFrame, [0, 8], [0, 1], {
    easing: Easing.bezier(0.16, 1, 0.3, 1),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const hasLegacyVisualPanel =
    Boolean(activeAsset) ||
    activeGraphic?.kind === "browser" ||
    activeGraphic?.kind === "phone" ||
    activeGraphic?.kind === "chat";
  const sceneLayout = scene?.layout ?? "presenter";
  const reference0806V3Scene = isReference0806V3Scene(scene);
  const reference0806Scene =
    reference0806V3Scene || isReference0806Scene(scene);
  const effectiveLayout =
    !reference0806Scene &&
    sceneLayout === "presenter" &&
    hasLegacyVisualPanel
      ? "split-screen"
      : sceneLayout;
  const presenterLayout = getPresenterLayout(effectiveLayout);
  const presenterScale = scale;
  const presenterTreatmentTransform =
    getReference0806V3PresenterTransform(scene?.treatment);
  const presenterFilter = reference0806V3Scene
    ? "brightness(1.04) contrast(0.98) saturate(0.76)"
    : undefined;
  const editorialVisual = findEditorialVisual(
    plan.editorial_visuals,
    scene?.visual_id ?? null,
  );
  const editorialLocalFrame = scene
    ? frame - millisecondsToFrames(scene.start_ms, fps)
    : 0;

  return (
    <AbsoluteFill style={{ backgroundColor: "#080A0D", overflow: "hidden" }}>
      <AudioLayer plan={plan} />
      {plan.timeline.map((segment, index) => {
        const {
          from,
          durationInFrames,
          trimBefore,
          trimAfter,
        } = getTimelineSegmentFrameRange(segment, fps);
        return (
          <Sequence
            key={`${segment.source_start_ms}-${segment.output_start_ms}`}
            from={from}
            durationInFrames={durationInFrames}
            premountFor={fps}
          >
            {effectiveLayout === "split-screen" ? (
              <div
                style={{
                  position: "absolute",
                  top: presenterLayout.top,
                  left: presenterLayout.left,
                  width: presenterLayout.width,
                  height: presenterLayout.height,
                  zIndex: presenterLayout.zIndex,
                  overflow: "hidden",
                  background: "#111619",
                }}
              >
                <Video
                  src={staticFile(plan.source_url)}
                  trimBefore={trimBefore}
                  trimAfter={trimAfter}
                  muted
                  objectFit="contain"
                  style={{
                    position: "absolute",
                    inset: 0,
                    width: "100%",
                    height: "100%",
                    transform: "translateY(-118px) scale(1.55)",
                    transformOrigin: "50% 0%",
                    filter:
                      presenterFilter ??
                      "contrast(1.035) saturate(1.025)",
                  }}
                />
              </div>
            ) : presenterLayout.visible ? (
              <Video
                src={staticFile(plan.source_url)}
                trimBefore={trimBefore}
                trimAfter={trimAfter}
                muted
                objectFit="cover"
                style={{
                  position: "absolute",
                  top: presenterLayout.top,
                  left: presenterLayout.left,
                  width: presenterLayout.width,
                  height: presenterLayout.height,
                  zIndex: presenterLayout.zIndex,
                  borderRadius: presenterLayout.borderRadius,
                  boxShadow:
                    effectiveLayout === "presenter-pip"
                      ? "0 26px 70px rgba(0,0,0,0.58)"
                      : undefined,
                  transform: `translateY(${
                    presenterTreatmentTransform.translateY
                  }px) scale(${
                    presenterScale *
                    presenterTreatmentTransform.scale
                  })`,
                  transformOrigin: `${reframe.x * 100}% ${reframe.y * 100}%`,
                  filter:
                    presenterFilter ??
                    (index % 2 === 0
                      ? "contrast(1.025) saturate(1.035)"
                      : "contrast(1.045) saturate(1.02)"),
                }}
              />
            ) : null}
          </Sequence>
        );
      })}

      <AbsoluteFill
        style={{
          zIndex: 12,
          background:
            effectiveLayout === "graphic"
              ? "linear-gradient(180deg, rgba(8,10,13,0.72) 0%, transparent 38%, rgba(8,10,13,0.16) 100%)"
              : "linear-gradient(180deg, rgba(8,10,13,0.18) 0%, transparent 34%, rgba(8,10,13,0.16) 100%)",
          pointerEvents: "none",
        }}
      />

      <EditorialVisualLayer
        visual={reference0806Scene ? undefined : editorialVisual}
        layout={effectiveLayout}
        frame={editorialLocalFrame}
        fps={fps}
      />
      <Reference0806VisualLayer
        scene={scene}
        assets={plan.assets}
        frame={editorialLocalFrame}
        fps={fps}
      />
      <Reference0806V3VisualLayer
        scene={scene}
        assets={plan.assets}
        frame={editorialLocalFrame}
        fps={fps}
      />
      {reference0806Scene ? (
        <AbsoluteFill
          data-reference-motion-texture="true"
          style={{
            zIndex: 35,
            pointerEvents: "none",
            overflow: "hidden",
          }}
        >
          <AbsoluteFill
            style={{
              opacity: 0.045,
              mixBlendMode: "soft-light",
              backgroundImage:
                "repeating-linear-gradient(180deg, rgba(255,255,255,0.24) 0 1px, transparent 1px 5px)",
              backgroundPosition: `0 ${editorialLocalFrame * 2.4}px`,
            }}
          />
          <div
            style={{
              position: "absolute",
              top: 0,
              bottom: 0,
              left: 0,
              width: 380,
              opacity: 0.11,
              mixBlendMode: "screen",
              background:
                "linear-gradient(90deg, transparent, rgba(150,190,200,0.24), transparent)",
              transform: `translateX(${
                (editorialLocalFrame * 18) % 1460 - 380
              }px)`,
            }}
          />
        </AbsoluteFill>
      ) : null}
      {!reference0806Scene ? (
        <>
          <AssetLayer
            assets={plan.assets}
            timeMs={timeMs}
            entranceProgress={assetEntrance}
            layout={effectiveLayout}
          />
          <GraphicLayer
            graphics={plan.graphics}
            timeMs={timeMs}
            entranceProgress={graphicEntrance}
          />
        </>
      ) : null}
      <CaptionLayer
        pages={plan.caption_pages}
        timeMs={timeMs}
        styleVariant={plan.style_variant}
        entranceProgress={captionEntrance}
      />

      <AbsoluteFill
        style={{
          pointerEvents: "none",
          opacity: 0.035,
          backgroundImage:
            "radial-gradient(circle at 25% 20%, #fff 0 0.7px, transparent 0.8px)",
          backgroundSize: "5px 5px",
          mixBlendMode: "overlay",
        }}
      />
    </AbsoluteFill>
  );
};

export const TechStoryComposition = () => (
  <Composition
    id="TechStory"
    component={TechStory}
    durationInFrames={90}
    fps={30}
    width={1080}
    height={1920}
    defaultProps={{ plan: defaultPlan }}
    schema={techStoryPropsSchema}
    calculateMetadata={calculateTechStoryMetadata}
  />
);
