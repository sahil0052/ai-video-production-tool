import { spring, useCurrentFrame, useVideoConfig } from "remotion";

import type { ProductionEditPlan } from "../productionSchema";
import { millisecondsToFrames } from "../timing";

type CaptionPage = ProductionEditPlan["caption_pages"][number];
type CaptionToken = CaptionPage["tokens"][number];

export const MARKER_COLOR = "#FFD700";

/**
 * Elastic word pop-in spring, tuned per the mission brief:
 * mass 0.4 / damping 10 / stiffness 220.
 */
export const wordPopInScale = (
  frame: number,
  fps: number,
  wordStartFrame: number,
) => {
  if (frame < wordStartFrame) {
    return 0.86;
  }
  return spring({
    frame: frame - wordStartFrame,
    fps,
    config: { mass: 0.4, damping: 10, stiffness: 220, overshootClamping: false },
    from: 0.86,
    to: 1,
  });
};

/**
 * Marker-swipe fill progress for a single word: 0 before the word starts,
 * 1 once the word's own spoken duration has fully elapsed. Driven by the
 * word's real start/end timestamps, not a fixed duration, so the swipe
 * always finishes exactly when the word finishes being spoken.
 */
export const markerSwipeProgress = (
  timeMs: number,
  token: Pick<CaptionToken, "start_ms" | "end_ms">,
) => {
  if (timeMs <= token.start_ms) {
    return 0;
  }
  if (timeMs >= token.end_ms) {
    return 1;
  }
  return (timeMs - token.start_ms) / (token.end_ms - token.start_ms);
};

type WordProps = {
  token: CaptionToken;
  timeMs: number;
  fps: number;
  frame: number;
  fontSize: number;
  fontFamily: string;
  fontWeight: number;
  letterSpacing: string;
  color: string;
};

/**
 * A single word: elastic pop-in on arrival, then a left-to-right marker
 * highlighter swipe in #FFD700 synchronized to its own word_timestamps
 * window (via markerSwipeProgress), matching the brief's
 * "word-by-word active marker-swipe kinetic captions" requirement.
 */
export const KineticWord: React.FC<WordProps> = ({
  token,
  timeMs,
  fps,
  frame,
  fontSize,
  fontFamily,
  fontWeight,
  letterSpacing,
  color,
}) => {
  const wordStartFrame = millisecondsToFrames(token.start_ms, fps);
  const scale = wordPopInScale(frame, fps, wordStartFrame);
  const swipe = markerSwipeProgress(timeMs, token);
  const isActive = timeMs >= token.start_ms && timeMs < token.end_ms;
  const hasPassed = timeMs >= token.end_ms;

  return (
    <span
      data-kinetic-word={token.text}
      data-word-active={isActive ? "true" : undefined}
      style={{
        position: "relative",
        display: "inline-block",
        transform: `scale(${scale})`,
        transformOrigin: "bottom center",
        marginRight: "0.28em",
      }}
    >
      <span
        aria-hidden
        data-marker-swipe="true"
        style={{
          position: "absolute",
          left: 0,
          bottom: "0.02em",
          height: "0.62em",
          width: `${Math.max(0, Math.min(1, swipe)) * 100}%`,
          background: MARKER_COLOR,
          opacity: 0.92,
          borderRadius: 2,
          zIndex: 0,
          transition: "none",
        }}
      />
      <span
        style={{
          position: "relative",
          zIndex: 1,
          fontFamily,
          fontSize,
          fontWeight,
          letterSpacing,
          color: hasPassed || isActive ? "#111111" : color,
        }}
      >
        {token.text}
      </span>
    </span>
  );
};

type Props = {
  page: CaptionPage;
  timeMs: number;
  fontSize: number;
  fontFamily: string;
  fontWeight: number;
  letterSpacing: string;
  color: string;
};

/**
 * Renders every token in the active caption page with word-by-word
 * elastic pop-in + marker-swipe highlight. Drop-in companion to
 * CaptionLayer for pages that opt into a "kinetic-marker" treatment.
 * Auto-wraps and shrinks: consumers should compute fontSize the same
 * way CaptionLayer.fittedFontSize does and pass a maxWidth wrapper
 * around this component to keep the presenter's face uncovered.
 */
export const KineticWordHighlight: React.FC<Props> = ({
  page,
  timeMs,
  fontSize,
  fontFamily,
  fontWeight,
  letterSpacing,
  color,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div
      data-caption-kinetic-marker="true"
      style={{
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
        alignItems: "baseline",
        rowGap: "0.15em",
      }}
    >
      {page.tokens.map((token, index) => (
        <KineticWord
          key={`${token.start_ms}-${token.end_ms}-${index}`}
          token={token}
          timeMs={timeMs}
          fps={fps}
          frame={frame}
          fontSize={fontSize}
          fontFamily={fontFamily}
          fontWeight={fontWeight}
          letterSpacing={letterSpacing}
          color={color}
        />
      ))}
    </div>
  );
};
