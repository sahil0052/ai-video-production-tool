import React from "react";
import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface CaptionWordCue {
  startFrame: number;
  endFrame: number;
  text: string;
  highlight?: "cyan" | "red" | "none";
}

export interface KineticPillCaptionsProps {
  captions: CaptionWordCue[];
}

export const KineticPillCaptions: React.FC<KineticPillCaptionsProps> = ({ captions }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const active = captions.find((c) => frame >= c.startFrame && frame < c.endFrame);
  if (!active) return null;

  const relFrame = frame - active.startFrame;
  const scale = spring({
    frame: relFrame,
    fps,
    config: { damping: 14, stiffness: 200, mass: 0.4 },
  });

  const isRed = active.highlight === "red" || ["KYUN", "RISK", "MISTAKE", "CAPITAL", "EMOTIONS", "TESTED"].some(k => active.text.toUpperCase().includes(k));
  const isCyan = active.highlight === "cyan" || ["90%", "LOSE", "LEVERAGE", "REVENGE", "EA USE", "FOLLOW"].some(k => active.text.toUpperCase().includes(k));

  const textColor = isCyan ? "#00E5FF" : isRed ? "#FF4B4B" : "#FFFFFF";
  const bgBadge = isCyan ? "rgba(0, 229, 255, 0.15)" : isRed ? "rgba(214, 46, 31, 0.2)" : "rgba(11, 16, 18, 0.85)";
  const borderBadge = isCyan ? "2px solid #00E5FF" : isRed ? "2px solid #D62E1F" : "2px solid rgba(255,255,255,0.2)";

  return (
    <AbsoluteFill
      style={{
        top: 1620,
        height: 200,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "12px 32px",
          backgroundColor: bgBadge,
          border: borderBadge,
          borderRadius: "14px",
          backdropFilter: "blur(8px)",
          boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
          transform: `scale(${scale})`,
          fontFamily: "'Share Tech Mono', 'Consolas', monospace",
          fontSize: "44px",
          fontWeight: 900,
          color: textColor,
          textTransform: "uppercase",
          letterSpacing: "1px",
          textAlign: "center",
          maxWidth: "880px",
        }}
      >
        {active.text}
      </div>
    </AbsoluteFill>
  );
};
