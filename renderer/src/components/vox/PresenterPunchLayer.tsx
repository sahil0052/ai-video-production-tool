import React from "react";
import { AbsoluteFill, OffthreadVideo, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

export interface PunchZoomCue {
  startFrame: number;
  durationFrames: number;
  scale: number;
}

export interface PresenterPunchLayerProps {
  videoSrc: string;
  punchCues?: PunchZoomCue[];
}

export const PresenterPunchLayer: React.FC<PresenterPunchLayerProps> = ({
  videoSrc,
  punchCues = [],
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Determine active scale punch
  let currentScale = 1.0;
  for (const cue of punchCues) {
    if (frame >= cue.startFrame && frame < cue.startFrame + cue.durationFrames) {
      const rel = frame - cue.startFrame;
      const s = spring({
        frame: rel,
        fps,
        config: { damping: 12, stiffness: 180, mass: 0.4 },
      });
      currentScale = 1.0 + (cue.scale - 1.0) * s;
      break;
    }
  }

  return (
    <AbsoluteFill
      style={{
        top: 960,
        width: 1080,
        height: 960,
        overflow: "hidden",
        backgroundColor: "#0B1012",
      }}
    >
      {/* Scaled Presenter Video */}
      <div
        style={{
          position: "absolute",
          width: 1080,
          height: 1920,
          top: -380,
          transform: `scale(${currentScale})`,
          transformOrigin: "540px 860px",
        }}
      >
        <OffthreadVideo
          src={videoSrc.startsWith("http") || videoSrc.startsWith("/") ? videoSrc : staticFile(videoSrc)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
      </div>

      {/* Archival Studio Dark Vignette */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: "radial-gradient(ellipse at center, transparent 60%, rgba(11,16,18,0.7) 100%)",
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};
