import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

export interface ParallaxDioramaLayerProps {
  imageSrc: string;
  cameraMotion?: "push_in" | "pan_left" | "dive_down" | "float";
  durationInFrames: number;
  children?: React.ReactNode;
}

export const ParallaxDioramaLayer: React.FC<ParallaxDioramaLayerProps> = ({
  imageSrc,
  cameraMotion = "push_in",
  durationInFrames,
  children,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const prog = interpolate(frame, [0, durationInFrames], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Smooth Bezier Easing
  const ease = prog * prog * (3 - 2 * prog);

  let bgScale = 1.0;
  let bgTranslateX = 0;
  let bgTranslateY = 0;

  if (cameraMotion === "push_in") {
    bgScale = 1.0 + 0.12 * ease;
  } else if (cameraMotion === "pan_left") {
    bgScale = 1.06;
    bgTranslateX = -40 * ease;
  } else if (cameraMotion === "dive_down") {
    bgScale = 1.08;
    bgTranslateY = -35 * ease;
  } else {
    bgScale = 1.03 + 0.02 * Math.sin(frame * 0.05);
  }

  // 3-layer parallax foreground spring bounce
  const fgSpring = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 100, mass: 0.5 },
  });

  return (
    <AbsoluteFill
      style={{
        width: 1080,
        height: 960,
        overflow: "hidden",
        backgroundColor: "#C9BB9C",
      }}
    >
      {/* Layer 1: Background Plate with 3D Camera Drift */}
      <div
        style={{
          position: "absolute",
          width: "100%",
          height: "100%",
          transform: `scale(${bgScale}) translate(${bgTranslateX}px, ${bgTranslateY}px)`,
          transformOrigin: "center center",
        }}
      >
        <Img
          src={imageSrc.startsWith("http") || imageSrc.startsWith("/") ? imageSrc : staticFile(imageSrc)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
        {/* Subtle Print Grain Overlay */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(26, 26, 26, 0.03)",
            mixBlendMode: "multiply",
            pointerEvents: "none",
          }}
        />
      </div>

      {/* Layer 2: Interactive Motion Overlays (Tickers, Stamps, Marker Swipes) */}
      <AbsoluteFill
        style={{
          transform: `translateY(${interpolate(fgSpring, [0, 1], [30, 0])}px)`,
          pointerEvents: "none",
        }}
      >
        {children}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
