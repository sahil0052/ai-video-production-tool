import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface AnimatedStockChartProps {
  startFrame?: number;
  durationFrames?: number;
  width?: number;
  height?: number;
  isCrashing?: boolean;
}

export const AnimatedStockChart: React.FC<AnimatedStockChartProps> = ({
  startFrame = 0,
  durationFrames = 60,
  width = 860,
  height = 360,
  isCrashing = false,
}) => {
  const frame = useCurrentFrame();
  const relFrame = Math.max(0, frame - startFrame);

  const progress = interpolate(relFrame, [0, durationFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // 12 Candlestick bars with heights and colors
  const candles = [
    { x: 50, y: 180, h: 60, isGreen: true },
    { x: 110, y: 150, h: 80, isGreen: true },
    { x: 170, y: 190, h: 50, isGreen: false },
    { x: 230, y: 130, h: 90, isGreen: true },
    { x: 290, y: 110, h: 70, isGreen: true },
    { x: 350, y: 140, h: 60, isGreen: false },
    { x: 410, y: 90, h: 110, isGreen: true },
    { x: 470, y: 160, h: 80, isGreen: false },
    { x: 530, y: isCrashing ? 260 : 120, h: isCrashing ? 140 : 70, isGreen: !isCrashing },
    { x: 590, y: isCrashing ? 310 : 100, h: isCrashing ? 160 : 80, isGreen: !isCrashing },
    { x: 650, y: isCrashing ? 340 : 130, h: isCrashing ? 190 : 60, isGreen: !isCrashing },
    { x: 710, y: isCrashing ? 350 : 90, h: isCrashing ? 200 : 90, isGreen: !isCrashing },
  ];

  return (
    <div
      style={{
        width,
        height,
        position: "relative",
        backgroundColor: "rgba(255, 255, 255, 0.75)",
        borderRadius: "16px",
        border: "3px solid #1A1A1A",
        boxShadow: "0 16px 36px rgba(0,0,0,0.15)",
        padding: "20px",
        overflow: "hidden",
      }}
    >
      {/* Grid Lines */}
      <svg width="100%" height="100%" style={{ position: "absolute", top: 0, left: 0, opacity: 0.2 }}>
        <line x1="0" y1="90" x2="100%" y2="90" stroke="#1A1A1A" strokeDasharray="4 4" />
        <line x1="0" y1="180" x2="100%" y2="180" stroke="#1A1A1A" strokeDasharray="4 4" />
        <line x1="0" y1="270" x2="100%" y2="270" stroke="#1A1A1A" strokeDasharray="4 4" />
      </svg>

      <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`}>
        {candles.map((c, i) => {
          const candleProgress = interpolate(progress, [i / candles.length, (i + 1) / candles.length], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          if (candleProgress <= 0) return null;

          const fill = c.isGreen ? "#00E5FF" : "#D62E1F";
          const currentH = c.h * candleProgress;

          return (
            <g key={i}>
              {/* Wick */}
              <line
                x1={c.x + 12}
                y1={c.y - 20}
                x2={c.x + 12}
                y2={c.y + currentH + 20}
                stroke={fill}
                strokeWidth="3"
              />
              {/* Candle Body */}
              <rect
                x={c.x}
                y={c.y}
                width="24"
                height={currentH}
                fill={fill}
                stroke="#1A1A1A"
                strokeWidth="2"
                rx="3"
              />
            </g>
          );
        })}
      </svg>
    </div>
  );
};
