import { Video } from "@remotion/media";
import { Img, staticFile } from "remotion";

import type { EditPlan } from "../schema";

type Props = {
  assets: EditPlan["assets"];
  timeMs: number;
  entranceProgress: number;
  layout: EditPlan["scenes"][number]["layout"];
};

export const findActiveAsset = (
  assets: EditPlan["assets"],
  timeMs: number,
) =>
  assets.find(
    (candidate) =>
      candidate.start_ms != null &&
      candidate.end_ms != null &&
      candidate.start_ms <= timeMs &&
      candidate.end_ms > timeMs &&
      (candidate.kind === "image" || candidate.kind === "video"),
  );

export const AssetLayer: React.FC<Props> = ({
  assets,
  timeMs,
  entranceProgress,
  layout,
}) => {
  const asset = findActiveAsset(assets, timeMs);
  if (!asset) {
    return null;
  }
  const dominant =
    layout === "asset-full" || layout === "presenter-pip";
  const source = staticFile(asset.path);
  const durationMs = Math.max(
    1,
    (asset.end_ms ?? timeMs + 1) - (asset.start_ms ?? timeMs),
  );
  const localProgress = Math.min(
    1,
    Math.max(0, (timeMs - (asset.start_ms ?? timeMs)) / durationMs),
  );
  const driftX = Math.sin(localProgress * Math.PI * 2) * 4;
  const driftY = Math.cos(localProgress * Math.PI) * 3;
  const continuousScale = 1.01 + localProgress * 0.018;
  const mediaStyle: React.CSSProperties = {
    width: "100%",
    height: "100%",
    objectFit: dominant && asset.kind === "image" ? "contain" : "cover",
    transform:
      asset.kind === "image"
        ? `translate3d(${driftX}px, ${driftY}px, 0) scale(${continuousScale})`
        : undefined,
    transformOrigin: "center",
  };
  return (
    <div
      data-asset-kind={asset.kind}
      data-asset-layout={layout}
      style={{
        position: "absolute",
        zIndex: 20,
        ...(dominant
          ? { inset: 0 }
          : {
              top: 90,
              left: 54,
              right: 54,
              height: 690,
            }),
        overflow: "hidden",
        border: dominant
          ? "none"
          : "2px solid rgba(255,255,255,0.16)",
        borderRadius: dominant ? 0 : 28,
        background: "#0B0E12",
        boxShadow: dominant
          ? "none"
          : "0 28px 70px rgba(0,0,0,0.48)",
        opacity: entranceProgress,
        transform: dominant
          ? `scale(${0.985 + entranceProgress * 0.015})`
          : `translateY(${(1 - entranceProgress) * 30}px) scale(${0.94 + entranceProgress * 0.06})`,
      }}
    >
      {dominant && asset.kind === "image" ? (
        <Img
          src={source}
          style={{
            position: "absolute",
            inset: -40,
            width: "calc(100% + 80px)",
            height: "calc(100% + 80px)",
            objectFit: "cover",
            filter: "blur(30px) saturate(0.78) brightness(0.48)",
            opacity: 0.72,
            transform: "scale(1.08)",
          }}
        />
      ) : null}
      {asset.kind === "image" ? (
        <div style={{ position: "absolute", inset: 0 }}>
          <Img src={source} style={mediaStyle} />
        </div>
      ) : (
        <Video
          src={source}
          muted
          loop
          objectFit="cover"
          style={{ width: "100%", height: "100%" }}
        />
      )}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            dominant
              ? "linear-gradient(180deg, rgba(8,10,13,0.12) 0%, transparent 48%, rgba(8,10,13,0.36) 100%)"
              : "linear-gradient(180deg, transparent 62%, rgba(8,10,13,0.46))",
          pointerEvents: "none",
        }}
      />
    </div>
  );
};
