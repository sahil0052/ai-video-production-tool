import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface AnimatedBalanceMeterProps {
  startFrame?: number;
  durationFrames?: number;
  startBalance?: number;
  endBalance?: number;
}

export const AnimatedBalanceMeter: React.FC<AnimatedBalanceMeterProps> = ({
  startFrame = 0,
  durationFrames = 45,
  startBalance = 10000,
  endBalance = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const relFrame = Math.max(0, frame - startFrame);

  const progress = interpolate(relFrame, [0, durationFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const currentBal = Math.round(interpolate(progress, [0, 1], [startBalance, endBalance]));
  const pctRemaining = interpolate(progress, [0, 1], [100, 0]);

  const badgeScale = spring({
    frame: Math.max(0, relFrame - 25),
    fps,
    config: { damping: 12, stiffness: 200, mass: 0.5 },
  });

  return (
    <div
      style={{
        width: 820,
        backgroundColor: "#FFFFFF",
        borderRadius: "20px",
        border: "4px solid #1A1A1A",
        padding: "32px",
        boxShadow: "0 20px 48px rgba(0,0,0,0.25)",
        fontFamily: "'Share Tech Mono', 'Consolas', monospace",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <span style={{ fontSize: "28px", fontWeight: 900, color: "#1A1A1A", letterSpacing: "1px" }}>
          ACCOUNT CAPITAL:
        </span>
        <span style={{ fontSize: "52px", fontWeight: 900, color: currentBal > 2000 ? "#00E5FF" : "#D62E1F" }}>
          ${currentBal.toLocaleString()}
        </span>
      </div>

      {/* Meter Bar Container */}
      <div
        style={{
          width: "100%",
          height: "44px",
          backgroundColor: "#E5E0D8",
          borderRadius: "12px",
          overflow: "hidden",
          border: "2px solid #1A1A1A",
          position: "relative",
        }}
      >
        <div
          style={{
            width: `${pctRemaining}%`,
            height: "100%",
            backgroundColor: pctRemaining > 30 ? "#00E5FF" : "#D62E1F",
            transition: "width 0.1s",
          }}
        />
      </div>

      {/* Warning Stamp */}
      {relFrame >= 25 && (
        <div
          style={{
            marginTop: "20px",
            display: "flex",
            justifyContent: "center",
            transform: `scale(${badgeScale})`,
          }}
        >
          <div
            style={{
              padding: "10px 32px",
              backgroundColor: "#D62E1F",
              color: "#FFFFFF",
              fontWeight: 900,
              fontSize: "36px",
              borderRadius: "10px",
              letterSpacing: "2px",
              boxShadow: "0 8px 24px rgba(214,46,31,0.4)",
            }}
          >
            ⚠️ 100% CAPITAL DRAINED!
          </div>
        </div>
      )}
    </div>
  );
};
