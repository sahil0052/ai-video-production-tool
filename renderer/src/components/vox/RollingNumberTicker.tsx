import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface RollingNumberTickerProps {
  startValue?: number;
  endValue: number;
  prefix?: string;
  suffix?: string;
  startFrame?: number;
  durationFrames?: number;
  color?: string;
  fontSize?: number;
}

export const RollingNumberTicker: React.FC<RollingNumberTickerProps> = ({
  startValue = 0,
  endValue,
  prefix = "",
  suffix = "",
  startFrame = 0,
  durationFrames = 20,
  color = "#1A1A1A",
  fontSize = 110,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const relFrame = Math.max(0, frame - startFrame);

  // Spring physics for rapid odometer spin with slight overshoot
  const progress = spring({
    frame: relFrame,
    fps,
    config: { damping: 14, stiffness: 120, mass: 0.6 },
  });

  const currentValue = Math.round(
    interpolate(progress, [0, 1], [startValue, endValue], {
      extrapolateRight: "clamp",
    })
  );

  const scale = spring({
    frame: relFrame,
    fps,
    config: { damping: 12, stiffness: 160, mass: 0.4 },
  });

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "'Anton', 'Barlow Condensed', sans-serif",
        fontWeight: 900,
        fontSize: `${fontSize}px`,
        color,
        letterSpacing: "-2px",
        transform: `scale(${scale})`,
        textShadow: "0 8px 24px rgba(0,0,0,0.18)",
        lineHeight: 1,
      }}
    >
      <span>{prefix}</span>
      <span>{currentValue}</span>
      <span style={{ color: "#D62E1F" }}>{suffix}</span>
    </div>
  );
};
