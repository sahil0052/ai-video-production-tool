import { Easing, interpolate } from "remotion";

import type { ProductionEditPlan } from "../productionSchema";

type Cue = ProductionEditPlan["kinetic_text_cues"][number];
type Family = Cue["family"];
type Animation = Cue["animation"];

type KineticStyle = {
  fontFamily: string;
  fontSize: number;
  fontWeight: number;
  lineHeight: number;
  letterSpacing: string;
  color: string;
  textShadow: string;
  stroke?: string;
  textTransform: React.CSSProperties["textTransform"];
  gradient?: string;
  extrusionColor?: string;
  extrusionOffsetPx?: number;
  foregroundFilter?: string;
};

export const kineticFamilyStyles: Record<Family, KineticStyle> = {
  "serif-hook": {
    fontFamily: '"Georgia", "Times New Roman", serif',
    fontSize: 92,
    fontWeight: 700,
    lineHeight: 0.94,
    letterSpacing: "-0.045em",
    color: "#F6F2E8",
    textShadow:
      "0 3px 4px rgba(0,0,0,0.9), 0 12px 30px rgba(0,0,0,0.58)",
    textTransform: "uppercase",
  },
  "hero-condensed": {
    fontFamily: '"Anton", "Arial Narrow", sans-serif',
    fontSize: 196,
    fontWeight: 400,
    lineHeight: 0.88,
    letterSpacing: "-0.025em",
    color: "#F7FF38",
    textShadow: "none",
    textTransform: "uppercase",
    gradient: "linear-gradient(180deg, #FFFFDE 0%, #FFFF54 42%, #EEFF00 100%)",
    extrusionColor: "#111300",
    extrusionOffsetPx: 8,
    foregroundFilter: "drop-shadow(0 8px 10px rgba(0,0,0,0.72))",
  },
  "outlined-stack": {
    fontFamily: '"Montserrat", Arial, sans-serif',
    fontSize: 114,
    fontWeight: 800,
    lineHeight: 0.9,
    letterSpacing: "-0.055em",
    color: "#FFFFFF",
    textShadow: "0 10px 26px rgba(0,0,0,0.68)",
    stroke: "9px #050505",
    textTransform: "uppercase",
  },
  "cyan-secondary": {
    fontFamily: '"Barlow Condensed", "Arial Narrow", sans-serif',
    fontSize: 90,
    fontWeight: 900,
    lineHeight: 0.9,
    letterSpacing: "-0.025em",
    color: "#52E7FF",
    textShadow:
      "0 4px 0 #093C48, 0 10px 22px rgba(0,0,0,0.64)",
    textTransform: "uppercase",
  },
  "gradient-number": {
    fontFamily: '"Anton", "Arial Narrow", sans-serif',
    fontSize: 156,
    fontWeight: 400,
    lineHeight: 0.92,
    letterSpacing: "-0.02em",
    color: "#FFFFFF",
    textShadow:
      "0 0 4px rgba(255,255,255,0.9), 0 0 12px rgba(191,255,74,0.7), 0 8px 18px rgba(0,0,0,0.68)",
    stroke: "2px rgba(24,45,0,0.72)",
    textTransform: "uppercase",
    gradient: "linear-gradient(180deg, #FFFFFF 0%, #E7FFB4 48%, #8DFF39 100%)",
  },
  "correction-symbol": {
    fontFamily: '"Montserrat", Arial, sans-serif',
    fontSize: 112,
    fontWeight: 800,
    lineHeight: 0.92,
    letterSpacing: "-0.055em",
    color: "#FF2525",
    textShadow: "0 7px 18px rgba(0,0,0,0.75)",
    stroke: "5px #111111",
    textTransform: "uppercase",
  },
  "cta-quote": {
    fontFamily: '"Anton", "Arial Narrow", sans-serif',
    fontSize: 138,
    fontWeight: 400,
    lineHeight: 0.94,
    letterSpacing: "-0.015em",
    color: "#FFE873",
    textShadow: "none",
    textTransform: "none",
    gradient: "linear-gradient(180deg, #FFFFF0 0%, #FFE85A 58%, #FFC400 100%)",
    extrusionColor: "#2A2100",
    extrusionOffsetPx: 8,
    foregroundFilter:
      "drop-shadow(0 0 9px rgba(255,226,94,0.55)) drop-shadow(0 9px 12px rgba(0,0,0,0.74))",
  },
  "micro-source": {
    fontFamily: '"Montserrat", Arial, sans-serif',
    fontSize: 24,
    fontWeight: 700,
    lineHeight: 1.05,
    letterSpacing: "0.035em",
    color: "rgba(255,255,255,0.9)",
    textShadow: "0 2px 5px rgba(0,0,0,0.9)",
    textTransform: "uppercase",
  },
};

export const resolveKineticCueMotion = (
  animation: Animation,
  localTimeMs: number,
  durationMs: number,
) => {
  const enterDuration = Math.min(240, Math.max(120, durationMs * 0.28));
  const enter = interpolate(localTimeMs, [0, enterDuration], [0, 1], {
    easing: Easing.bezier(0.16, 1, 0.3, 1),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const exitDuration = animation === "draw" ? 320 : 120;
  const exit = interpolate(
    localTimeMs,
    [Math.max(enterDuration, durationMs - exitDuration), durationMs],
    [1, 0],
    {
      easing: Easing.in(Easing.cubic),
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    },
  );
  const opacity = animation === "hard-cut" ? 1 : Math.min(enter, exit);
  const scale =
    animation === "slam"
      ? interpolate(enter, [0, 1], [1.28, 1])
      : animation === "quote-pop"
        ? interpolate(enter, [0, 1], [0.82, 1])
        : animation === "glow"
          ? interpolate(enter, [0, 1], [0.94, 1])
          : 1;
  const translateY =
    animation === "rise" || animation === "stack"
      ? interpolate(enter, [0, 1], [34, 0])
      : 0;
  const translateX =
    animation === "draw"
      ? interpolate(enter, [0, 1], [-28, 0])
      : 0;
  return { opacity, scale, translateX, translateY };
};

const KineticCue: React.FC<{ cue: Cue; timeMs: number }> = ({
  cue,
  timeMs,
}) => {
  const style = kineticFamilyStyles[cue.family];
  const localTimeMs = timeMs - cue.start_ms;
  const motion = resolveKineticCueMotion(
    cue.animation,
    localTimeMs,
    cue.end_ms - cue.start_ms,
  );
  const gradient = cue.accent
    ? `linear-gradient(180deg, #FFFFFF 0%, ${cue.accent} 100%)`
    : style.gradient;
  const isCorrection = cue.family === "correction-symbol";
  const isMicroSource = cue.family === "micro-source";
  const sharedTextStyle: React.CSSProperties = {
    fontFamily: style.fontFamily,
    fontSize: style.fontSize,
    fontWeight: style.fontWeight,
    lineHeight: style.lineHeight,
    letterSpacing: style.letterSpacing,
    WebkitTextStroke: style.stroke,
    paintOrder: style.stroke ? "stroke fill" : undefined,
    textTransform: style.textTransform,
  };

  return (
    <div
      data-kinetic-text={cue.id}
      data-kinetic-family={cue.family}
      style={{
        position: "absolute",
        zIndex: cue.z_index,
        left: cue.x,
        top: cue.y,
        width: cue.max_width,
        transform: `translate(-50%, -50%) translate(${motion.translateX}px, ${motion.translateY}px) scale(${motion.scale}) rotate(${cue.rotation_deg}deg)`,
        transformOrigin: "center",
        opacity: motion.opacity,
        textAlign: cue.align,
        pointerEvents: "none",
        whiteSpace: "pre-line",
      }}
    >
      <div style={{ position: "relative" }}>
        {style.extrusionColor ? (
          <div
            aria-hidden
            data-kinetic-paint="extrusion"
            style={{
              ...sharedTextStyle,
              position: "absolute",
              inset: 0,
              color: style.extrusionColor,
              transform: `translateY(${style.extrusionOffsetPx ?? 7}px)`,
              textShadow: "0 13px 24px rgba(0,0,0,0.68)",
            }}
          >
            {cue.text}
          </div>
        ) : null}
        <div
          data-kinetic-paint="foreground"
          style={{
            ...sharedTextStyle,
            position: "relative",
            color: gradient ? "transparent" : style.color,
            backgroundImage: gradient,
            backgroundClip: gradient ? "text" : undefined,
            WebkitBackgroundClip: gradient ? "text" : undefined,
            WebkitTextFillColor: gradient ? "transparent" : undefined,
            textShadow: style.textShadow,
            filter: style.foregroundFilter,
            display: isMicroSource ? "inline-block" : undefined,
            backgroundColor: isMicroSource
              ? "rgba(3, 18, 42, 0.9)"
              : undefined,
            padding: isMicroSource ? "10px 18px 11px" : undefined,
            borderRadius: isMicroSource ? 10 : undefined,
            boxShadow: isMicroSource
              ? "0 6px 18px rgba(0, 0, 0, 0.35)"
              : undefined,
          }}
        >
          {cue.text}
        </div>
      </div>
      {cue.secondary_text ? (
        <div
          style={{
            marginTop: isCorrection ? 10 : 12,
            marginLeft: 0,
            color: isCorrection ? "#29DD3E" : cue.accent ?? "#52E7FF",
            fontFamily: '"Montserrat", Arial, sans-serif',
            fontSize: isCorrection ? 132 : 54,
            fontWeight: 900,
            lineHeight: 0.8,
            WebkitTextStroke: isCorrection ? "4px #111111" : undefined,
            paintOrder: isCorrection ? "stroke fill" : undefined,
            textShadow: "0 7px 16px rgba(0,0,0,0.72)",
          }}
        >
          {cue.secondary_text}
        </div>
      ) : null}
    </div>
  );
};

export const KineticTextLayer: React.FC<{
  cues: ProductionEditPlan["kinetic_text_cues"];
  timeMs: number;
}> = ({ cues, timeMs }) => (
  <>
    {cues
      .filter((cue) => cue.start_ms <= timeMs && cue.end_ms > timeMs)
      .map((cue) => (
        <KineticCue key={cue.id} cue={cue} timeMs={timeMs} />
      ))}
  </>
);
