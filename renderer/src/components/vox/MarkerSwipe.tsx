import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";

export interface MarkerSwipeProps {
  type?: "underline" | "cross_out" | "circle";
  width?: number;
  height?: number;
  color?: string;
  startFrame?: number;
  durationFrames?: number;
}

export const MarkerSwipe: React.FC<MarkerSwipeProps> = ({
  type = "underline",
  width = 380,
  height = 40,
  color = "#D62E1F",
  startFrame = 0,
  durationFrames = 12,
}) => {
  const frame = useCurrentFrame();
  const relFrame = Math.max(0, frame - startFrame);

  const progress = interpolate(relFrame, [0, durationFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  if (type === "cross_out") {
    // Red "X" cross-out
    return (
      <svg width={width} height={height} viewBox="0 0 100 100" style={{ overflow: "visible" }}>
        <line
          x1="10"
          y1="10"
          x2="90"
          y2="90"
          stroke={color}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray="120"
          strokeDashoffset={120 * (1 - Math.min(1, progress * 2))}
        />
        <line
          x1="90"
          y1="10"
          x2="10"
          y2="90"
          stroke={color}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray="120"
          strokeDashoffset={120 * (1 - Math.max(0, (progress - 0.5) * 2))}
        />
      </svg>
    );
  }

  // Real-time organic felt-tip underline stroke
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} 24`} style={{ overflow: "visible" }}>
      <path
        d={`M 4,14 Q ${width * 0.25},6 ${width * 0.5},12 T ${width - 4},10`}
        fill="none"
        stroke={color}
        strokeWidth="12"
        strokeLinecap="round"
        strokeDasharray={width + 50}
        strokeDashoffset={(width + 50) * (1 - progress)}
        style={{ filter: "drop-shadow(0 2px 4px rgba(214,46,31,0.3))" }}
      />
    </svg>
  );
};
