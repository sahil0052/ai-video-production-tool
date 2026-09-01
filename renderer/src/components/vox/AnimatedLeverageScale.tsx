import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface AnimatedLeverageScaleProps {
  startFrame?: number;
}

export const AnimatedLeverageScale: React.FC<AnimatedLeverageScaleProps> = ({ startFrame = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const relFrame = Math.max(0, frame - startFrame);

  // Big block slams down on frame 12
  const dropProgress = spring({
    frame: Math.max(0, relFrame - 10),
    fps,
    config: { damping: 10, stiffness: 180, mass: 0.6 },
  });

  const beamAngle = interpolate(dropProgress, [0, 1], [0, 18]);

  return (
    <div
      style={{
        width: 860,
        height: 480,
        backgroundColor: "rgba(255, 255, 255, 0.85)",
        borderRadius: "24px",
        border: "4px solid #1A1A1A",
        boxShadow: "0 20px 48px rgba(0,0,0,0.2)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div style={{ position: "absolute", top: 24, fontSize: "38px", fontWeight: 900, color: "#1A1A1A", fontFamily: "'Anton', sans-serif" }}>
        LEVERAGE: <span style={{ color: "#D62E1F" }}>1:500 MULTIPLIER</span>
      </div>

      {/* The Physical Balance Scale */}
      <div style={{ marginTop: "60px", position: "relative", width: "700px", height: "300px" }}>
        {/* Fulcrum Triangle */}
        <svg width="80" height="80" viewBox="0 0 100 100" style={{ position: "absolute", left: "310px", bottom: "40px" }}>
          <polygon points="50,10 10,90 90,90" fill="#1A1A1A" />
        </svg>

        {/* The Rotating Beam */}
        <div
          style={{
            position: "absolute",
            left: "50px",
            bottom: "105px",
            width: "600px",
            height: "16px",
            backgroundColor: "#1A1A1A",
            borderRadius: "8px",
            transform: `rotate(${beamAngle}deg)`,
            transformOrigin: "300px center",
          }}
        >
          {/* Left Side: Tiny $100 Capital */}
          <div
            style={{
              position: "absolute",
              left: "-10px",
              bottom: "20px",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
            }}
          >
            <div
              style={{
                width: "64px",
                height: "64px",
                borderRadius: "50%",
                backgroundColor: "#D9A441",
                border: "3px solid #1A1A1A",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 900,
                fontSize: "20px",
                boxShadow: "0 6px 14px rgba(0,0,0,0.2)",
              }}
            >
              $100
            </div>
            <span style={{ fontSize: "18px", fontWeight: 900, color: "#1A1A1A", marginTop: "4px" }}>
              Capital
            </span>
          </div>

          {/* Right Side: Giant 500x Block */}
          <div
            style={{
              position: "absolute",
              right: "-20px",
              bottom: `${interpolate(dropProgress, [0, 1], [180, 20])}px`,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
            }}
          >
            <div
              style={{
                width: "160px",
                height: "140px",
                backgroundColor: "#D62E1F",
                border: "4px solid #1A1A1A",
                borderRadius: "14px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                color: "#FFFFFF",
                boxShadow: "0 14px 32px rgba(214,46,31,0.4)",
              }}
            >
              <span style={{ fontSize: "44px", fontWeight: 900, fontFamily: "'Anton', sans-serif" }}>500X</span>
              <span style={{ fontSize: "18px", fontWeight: 900 }}>$50,000 POS</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
