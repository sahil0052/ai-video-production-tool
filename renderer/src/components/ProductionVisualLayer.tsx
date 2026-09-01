import { Video } from "@remotion/media";
import {
  Img,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

import type {
  ProductionEditPlan,
  ProductionVisualLayer as Layer,
} from "../productionSchema";
import { interpolateLayerKeyframes } from "../productionTiming";
import { millisecondsToFrames } from "../timing";

const resolveSource = (path: string) =>
  /^(data:|https?:)/.test(path) ? path : staticFile(path);

const interpolateOpacity = (
  keyframes: Layer["opacity_keyframes"],
  timeMs: number,
) => {
  const values = keyframes.map((keyframe) => ({
    at_ms: keyframe.at_ms,
    x: keyframe.value,
    y: 0,
    scale: 1,
    rotate_deg: 0,
  }));
  return interpolateLayerKeyframes(values, timeMs).x;
};

const interpolateEffects = (
  keyframes: Layer["effect_keyframes"],
  timeMs: number,
) => {
  const property = (
    name: "brightness" | "contrast" | "saturation" | "blur_px",
  ) =>
    interpolateLayerKeyframes(
      keyframes.map((keyframe) => ({
        at_ms: keyframe.at_ms,
        x: keyframe[name],
        y: 0,
        scale: 1,
        rotate_deg: 0,
      })),
      timeMs,
    ).x;
  return {
    brightness: property("brightness"),
    contrast: property("contrast"),
    saturation: property("saturation"),
    blurPx: property("blur_px"),
  };
};

const LayerMedia: React.FC<{
  layer: Layer;
  asset: ProductionEditPlan["assets"][number];
  motionEvents: ProductionEditPlan["motion_events"];
}> = ({ layer, asset, motionEvents }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const localTimeMs = (frame / fps) * 1000;
  const globalTimeMs = layer.start_ms + localTimeMs;
  const transform = interpolateLayerKeyframes(
    layer.transform_keyframes,
    localTimeMs,
  );
  const opacity = interpolateOpacity(
    layer.opacity_keyframes,
    localTimeMs,
  );
  const effects = interpolateEffects(
    layer.effect_keyframes,
    localTimeMs,
  );
  const effectFilter = `brightness(${effects.brightness}) contrast(${effects.contrast}) saturate(${effects.saturation}) blur(${effects.blurPx}px)`;
  const mediaFilter = [layer.color_filter, effectFilter]
    .filter(Boolean)
    .join(" ");
  const activeMotion = motionEvents.filter(
    (event) =>
      event.target_id === layer.id &&
      event.start_ms <= globalTimeMs &&
      event.end_ms > globalTimeMs,
  );
  let motionScale = 0;
  let motionX = 0;
  let motionY = 0;
  for (const event of activeMotion) {
    const linear = Math.min(
      1,
      Math.max(
        0,
        (globalTimeMs - event.start_ms) /
          (event.end_ms - event.start_ms),
      ),
    );
    const settle = (1 - linear) ** 3;
    if (
      [
        "punch-crop",
        "proof-punch",
        "impact-flash",
        "question-pulse",
        "logo-build",
      ].includes(event.kind)
    ) {
      motionScale += settle * event.intensity * 0.09;
    }
    if (event.kind === "directional-jump") {
      const distance = settle * event.intensity * 90;
      if (event.direction === "left") motionX -= distance;
      if (event.direction === "right") motionX += distance;
      if (event.direction === "up") motionY -= distance;
      if (event.direction === "down") motionY += distance;
    }
  }
  const source = resolveSource(asset.path);
  const isOverlayLayer =
    layer.source_role === "deterministic-graphic";
  const layerBackground = isOverlayLayer
    ? "transparent"
    : layer.source_role === "direct-evidence"
      ? "#F7F7F5"
      : layer.fit === "contain"
        ? "#091012"
        : "#0D1112";
  const cropStyle: React.CSSProperties = {
    position: "absolute",
    width: `${100 / layer.crop.width}%`,
    height: `${100 / layer.crop.height}%`,
    left: `${(-layer.crop.x / layer.crop.width) * 100}%`,
    top: `${(-layer.crop.y / layer.crop.height) * 100}%`,
  };
  const trimBefore =
    layer.source_start_ms == null
      ? undefined
      : millisecondsToFrames(layer.source_start_ms, fps);
  const trimAfter =
    layer.source_end_ms == null
      ? undefined
      : millisecondsToFrames(layer.source_end_ms, fps);

  return (
    <div
      data-production-layer={layer.id}
      data-source-role={layer.source_role}
      data-shot-id={layer.shot_id}
      style={{
        position: "absolute",
        left: layer.bounds.x,
        top: layer.bounds.y,
        width: layer.bounds.width,
        height: layer.bounds.height,
        overflow: "hidden",
        borderRadius: layer.border_radius,
        zIndex: layer.z_index,
        opacity,
        mixBlendMode: layer.blend_mode,
        transform: `translate(${transform.x + motionX}px, ${transform.y + motionY}px) scale(${transform.scale + motionScale}) rotate(${transform.rotate_deg}deg)`,
        transformOrigin: "center",
        background: layerBackground,
        boxShadow:
          layer.border_radius > 0
            ? "0 22px 70px rgba(0,0,0,0.34)"
            : undefined,
      }}
    >
      {layer.kind === "video" ? (
        <Video
          src={source}
          trimBefore={trimBefore}
          trimAfter={trimAfter}
          playbackRate={layer.playback_rate}
          muted={layer.muted}
          loop={layer.loop}
          objectFit={layer.fit}
          style={{
            ...cropStyle,
            filter: mediaFilter,
          }}
        />
      ) : (
        <Img
          src={source}
          style={{
            ...cropStyle,
            objectFit: layer.fit,
            filter: mediaFilter,
          }}
        />
      )}
      {layer.illustrative_label ? (
        <div
          data-illustrative-label="true"
          style={{
            position: "absolute",
            top: 18,
            right: 18,
            padding: "7px 11px",
            border: "1px solid rgba(255,255,255,0.22)",
            borderRadius: 5,
            color: "rgba(255,255,255,0.86)",
            background: "rgba(5,8,9,0.76)",
            fontFamily:
              '"Share Tech Mono", "IBM Plex Mono", monospace',
            fontSize: 18,
            letterSpacing: "0.08em",
          }}
        >
          ILLUSTRATIVE
        </div>
      ) : null}
    </div>
  );
};

export const ProductionVisualLayer: React.FC<{
  layer: Layer;
  assets: ProductionEditPlan["assets"];
  motionEvents: ProductionEditPlan["motion_events"];
}> = ({ layer, assets, motionEvents }) => {
  const { fps } = useVideoConfig();
  const asset = assets.find((candidate) => candidate.id === layer.asset_id);
  if (!asset) {
    throw new Error(`Missing production asset: ${layer.asset_id}`);
  }
  const from = millisecondsToFrames(layer.start_ms, fps);
  const until = millisecondsToFrames(layer.end_ms, fps);
  return (
    <Sequence
      from={from}
      durationInFrames={Math.max(1, until - from)}
      premountFor={fps}
      name={`${layer.shot_id}: ${layer.source_role}`}
    >
      <LayerMedia
        layer={layer}
        asset={asset}
        motionEvents={motionEvents}
      />
    </Sequence>
  );
};
