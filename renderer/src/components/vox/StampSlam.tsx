import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface StampSlamProps {
  text: string;
  subText?: string;
  color?: string;
  borderColor?: string;
  rotation?: number;
  startFrame?: number;
  fontSize?: number;
}

export const StampSlam: React.FC<StampSlamProps> = ({
  text,
  subText,
  color = "#D62E1F",
  borderColor = "#D62E1F",
  rotation = -8,
  startFrame = 0,
  fontSize = 54,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const relFrame = Math.max(0, frame - startFrame);

  // Slam from 2.5x scale down to 1.0x in ~5 frames with elastic spring
  const scale = spring({
    frame: relFrame,
    fps,
    config: { damping: 10, stiffness: 220, mass: 0.5 },
  });

  const opacity = interpolate(relFrame, [0, 2], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Micro-impact jitter on landing
  const impactShake = relFrame >= 3 && relFrame <= 7 ? (relFrame % 2 === 0 ? 3 : -3) : 0;

  return (
    <div
      style={{
        display: "inline-flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "10px 28px",
        border: `8px solid ${borderColor}`,
        borderRadius: "10px",
        backgroundColor: "rgba(255, 255, 255, 0.92)",
        boxShadow: "0 12px 32px rgba(0,0,0,0.35), inset 0 0 12px rgba(214,46,31,0.15)",
        transform: `translateY(${impactShake}px) rotate(${rotation}deg) scale(${scale})`,
        opacity,
        fontFamily: "'Anton', 'Barlow Condensed', sans-serif",
        textTransform: "uppercase",
        letterSpacing: "3px",
        lineHeight: 1.1,
      }}
    >
      <span style={{ fontSize: `${fontSize}px`, color, fontWeight: 900 }}>{text}</span>
      {subText && (
        <span style={{ fontSize: `${fontSize * 0.42}px`, color: "#1A1A1A", letterSpacing: "1px" }}>
          {subText}
        </span>
      )}
    </div>
  );
};
