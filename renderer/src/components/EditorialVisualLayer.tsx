import { Easing, interpolate } from "remotion";

import type { EditPlan } from "../schema";

type EditorialVisual = EditPlan["editorial_visuals"][number];
type SceneLayout = EditPlan["scenes"][number]["layout"];

type Props = {
  visual: EditorialVisual | undefined;
  layout: SceneLayout;
  frame: number;
  fps: number;
};

const clampProgress = (frame: number, fps: number, seconds = 0.28) =>
  interpolate(frame, [0, Math.max(1, seconds * fps)], [0, 1], {
    easing: Easing.bezier(0.16, 1, 0.3, 1),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

const panelFrame = (layout: SceneLayout): React.CSSProperties => {
  if (layout === "split-screen") {
    return {
      top: 48,
      left: 48,
      right: 48,
      height: 990,
      borderRadius: 32,
    };
  }
  return {
    inset: 0,
    borderRadius: 0,
  };
};

const GridBackground = ({
  accent,
  frame,
}: {
  accent: string;
  frame: number;
}) => (
  <>
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: `
          radial-gradient(circle at 75% 12%, ${accent}22 0, transparent 34%),
          radial-gradient(circle at 14% 72%, rgba(87,95,255,0.18) 0, transparent 30%),
          linear-gradient(145deg, #090D13 0%, #06080C 58%, #0A1016 100%)
        `,
      }}
    />
    <div
      style={{
        position: "absolute",
        inset: 0,
        opacity: 0.13,
        backgroundImage: `
          linear-gradient(${accent}33 1px, transparent 1px),
          linear-gradient(90deg, ${accent}33 1px, transparent 1px)
        `,
        backgroundSize: "72px 72px",
        backgroundPosition: `${frame * 0.8}px ${frame * 0.45}px`,
        maskImage:
          "linear-gradient(180deg, rgba(0,0,0,0.75), transparent 88%)",
      }}
    />
  </>
);

const Header = ({
  visual,
  progress,
}: {
  visual: EditorialVisual;
  progress: number;
}) => (
  <div
    style={{
      position: "relative",
      zIndex: 2,
      opacity: progress,
      transform: `translateY(${(1 - progress) * -28}px)`,
    }}
  >
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 14,
        color: visual.accent,
        fontFamily: '"IBM Plex Mono", Consolas, monospace',
        fontSize: 22,
        fontWeight: 700,
        letterSpacing: "0.16em",
        textTransform: "uppercase",
      }}
    >
      <span
        style={{
          width: 12,
          height: 12,
          borderRadius: 999,
          background: visual.accent,
          boxShadow: `0 0 22px ${visual.accent}`,
        }}
      />
      Technical breakdown
    </div>
    <div
      style={{
        maxWidth: 920,
        marginTop: 22,
        color: "#FFFFFF",
        fontFamily: '"Inter Tight", Arial, sans-serif',
        fontSize: 72,
        fontWeight: 800,
        letterSpacing: "-0.055em",
        lineHeight: 0.94,
        textTransform: "uppercase",
      }}
    >
      {visual.title}
    </div>
    {visual.subtitle ? (
      <div
        style={{
          maxWidth: 820,
          marginTop: 20,
          color: "rgba(255,255,255,0.68)",
          fontFamily: '"Inter Tight", Arial, sans-serif',
          fontSize: 30,
          fontWeight: 700,
          lineHeight: 1.15,
        }}
      >
        {visual.subtitle}
      </div>
    ) : null}
  </div>
);

const TradingChart = ({
  visual,
  progress,
}: {
  visual: EditorialVisual;
  progress: number;
}) => {
  const candles = [
    [570, 510, 548, 526],
    [532, 472, 490, 514],
    [496, 438, 468, 448],
    [462, 398, 446, 414],
    [430, 384, 404, 418],
    [414, 340, 392, 354],
    [372, 310, 338, 356],
    [350, 286, 324, 298],
    [318, 270, 286, 304],
    [300, 232, 278, 244],
    [270, 218, 238, 254],
    [244, 174, 220, 188],
  ];
  const bearish = visual.direction === "down";
  return (
    <div
      style={{
        position: "absolute",
        zIndex: 2,
        left: 58,
        right: 58,
        top: 470,
        height: 760,
        padding: 28,
        border: "1px solid rgba(255,255,255,0.13)",
        borderRadius: 26,
        background: "rgba(5,8,12,0.86)",
        boxShadow: "0 30px 90px rgba(0,0,0,0.48)",
        opacity: progress,
        transform: `translateY(${(1 - progress) * 34}px)`,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 8px 20px",
          color: "white",
          fontFamily: '"IBM Plex Mono", Consolas, monospace',
        }}
      >
        <div style={{ fontSize: 25, fontWeight: 700 }}>EUR / USD</div>
        <div
          style={{
            color: bearish ? "#FF5D73" : "#55F2A2",
            fontSize: 22,
            fontWeight: 700,
          }}
        >
          SIMULATED PATH • RULE ENGINE ACTIVE
        </div>
      </div>
      <svg viewBox="0 0 900 620" width="100%" height="620">
        {Array.from({ length: 7 }, (_, index) => (
          <line
            key={`h-${index}`}
            x1="0"
            x2="900"
            y1={55 + index * 82}
            y2={55 + index * 82}
            stroke="rgba(255,255,255,0.08)"
            strokeWidth="1"
          />
        ))}
        {Array.from({ length: 10 }, (_, index) => (
          <line
            key={`v-${index}`}
            y1="0"
            y2="620"
            x1={index * 100}
            x2={index * 100}
            stroke="rgba(255,255,255,0.055)"
            strokeWidth="1"
          />
        ))}
        {candles.map((candle, index) => {
          const candleProgress = interpolate(
            progress,
            [index / candles.length, (index + 2) / candles.length],
            [0, 1],
            {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            },
          );
          const [high, low, open, close] = bearish
            ? candle.map((value) => 650 - value)
            : candle;
          const rising = close < open;
          const color = rising ? "#55F2A2" : "#FF5D73";
          const x = 36 + index * 70;
          const bodyTop = Math.min(open, close);
          const bodyHeight = Math.max(10, Math.abs(open - close));
          return (
            <g
              key={x}
              opacity={candleProgress}
              transform={`translate(${(1 - candleProgress) * 14} 0)`}
            >
              <line
                x1={x + 18}
                x2={x + 18}
                y1={high}
                y2={low}
                stroke={color}
                strokeWidth="4"
              />
              <rect
                x={x}
                y={bodyTop}
                width="36"
                height={bodyHeight}
                rx="5"
                fill={color}
              />
            </g>
          );
        })}
        <path
          d={
            bearish
              ? "M 30 130 C 220 150, 320 210, 430 280 S 680 430, 860 520"
              : "M 30 520 C 210 480, 310 400, 430 360 S 670 250, 860 118"
          }
          fill="none"
          stroke={visual.accent}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray="1100"
          strokeDashoffset={1100 * (1 - progress)}
          filter="drop-shadow(0 0 12px rgba(0,229,255,0.48))"
        />
      </svg>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 14,
          marginTop: -14,
        }}
      >
        {visual.items.map((item, index) => (
          <div
            key={item}
            style={{
              padding: "16px 18px",
              borderRadius: 14,
              background:
                index === visual.items.length - 1
                  ? `${visual.accent}18`
                  : "rgba(255,255,255,0.055)",
              color:
                index === visual.items.length - 1
                  ? visual.accent
                  : "rgba(255,255,255,0.66)",
              fontFamily: '"IBM Plex Mono", Consolas, monospace',
              fontSize: 19,
              fontWeight: 700,
              textAlign: "center",
            }}
          >
            {item}
          </div>
        ))}
      </div>
    </div>
  );
};

const RuleFlow = ({
  visual,
  progress,
}: {
  visual: EditorialVisual;
  progress: number;
}) => (
  <div
    style={{
      position: "absolute",
      zIndex: 2,
      left: 54,
      right: 430,
      top: 500,
      display: "grid",
      gap: 34,
      opacity: progress,
    }}
  >
    {visual.items.map((item, index) => {
      const itemProgress = interpolate(
        progress,
        [index * 0.16, Math.min(1, index * 0.16 + 0.48)],
        [0, 1],
        {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        },
      );
      return (
        <div key={item} style={{ position: "relative" }}>
          <div
            style={{
              padding: "30px 34px",
              border: `2px solid ${index === 1 ? visual.accent : "rgba(255,255,255,0.16)"}`,
              borderRadius: 22,
              background:
                index === 1
                  ? `${visual.accent}13`
                  : "rgba(255,255,255,0.045)",
              color: index === 1 ? visual.accent : "#FFFFFF",
              fontFamily: '"IBM Plex Mono", Consolas, monospace',
              fontSize: 27,
              fontWeight: 700,
              letterSpacing: "0.04em",
              opacity: itemProgress,
              transform: `translateX(${(1 - itemProgress) * -38}px)`,
              boxShadow:
                index === 1 ? `0 0 42px ${visual.accent}18` : undefined,
            }}
          >
            <span
              style={{
                marginRight: 18,
                color: "rgba(255,255,255,0.38)",
              }}
            >
              0{index + 1}
            </span>
            {item}
          </div>
          {index < visual.items.length - 1 ? (
            <div
              style={{
                width: 3,
                height: 34,
                marginLeft: 58,
                background: visual.accent,
                opacity: itemProgress,
              }}
            />
          ) : null}
        </div>
      );
    })}
  </div>
);

const CodeTerminal = ({
  visual,
  progress,
}: {
  visual: EditorialVisual;
  progress: number;
}) => (
  <div
    style={{
      position: "absolute",
      zIndex: 2,
      left: 58,
      right: 58,
      top: 470,
      padding: "0 0 34px",
      overflow: "hidden",
      border: "1px solid rgba(255,255,255,0.15)",
      borderRadius: 24,
      background: "rgba(3,6,10,0.94)",
      boxShadow: "0 30px 90px rgba(0,0,0,0.55)",
      opacity: progress,
      transform: `scale(${0.96 + progress * 0.04})`,
    }}
  >
    <div
      style={{
        padding: "18px 24px",
        borderBottom: "1px solid rgba(255,255,255,0.1)",
        color: "#FF6A76",
        fontFamily: '"IBM Plex Mono", Consolas, monospace',
        fontSize: 18,
        letterSpacing: "0.24em",
      }}
    >
      ● ● ●{" "}
      <span style={{ color: "rgba(255,255,255,0.45)" }}>
        ILLUSTRATIVE LOGIC
      </span>
    </div>
    <div
      style={{
        display: "grid",
        gap: 22,
        padding: "42px 38px",
        fontFamily: '"IBM Plex Mono", Consolas, monospace',
        fontSize: 29,
        lineHeight: 1.35,
      }}
    >
      {visual.items.map((line, index) => {
        const lineProgress = interpolate(
          progress,
          [index * 0.18, Math.min(1, index * 0.18 + 0.5)],
          [0, 1],
          {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          },
        );
        return (
          <div
            key={line}
            style={{
              display: "grid",
              gridTemplateColumns: "38px 1fr",
              gap: 18,
              opacity: lineProgress,
            }}
          >
            <span style={{ color: "rgba(255,255,255,0.22)" }}>
              {index + 1}
            </span>
            <span style={{ color: index === 1 ? visual.accent : "#D8E1EA" }}>
              {line}
            </span>
          </div>
        );
      })}
      <div style={{ color: visual.accent }}>
        <span style={{ opacity: 0.55 }}>&gt;</span> RUNNING_
      </div>
    </div>
  </div>
);

const EvidenceCard = ({
  visual,
  progress,
}: {
  visual: EditorialVisual;
  progress: number;
}) => (
  <div
    style={{
      position: "absolute",
      zIndex: 2,
      left: 70,
      right: 70,
      top: 500,
      padding: 42,
      borderRadius: 30,
      background: "#F4F1E8",
      color: "#101318",
      boxShadow: "0 34px 100px rgba(0,0,0,0.5)",
      opacity: progress,
      transform: `rotate(${(1 - progress) * -2.2}deg) translateY(${(1 - progress) * 40}px)`,
    }}
  >
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        borderBottom: "3px solid #11151B",
        paddingBottom: 28,
      }}
    >
      <div
        style={{
          maxWidth: 650,
          fontFamily: '"Inter Tight", Arial, sans-serif',
          fontSize: 50,
          fontWeight: 800,
          letterSpacing: "-0.045em",
          lineHeight: 0.95,
        }}
      >
        AUTOMATED TRADING
        <br />
        CHAMPIONSHIP
      </div>
      <div
        style={{
          padding: "12px 16px",
          border: "2px solid #11151B",
          fontFamily: '"IBM Plex Mono", Consolas, monospace',
          fontSize: 28,
          fontWeight: 700,
        }}
      >
        {visual.value ?? "CASE"}
      </div>
    </div>
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1.25fr 0.75fr",
        gap: 30,
        marginTop: 34,
      }}
    >
      <div>
        <div
          style={{
            fontFamily: '"IBM Plex Mono", Consolas, monospace',
            fontSize: 18,
            lineHeight: 1.55,
            color: "#3A414A",
          }}
        >
          ILLUSTRATIVE EDITORIAL SUMMARY
        </div>
        <div
          style={{
            marginTop: 24,
            fontFamily: '"Inter Tight", Arial, sans-serif',
            fontSize: 34,
            fontWeight: 750,
            lineHeight: 1.12,
          }}
        >
          {visual.title}
          <div
            style={{
              marginTop: 14,
              color: "#4A5561",
              fontFamily: '"IBM Plex Mono", Consolas, monospace',
              fontSize: 19,
              fontWeight: 400,
              letterSpacing: "0",
            }}
          >
            {visual.subtitle}
          </div>
        </div>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 12,
            marginTop: 34,
          }}
        >
          {visual.items.map((item) => (
            <span
              key={item}
              style={{
                padding: "10px 14px",
                border: "1px solid #7E8792",
                fontFamily: '"IBM Plex Mono", Consolas, monospace',
                fontSize: 17,
                fontWeight: 700,
              }}
            >
              {item}
            </span>
          ))}
        </div>
      </div>
      <div
        style={{
          display: "grid",
          placeItems: "center",
          minHeight: 300,
          background:
            "repeating-linear-gradient(135deg, #11151B 0 12px, #26303A 12px 24px)",
          color: visual.accent,
          fontFamily: '"IBM Plex Mono", Consolas, monospace',
          fontSize: 70,
          fontWeight: 700,
        }}
      >
        {visual.value ?? "DATA"}
      </div>
    </div>
  </div>
);

const MetricReveal = ({
  visual,
  progress,
}: {
  visual: EditorialVisual;
  progress: number;
}) => (
  <div
    style={{
      position: "absolute",
      zIndex: 2,
      inset: "500px 64px auto",
      textAlign: "center",
      opacity: progress,
    }}
  >
    <div
      style={{
        color: visual.accent,
        fontFamily: '"IBM Plex Mono", Consolas, monospace',
        fontSize: 22,
        fontWeight: 700,
        letterSpacing: "0.2em",
      }}
    >
      PEAK RESULT
    </div>
    <div
      style={{
        marginTop: 22,
        color: "#FFFFFF",
        fontFamily: '"Inter Tight", Arial, sans-serif',
        fontSize: 154,
        fontWeight: 800,
        letterSpacing: "-0.075em",
        lineHeight: 0.92,
        transform: `scale(${0.78 + progress * 0.22})`,
        textShadow: `0 0 58px ${visual.accent}35`,
      }}
    >
      {visual.value ?? "RESULT"}
    </div>
    <div
      style={{
        width: `${progress * 82}%`,
        height: 10,
        margin: "36px auto 0",
        borderRadius: 999,
        background: visual.accent,
        boxShadow: `0 0 30px ${visual.accent}88`,
      }}
    />
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: 14,
        marginTop: 44,
      }}
    >
      {visual.items.map((item) => (
        <div
          key={item}
          style={{
            padding: "20px 12px",
            border: "1px solid rgba(255,255,255,0.13)",
            borderRadius: 16,
            background: "rgba(255,255,255,0.045)",
            color: "rgba(255,255,255,0.75)",
            fontFamily: '"IBM Plex Mono", Consolas, monospace',
            fontSize: 18,
            fontWeight: 700,
          }}
        >
          {item}
        </div>
      ))}
    </div>
  </div>
);

const RiskMeter = ({
  visual,
  progress,
}: {
  visual: EditorialVisual;
  progress: number;
}) => {
  const risk = visual.direction === "down" ? 0.84 : 0.68;
  const riskLabel =
    visual.value ||
    (visual.direction === "down" ? "AGGRESSIVE" : "CONTROLLED");
  return (
    <div
      style={{
        position: "absolute",
        zIndex: 2,
        left: 64,
        right: 64,
        top: 500,
        padding: 42,
        border: "1px solid rgba(255,255,255,0.13)",
        borderRadius: 30,
        background: "rgba(6,9,13,0.9)",
        opacity: progress,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "space-between",
        }}
      >
        <div>
          <div
            style={{
              color: "#FF657A",
              fontFamily: '"IBM Plex Mono", Consolas, monospace',
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: "0.16em",
            }}
          >
            RISK EXPOSURE
          </div>
          <div
            style={{
              marginTop: 12,
              color: "#FFFFFF",
              fontFamily: '"Inter Tight", Arial, sans-serif',
              fontSize: 88,
              fontWeight: 800,
              letterSpacing: "-0.06em",
            }}
          >
            {riskLabel}
          </div>
        </div>
        <div
          style={{
            color: "#FF657A",
            fontFamily: '"IBM Plex Mono", Consolas, monospace',
            fontSize: 32,
            fontWeight: 700,
          }}
        >
          ILLUSTRATIVE
        </div>
      </div>
      <div
        style={{
          height: 32,
          marginTop: 34,
          overflow: "hidden",
          borderRadius: 999,
          background: "rgba(255,255,255,0.08)",
        }}
      >
        <div
          style={{
            width: `${risk * progress * 100}%`,
            height: "100%",
            borderRadius: 999,
            background:
              "linear-gradient(90deg, #55F2A2 0%, #FFF078 48%, #FF5D73 100%)",
            boxShadow: "0 0 28px rgba(255,93,115,0.48)",
          }}
        />
      </div>
      <svg
        viewBox="0 0 900 340"
        width="100%"
        height="340"
        style={{ marginTop: 34 }}
      >
        <defs>
          <linearGradient id="risk-fill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#FF5D73" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#FF5D73" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path
          d="M 10 70 C 150 92, 230 40, 330 92 S 500 135, 590 125 S 735 220, 890 300 L 890 340 L 10 340 Z"
          fill="url(#risk-fill)"
          opacity={progress}
        />
        <path
          d="M 10 70 C 150 92, 230 40, 330 92 S 500 135, 590 125 S 735 220, 890 300"
          fill="none"
          stroke="#FF5D73"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray="1200"
          strokeDashoffset={1200 * (1 - progress)}
        />
      </svg>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 14,
        }}
      >
        {visual.items.map((item, index) => (
          <div
            key={item}
            style={{
              padding: "16px",
              borderRadius: 14,
              background:
                index === visual.items.length - 1
                  ? "rgba(255,93,115,0.12)"
                  : "rgba(255,255,255,0.045)",
              color:
                index === visual.items.length - 1
                  ? "#FF657A"
                  : "rgba(255,255,255,0.65)",
              fontFamily: '"IBM Plex Mono", Consolas, monospace',
              fontSize: 18,
              fontWeight: 700,
              textAlign: "center",
            }}
          >
            {item}
          </div>
        ))}
      </div>
    </div>
  );
};

const Comparison = ({
  visual,
  progress,
}: {
  visual: EditorialVisual;
  progress: number;
}) => (
  <div
    style={{
      position: "absolute",
      zIndex: 2,
      left: 58,
      right: 58,
      top: 510,
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: 22,
      opacity: progress,
    }}
  >
    {[
      {
        title: "HUMAN EMOTION",
        color: "#FF657A",
        points: ["FEAR", "GREED", "HESITATION"],
      },
      {
        title: "FIXED RULES",
        color: visual.accent,
        points: visual.items,
      },
    ].map((column, columnIndex) => (
      <div
        key={column.title}
        style={{
          minHeight: 560,
          padding: 30,
          border: `2px solid ${column.color}55`,
          borderRadius: 26,
          background: `${column.color}0D`,
          transform: `translateX(${(1 - progress) * (columnIndex ? 36 : -36)}px)`,
        }}
      >
        <div
          style={{
            color: column.color,
            fontFamily: '"IBM Plex Mono", Consolas, monospace',
            fontSize: 21,
            fontWeight: 700,
            letterSpacing: "0.12em",
          }}
        >
          {column.title}
        </div>
        <div
          style={{
            width: 76,
            height: 8,
            marginTop: 22,
            borderRadius: 999,
            background: column.color,
          }}
        />
        <div style={{ display: "grid", gap: 18, marginTop: 48 }}>
          {column.points.map((point, index) => (
            <div
              key={point}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 14,
                padding: "18px 16px",
                borderRadius: 14,
                background: "rgba(255,255,255,0.055)",
                color: "#FFFFFF",
                fontFamily: '"Inter Tight", Arial, sans-serif',
                fontSize: 25,
                fontWeight: 750,
              }}
            >
              <span style={{ color: column.color }}>
                {columnIndex ? "✓" : index === 2 ? "?" : "×"}
              </span>
              {point}
            </div>
          ))}
        </div>
      </div>
    ))}
  </div>
);

const ChatCta = ({
  visual,
  progress,
}: {
  visual: EditorialVisual;
  progress: number;
}) => (
  <div
    style={{
      position: "absolute",
      zIndex: 2,
      left: 170,
      right: 170,
      top: 490,
      minHeight: 720,
      padding: "24px 24px 36px",
      border: "2px solid rgba(255,255,255,0.16)",
      borderRadius: 48,
      background: "#0C1219",
      boxShadow: "0 34px 100px rgba(0,0,0,0.56)",
      opacity: progress,
      transform: `translateY(${(1 - progress) * 52}px) scale(${0.94 + progress * 0.06})`,
    }}
  >
    <div
      style={{
        width: 100,
        height: 9,
        margin: "0 auto 28px",
        borderRadius: 999,
        background: "rgba(255,255,255,0.24)",
      }}
    />
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 18,
        padding: "18px 16px 26px",
        borderBottom: "1px solid rgba(255,255,255,0.1)",
      }}
    >
      <div
        style={{
          display: "grid",
          placeItems: "center",
          width: 64,
          height: 64,
          borderRadius: 999,
          background: visual.accent,
          color: "#071018",
          fontSize: 32,
          fontWeight: 900,
        }}
      >
        ↗
      </div>
      <div>
        <div
          style={{
            color: "#FFFFFF",
            fontFamily: '"Inter Tight", Arial, sans-serif',
            fontSize: 30,
            fontWeight: 800,
          }}
        >
          LIVE EA UPDATES
        </div>
        <div
          style={{
            marginTop: 5,
            color: visual.accent,
            fontFamily: '"IBM Plex Mono", Consolas, monospace',
            fontSize: 17,
          }}
        >
          EDUCATIONAL UPDATES • LIVE
        </div>
      </div>
    </div>
    <div style={{ display: "grid", gap: 18, padding: "32px 12px" }}>
      {visual.items.map((item, index) => (
        <div
          key={item}
          style={{
            width: index === 1 ? "76%" : "88%",
            marginLeft: index === 1 ? "auto" : 0,
            padding: "20px 22px",
            borderRadius: index === 1 ? "22px 22px 6px 22px" : "22px 22px 22px 6px",
            background:
              index === 1
                ? `${visual.accent}1E`
                : "rgba(255,255,255,0.07)",
            color: "#FFFFFF",
            fontFamily: '"IBM Plex Mono", Consolas, monospace',
            fontSize: 21,
            fontWeight: 700,
            opacity: interpolate(
              progress,
              [index * 0.18, Math.min(1, index * 0.18 + 0.45)],
              [0, 1],
              {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              },
            ),
          }}
        >
          {item}
        </div>
      ))}
    </div>
    <div
      style={{
        margin: "8px 12px 0",
        padding: "20px",
        borderRadius: 999,
        background: visual.accent,
        color: "#071018",
        fontFamily: '"Inter Tight", Arial, sans-serif',
        fontSize: 28,
        fontWeight: 850,
        textAlign: "center",
      }}
    >
      JOIN TELEGRAM GROUP
    </div>
  </div>
);

export const findEditorialVisual = (
  visuals: EditPlan["editorial_visuals"],
  visualId: string | null,
) =>
  visualId == null
    ? undefined
    : visuals.find((candidate) => candidate.id === visualId);

export const EditorialVisualLayer: React.FC<Props> = ({
  visual,
  layout,
  frame,
  fps,
}) => {
  if (!visual) {
    return null;
  }
  const progress = clampProgress(frame, fps);
  const content = (() => {
    switch (visual.kind) {
      case "trading-chart":
        return <TradingChart visual={visual} progress={progress} />;
      case "rule-flow":
        return <RuleFlow visual={visual} progress={progress} />;
      case "code-terminal":
        return <CodeTerminal visual={visual} progress={progress} />;
      case "evidence-card":
        return <EvidenceCard visual={visual} progress={progress} />;
      case "metric-reveal":
        return <MetricReveal visual={visual} progress={progress} />;
      case "risk-meter":
        return <RiskMeter visual={visual} progress={progress} />;
      case "comparison":
        return <Comparison visual={visual} progress={progress} />;
      case "chat-cta":
        return <ChatCta visual={visual} progress={progress} />;
    }
  })();

  return (
    <div
      data-editorial-visual={visual.kind}
      style={{
        position: "absolute",
        zIndex: 18,
        overflow: "hidden",
        ...panelFrame(layout),
      }}
    >
      <GridBackground accent={visual.accent} frame={frame} />
      <div
        style={{
          position: "absolute",
          inset: layout === "split-screen" ? "42px 42px auto" : "106px 64px auto",
        }}
      >
        <Header visual={visual} progress={progress} />
      </div>
      {content}
      <div
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          boxShadow:
            layout === "split-screen"
              ? "inset 0 0 0 1px rgba(255,255,255,0.08)"
              : "inset 0 -260px 180px rgba(0,0,0,0.16)",
        }}
      />
    </div>
  );
};
