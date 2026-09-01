import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface ChecklistPillarsProps {
  startFrame?: number;
}

export const ChecklistPillars: React.FC<ChecklistPillarsProps> = ({ startFrame = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const relFrame = Math.max(0, frame - startFrame);

  const items = [
    { title: "PREDEFINED RULES", desc: "Strict algorithmic entry & exit", delay: 0 },
    { title: "AUTOMATED RISK", desc: "Never risks >1% per trade", delay: 25 },
    { title: "ZERO EMOTIONS", desc: "No revenge trading or greed", delay: 50 },
  ];

  return (
    <div
      style={{
        width: 860,
        backgroundColor: "#FFFFFF",
        borderRadius: "24px",
        border: "4px solid #1A1A1A",
        padding: "32px",
        boxShadow: "0 20px 48px rgba(0,0,0,0.25)",
        display: "flex",
        flexDirection: "column",
        gap: "18px",
      }}
    >
      <div style={{ fontSize: "36px", fontWeight: 900, color: "#1A1A1A", fontFamily: "'Anton', sans-serif", letterSpacing: "1px" }}>
        🤖 EA BOT SYSTEM LOGIC:
      </div>

      {items.map((it, idx) => {
        const itemRel = Math.max(0, relFrame - it.delay);
        const slide = spring({
          frame: itemRel,
          fps,
          config: { damping: 14, stiffness: 180, mass: 0.5 },
        });

        const checkProgress = interpolate(itemRel, [5, 18], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });

        return (
          <div
            key={idx}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "20px",
              padding: "16px 24px",
              backgroundColor: "#F8F6F0",
              borderRadius: "14px",
              border: "2px solid #1A1A1A",
              transform: `translateX(${interpolate(slide, [0, 1], [-80, 0])}px)`,
              opacity: slide,
            }}
          >
            {/* Animated Checkmark Circle */}
            <svg width="48" height="48" viewBox="0 0 48 48">
              <circle cx="24" cy="24" r="20" fill="#00E5FF" stroke="#1A1A1A" strokeWidth="3" />
              <path
                d="M 14,24 L 21,31 L 34,17"
                fill="none"
                stroke="#1A1A1A"
                strokeWidth="4"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeDasharray="40"
                strokeDashoffset={40 * (1 - checkProgress)}
              />
            </svg>

            <div>
              <div style={{ fontSize: "28px", fontWeight: 900, color: "#1A1A1A", fontFamily: "'Barlow Condensed', sans-serif" }}>
                {it.title}
              </div>
              <div style={{ fontSize: "20px", color: "#555555", fontWeight: 600 }}>
                {it.desc}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
