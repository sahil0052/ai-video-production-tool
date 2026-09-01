import type { EditPlan } from "../schema";

type Props = {
  pages: EditPlan["caption_pages"];
  timeMs: number;
  styleVariant: EditPlan["style_variant"];
  entranceProgress: number;
};

const anchorTop: Record<
  EditPlan["caption_pages"][number]["anchor"],
  string
> = {
  "center-69": "69%",
  "center-71": "71%",
  "center-74": "74%",
  "center-76": "76%",
  "center-78": "78%",
  "lower-82": "82%",
  "upper-46": "46%",
  "upper-56": "56%",
  "upper-62": "62%",
};

type CaptionStyle = {
  fontFamily: string;
  fontSize: number;
  minFontSize: number;
  fontWeight: number;
  letterSpacing: string;
  lineHeight: number;
  textTransform: React.CSSProperties["textTransform"];
  padding: string;
  borderRadius: number;
  background: string;
  boxShadow: string;
  textShadow: string;
  stroke?: string;
  allowWrap: boolean;
};

const familyStyles: Record<
  EditPlan["caption_pages"][number]["family"],
  CaptionStyle
> = {
  "technical-mono": {
    fontFamily: '"Share Tech Mono", "IBM Plex Mono", Consolas, monospace',
    fontSize: 33,
    minFontSize: 31,
    fontWeight: 400,
    letterSpacing: "0.01em",
    lineHeight: 1.04,
    textTransform: "uppercase",
    padding: "7px 12px",
    borderRadius: 5,
    background: "rgba(3, 4, 6, 0.94)",
    boxShadow: "0 5px 16px rgba(0, 0, 0, 0.36)",
    textShadow: "none",
    allowWrap: false,
  },
  "documentary-clean": {
    fontFamily: '"Inter Tight", Arial, sans-serif',
    fontSize: 36,
    minFontSize: 32,
    fontWeight: 800,
    letterSpacing: "-0.025em",
    lineHeight: 1.05,
    textTransform: "none",
    padding: "0",
    borderRadius: 0,
    background: "transparent",
    boxShadow: "none",
    textShadow:
      "0 2px 3px rgba(0,0,0,0.98), 0 0 14px rgba(0,0,0,0.78)",
    allowWrap: true,
  },
  "compact-pill": {
    fontFamily: '"Inter Tight", Arial, sans-serif',
    fontSize: 38,
    minFontSize: 34,
    fontWeight: 800,
    letterSpacing: "-0.025em",
    lineHeight: 1.02,
    textTransform: "none",
    padding: "8px 15px 9px",
    borderRadius: 12,
    background: "rgba(12, 13, 16, 0.9)",
    boxShadow: "0 7px 22px rgba(0, 0, 0, 0.42)",
    textShadow: "0 1px 5px rgba(0,0,0,0.55)",
    allowWrap: false,
  },
  "outlined-demo": {
    fontFamily: '"Inter Tight", Arial, sans-serif',
    fontSize: 58,
    minFontSize: 52,
    fontWeight: 800,
    letterSpacing: "-0.035em",
    lineHeight: 0.98,
    textTransform: "uppercase",
    padding: "0",
    borderRadius: 0,
    background: "transparent",
    boxShadow: "none",
    textShadow: "0 4px 14px rgba(0,0,0,0.9)",
    stroke: "4px rgba(0,0,0,0.96)",
    allowWrap: true,
  },
  "display-emphasis": {
    fontFamily: '"Inter Tight", Arial, sans-serif',
    fontSize: 78,
    minFontSize: 64,
    fontWeight: 800,
    letterSpacing: "-0.05em",
    lineHeight: 0.92,
    textTransform: "uppercase",
    padding: "0",
    borderRadius: 0,
    background: "transparent",
    boxShadow: "none",
    textShadow:
      "0 3px 3px rgba(0,0,0,0.9), 0 0 18px rgba(0,0,0,0.72)",
    allowWrap: true,
  },
};

const measureTextWidth = (
  text: string,
  style: CaptionStyle,
  fontSize: number,
) => {
  if (typeof document === "undefined") {
    return 0;
  }
  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d");
  if (!context) {
    return 0;
  }
  context.font = `${style.fontWeight} ${fontSize}px ${style.fontFamily}`;
  return context.measureText(text).width;
};

const fittedFontSize = (
  text: string,
  style: CaptionStyle,
  maxWidth: number,
) => {
  if (style.allowWrap) {
    return style.fontSize;
  }
  const measured = measureTextWidth(text, style, style.fontSize);
  if (measured === 0 || measured <= maxWidth) {
    return style.fontSize;
  }
  const fitted = Math.floor(style.fontSize * (maxWidth / measured));
  if (fitted < style.minFontSize) {
    throw new Error(
      `Caption overflow: "${text}" exceeds ${maxWidth}px for its family`,
    );
  }
  return fitted;
};

export const CaptionLayer: React.FC<Props> = ({
  pages,
  timeMs,
  entranceProgress,
}) => {
  const page = pages.find(
    (candidate) =>
      candidate.start_ms <= timeMs && candidate.end_ms > timeMs,
  );
  if (!page) {
    return null;
  }
  const style = familyStyles[page.family];
  const text = page.tokens.map((token) => token.text).join(" ");
  const fontSize = fittedFontSize(text, style, page.max_width);
  const animated = page.transition !== "hard-cut";
  const opacity = animated ? entranceProgress : 1;
  const translateY =
    page.transition === "fade-up" ? (1 - entranceProgress) * 12 : 0;
  const scale =
    page.transition === "scale-in"
      ? 0.96 + entranceProgress * 0.04
      : 1;

  return (
    <div
      data-caption-page="true"
      data-caption-family={page.family}
      data-caption-anchor={page.anchor}
      data-caption-transition={page.transition}
      style={{
        position: "absolute",
        zIndex: 40,
        top: anchorTop[page.anchor],
        left: 72,
        right: 72,
        display: "flex",
        justifyContent: "center",
        pointerEvents: "none",
        opacity,
        transform: `translateY(${translateY}px) scale(${scale})`,
        transformOrigin: "center",
      }}
    >
      <div
        style={{
          maxWidth: page.max_width,
          padding: style.padding,
          borderRadius: style.borderRadius,
          background: style.background,
          boxShadow: style.boxShadow,
          color: "white",
          fontFamily: style.fontFamily,
          fontSize,
          fontWeight: style.fontWeight,
          letterSpacing: style.letterSpacing,
          lineHeight: style.lineHeight,
          textAlign: "center",
          textTransform: style.textTransform,
          textShadow: style.textShadow,
          WebkitTextStroke: style.stroke,
          paintOrder: style.stroke ? "stroke fill" : undefined,
          whiteSpace: style.allowWrap ? "normal" : "nowrap",
          textWrap: style.allowWrap ? "balance" : undefined,
        }}
      >
        {page.tokens.map((token, index) => (
          <span
            key={`${token.start_ms}-${token.end_ms}-${index}`}
            data-static-highlight={
              token.highlighted ? "true" : undefined
            }
            style={{
              color:
                page.family === "display-emphasis" &&
                token.highlighted
                  ? "#D9FF45"
                  : "white",
            }}
          >
            {index > 0 ? " " : ""}
            {token.text}
          </span>
        ))}
      </div>
    </div>
  );
};
